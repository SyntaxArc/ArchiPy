"""Redis adapter mixins for arrays operations."""

from __future__ import annotations

from collections.abc import Awaitable

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase


class RedisArraysMixin(SyncRedisMixinBase):
    """Sync Redis mixin for arrays operations."""

    def arset(self, name: bytes | str, index: int, *values: bytes | str | float) -> int:
        """Set one or more contiguous values in an array.

        Args:
            name (bytes | str): The key of the array.
            index (int): The starting index to set values at.
            *values (bytes | str | float): Values to store at consecutive indices.

        Returns:
            RedisResponseType: The number of previously empty slots that were set.
        """
        result = self.client.arset(name, index, *values)
        return self._ensure_sync_int(result)

    def arget(self, name: bytes | str, index: int) -> bytes | str | None:
        """Get the value at an index in an array.

        Args:
            name (bytes | str): The key of the array.
            index (int): The index to read.

        Returns:
            RedisResponseType: The value at the index, or None if unset.
        """
        return self.read_only_client.arget(name, index)

    def arlen(self, name: bytes | str) -> int:
        """Get the number of populated elements in an array.

        Args:
            name (bytes | str): The key of the array.

        Returns:
            RedisResponseType: The number of populated elements.
        """
        result = self.read_only_client.arlen(name)
        return self._ensure_sync_int(result)

    def ardel(self, name: bytes | str, *indices: int) -> int:
        """Delete one or more indices from an array.

        Args:
            name (bytes | str): The key of the array.
            *indices (int): Indices to delete.

        Returns:
            RedisResponseType: The number of elements deleted.
        """
        result = self.client.ardel(name, *indices)
        return self._ensure_sync_int(result)

    def arring(self, name: bytes | str, size: int, *values: bytes | str | float) -> int:
        """Insert values into an array as a fixed-size ring buffer.

        Args:
            name (bytes | str): The key of the array.
            size (int): The fixed size of the ring buffer.
            *values (bytes | str | float): Values to insert.

        Returns:
            RedisResponseType: The last index where a value was inserted.
        """
        result = self.client.arring(name, size, *values)
        return self._ensure_sync_int(result)


class AsyncRedisArraysMixin(AsyncRedisMixinBase):
    """Async Redis mixin for arrays operations."""

    async def arset(self, name: bytes | str, index: int, *values: bytes | str | float) -> int:
        """Set one or more contiguous values in an array asynchronously.

        Args:
            name (bytes | str): The key of the array.
            index (int): The starting index to set values at.
            *values (bytes | str | float): Values to store at consecutive indices.

        Returns:
            RedisResponseType: The number of previously empty slots that were set.
        """
        result = self.client.arset(name, index, *values)
        return await self._ensure_async_int(result)

    async def arget(self, name: bytes | str, index: int) -> bytes | str | None:
        """Get the value at an index in an array asynchronously.

        Args:
            name (bytes | str): The key of the array.
            index (int): The index to read.

        Returns:
            RedisResponseType: The value at the index, or None if unset.
        """
        result = self.read_only_client.arget(name, index)
        if isinstance(result, Awaitable):
            return await result
        return result

    async def arlen(self, name: bytes | str) -> int:
        """Get the number of populated elements in an array asynchronously.

        Args:
            name (bytes | str): The key of the array.

        Returns:
            RedisResponseType: The number of populated elements.
        """
        result = self.read_only_client.arlen(name)
        return await self._ensure_async_int(result)

    async def ardel(self, name: bytes | str, *indices: int) -> int:
        """Delete one or more indices from an array asynchronously.

        Args:
            name (bytes | str): The key of the array.
            *indices (int): Indices to delete.

        Returns:
            RedisResponseType: The number of elements deleted.
        """
        result = self.client.ardel(name, *indices)
        return await self._ensure_async_int(result)

    async def arring(self, name: bytes | str, size: int, *values: bytes | str | float) -> int:
        """Insert values into an array as a fixed-size ring buffer asynchronously.

        Args:
            name (bytes | str): The key of the array.
            size (int): The fixed size of the ring buffer.
            *values (bytes | str | float): Values to insert.

        Returns:
            RedisResponseType: The last index where a value was inserted.
        """
        result = self.client.arring(name, size, *values)
        return await self._ensure_async_int(result)
