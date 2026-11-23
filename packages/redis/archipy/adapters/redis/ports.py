"""Redis port interfaces composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.redis.port_mixins import (
    AsyncRedisArraysPort,
    AsyncRedisClusterPort,
    AsyncRedisConnectionPort,
    AsyncRedisHashesPort,
    AsyncRedisKeysPort,
    AsyncRedisListsPort,
    AsyncRedisPubSubPort,
    AsyncRedisSetsPort,
    AsyncRedisSortedSetsPort,
    AsyncRedisStreamsPort,
    AsyncRedisTimeSeriesPort,
    RedisArraysPort,
    RedisClusterPort,
    RedisConnectionPort,
    RedisHashesPort,
    RedisKeysPort,
    RedisListsPort,
    RedisPubSubPort,
    RedisScoreCastType,
    RedisSetsPort,
    RedisSortedSetsPort,
    RedisStreamsPort,
    RedisTimeSeriesPort,
)

__all__ = [
    "AsyncRedisPort",
    "RedisPort",
    "RedisScoreCastType",
]


class RedisPort(
    RedisConnectionPort,
    RedisClusterPort,
    RedisKeysPort,
    RedisListsPort,
    RedisSetsPort,
    RedisSortedSetsPort,
    RedisTimeSeriesPort,
    RedisStreamsPort,
    RedisArraysPort,
    RedisHashesPort,
    RedisPubSubPort,
):
    """Interface for Redis operations providing a standardized access pattern.

    Defines the contract for Redis adapters: key-value ops, collections
    (lists, sets, sorted sets, hashes), cluster admin, and pub/sub.
    """


class AsyncRedisPort(
    AsyncRedisConnectionPort,
    AsyncRedisClusterPort,
    AsyncRedisKeysPort,
    AsyncRedisListsPort,
    AsyncRedisSetsPort,
    AsyncRedisSortedSetsPort,
    AsyncRedisTimeSeriesPort,
    AsyncRedisStreamsPort,
    AsyncRedisArraysPort,
    AsyncRedisHashesPort,
    AsyncRedisPubSubPort,
):
    """Async interface for Redis operations providing a standardized access pattern.

    Async counterpart of RedisPort: same surface, async methods throughout.
    """
