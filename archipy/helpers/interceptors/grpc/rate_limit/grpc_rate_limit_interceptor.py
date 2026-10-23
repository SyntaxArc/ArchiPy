"""gRPC server interceptors that enforce decorator-declared Redis rate limits."""

from __future__ import annotations

import asyncio
import inspect
import logging
from math import ceil
from typing import TYPE_CHECKING, Any

from archipy.configs.base_config import BaseConfig
from archipy.helpers.errors.grpc.abort import abort_grpc
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.interceptors.grpc.rate_limit.identifiers import (
    invocation_metadata_to_dict,
    resolve_jwt_access_token_sub_from_metadata,
)
from archipy.helpers.utils.rate_limit_utils import RateLimitUtils
from archipy.models.errors import RateLimitExceededError, UnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import grpc

    from archipy.configs.config_template import GrpcRateLimitConfig
    from archipy.helpers.interceptors.grpc.rate_limit.stores import AsyncRateLimitStore, RateLimitStore
    from archipy.models.dtos.rate_limit_window_dto import RateLimitWindowDTO

logger = logging.getLogger(__name__)

_FORWARDED_FOR_HEADER = "x-forwarded-for"


class _GrpcRateLimitInterceptorMixin:
    """Shared configuration and helpers for sync and async gRPC rate-limit interceptors."""

    _identifier_fn: Callable[..., object] | None = None

    def __init__(
        self,
        *,
        rate_limit_config: GrpcRateLimitConfig | None = None,
        key_prefix: str | None = None,
        fail_closed: bool | None = None,
        skip_methods: frozenset[str] | None = None,
        identity_from_access_token: bool | None = None,
        trusted_proxy_hosts: frozenset[str] | None = None,
    ) -> None:
        """Initialize global rate-limit settings for the interceptor.

        Args:
            rate_limit_config: Rate-limit settings. When None, ``GRPC_RATE_LIMIT`` from global config is used.
            key_prefix: Override for ``GRPC_RATE_LIMIT.KEY_PREFIX``.
            fail_closed: Override for ``GRPC_RATE_LIMIT.FAIL_CLOSED``.
            skip_methods: Full gRPC method names excluded from rate limiting.
            identity_from_access_token: Override for ``GRPC_RATE_LIMIT.IDENTITY_FROM_ACCESS_TOKEN``.
            trusted_proxy_hosts: Peer hosts (load balancers, ingress) whose ``x-forwarded-for`` header is trusted.
                When the direct peer is in this set, the client address comes from the header instead of the
                proxy address, so callers behind the proxy no longer share one rate-limit bucket.
        """
        resolved_rate_limit_config = rate_limit_config or BaseConfig.global_config().GRPC_RATE_LIMIT
        app_config = BaseConfig.global_config()

        resolved_key_prefix = key_prefix if key_prefix is not None else resolved_rate_limit_config.KEY_PREFIX
        serve_host = app_config.GRPC.SERVE_HOST.replace("[", "").replace("]", "")
        self._key_prefix = resolved_key_prefix or f"{serve_host}:RateLimit"
        self._fail_closed = fail_closed if fail_closed is not None else resolved_rate_limit_config.FAIL_CLOSED
        resolved_skip_methods = (
            skip_methods if skip_methods is not None else frozenset(resolved_rate_limit_config.SKIP_METHODS)
        )
        self._skip_methods = resolved_skip_methods
        self._identity_from_access_token = (
            identity_from_access_token
            if identity_from_access_token is not None
            else resolved_rate_limit_config.IDENTITY_FROM_ACCESS_TOKEN
        )
        self._trusted_proxy_hosts = trusted_proxy_hosts or frozenset()
        self._windows_by_method: dict[str, tuple[RateLimitWindowDTO, ...]] = {}

    @staticmethod
    def _full_method_name(method_name_model: MethodName) -> str:
        """Return the canonical full gRPC method name with a leading slash."""
        if method_name_model.full_name.startswith("/"):
            return method_name_model.full_name
        return f"/{method_name_model.full_name}"

    @staticmethod
    def _retry_after_seconds(pexpire: int, window_ms: int) -> int:
        """Convert a PTTL value to a safe retry delay in seconds."""
        if pexpire > 0:
            return max(1, ceil(pexpire / 1000))
        return max(1, ceil(window_ms / 1000))

    @staticmethod
    def _parse_peer(peer: str | None) -> str:
        """Parse ``ServicerContext.peer()`` into a host identifier.

        Args:
            peer: Peer string such as ``ipv4:1.2.3.4:5678``.

        Returns:
            Parsed host, the raw peer string, or ``unknown`` when missing.
        """
        if not peer:
            return "unknown"

        if peer.startswith("ipv4:"):
            host_port = peer.removeprefix("ipv4:")
            if ":" in host_port:
                return host_port.rsplit(":", maxsplit=1)[0]
            return host_port

        if peer.startswith("ipv6:"):
            host_port = peer.removeprefix("ipv6:")
            if host_port.startswith("[") and "]" in host_port:
                return host_port[1 : host_port.index("]")]
            if ":" in host_port:
                return host_port.rsplit(":", maxsplit=1)[0]
            return host_port

        if peer.startswith("unix:"):
            return peer.removeprefix("unix:")

        return peer

    def _windows_for(self, method: Callable[..., Any], method_name_model: MethodName) -> tuple[RateLimitWindowDTO, ...]:
        """Return the rate-limit windows declared on ``method``, validated once per RPC method."""
        full_method = self._full_method_name(method_name_model)
        windows = self._windows_by_method.get(full_method)
        if windows is None:
            windows = RateLimitUtils.get_rate_limit_windows_from_callable(method)
            self._windows_by_method[full_method] = windows
        return windows

    def _peer_identity(self, context: grpc.ServicerContext | grpc.aio.ServicerContext) -> str:
        """Return the client host, honouring ``x-forwarded-for`` only when the direct peer is a trusted proxy."""
        peer_host = self._parse_peer(context.peer())
        if peer_host not in self._trusted_proxy_hosts:
            return peer_host
        metadata = context.invocation_metadata()
        forwarded = invocation_metadata_to_dict(list(metadata) if metadata is not None else []).get(
            _FORWARDED_FOR_HEADER,
        )
        if not forwarded:
            return peer_host
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        # Walk from the proxy side: the first hop that is not itself a trusted proxy is the real client.
        for hop in reversed(hops):
            if hop not in self._trusted_proxy_hosts:
                return hop
        return hops[0] if hops else peer_host

    def _build_rate_limit_key(self, identity: str, method_name_model: MethodName, window: RateLimitWindowDTO) -> str:
        """Build the Redis key for one rate-limit window tier."""
        full_method = self._full_method_name(method_name_model)
        return f"{self._key_prefix}:{identity}:{full_method}:{window.key_suffix}"

    def _resolve_identity(self, context: grpc.ServicerContext, method_name_model: MethodName) -> str | None:
        """Resolve the server-side rate-limit identity for an RPC.

        Returns:
            The identity, or ``None`` when a custom ``identifier_fn`` failed and the limiter is fail-open. In that
            case the call is not limited, instead of pooling every such caller into one shared bucket.
        """
        if self._identifier_fn is not None:
            try:
                return str(self._identifier_fn(context, method_name_model))
            except Exception as exc:
                if self._fail_closed:
                    abort_grpc(
                        UnavailableError(additional_data={"detail": "Rate limiter identity resolution failed"}),
                        context,
                    )
                    raise RuntimeError("unreachable") from exc
                logger.warning("Rate limiter identity resolution failed; the call is not rate limited", exc_info=True)
                return None

        if self._identity_from_access_token:
            metadata = context.invocation_metadata()
            metadata_items = list(metadata) if metadata is not None else []
            if user_sub := resolve_jwt_access_token_sub_from_metadata(metadata_items):
                return user_sub

        return self._peer_identity(context)

    async def _resolve_identity_async(
        self,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> str | None:
        """Resolve the server-side rate-limit identity for an async RPC (``None`` means do not limit)."""
        if self._identifier_fn is not None:
            try:
                result = self._identifier_fn(context, method_name_model)
                if inspect.isawaitable(result):
                    result = await result
                return str(result)
            except Exception as exc:
                if self._fail_closed:
                    await abort_grpc(
                        UnavailableError(additional_data={"detail": "Rate limiter identity resolution failed"}),
                        context,
                    )
                    raise RuntimeError("unreachable") from exc
                logger.warning("Rate limiter identity resolution failed; the call is not rate limited", exc_info=True)
                return None

        if self._identity_from_access_token:
            metadata = context.invocation_metadata()
            metadata_items = list(metadata) if metadata is not None else []
            # Signature verification is CPU bound; keep it off the event loop.
            user_sub = await asyncio.to_thread(resolve_jwt_access_token_sub_from_metadata, metadata_items)
            if user_sub:
                return user_sub

        return self._peer_identity(context)

    def _abort_rate_limited_sync(self, context: grpc.ServicerContext, window: RateLimitWindowDTO, pexpire: int) -> None:
        """Abort a sync RPC with RESOURCE_EXHAUSTED when a window is breached."""
        abort_grpc(
            RateLimitExceededError(
                retry_after=self._retry_after_seconds(pexpire, window.window_ms),
                additional_data={
                    "limit": window.calls_count,
                    "window_ms": window.window_ms,
                    "remaining": 0,
                },
            ),
            context,
        )

    async def _abort_rate_limited_async(
        self,
        context: grpc.aio.ServicerContext,
        window: RateLimitWindowDTO,
        pexpire: int,
    ) -> None:
        """Abort an async RPC with RESOURCE_EXHAUSTED when a window is breached."""
        await abort_grpc(
            RateLimitExceededError(
                retry_after=self._retry_after_seconds(pexpire, window.window_ms),
                additional_data={
                    "limit": window.calls_count,
                    "window_ms": window.window_ms,
                    "remaining": 0,
                },
            ),
            context,
        )

    def _abort_unavailable_sync(self, context: grpc.ServicerContext, *, detail: str) -> None:
        """Abort a sync RPC when the rate limiter backend is unavailable."""
        abort_grpc(UnavailableError(additional_data={"detail": detail}), context)

    async def _abort_unavailable_async(self, context: grpc.aio.ServicerContext, *, detail: str) -> None:
        """Abort an async RPC when the rate limiter backend is unavailable."""
        await abort_grpc(UnavailableError(additional_data={"detail": detail}), context)

    @staticmethod
    async def _invoke_maybe_async_handler(method: Callable[..., Any], request: object, context: object) -> object:
        """Invoke a gRPC handler and await the result when it is awaitable."""
        result = method(request, context)
        if inspect.isawaitable(result):
            return await result
        return result


class GrpcServerRateLimitInterceptor(_GrpcRateLimitInterceptorMixin, BaseGrpcServerInterceptor):
    """Sync gRPC server interceptor for decorator-declared Redis rate limits."""

    def __init__(
        self,
        *,
        rate_limit_config: GrpcRateLimitConfig | None = None,
        key_prefix: str | None = None,
        fail_closed: bool | None = None,
        skip_methods: frozenset[str] | None = None,
        identifier_fn: Callable[[grpc.ServicerContext, MethodName], str] | None = None,
        identity_from_access_token: bool | None = None,
        trusted_proxy_hosts: frozenset[str] | None = None,
        store: RateLimitStore | None = None,
        store_errors: tuple[type[BaseException], ...] = (),
    ) -> None:
        """Initialize the sync gRPC rate-limit interceptor.

        Args:
            rate_limit_config: Rate-limit settings. When None, ``GRPC_RATE_LIMIT`` from global config is used.
            key_prefix: Override for ``GRPC_RATE_LIMIT.KEY_PREFIX``.
            fail_closed: Override for ``GRPC_RATE_LIMIT.FAIL_CLOSED``.
            skip_methods: Full gRPC method names excluded from rate limiting.
            identifier_fn: Custom identity resolver for an RPC.
            identity_from_access_token: Override for ``GRPC_RATE_LIMIT.IDENTITY_FROM_ACCESS_TOKEN``.
            trusted_proxy_hosts: Peer hosts whose ``x-forwarded-for`` header is trusted.
            store: Counter store. When None, a ``RedisAdapter`` built from the global config is used.
            store_errors: Exception types of ``store`` that mean the backend is unavailable, besides the connection,
                OS and timeout errors every store may raise. They follow the ``fail_closed`` setting.
        """
        super().__init__(
            rate_limit_config=rate_limit_config,
            key_prefix=key_prefix,
            fail_closed=fail_closed,
            skip_methods=skip_methods,
            identity_from_access_token=identity_from_access_token,
            trusted_proxy_hosts=trusted_proxy_hosts,
        )
        self._identifier_fn = identifier_fn
        if store is None:
            store, default_errors = self._create_default_store()
            store_errors = (*default_errors, *store_errors)
        self._store: RateLimitStore = store
        self._unavailable_errors = (ConnectionError, OSError, TimeoutError, *store_errors)

    @staticmethod
    def _create_default_store() -> tuple[RateLimitStore, tuple[type[BaseException], ...]]:
        """Build the default Redis store and the Redis errors that mean it is unavailable."""
        from redis.exceptions import RedisError  # noqa: PLC0415

        from archipy.adapters.redis.adapters import RedisAdapter  # noqa: PLC0415

        return RedisAdapter(), (RedisError,)

    def _check(self, key: str, window: RateLimitWindowDTO) -> tuple[int, int]:
        """Increment the rate-limit counter and return limit state."""
        new_value, applied = self._store.increx(
            key,
            byint=1,
            ubound=window.calls_count,
            saturate=True,
            px=window.window_ms,
            enx=True,
        )
        if applied:
            remaining = max(0, window.calls_count - int(new_value))
            return 0, remaining
        return self._store.pttl(key), 0

    def _refund(self, keys: Sequence[str]) -> None:
        """Give back the quota consumed in earlier windows by a call that a later window rejected."""
        for key in keys:
            try:
                self._store.increx(key, byint=-1, lbound=0, saturate=True)
            except self._unavailable_errors:
                logger.debug("Could not refund rate-limit quota for %s", key, exc_info=True)

    def intercept(
        self,
        method: Callable[..., Any],
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Enforce stacked rate-limit windows before invoking the RPC handler."""
        windows = self._windows_for(method, method_name_model)
        if not windows:
            return method(request, context)

        full_method = self._full_method_name(method_name_model)
        if full_method in self._skip_methods:
            return method(request, context)

        identity = self._resolve_identity(context, method_name_model)
        if identity is None:
            return method(request, context)

        consumed: list[str] = []
        for window in windows:
            key = self._build_rate_limit_key(identity, method_name_model, window)
            try:
                pexpire, _remaining = self._check(key, window)
            except self._unavailable_errors as exc:
                if self._fail_closed:
                    self._abort_unavailable_sync(context, detail="Rate limiter unavailable")
                    raise RuntimeError("unreachable") from exc
                return method(request, context)

            if pexpire != 0:
                self._refund(consumed)
                self._abort_rate_limited_sync(context, window, pexpire)
                raise RuntimeError("unreachable")
            consumed.append(key)

        return method(request, context)


class AsyncGrpcServerRateLimitInterceptor(_GrpcRateLimitInterceptorMixin, BaseAsyncGrpcServerInterceptor):
    """Async gRPC server interceptor for decorator-declared Redis rate limits."""

    def __init__(
        self,
        *,
        rate_limit_config: GrpcRateLimitConfig | None = None,
        key_prefix: str | None = None,
        fail_closed: bool | None = None,
        skip_methods: frozenset[str] | None = None,
        identifier_fn: Callable[[grpc.aio.ServicerContext, MethodName], str] | None = None,
        identity_from_access_token: bool | None = None,
        trusted_proxy_hosts: frozenset[str] | None = None,
        store: AsyncRateLimitStore | None = None,
        store_errors: tuple[type[BaseException], ...] = (),
    ) -> None:
        """Initialize the async gRPC rate-limit interceptor.

        Takes the same arguments as :class:`GrpcServerRateLimitInterceptor`, except that ``store`` is an
        :class:`AsyncRateLimitStore` and defaults to an ``AsyncRedisAdapter`` built from the global config.
        """
        super().__init__(
            rate_limit_config=rate_limit_config,
            key_prefix=key_prefix,
            fail_closed=fail_closed,
            skip_methods=skip_methods,
            identity_from_access_token=identity_from_access_token,
            trusted_proxy_hosts=trusted_proxy_hosts,
        )
        self._identifier_fn = identifier_fn
        if store is None:
            store, default_errors = self._create_default_store()
            store_errors = (*default_errors, *store_errors)
        self._store: AsyncRateLimitStore = store
        self._unavailable_errors = (ConnectionError, OSError, TimeoutError, *store_errors)

    @staticmethod
    def _create_default_store() -> tuple[AsyncRateLimitStore, tuple[type[BaseException], ...]]:
        """Build the default async Redis store and the Redis errors that mean it is unavailable."""
        from redis.exceptions import RedisError  # noqa: PLC0415

        from archipy.adapters.redis.adapters import AsyncRedisAdapter  # noqa: PLC0415

        return AsyncRedisAdapter(), (RedisError,)

    async def _check(self, key: str, window: RateLimitWindowDTO) -> tuple[int, int]:
        """Increment the rate-limit counter and return limit state."""
        new_value, applied = await self._store.increx(
            key,
            byint=1,
            ubound=window.calls_count,
            saturate=True,
            px=window.window_ms,
            enx=True,
        )
        if applied:
            remaining = max(0, window.calls_count - int(new_value))
            return 0, remaining
        return await self._store.pttl(key), 0

    async def _refund(self, keys: Sequence[str]) -> None:
        """Give back the quota consumed in earlier windows by a call that a later window rejected."""
        for key in keys:
            try:
                await self._store.increx(key, byint=-1, lbound=0, saturate=True)
            except self._unavailable_errors:
                logger.debug("Could not refund rate-limit quota for %s", key, exc_info=True)

    async def _enforce_rate_limit_windows_async(
        self,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
        windows: Sequence[RateLimitWindowDTO],
    ) -> None:
        """Enforce rate-limit windows, aborting the call when one is breached.

        Returns once the call may proceed, including when the limiter is fail-open and Redis is unavailable.
        """
        identity = await self._resolve_identity_async(context, method_name_model)
        if identity is None:
            return

        consumed: list[str] = []
        for window in windows:
            key = self._build_rate_limit_key(identity, method_name_model, window)
            try:
                pexpire, _remaining = await self._check(key, window)
            except self._unavailable_errors as exc:
                if self._fail_closed:
                    await self._abort_unavailable_async(context, detail="Rate limiter unavailable")
                    raise RuntimeError("unreachable") from exc
                return

            if pexpire != 0:
                await self._refund(consumed)
                await self._abort_rate_limited_async(context, window, pexpire)
                raise RuntimeError("unreachable")
            consumed.append(key)

    async def intercept(
        self,
        method: Callable[..., Any],
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Enforce stacked rate-limit windows before invoking the async RPC handler."""
        windows = self._windows_for(method, method_name_model)
        full_method = self._full_method_name(method_name_model)
        if windows and full_method not in self._skip_methods:
            await self._enforce_rate_limit_windows_async(context, method_name_model, windows)

        return await self._invoke_maybe_async_handler(method, request, context)
