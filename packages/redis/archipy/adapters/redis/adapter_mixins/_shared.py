"""Shared helpers and attribute bases for Redis adapter mixins."""

from __future__ import annotations

from collections.abc import Awaitable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, cast

from redis.asyncio.retry import Retry as AsyncRetry
from redis.backoff import ExponentialBackoff
from redis.exceptions import TimeoutError as RedisTimeoutError
from redis.retry import Retry, is_retryable_connect_error

if TYPE_CHECKING:
    from redis import RedisCluster
    from redis.asyncio import RedisCluster as AsyncRedisCluster
    from redis.asyncio.client import Redis as AsyncRedis
    from redis.client import Redis

    from archipy.configs.config_template import RedisConfig

_set = set


def _text(value: bytes | str) -> str:
    """Return a key, field or value unchanged for the Redis client.

    redis-py accepts bytes as well as str, so bytes must never be coerced with ``str()``
    (which would store the literal ``"b'..'"`` repr). The cast only satisfies the client's typing.
    """
    return cast("str", value)


class SyncRedisMixinBase:
    """Shared attribute/method declarations for sync Redis adapter mixins."""

    client: Redis | RedisCluster
    read_only_client: Redis | RedisCluster
    _configs: RedisConfig
    _search_client: Redis | RedisCluster | None

    @staticmethod
    def _ensure_sync_int(value: int | Awaitable[int]) -> int:
        """Coerce sync Redis int responses that may be typed as Awaitable."""
        raise NotImplementedError


class AsyncRedisMixinBase:
    """Shared attribute/method declarations for async Redis adapter mixins."""

    client: AsyncRedis | AsyncRedisCluster
    read_only_client: AsyncRedis | AsyncRedisCluster
    _configs: RedisConfig
    _search_client: AsyncRedis | AsyncRedisCluster | None

    @staticmethod
    async def _ensure_async_int(value: int | Awaitable[int]) -> int:
        """Coerce async Redis int responses that may be typed as Awaitable."""
        raise NotImplementedError

    @staticmethod
    async def _ensure_async_bool(value: bool | Awaitable[bool]) -> bool:
        """Coerce async Redis bool responses that may be typed as Awaitable."""
        raise NotImplementedError

    @staticmethod
    async def _ensure_async_str(
        value: str | bytes | Awaitable[str | bytes | None] | None,
    ) -> str | None:
        """Coerce async Redis string responses that may be typed as Awaitable."""
        raise NotImplementedError

    @staticmethod
    async def _ensure_async_list(value: list[Any] | Awaitable[list[Any]]) -> list[Any]:
        """Coerce async Redis list responses that may be typed as Awaitable."""
        raise NotImplementedError


def _tls_acl_kwargs(configs: RedisConfig) -> dict[str, Any]:
    """Build ACL username and TLS kwargs; empty when neither is configured."""
    kwargs: dict[str, Any] = {}
    if configs.USERNAME:
        kwargs["username"] = configs.USERNAME
    if configs.TLS.IS_ENABLED:
        kwargs["ssl"] = True
        kwargs["ssl_check_hostname"] = configs.TLS.CHECK_HOSTNAME
        if configs.TLS.CA_CERTS:
            kwargs["ssl_ca_certs"] = configs.TLS.CA_CERTS
        if configs.TLS.CERTFILE and configs.TLS.KEYFILE:
            kwargs["ssl_certfile"] = configs.TLS.CERTFILE
            kwargs["ssl_keyfile"] = configs.TLS.KEYFILE
    return kwargs


def _resilience_kwargs(configs: RedisConfig, *, is_async: bool = False) -> dict[str, Any]:
    """Build retry, keepalive and client-name kwargs; empty when none is configured."""
    kwargs: dict[str, Any] = {}
    if configs.RETRY.ATTEMPTS is not None or configs.RETRY.FAIL_FAST_MISSING_SOCKET:
        backoff = ExponentialBackoff(cap=configs.RETRY.BACKOFF_CAP, base=configs.RETRY.BACKOFF_BASE)
        retry_class = AsyncRetry if is_async else Retry
        attempts = configs.RETRY.ATTEMPTS if configs.RETRY.ATTEMPTS is not None else 3
        checker = is_retryable_connect_error if configs.RETRY.FAIL_FAST_MISSING_SOCKET else None
        kwargs["retry"] = retry_class(backoff, attempts, is_retryable=checker)
    if configs.RETRY.ON_TIMEOUT:
        kwargs["retry_on_error"] = [RedisTimeoutError]
    if configs.SOCKET_KEEPALIVE is not None:
        kwargs["socket_keepalive"] = configs.SOCKET_KEEPALIVE
    if configs.CLIENT_NAME:
        kwargs["client_name"] = configs.CLIENT_NAME
    return kwargs


def _redis_connection_kwargs(
    configs: RedisConfig,
    *,
    decode_responses: bool | None = None,
    is_async: bool = False,
) -> dict[str, Any]:
    """Build common Redis client connection kwargs from config."""
    return {
        "password": configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
        "decode_responses": (configs.DECODE_RESPONSES if decode_responses is None else decode_responses),
        "health_check_interval": configs.HEALTH_CHECK_INTERVAL,
        "max_connections": configs.MAX_CONNECTIONS,
        "socket_connect_timeout": configs.SOCKET_CONNECT_TIMEOUT,
        "socket_timeout": configs.SOCKET_TIMEOUT,
        "protocol": configs.PROTOCOL,
        **_tls_acl_kwargs(configs),
        **_resilience_kwargs(configs, is_async=is_async),
    }


def _sentinel_redis_kwargs(configs: RedisConfig, *, is_async: bool = False) -> dict[str, Any]:
    """Build Redis kwargs for sentinel master_for/slave_for connections."""
    return {
        "socket_timeout": configs.SOCKET_TIMEOUT,
        "socket_connect_timeout": configs.SOCKET_CONNECT_TIMEOUT,
        "max_connections": configs.MAX_CONNECTIONS,
        "password": configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
        "db": configs.DATABASE,
        "decode_responses": configs.DECODE_RESPONSES,
        "health_check_interval": configs.HEALTH_CHECK_INTERVAL,
        "protocol": configs.PROTOCOL,
        **_tls_acl_kwargs(configs),
        **_resilience_kwargs(configs, is_async=is_async),
    }


def _sentinel_kwargs(configs: RedisConfig) -> dict[str, Any] | None:
    """Build sentinel-node kwargs: sentinel username, password and the shared TLS settings."""
    kwargs: dict[str, Any] = {}
    if configs.SENTINEL.USERNAME:
        kwargs["username"] = configs.SENTINEL.USERNAME
    if configs.SENTINEL.PASSWORD:
        kwargs["password"] = configs.SENTINEL.PASSWORD.get_secret_value()
    if configs.TLS.IS_ENABLED:
        kwargs.update({k: v for k, v in _tls_acl_kwargs(configs).items() if k != "username"})
    return kwargs or None


def _normalize_zset_keys(
    keys: Mapping[bytes | str, float] | Iterable[bytes | str],
) -> dict[str, float] | list[str]:
    """Normalize sorted-set keys for zunion/zinter into a form the Redis client accepts."""
    if isinstance(keys, Mapping):
        return {_text(key): float(value) for key, value in keys.items()}
    return [_text(key) for key in keys]
