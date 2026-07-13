"""gRPC server interceptors that enforce decorator-declared Redis rate limits."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from math import ceil
from typing import TYPE_CHECKING

import grpc

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import GrpcRateLimitConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.interceptors.grpc.rate_limit.identifiers import resolve_jwt_access_token_sub_from_metadata
from archipy.helpers.utils.rate_limit_utils import RateLimitUtils
from archipy.models.dtos.rate_limit_window_dto import RateLimitWindowDTO
from archipy.models.errors import RateLimitExceededError, UnavailableError

if TYPE_CHECKING:
    from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter


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
    ) -> None:
        """Initialize global rate-limit settings for the interceptor.

        Args:
            rate_limit_config: Rate-limit settings. When None, ``GRPC_RATE_LIMIT`` from global config is used.
            key_prefix: Override for ``GRPC_RATE_LIMIT.KEY_PREFIX``.
            fail_closed: Override for ``GRPC_RATE_LIMIT.FAIL_CLOSED``.
            skip_methods: Full gRPC method names excluded from rate limiting.
            identity_from_access_token: Override for ``GRPC_RATE_LIMIT.IDENTITY_FROM_ACCESS_TOKEN``.
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

    def _build_rate_limit_key(self, identity: str, method_name_model: MethodName, window: RateLimitWindowDTO) -> str:
        """Build the Redis key for one rate-limit window tier."""
        full_method = self._full_method_name(method_name_model)
        return f"{self._key_prefix}:{identity}:{full_method}:{window.key_suffix}"

    def _resolve_identity(self, context: grpc.ServicerContext, method_name_model: MethodName) -> str:
        """Resolve the server-side rate-limit identity for an RPC."""
        if self._identifier_fn is not None:
            try:
                return str(self._identifier_fn(context, method_name_model))
            except Exception as exc:
                if self._fail_closed:
                    UnavailableError(
                        additional_data={"detail": "Rate limiter identity resolution failed"},
                    ).abort_grpc_sync(context)
                    raise RuntimeError("unreachable") from exc
                return "unknown"

        if self._identity_from_access_token:
            metadata = context.invocation_metadata()
            metadata_items = list(metadata) if metadata is not None else []
            if user_sub := resolve_jwt_access_token_sub_from_metadata(metadata_items):
                return user_sub
            return self._parse_peer(context.peer())

        return self._parse_peer(context.peer())

    async def _resolve_identity_async(self, context: grpc.aio.ServicerContext, method_name_model: MethodName) -> str:
        """Resolve the server-side rate-limit identity for an async RPC."""
        if self._identifier_fn is not None:
            try:
                result = self._identifier_fn(context, method_name_model)
                if inspect.isawaitable(result):
                    result = await result
                return str(result)
            except Exception as exc:
                if self._fail_closed:
                    await UnavailableError(
                        additional_data={"detail": "Rate limiter identity resolution failed"},
                    ).abort_grpc_async(context)
                    raise RuntimeError("unreachable") from exc
                return "unknown"

        if self._identity_from_access_token:
            metadata = context.invocation_metadata()
            metadata_items = list(metadata) if metadata is not None else []
            if user_sub := resolve_jwt_access_token_sub_from_metadata(metadata_items):
                return user_sub
            return self._parse_peer(context.peer())

        return self._parse_peer(context.peer())

    def _abort_rate_limited_sync(self, context: grpc.ServicerContext, window: RateLimitWindowDTO, pexpire: int) -> None:
        """Abort a sync RPC with RESOURCE_EXHAUSTED when a window is breached."""
        RateLimitExceededError(
            retry_after=self._retry_after_seconds(pexpire, window.window_ms),
            additional_data={
                "limit": window.calls_count,
                "window_ms": window.window_ms,
                "remaining": 0,
            },
        ).abort_grpc_sync(context)

    async def _abort_rate_limited_async(
        self,
        context: grpc.aio.ServicerContext,
        window: RateLimitWindowDTO,
        pexpire: int,
    ) -> None:
        """Abort an async RPC with RESOURCE_EXHAUSTED when a window is breached."""
        await RateLimitExceededError(
            retry_after=self._retry_after_seconds(pexpire, window.window_ms),
            additional_data={
                "limit": window.calls_count,
                "window_ms": window.window_ms,
                "remaining": 0,
            },
        ).abort_grpc_async(context)

    def _abort_unavailable_sync(self, context: grpc.ServicerContext, *, detail: str) -> None:
        """Abort a sync RPC when the rate limiter backend is unavailable."""
        UnavailableError(additional_data={"detail": detail}).abort_grpc_sync(context)

    async def _abort_unavailable_async(self, context: grpc.aio.ServicerContext, *, detail: str) -> None:
        """Abort an async RPC when the rate limiter backend is unavailable."""
        await UnavailableError(additional_data={"detail": detail}).abort_grpc_async(context)


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
    ) -> None:
        """Initialize the sync gRPC rate-limit interceptor."""
        super().__init__(
            rate_limit_config=rate_limit_config,
            key_prefix=key_prefix,
            fail_closed=fail_closed,
            skip_methods=skip_methods,
            identity_from_access_token=identity_from_access_token,
        )
        self._identifier_fn = identifier_fn
        self._redis_client: RedisAdapter = self._create_redis_client()

    @staticmethod
    def _create_redis_client() -> RedisAdapter:
        """Lazily initialized sync Redis client for rate limiting."""
        from archipy.adapters.redis.adapters import RedisAdapter  # noqa: PLC0415

        return RedisAdapter()

    def _check(self, key: str, window: RateLimitWindowDTO) -> tuple[int, int]:
        """Increment the rate-limit counter and return limit state."""
        new_value, applied = self._redis_client.increx(
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
        return self._redis_client.pttl(key), 0

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Enforce stacked rate-limit windows before invoking the RPC handler."""
        from redis.exceptions import RedisError  # noqa: PLC0415

        windows = RateLimitUtils.get_rate_limit_windows_from_callable(method)
        if not windows:
            return method(request, context)

        full_method = self._full_method_name(method_name_model)
        if full_method in self._skip_methods:
            return method(request, context)

        identity = self._resolve_identity(context, method_name_model)
        for window in windows:
            key = self._build_rate_limit_key(identity, method_name_model, window)
            try:
                pexpire, _remaining = self._check(key, window)
            except (ConnectionError, OSError, TimeoutError, RedisError) as exc:
                if self._fail_closed:
                    self._abort_unavailable_sync(context, detail="Rate limiter unavailable")
                    raise RuntimeError("unreachable") from exc
                return method(request, context)

            if pexpire != 0:
                self._abort_rate_limited_sync(context, window, pexpire)
                raise RuntimeError("unreachable")

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
    ) -> None:
        """Initialize the async gRPC rate-limit interceptor."""
        super().__init__(
            rate_limit_config=rate_limit_config,
            key_prefix=key_prefix,
            fail_closed=fail_closed,
            skip_methods=skip_methods,
            identity_from_access_token=identity_from_access_token,
        )
        self._identifier_fn = identifier_fn
        self._redis_client: AsyncRedisAdapter = self._create_redis_client()

    @staticmethod
    def _create_redis_client() -> AsyncRedisAdapter:
        """Lazily initialized async Redis client for rate limiting."""
        from archipy.adapters.redis.adapters import AsyncRedisAdapter  # noqa: PLC0415

        return AsyncRedisAdapter()

    async def _check(self, key: str, window: RateLimitWindowDTO) -> tuple[int, int]:
        """Increment the rate-limit counter and return limit state."""
        new_value, applied = await self._redis_client.increx(
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
        return await self._redis_client.pttl(key), 0

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Enforce stacked rate-limit windows before invoking the async RPC handler."""
        from redis.exceptions import RedisError  # noqa: PLC0415

        windows = RateLimitUtils.get_rate_limit_windows_from_callable(method)
        if not windows:
            result = method(request, context)
            if inspect.isawaitable(result):
                return await result
            return result

        full_method = self._full_method_name(method_name_model)
        if full_method in self._skip_methods:
            result = method(request, context)
            if inspect.isawaitable(result):
                return await result
            return result

        identity = await self._resolve_identity_async(context, method_name_model)
        for window in windows:
            key = self._build_rate_limit_key(identity, method_name_model, window)
            try:
                pexpire, _remaining = await self._check(key, window)
            except (ConnectionError, OSError, TimeoutError, RedisError) as exc:
                if self._fail_closed:
                    await self._abort_unavailable_async(context, detail="Rate limiter unavailable")
                    raise RuntimeError("unreachable") from exc
                result = method(request, context)
                if inspect.isawaitable(result):
                    return await result
                return result

            if pexpire != 0:
                await self._abort_rate_limited_async(context, window, pexpire)
                raise RuntimeError("unreachable")

        result = method(request, context)
        if inspect.isawaitable(result):
            return await result
        return result
