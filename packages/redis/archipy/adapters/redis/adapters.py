"""Redis adapters composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.redis.adapter_mixins import (
    AsyncRedisArraysMixin,
    AsyncRedisClusterMixin,
    AsyncRedisConnectionMixin,
    AsyncRedisHashesMixin,
    AsyncRedisKeysMixin,
    AsyncRedisListsMixin,
    AsyncRedisPubSubMixin,
    AsyncRedisSetsMixin,
    AsyncRedisSortedSetsMixin,
    RedisArraysMixin,
    RedisClusterMixin,
    RedisConnectionMixin,
    RedisHashesMixin,
    RedisKeysMixin,
    RedisListsMixin,
    RedisPubSubMixin,
    RedisSetsMixin,
    RedisSortedSetsMixin,
)
from archipy.adapters.redis.error_mapping import map_redis_errors
from archipy.adapters.redis.ports import AsyncRedisPort, RedisPort

__all__ = [
    "AsyncRedisAdapter",
    "RedisAdapter",
]


class RedisAdapter(
    RedisConnectionMixin,
    RedisClusterMixin,
    RedisKeysMixin,
    RedisListsMixin,
    RedisSetsMixin,
    RedisSortedSetsMixin,
    RedisArraysMixin,
    RedisHashesMixin,
    RedisPubSubMixin,
    RedisPort,
):
    """Adapter for Redis operations providing a standardized interface.

    Implements RedisPort over sync redis-py clients. Maintains separate
    read/write clients for replica-friendly deployments.

    Args:
        redis_config: Redis settings. Uses global config when None.
    """


class AsyncRedisAdapter(
    AsyncRedisConnectionMixin,
    AsyncRedisClusterMixin,
    AsyncRedisKeysMixin,
    AsyncRedisListsMixin,
    AsyncRedisSetsMixin,
    AsyncRedisSortedSetsMixin,
    AsyncRedisArraysMixin,
    AsyncRedisHashesMixin,
    AsyncRedisPubSubMixin,
    AsyncRedisPort,
):
    """Async adapter for Redis operations providing a standardized interface.

    Implements AsyncRedisPort over async redis-py clients. Maintains separate
    read/write clients for replica-friendly deployments.

    Args:
        redis_config: Redis settings. Uses global config when None.
    """


map_redis_errors(RedisAdapter, is_async=False)
map_redis_errors(AsyncRedisAdapter, is_async=True)
