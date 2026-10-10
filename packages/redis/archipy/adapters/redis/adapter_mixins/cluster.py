"""Redis adapter mixins for cluster operations."""

from __future__ import annotations

from typing import Any

from redis import RedisCluster
from redis.asyncio import RedisCluster as AsyncRedisCluster

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase


class RedisClusterMixin(SyncRedisMixinBase):
    """Sync Redis mixin for cluster operations."""

    def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_info()
        return None

    def cluster_nodes(self) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_nodes()
        return None

    def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_slots()
        return None

    def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_keyslot(key)
        return None

    def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_countkeysinslot(slot)
        return None

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_get_keys_in_slot(slot, count)
        return None


class AsyncRedisClusterMixin(AsyncRedisMixinBase):
    """Async Redis mixin for cluster operations."""

    async def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_info()
        return None

    async def cluster_nodes(self) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_nodes()
        return None

    async def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_slots()
        return None

    async def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_keyslot(key)
        return None

    async def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_countkeysinslot(slot)
        return None

    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_get_keys_in_slot(slot, count)
        return None
