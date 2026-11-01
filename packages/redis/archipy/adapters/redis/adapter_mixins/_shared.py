"""Shared helpers and attribute bases for Redis adapter mixins."""

from __future__ import annotations

from collections.abc import Awaitable, Iterable, Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from redis import RedisCluster
    from redis.asyncio import RedisCluster as AsyncRedisCluster
    from redis.asyncio.client import Redis as AsyncRedis
    from redis.client import Redis

    from archipy.configs.config_template import RedisConfig

_set = set


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
    if configs.SSL:
        kwargs["ssl"] = True
        kwargs["ssl_check_hostname"] = configs.SSL_CHECK_HOSTNAME
        if configs.SSL_CA_CERTS:
            kwargs["ssl_ca_certs"] = configs.SSL_CA_CERTS
        if configs.SSL_CERTFILE and configs.SSL_KEYFILE:
            kwargs["ssl_certfile"] = configs.SSL_CERTFILE
            kwargs["ssl_keyfile"] = configs.SSL_KEYFILE
    return kwargs


def _redis_connection_kwargs(configs: RedisConfig, *, decode_responses: bool | None = None) -> dict[str, Any]:
    """Build common Redis client connection kwargs from config."""
    return {
        "password": configs.PASSWORD,
        "decode_responses": (configs.DECODE_RESPONSES if decode_responses is None else decode_responses),
        "health_check_interval": configs.HEALTH_CHECK_INTERVAL,
        "max_connections": configs.MAX_CONNECTIONS,
        "socket_connect_timeout": configs.SOCKET_CONNECT_TIMEOUT,
        "socket_timeout": configs.SOCKET_TIMEOUT,
        "protocol": configs.PROTOCOL,
        **_tls_acl_kwargs(configs),
    }


def _sentinel_redis_kwargs(configs: RedisConfig) -> dict[str, Any]:
    """Build Redis kwargs for sentinel master_for/slave_for connections."""
    return {
        "socket_timeout": configs.SOCKET_TIMEOUT,
        "socket_connect_timeout": configs.SOCKET_CONNECT_TIMEOUT,
        "max_connections": configs.MAX_CONNECTIONS,
        "password": configs.PASSWORD,
        "decode_responses": configs.DECODE_RESPONSES,
        "protocol": configs.PROTOCOL,
        **_tls_acl_kwargs(configs),
    }


def _sentinel_kwargs(configs: RedisConfig) -> dict[str, Any] | None:
    """Build sentinel-node kwargs: SENTINEL_PASSWORD auth and the TLS settings (sentinels share them)."""
    kwargs: dict[str, Any] = {}
    if configs.SENTINEL_PASSWORD:
        kwargs["password"] = configs.SENTINEL_PASSWORD
    if configs.SSL:
        kwargs.update({k: v for k, v in _tls_acl_kwargs(configs).items() if k != "username"})
    return kwargs or None


def _normalize_zset_keys(
    keys: Mapping[bytes | str, float] | Iterable[bytes | str],
) -> dict[str, float] | list[str]:
    """Normalize sorted-set keys for zunion/zinter into a form the Redis client accepts."""
    if isinstance(keys, Mapping):
        return {str(key): float(value) for key, value in keys.items()}
    return [str(key) for key in keys]
