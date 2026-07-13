from __future__ import annotations

import hashlib
from collections.abc import Callable
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from math import ceil
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, Response
from pydantic import StrictInt, StrictStr
from starlette.datastructures import QueryParams
from starlette.status import HTTP_429_TOO_MANY_REQUESTS, HTTP_503_SERVICE_UNAVAILABLE

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import FastAPIRateLimitConfig
from archipy.helpers.interceptors.fastapi.rate_limit.identifiers import resolve_jwt_access_token_sub
from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from archipy.adapters.redis.adapters import AsyncRedisAdapter

_SINGLE_VALUE_PROXY_HEADER_NAMES: tuple[str, ...] = (
    "CF-Connecting-IP",
    "True-Client-IP",
)


class FastAPIRestRateLimitHandler:
    """A rate-limiting handler for FastAPI REST endpoints using Redis for tracking.

    This class provides rate-limiting functionality by tracking the number of requests
    made to a specific endpoint within a defined time window. If the request limit is
    exceeded, it raises an HTTP 429 Too Many Requests error.

    Args:
        calls_count (StrictInt): The maximum number of allowed requests within the time window.
        milliseconds (StrictInt): The time window in milliseconds.
        seconds (StrictInt): The time window in seconds.
        minutes (StrictInt): The time window in minutes.
        hours (StrictInt): The time window in hours.
        days (StrictInt): The time window in days.
        query_params (set(StrictStr)): request query parameters for rate-limiting based on query params.
    """

    def __init__(
        self,
        calls_count: StrictInt = 1,
        milliseconds: StrictInt = 0,
        seconds: StrictInt = 0,
        minutes: StrictInt = 0,
        hours: StrictInt = 0,
        days: StrictInt = 0,
        query_params: set[StrictStr] | None = None,
        *,
        rate_limit_config: FastAPIRateLimitConfig | None = None,
        trusted_proxy_ips: list[str] | None = None,
        allow_private_ips: bool | None = None,
        identifier_fn: Callable[[Request], str] | None = None,
        key_prefix: str | None = None,
        fail_closed: bool | None = None,
        skip_methods: frozenset[str] | None = None,
        hash_query_param_values: bool | None = None,
        require_identifier_for_query_params: bool | None = None,
        reject_unknown_client: bool | None = None,
        rate_limit_headers: bool | None = None,
        identity_from_access_token: bool | None = None,
    ) -> None:
        """Initialize the rate limit handler with specified time window and request limits.

        The time window is calculated by combining all time unit parameters into milliseconds.
        At least one time unit parameter should be greater than 0 to create a valid window.

        Args:
            calls_count (StrictInt, optional): Maximum number of allowed requests within the time window.
                Defaults to 1.
            milliseconds (StrictInt, optional): Number of milliseconds in the time window.
                Defaults to 0.
            seconds (StrictInt, optional): Number of seconds in the time window.
                Defaults to 0.
            minutes (StrictInt, optional): Number of minutes in the time window.
                Defaults to 0.
            hours (StrictInt, optional): Number of hours in the time window.
                Defaults to 0.
            days (StrictInt, optional): Number of days in the time window.
                Defaults to 0.
            query_params (set[StrictStr] | None, optional): Set of query parameter names to include
                in rate limit key generation. If None, no query parameters will be used.
                Defaults to None.
            rate_limit_config (FastAPIRateLimitConfig | None, optional): Rate-limit settings.
                When None, ``FASTAPI_RATE_LIMIT`` from ``BaseConfig.global_config()`` is used.
            trusted_proxy_ips (list[str] | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.TRUSTED_PROXY_IPS`` / ``FASTAPI.FORWARDED_ALLOW_IPS``.
            allow_private_ips (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.ALLOW_PRIVATE_IPS``.
            identifier_fn (Callable[[Request], str] | None, optional): Custom callable that returns
                the rate-limit identity (for example authenticated user ID). When provided, it
                replaces IP-based identification.
            key_prefix (str | None, optional): Override for ``FASTAPI_RATE_LIMIT.KEY_PREFIX``.
            fail_closed (bool | None, optional): Override for ``FASTAPI_RATE_LIMIT.FAIL_CLOSED``.
            skip_methods (frozenset[str] | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.SKIP_METHODS``.
            hash_query_param_values (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.HASH_QUERY_PARAM_VALUES``.
            require_identifier_for_query_params (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.REQUIRE_IDENTIFIER_FOR_QUERY_PARAMS``.
            reject_unknown_client (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.REJECT_UNKNOWN_CLIENT``.
            rate_limit_headers (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.RATE_LIMIT_HEADERS``.
            identity_from_access_token (bool | None, optional): Override for
                ``FASTAPI_RATE_LIMIT.IDENTITY_FROM_ACCESS_TOKEN``. Defaults to True. When enabled,
                verifies Bearer access tokens via ``JWTUtils`` and buckets by ``sub``, falling back
                to client IP.

        Raises:
            InvalidArgumentError: If ``calls_count``, the computed window, or ``query_params`` config is invalid.

        Example:
            >>> # Allow 100 requests per minute
            >>> handler = FastAPIRestRateLimitHandler(calls_count=100, minutes=1)
            >>>
            >>> # Allow 1000 requests per day with specific query params
            >>> handler = FastAPIRestRateLimitHandler(calls_count=1000, days=1, query_params={"user_id", "action"})
        """
        if calls_count < 1:
            raise InvalidArgumentError(additional_data={"detail": "calls_count must be at least 1"})

        self.query_params = query_params or set()
        resolved_rate_limit_config = rate_limit_config or BaseConfig.global_config().FASTAPI_RATE_LIMIT
        resolved_require_identifier = (
            require_identifier_for_query_params
            if require_identifier_for_query_params is not None
            else resolved_rate_limit_config.REQUIRE_IDENTIFIER_FOR_QUERY_PARAMS
        )
        resolved_identity_from_access_token = (
            identity_from_access_token
            if identity_from_access_token is not None
            else resolved_rate_limit_config.IDENTITY_FROM_ACCESS_TOKEN
        )
        has_server_resolved_identity = identifier_fn is not None or resolved_identity_from_access_token
        if resolved_require_identifier and self.query_params and not has_server_resolved_identity:
            raise InvalidArgumentError(
                additional_data={
                    "detail": (
                        "query_params requires identifier_fn or identity_from_access_token to avoid "
                        "client-controlled quota targeting; set require_identifier_for_query_params=False "
                        "to override"
                    ),
                },
            )

        self.calls_count = calls_count
        self.milliseconds = (
            milliseconds + 1000 * seconds + 60 * 1000 * minutes + 60 * 60 * 1000 * hours + 24 * 60 * 60 * 1000 * days
        )
        if self.milliseconds <= 0:
            raise InvalidArgumentError(
                additional_data={"detail": "Rate limit window must be greater than 0 milliseconds"},
            )

        app_config = BaseConfig.global_config()
        resolved_trusted_proxy_ips = trusted_proxy_ips
        if resolved_trusted_proxy_ips is None:
            resolved_trusted_proxy_ips = resolved_rate_limit_config.TRUSTED_PROXY_IPS
        if resolved_trusted_proxy_ips is None:
            resolved_trusted_proxy_ips = app_config.FASTAPI.FORWARDED_ALLOW_IPS or []

        self._always_trust_proxies, self._trusted_proxy_exact, self._trusted_proxy_networks = (
            self._parse_trusted_proxy_ips(resolved_trusted_proxy_ips)
        )
        self._allow_private_ips = (
            allow_private_ips if allow_private_ips is not None else resolved_rate_limit_config.ALLOW_PRIVATE_IPS
        )
        self._identifier_fn = identifier_fn
        self._identity_from_access_token = resolved_identity_from_access_token
        resolved_key_prefix = key_prefix if key_prefix is not None else resolved_rate_limit_config.KEY_PREFIX
        self._key_prefix = resolved_key_prefix or f"{app_config.FASTAPI.PROJECT_NAME}:RateLimit"
        self._fail_closed = fail_closed if fail_closed is not None else resolved_rate_limit_config.FAIL_CLOSED
        resolved_skip_methods = (
            skip_methods if skip_methods is not None else frozenset(resolved_rate_limit_config.SKIP_METHODS)
        )
        self._skip_methods = resolved_skip_methods
        self._hash_query_param_values = (
            hash_query_param_values
            if hash_query_param_values is not None
            else resolved_rate_limit_config.HASH_QUERY_PARAM_VALUES
        )
        self._reject_unknown_client = (
            reject_unknown_client
            if reject_unknown_client is not None
            else resolved_rate_limit_config.REJECT_UNKNOWN_CLIENT
        )
        self._rate_limit_headers = (
            rate_limit_headers if rate_limit_headers is not None else resolved_rate_limit_config.RATE_LIMIT_HEADERS
        )
        self._redis_client: AsyncRedisAdapter = self._create_redis_client()

    @staticmethod
    def _create_redis_client() -> AsyncRedisAdapter:
        """Lazily initialized Redis client for rate limiting."""
        from archipy.adapters.redis.adapters import AsyncRedisAdapter  # noqa: PLC0415

        return AsyncRedisAdapter()

    @staticmethod
    def _parse_trusted_proxy_ips(
        trusted_proxy_ips: list[str],
    ) -> tuple[bool, frozenset[str], tuple[IPv4Network | IPv6Network, ...]]:
        """Parse trusted proxy IP entries into always-trust flag, exact hosts, and networks."""
        always_trust = False
        exact_hosts: set[str] = set()
        networks = []
        for entry in trusted_proxy_ips:
            stripped = entry.strip()
            if not stripped:
                continue
            if stripped == "*":
                always_trust = True
                continue
            try:
                networks.append(ip_network(stripped, strict=False))
            except ValueError:
                exact_hosts.add(stripped)
        return always_trust, frozenset(exact_hosts), tuple(networks)

    def _is_trusted_proxy_value(self, host: str) -> bool:
        """Return whether a host or IP belongs to the configured trusted proxy set."""
        if self._always_trust_proxies:
            return bool(host)
        if not host or (not self._trusted_proxy_exact and not self._trusted_proxy_networks):
            return False
        if host in self._trusted_proxy_exact:
            return True
        try:
            ip = ip_address(host.strip())
        except ValueError:
            return False
        return any(ip in network for network in self._trusted_proxy_networks)

    def _peer_is_trusted(self, peer_host: str | None) -> bool:
        """Return whether the immediate peer is a configured trusted proxy."""
        if not peer_host:
            return False
        if self._always_trust_proxies:
            return True
        return self._is_trusted_proxy_value(peer_host)

    @staticmethod
    def _is_non_routable(ip: IPv4Address | IPv6Address) -> bool:
        """Return whether an IP should be rejected when private addresses are disallowed."""
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast

    def _normalize_ip(self, ip_str: str) -> str | None:
        """Validate and canonicalize an IP address string."""
        host = self._parse_host_port(ip_str)
        try:
            ip = ip_address(host)
        except ValueError:
            return None
        if not self._allow_private_ips and self._is_non_routable(ip):
            return None
        return str(ip)

    @staticmethod
    def _parse_host_port(value: str) -> str:
        """Return the host portion from a forwarded address token that may include a port."""
        stripped = value.strip()
        if stripped.startswith("[") and "]" in stripped:
            return stripped[1 : stripped.index("]")]
        if stripped.count(":") == 1 and "." in stripped:
            return stripped.split(":", maxsplit=1)[0]
        return stripped

    @staticmethod
    def _hash_segment(value: str) -> str:
        """Return a fixed-length hash for Redis key segments."""
        return hashlib.sha256(value.encode()).hexdigest()[:16]

    @staticmethod
    def _normalize_path(path: str) -> str:
        """Normalize request paths for stable rate-limit keys."""
        if path != "/" and path.endswith("/"):
            return path.rstrip("/")
        return path

    @staticmethod
    def _get_combined_x_forwarded_for(request: Request) -> str | None:
        """Combine all X-Forwarded-For header fields per RFC 9110."""
        values = request.headers.getlist("x-forwarded-for")
        if not values:
            return None
        return ", ".join(value.strip() for value in values if value.strip())

    def _resolve_trusted_chain(self, entries: list[str]) -> str | None:
        """Resolve the client IP from an ordered forwarded chain using recursive trust semantics."""
        if not entries:
            return None

        hosts = [self._parse_host_port(entry) for entry in entries]
        if self._always_trust_proxies:
            return self._normalize_ip(hosts[0])

        for host in reversed(hosts):
            candidate = self._normalize_ip(host) or host
            if not self._is_trusted_proxy_value(candidate):
                return self._normalize_ip(host)

        return self._normalize_ip(hosts[0])

    async def _check(self, key: str) -> tuple[int, int]:
        """Increment the rate-limit counter and return limit state.

        Returns:
            tuple[int, int]: ``(pexpire_if_limited, remaining_calls)``. ``pexpire`` is 0 when allowed.
        """
        new_value, applied = await self._redis_client.increx(
            key,
            byint=1,
            ubound=self.calls_count,
            saturate=True,
            px=self.milliseconds,
            enx=True,
        )
        if applied:
            remaining = max(0, self.calls_count - int(new_value))
            return 0, remaining
        return await self._redis_client.pttl(key), 0

    def _rate_limit_response_headers(self, remaining: int, *, limited: bool, pexpire: int = 0) -> dict[str, str]:
        """Build standard rate-limit response headers."""
        headers = {
            "X-RateLimit-Limit": str(self.calls_count),
            "X-RateLimit-Remaining": str(remaining),
        }
        if limited:
            headers["Retry-After"] = str(self._retry_after_seconds(pexpire))
        return headers

    async def __call__(self, request: Request, response: Response) -> None:
        """Handles the rate-limiting logic for incoming requests.

        Args:
            request (Request): The incoming FastAPI request.
            response (Response): The outgoing response for rate-limit headers.

        Raises:
            HTTPException: If the rate limit is exceeded, an HTTP 429 Too Many Requests error is raised.
            HTTPException: If Redis is unavailable and ``fail_closed`` is enabled.
        """
        from redis.exceptions import RedisError  # noqa: PLC0415

        if request.method in self._skip_methods:
            return

        rate_key = self._get_identifier(request)
        key = f"{self._key_prefix}:{rate_key}:{request.method}"
        try:
            pexpire, remaining = await self._check(key)
        except (ConnectionError, OSError, TimeoutError, RedisError) as exc:
            if self._fail_closed:
                raise HTTPException(
                    status_code=HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Rate limiter unavailable",
                ) from exc
            return

        if pexpire != 0:
            self._create_callback(pexpire)

        if self._rate_limit_headers:
            for header_name, header_value in self._rate_limit_response_headers(remaining, limited=False).items():
                response.headers[header_name] = header_value

    def _retry_after_seconds(self, pexpire: int) -> int:
        """Convert a PTTL value to a safe Retry-After header in seconds."""
        if pexpire > 0:
            return max(1, ceil(pexpire / 1000))
        return max(1, ceil(self.milliseconds / 1000))

    def _create_callback(self, pexpire: int) -> None:
        """Raises an HTTP 429 Too Many Requests error with the appropriate headers.

        Args:
            pexpire (int): The remaining time-to-live (TTL) in milliseconds before the rate limit resets.

        Raises:
            HTTPException: An HTTP 429 Too Many Requests error with rate-limit headers.
        """
        headers = (
            self._rate_limit_response_headers(0, limited=True, pexpire=pexpire)
            if self._rate_limit_headers
            else {"Retry-After": str(self._retry_after_seconds(pexpire))}
        )
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers=headers,
        )

    def _resolve_base_identifier(self, request: Request) -> str:
        """Resolve the base rate-limit identity from the request.

        Args:
            request: The incoming FastAPI request.

        Returns:
            str: Server-resolved client or user identity.

        Raises:
            HTTPException: If identity resolution fails and ``fail_closed`` is enabled.
        """
        if self._identifier_fn is not None:
            try:
                return self._identifier_fn(request)
            except Exception as exc:
                if self._fail_closed:
                    raise HTTPException(
                        status_code=HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Rate limiter identity resolution failed",
                    ) from exc
                return "unknown"

        if self._identity_from_access_token:
            if user_sub := resolve_jwt_access_token_sub(request):
                return user_sub
            return self._extract_client_ip(request)

        return self._extract_client_ip(request)

    def _get_identifier(self, request: Request) -> str:
        """Extract a unique identifier from the request, typically an IP address and endpoint.

        Args:
            request (Request): The FastAPI request object containing headers and client info.

        Returns:
            str: A Redis key segment built from the client identity and request path.

        Raises:
            HTTPException: If identity resolution fails and ``fail_closed`` is enabled.
        """
        base_identifier = self._resolve_base_identifier(request)

        path = self._normalize_path(request.url.path)
        path_key = f"{base_identifier}:{path}"

        if not self.query_params:
            return path_key

        return self._append_query_params(path_key, request.query_params)

    def _extract_client_ip(self, request: Request) -> str:
        """Extract and validate the client IP from the request.

        Forwarded headers are honored only when the immediate peer is a configured trusted proxy.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            str: Canonical client IP or peer host.

        Raises:
            HTTPException: If the client cannot be identified and ``reject_unknown_client`` is enabled.
        """
        peer = request.client.host if request.client is not None else None

        if peer and self._peer_is_trusted(peer):
            if client_ip := self._client_ip_from_trusted_headers(request):
                return client_ip
            if normalized_peer := self._normalize_ip(peer):
                return normalized_peer
            return peer

        if peer:
            if normalized_peer := self._normalize_ip(peer):
                return normalized_peer
            return peer

        if self._reject_unknown_client:
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="Client identity unknown",
            )
        return "unknown"

    def _client_ip_from_trusted_headers(self, request: Request) -> str | None:
        """Resolve the client IP from proxy headers when the peer is trusted."""
        for header_name in _SINGLE_VALUE_PROXY_HEADER_NAMES:
            if client_ip := self._validate_ip_from_header(request.headers.get(header_name)):
                return client_ip

        if forwarded := request.headers.get("Forwarded"):
            if client_ip := self._parse_forwarded_header(forwarded):
                return client_ip

        if forwarded_for := self._get_combined_x_forwarded_for(request):
            if client_ip := self._client_ip_from_forwarded_for(forwarded_for):
                return client_ip

        if client_ip := self._validate_ip_from_header(request.headers.get("X-Real-IP")):
            return client_ip

        return None

    def _validate_ip_from_header(self, header_value: str | None) -> str | None:
        """Validate the first IP in a single-value proxy header.

        Args:
            header_value (str | None): IP address from a proxy header.

        Returns:
            str | None: Canonical IP address or None.
        """
        if not header_value:
            return None

        first_value = header_value.split(",")[0].strip()
        return self._normalize_ip(first_value)

    def _client_ip_from_forwarded_for(self, forwarded_for: str) -> str | None:
        """Validate the client IP from an X-Forwarded-For header chain.

        Walks the chain right-to-left (nginx ``real_ip_recursive`` semantics): trusted proxy
        entries are skipped until the first non-trusted address is found.

        Args:
            forwarded_for (str): X-Forwarded-For header value.

        Returns:
            str | None: Canonical client IP or None.
        """
        parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        return self._resolve_trusted_chain(parts)

    def _parse_forwarded_header(self, forwarded_value: str) -> str | None:
        """Parse the client IP from an RFC 7239 Forwarded header using recursive trust semantics.

        Args:
            forwarded_value (str): Forwarded header value.

        Returns:
            str | None: Canonical client IP or None.
        """
        forwarded_hosts: list[str] = []
        for forwarded_part in forwarded_value.split(","):
            for directive in forwarded_part.split(";"):
                stripped = directive.strip()
                if not stripped.lower().startswith("for="):
                    continue

                for_value = stripped[4:].strip().strip('"')
                if for_value.lower() == "unknown":
                    continue
                forwarded_hosts.append(for_value)

        return self._resolve_trusted_chain(forwarded_hosts)

    def _append_query_params(self, base_key: str, query_params: QueryParams) -> str:
        """Append sorted query parameters to the Redis key.

        Args:
            base_key (str): Base Redis key without query parameters.
            query_params (QueryParams): Request query parameters.

        Returns:
            str: Redis key with appended query parameters.
        """
        filtered_params = {
            key: value for key, value in query_params.items() if key in self.query_params and value is not None
        }

        if not filtered_params:
            return base_key

        sorted_params = sorted(filtered_params.items())
        if self._hash_query_param_values:
            query_string = "&".join(f"{key}={self._hash_segment(value)}" for key, value in sorted_params)
        else:
            query_string = "&".join(f"{key}={value}" for key, value in sorted_params)
        return f"{base_key}?{query_string}"
