"""Shared helpers and attribute bases for Redis adapter mixins."""

from __future__ import annotations

from collections.abc import Awaitable, Iterable, Mapping
from typing import Any, cast

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
    async def _ensure_async_str(value: str | bytes | Awaitable[str | bytes | None] | None) -> str | None:
        """Coerce async Redis string responses that may be typed as Awaitable."""
        raise NotImplementedError

    @staticmethod
    async def _ensure_async_list(value: list[Any] | Awaitable[list[Any]]) -> list[Any]:
        """Coerce async Redis list responses that may be typed as Awaitable."""
        raise NotImplementedError


def _redis_connection_kwargs(configs: RedisConfig, *, decode_responses: bool | None = None) -> dict[str, Any]:
    """Build common Redis client connection kwargs from config."""
    return {
        "password": configs.PASSWORD,
        "decode_responses": configs.DECODE_RESPONSES if decode_responses is None else decode_responses,
        "health_check_interval": configs.HEALTH_CHECK_INTERVAL,
        "max_connections": configs.MAX_CONNECTIONS,
        "socket_connect_timeout": configs.SOCKET_CONNECT_TIMEOUT,
        "socket_timeout": configs.SOCKET_TIMEOUT,
        "protocol": configs.PROTOCOL,
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
    }


def _sentinel_kwargs(configs: RedisConfig) -> dict[str, str] | None:
    """Build sentinel-node auth kwargs when SENTINEL_PASSWORD is set."""
    if configs.SENTINEL_PASSWORD:
        return {"password": configs.SENTINEL_PASSWORD}
    return None


def _normalize_zset_keys(
    keys: Mapping[bytes | str, float] | Iterable[bytes | str],
) -> dict[str, float] | list[str]:
    """Normalize sorted-set keys for zunion/zinter into a form the Redis client accepts."""
    if isinstance(keys, Mapping):
        items = cast("Mapping[bytes | str, float]", keys).items()
        return {str(k): float(v) for k, v in items}
    return [str(k) for k in keys]
