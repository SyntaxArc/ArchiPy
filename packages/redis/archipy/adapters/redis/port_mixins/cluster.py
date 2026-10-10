"""Redis port mixins for cluster operations."""

from __future__ import annotations

from typing import Any


class RedisClusterPort:
    """Sync Redis port for cluster operations."""

    def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information.

        Returns:
            RedisResponseType: Cluster information or None for standalone mode.
        """
        return None

    def cluster_nodes(self) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information.

        Returns:
            RedisResponseType: Cluster nodes info or None for standalone mode.
        """
        return None

    def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping.

        Returns:
            RedisResponseType: Slots mapping or None for standalone mode.
        """
        return None

    def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key.

        Args:
            key (str): The key to get slot for.

        Returns:
            RedisResponseType: Key slot or None for standalone mode.
        """
        return None

    def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot.

        Args:
            slot (int): The slot number.

        Returns:
            RedisResponseType: Key count or None for standalone mode.
        """
        return None

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot.

        Args:
            slot (int): The slot number.
            count (int): Maximum number of keys to return.

        Returns:
            RedisResponseType: List of keys or None for standalone mode.
        """
        return None


class AsyncRedisClusterPort:
    """Async Redis port for cluster operations."""

    async def cluster_info(self) -> dict[str, str] | None:
        """Get cluster information asynchronously.

        Returns:
            RedisResponseType: Cluster information or None for standalone mode.
        """
        return None

    async def cluster_nodes(self) -> dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]] | None:
        """Get cluster nodes information asynchronously.

        Returns:
            RedisResponseType: Cluster nodes info or None for standalone mode.
        """
        return None

    async def cluster_slots(self) -> list[Any] | None:
        """Get cluster slots mapping asynchronously.

        Returns:
            RedisResponseType: Slots mapping or None for standalone mode.
        """
        return None

    async def cluster_key_slot(self, key: str) -> int | None:
        """Get the hash slot for a key asynchronously.

        Args:
            key (str): The key to get slot for.

        Returns:
            RedisResponseType: Key slot or None for standalone mode.
        """
        return None

    async def cluster_count_keys_in_slot(self, slot: int) -> int | None:
        """Count keys in a specific slot asynchronously.

        Args:
            slot (int): The slot number.

        Returns:
            RedisResponseType: Key count or None for standalone mode.
        """
        return None

    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[bytes | str] | None:
        """Get keys in a specific slot asynchronously.

        Args:
            slot (int): The slot number.
            count (int): Maximum number of keys to return.

        Returns:
            RedisResponseType: List of keys or None for standalone mode.
        """
        return None
