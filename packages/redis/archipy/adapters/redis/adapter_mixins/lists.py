"""Redis adapter mixins for lists operations."""

from __future__ import annotations

from collections.abc import Awaitable, Iterable

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase
from archipy.models.errors import InternalError


class RedisListsMixin(SyncRedisMixinBase):
    """Sync Redis mixin for lists operations."""

    def llen(self, name: str) -> int:
        """Get the length of a list.

        Args:
            name (str): The key name of the list.

        Returns:
            RedisIntegerResponseType: Length of the list.
        """
        result = self.read_only_client.llen(name)
        return self._ensure_sync_int(result)

    def lpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Remove and return elements from the left of a list.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        return self.client.lpop(name, count)

    def lpush(self, name: str, *values: bytes | str | float) -> int:
        """Push elements to the left of a list.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.lpush(name, *values)
        return self._ensure_sync_int(result)

    def lrange(self, name: str, start: int, end: int) -> list[bytes | str]:
        """Get a range of elements from a list.

        Args:
            name (str): The key name of the list.
            start (int): Start index.
            end (int): End index.

        Returns:
            RedisListResponseType: List of elements in the specified range.
        """
        result = self.read_only_client.lrange(name, start, end)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return list(result)

    def lrem(self, name: str, count: int, value: str) -> int:
        """Remove elements from a list.

        Args:
            name (str): The key name of the list.
            count (int): Number of occurrences to remove.
            value (str): Value to remove.

        Returns:
            RedisIntegerResponseType: Number of elements removed.
        """
        result = self.client.lrem(name, count, value)
        return self._ensure_sync_int(result)

    def lset(self, name: str, index: int, value: str) -> bool:
        """Set the value of an element in a list by its index.

        Args:
            name (str): The key name of the list.
            index (int): Index of the element.
            value (str): New value.

        Returns:
            bool: True if successful.
        """
        return bool(self.client.lset(name, index, value))

    def rpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Remove and return elements from the right of a list.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        return self.client.rpop(name, count)

    def rpush(self, name: str, *values: bytes | str | float) -> int:
        """Push elements to the right of a list.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.rpush(name, *values)
        return self._ensure_sync_int(result)


class AsyncRedisListsMixin(AsyncRedisMixinBase):
    """Async Redis mixin for lists operations."""

    async def llen(self, name: str) -> int:
        """Get the length of a list asynchronously.

        Args:
            name (str): The key name of the list.

        Returns:
            RedisIntegerResponseType: Length of the list.
        """
        result = self.read_only_client.llen(name)
        return await self._ensure_async_int(result)

    async def lpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Remove and return elements from list left asynchronously.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        result = self.client.lpop(name, count)
        if isinstance(result, Awaitable):
            return await result
        return result

    async def lpush(self, name: str, *values: bytes | str | float) -> int:
        """Push elements to list left asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.lpush(name, *values)
        return await self._ensure_async_int(result)

    async def lrange(self, name: str, start: int, end: int) -> list[bytes | str]:
        """Get a range of elements from a list asynchronously.

        Args:
            name (str): The key name of the list.
            start (int): Start index.
            end (int): End index.

        Returns:
            RedisListResponseType: List of elements in range.
        """
        result = self.read_only_client.lrange(name, start, end)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, Iterable):
            return list(result)
        return []

    async def lrem(self, name: str, count: int, value: str) -> int:
        """Remove elements from a list asynchronously.

        Args:
            name (str): The key name of the list.
            count (int): Number of occurrences to remove.
            value (str): Value to remove.

        Returns:
            RedisIntegerResponseType: Number of elements removed.
        """
        result = self.client.lrem(name, count, value)
        return await self._ensure_async_int(result)

    async def lset(self, name: str, index: int, value: str) -> bool:
        """Set list element by index asynchronously.

        Args:
            name (str): The key name of the list.
            index (int): Index of the element.
            value (str): New value.

        Returns:
            bool: True if successful.
        """
        result = self.client.lset(name, index, value)
        if isinstance(result, Awaitable):
            result = await result
        return bool(result)

    async def rpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Remove and return elements from list right asynchronously.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        result = self.client.rpop(name, count)
        if isinstance(result, Awaitable):
            return await result
        return result

    async def rpush(self, name: str, *values: bytes | str | float) -> int:
        """Push elements to list right asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.rpush(name, *values)
        return await self._ensure_async_int(result)
