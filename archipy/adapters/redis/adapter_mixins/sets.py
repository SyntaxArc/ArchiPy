"""Redis adapter mixins for sets operations."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Iterator

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase, _set
from archipy.models.errors import InternalError, InvalidArgumentError


class RedisSetsMixin(SyncRedisMixinBase):
    """Sync Redis mixin for sets operations."""

    def sscan(
        self,
        name: bytes | str,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[bytes | str]]:
        """Scan members of a set incrementally.

        Args:
            name (bytes | str): The set key name.
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            RedisResponseType: Tuple of cursor and list of members.
        """
        return self.read_only_client.sscan(name, cursor, match, count)

    def sscan_iter(
        self,
        name: bytes | str,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator[bytes | str]:
        """Iterate over members of a set.

        Args:
            name (bytes | str): The set key name.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            Iterator: Iterator over set members.
        """
        return self.read_only_client.sscan_iter(name, match, count)

    def sadd(self, name: str, *values: bytes | str | float) -> int:
        """Add members to a set.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: Number of elements added.
        """
        result = self.client.sadd(name, *values)
        return self._ensure_sync_int(result)

    def scard(self, name: str) -> int:
        """Get the number of members in a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        result = self.client.scard(name)
        return self._ensure_sync_int(result)

    def sismember(self, name: str, value: str) -> bool:
        """Check if a value is a member of a set.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            bool: True if value is a member, False otherwise.
        """
        result = self.read_only_client.sismember(name, value)
        return bool(result)

    def smembers(self, name: str) -> _set[bytes | str]:
        """Get all members of a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        result = self.read_only_client.smembers(name)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return set(result) if result else set()

    def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Remove and return random members from a set.

        Args:
            name (str): The set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            bytes | float | int | str | list | None: Popped member(s) or None.
        """
        result = self.client.spop(name, count)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        if isinstance(result, set):
            return list(result)
        return result

    def srem(self, name: str, *values: bytes | str | float) -> int:
        """Remove members from a set.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: Number of members removed.
        """
        result = self.client.srem(name, *values)
        return self._ensure_sync_int(result)

    def sunion(self, keys: bytes | str, *args: bytes | str) -> _set[bytes | str]:
        """Get the union of multiple sets.

        Args:
            keys (bytes | str): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        # Redis sunion expects a list of keys as first argument
        keys_list: list[str | bytes] = [keys, *list(args)]
        result = self.client.sunion(keys_list)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return set(result) if result else set()


class AsyncRedisSetsMixin(AsyncRedisMixinBase):
    """Async Redis mixin for sets operations."""

    async def sscan(
        self,
        name: bytes | str,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[bytes | str]]:
        """Scan set members incrementally asynchronously.

        Args:
            name (bytes | str): The set key name.
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            RedisResponseType: Tuple of cursor and list of members.
        """
        result = self.read_only_client.sscan(name, cursor, match, count)
        if isinstance(result, Awaitable):
            awaited_result: tuple[int, list[bytes | str]] = await result
            return awaited_result
        return result

    async def sscan_iter(
        self,
        name: bytes | str,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> AsyncIterator[bytes | str]:
        """Iterate over set members asynchronously.

        Args:
            name (bytes | str): The set key name.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            Iterator[Any]: Iterator over set members.
        """
        return self.read_only_client.sscan_iter(name, match, count)

    async def sadd(self, name: str, *values: bytes | str | float) -> int:
        """Add members to a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: Number of elements added.
        """
        result = self.client.sadd(name, *values)
        return await self._ensure_async_int(result)

    async def scard(self, name: str) -> int:
        """Get number of members in a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        result = self.client.scard(name)
        return await self._ensure_async_int(result)

    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is in set asynchronously.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            bool: True if value is member, False otherwise.
        """
        result = self.read_only_client.sismember(name, value)
        if isinstance(result, Awaitable):
            result = await result
        return bool(result)

    async def smembers(self, name: str) -> _set[bytes | str]:
        """Get all members of a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        result = self.read_only_client.smembers(name)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return set()
        if isinstance(result, set):
            return result
        from collections.abc import Iterable

        if isinstance(result, Iterable):
            return set(result)
        return set()

    async def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Remove and return random set members asynchronously.

        Args:
            name (str): The set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            bytes | float | int | str | list | None: Popped member(s) or None.
        """
        result = self.client.spop(name, count)
        if isinstance(result, Awaitable):
            awaited_result = await result
            # Type narrowing: result can be any of the return types
            if awaited_result is None or isinstance(awaited_result, (bytes, float, int, str, list)):
                return awaited_result
            raise InvalidArgumentError(
                argument_name="spop_result",
                additional_data={"got": type(awaited_result).__name__},
            )
        return result

    async def srem(self, name: str, *values: bytes | str | float) -> int:
        """Remove members from a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: Number of members removed.
        """
        result = self.client.srem(name, *values)
        return await self._ensure_async_int(result)

    async def sunion(self, keys: bytes | str, *args: bytes | str) -> _set[bytes | str]:
        """Get union of multiple sets asynchronously.

        Args:
            keys (bytes | str): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        # Convert keys to str for type compatibility, combine into list
        keys_list: list[str] = [str(keys)] + [str(arg) if isinstance(arg, bytes) else arg for arg in args]
        result = self.client.sunion(keys_list)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return set()
        if isinstance(result, set):
            return result
        from collections.abc import Iterable

        if isinstance(result, Iterable):
            return set(result)
        return set()
