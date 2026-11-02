"""Redis adapter mixins for cluster operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.redis.adapter_mixins._shared import (
    AsyncRedisMixinBase,
    SyncRedisMixinBase,
)


class RedisClusterMixin(SyncRedisMixinBase):
    """Sync Redis mixin for cluster operations."""

    def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information."""
        getter = getattr(self.client, "cluster_info", None)
        return getter() if callable(getter) else None

    def cluster_nodes(
        self,
    ) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information."""
        getter = getattr(self.client, "cluster_nodes", None)
        return getter() if callable(getter) else None

    def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping."""
        getter = getattr(self.client, "cluster_slots", None)
        return getter() if callable(getter) else None

    def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key."""
        getter = getattr(self.client, "cluster_keyslot", None)
        return getter(key) if callable(getter) else None

    def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot."""
        getter = getattr(self.client, "cluster_countkeysinslot", None)
        return getter(slot) if callable(getter) else None

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot."""
        getter = getattr(self.client, "cluster_get_keys_in_slot", None)
        return getter(slot, count) if callable(getter) else None


class AsyncRedisClusterMixin(AsyncRedisMixinBase):
    """Async Redis mixin for cluster operations."""

    async def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information asynchronously."""
        getter = getattr(self.client, "cluster_info", None)
        return await getter() if callable(getter) else None

    async def cluster_nodes(
        self,
    ) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information asynchronously."""
        getter = getattr(self.client, "cluster_nodes", None)
        return await getter() if callable(getter) else None

    async def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping asynchronously."""
        getter = getattr(self.client, "cluster_slots", None)
        return await getter() if callable(getter) else None

    async def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key asynchronously."""
        getter = getattr(self.client, "cluster_keyslot", None)
        return await getter(key) if callable(getter) else None

    async def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot asynchronously."""
        getter = getattr(self.client, "cluster_countkeysinslot", None)
        return await getter(slot) if callable(getter) else None

    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot asynchronously."""
        getter = getattr(self.client, "cluster_get_keys_in_slot", None)
        return await getter(slot, count) if callable(getter) else None
