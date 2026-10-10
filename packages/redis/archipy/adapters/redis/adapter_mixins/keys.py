"""Redis adapter mixins for keys operations."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Iterable, Iterator, Mapping
from typing import TYPE_CHECKING, Any

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase

if TYPE_CHECKING:
    from datetime import datetime, timedelta


class RedisKeysMixin(SyncRedisMixinBase):
    """Sync Redis mixin for keys operations."""

    def pttl(self, name: bytes | str) -> int:
        """Get the time to live in milliseconds for a key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in milliseconds.
        """
        return self.read_only_client.pttl(name)

    def incrby(self, name: bytes | str, amount: int = 1) -> int:
        """Increment the integer value of a key by the given amount.

        Args:
            name (bytes | str): The key name.
            amount (int): Amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after increment.
        """
        return self.client.incrby(name, amount)

    def increx(
        self,
        name: bytes | str,
        byfloat: float | None = None,
        byint: int | None = None,
        lbound: float | None = None,
        ubound: float | None = None,
        saturate: bool = False,
        ex: int | timedelta | None = None,
        px: int | timedelta | None = None,
        exat: int | datetime | None = None,
        pxat: int | datetime | None = None,
        persist: bool = False,
        enx: bool = False,
    ) -> list[Any]:
        """Increment a windowed counter with bounds and expiration control.

        Args:
            name (bytes | str): The key to increment.
            byfloat (float, optional): Increment amount as a float.
            byint (int, optional): Increment amount as an int.
            lbound (float | int, optional): Lower bound for the resulting value.
            ubound (float | int, optional): Upper bound for the resulting value.
            saturate (bool): Clamp out-of-bounds results instead of rejecting. Defaults to False.
            ex (int | timedelta | None): Expire time in seconds.
            px (int | timedelta | None): Expire time in milliseconds.
            exat (int | datetime | None): Absolute expiration time in seconds.
            pxat (int | datetime | None): Absolute expiration time in milliseconds.
            persist (bool): Remove any existing expiration. Defaults to False.
            enx (bool): Set expiration only if none already exists. Defaults to False.

        Returns:
            RedisResponseType: A two-element list of [new_value, actual_increment_applied].
        """
        return list(
            self.client.increx(
                name,
                byfloat=byfloat,
                byint=byint,
                lbound=lbound,
                ubound=ubound,
                saturate=saturate,
                ex=ex,
                px=px,
                exat=exat,
                pxat=pxat,
                persist=persist,
                enx=enx,
            ),
        )

    def set(
        self,
        name: bytes | str,
        value: bytes | str | float,
        ex: int | timedelta | None = None,
        px: int | timedelta | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: int | datetime | None = None,
        pxat: int | datetime | None = None,
    ) -> bool | str | bytes | None:
        """Set the value of a key with optional expiration and conditions.

        Args:
            name (bytes | str): The key name.
            value (int | bytes | str | float): The value to set.
            ex (int | timedelta | None): Expire time in seconds.
            px (int | timedelta | None): Expire time in milliseconds.
            nx (bool): Only set if key doesn't exist.
            xx (bool): Only set if key exists.
            keepttl (bool): Retain the TTL from the previous value.
            get (bool): Return the old value.
            exat (int | datetime | None): Absolute expiration time in seconds.
            pxat (int | datetime | None): Absolute expiration time in milliseconds.

        Returns:
            RedisResponseType: Result of the operation.
        """
        return self.client.set(name, value, ex, px, nx, xx, keepttl, get, exat, pxat)

    def get(self, key: str) -> bytes | str | None:
        """Get the value of a key.

        Args:
            key (str): The key name.

        Returns:
            RedisResponseType: The value of the key or None if not exists.
        """
        return self.read_only_client.get(key)

    def mget(
        self,
        keys: bytes | str | Iterable[bytes | str],
        *args: bytes | str,
    ) -> list[bytes | str | None]:
        """Get the values of multiple keys.

        Args:
            keys (bytes | str | Iterable[bytes | str]): Single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: List of values.
        """
        return self.read_only_client.mget(keys, *args)

    def mset(self, mapping: Mapping[bytes | str, bytes | str | float]) -> bool:
        """Set multiple keys to their respective values.

        Args:
            mapping (Mapping[bytes | str, bytes | str | float]): Dictionary of key-value pairs.

        Returns:
            RedisResponseType: Always returns 'OK'.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        return self.client.mset(dict_mapping)

    def keys(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Find all keys matching the given pattern.

        Args:
            pattern (bytes | str): Pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of matching keys.
        """
        return self.read_only_client.keys(pattern, **kwargs)

    def getset(self, key: bytes | str, value: bytes | str | float) -> bytes | str | None:
        """Set the value of a key and return its old value.

        Args:
            key (bytes | str): The key name.
            value (bytes | str | float): The new value.

        Returns:
            RedisResponseType: The previous value or None.
        """
        return self.client.getset(key, value)

    def getdel(self, key: bytes | str) -> bytes | str | None:
        """Get the value of a key and delete it.

        Args:
            key (bytes | str): The key name.

        Returns:
            RedisResponseType: The value of the key or None.
        """
        return self.client.getdel(key)

    def exists(self, *names: bytes | str) -> int:
        """Check if one or more keys exist.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys that exist.
        """
        return self.read_only_client.exists(*names)

    def delete(self, *names: bytes | str) -> int:
        """Delete one or more keys.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys deleted.
        """
        return self.client.delete(*names)

    def append(self, key: bytes | str, value: bytes | str | float) -> int:
        """Append a value to a key.

        Args:
            key (bytes | str): The key name.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: Length of the string after append.
        """
        return self.client.append(key, value)

    def ttl(self, name: bytes | str) -> int:
        """Get the time to live in seconds for a key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in seconds.
        """
        return self.read_only_client.ttl(name)

    def type(self, name: bytes | str) -> bytes | str:
        """Determine the type stored at key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Type of the key's value.
        """
        return self.read_only_client.type(name)

    def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> tuple[int, list[bytes | str]]:
        """Scan keys in the database incrementally.

        Args:
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys to return. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Tuple of cursor and list of keys.
        """
        return self.read_only_client.scan(cursor, match, count, _type, **kwargs)

    def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator[bytes | str]:
        """Iterate over keys in the database.

        Args:
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys to return. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            Iterator: Iterator over matching keys.
        """
        return self.read_only_client.scan_iter(match, count, _type, **kwargs)


class AsyncRedisKeysMixin(AsyncRedisMixinBase):
    """Async Redis mixin for keys operations."""

    async def pttl(self, name: bytes | str) -> int:
        """Get the time to live in milliseconds for a key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in milliseconds.
        """
        return await self.read_only_client.pttl(name)

    async def incrby(self, name: bytes | str, amount: int = 1) -> int:
        """Increment the integer value of a key by the given amount asynchronously.

        Args:
            name (bytes | str): The key name.
            amount (int): Amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after increment.
        """
        return await self.client.incrby(name, amount)

    async def increx(
        self,
        name: bytes | str,
        byfloat: float | None = None,
        byint: int | None = None,
        lbound: float | None = None,
        ubound: float | None = None,
        saturate: bool = False,
        ex: int | timedelta | None = None,
        px: int | timedelta | None = None,
        exat: int | datetime | None = None,
        pxat: int | datetime | None = None,
        persist: bool = False,
        enx: bool = False,
    ) -> list[Any]:
        """Increment a windowed counter with bounds and expiration control asynchronously.

        Args:
            name (bytes | str): The key to increment.
            byfloat (float, optional): Increment amount as a float.
            byint (int, optional): Increment amount as an int.
            lbound (float | int, optional): Lower bound for the resulting value.
            ubound (float | int, optional): Upper bound for the resulting value.
            saturate (bool): Clamp out-of-bounds results instead of rejecting. Defaults to False.
            ex (int | timedelta | None): Expire time in seconds.
            px (int | timedelta | None): Expire time in milliseconds.
            exat (int | datetime | None): Absolute expiration time in seconds.
            pxat (int | datetime | None): Absolute expiration time in milliseconds.
            persist (bool): Remove any existing expiration. Defaults to False.
            enx (bool): Set expiration only if none already exists. Defaults to False.

        Returns:
            RedisResponseType: A two-element list of [new_value, actual_increment_applied].
        """
        result = self.client.increx(
            name,
            byfloat=byfloat,
            byint=byint,
            lbound=lbound,
            ubound=ubound,
            saturate=saturate,
            ex=ex,
            px=px,
            exat=exat,
            pxat=pxat,
            persist=persist,
            enx=enx,
        )
        if isinstance(result, Awaitable):
            result = await result
        return list(result)

    async def set(
        self,
        name: bytes | str,
        value: bytes | str | float,
        ex: int | timedelta | None = None,
        px: int | timedelta | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: int | datetime | None = None,
        pxat: int | datetime | None = None,
    ) -> bool | str | bytes | None:
        """Set the value of a key with optional expiration asynchronously.

        Args:
            name (bytes | str): The key name.
            value (int | bytes | str | float): The value to set.
            ex (int | timedelta | None): Expire time in seconds.
            px (int | timedelta | None): Expire time in milliseconds.
            nx (bool): Only set if key doesn't exist.
            xx (bool): Only set if key exists.
            keepttl (bool): Retain the TTL from the previous value.
            get (bool): Return the old value.
            exat (int | datetime | None): Absolute expiration time in seconds.
            pxat (int | datetime | None): Absolute expiration time in milliseconds.

        Returns:
            RedisResponseType: Result of the operation.
        """
        return await self.client.set(name, value, ex, px, nx, xx, keepttl, get, exat, pxat)

    async def get(self, key: str) -> bytes | str | None:
        """Get the value of a key asynchronously.

        Args:
            key (str): The key name.

        Returns:
            RedisResponseType: The value of the key or None if not exists.
        """
        return await self.read_only_client.get(key)

    async def mget(
        self,
        keys: bytes | str | Iterable[bytes | str],
        *args: bytes | str,
    ) -> list[bytes | str | None]:
        """Get the values of multiple keys asynchronously.

        Args:
            keys (bytes | str | Iterable[bytes | str]): Single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: List of values.
        """
        return await self.read_only_client.mget(keys, *args)

    async def mset(self, mapping: Mapping[bytes | str, bytes | str | float]) -> bool:
        """Set multiple keys to their values asynchronously.

        Args:
            mapping (Mapping[bytes | str, bytes | str | float]): Dictionary of key-value pairs.

        Returns:
            RedisResponseType: Always returns 'OK'.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        return await self.client.mset(dict_mapping)

    async def keys(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Find all keys matching the pattern asynchronously.

        Args:
            pattern (bytes | str): Pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of matching keys.
        """
        return await self.read_only_client.keys(pattern, **kwargs)

    async def getset(self, key: bytes | str, value: bytes | str | float) -> bytes | str | None:
        """Set a key's value and return its old value asynchronously.

        Args:
            key (bytes | str): The key name.
            value (bytes | str | float): The new value.

        Returns:
            RedisResponseType: The previous value or None.
        """
        return await self.client.getset(key, value)

    async def getdel(self, key: bytes | str) -> bytes | str | None:
        """Get a key's value and delete it asynchronously.

        Args:
            key (bytes | str): The key name.

        Returns:
            RedisResponseType: The value of the key or None.
        """
        return await self.client.getdel(key)

    async def exists(self, *names: bytes | str) -> int:
        """Check if keys exist asynchronously.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys that exist.
        """
        return await self.read_only_client.exists(*names)

    async def delete(self, *names: bytes | str) -> int:
        """Delete keys asynchronously.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys deleted.
        """
        return await self.client.delete(*names)

    async def append(self, key: bytes | str, value: bytes | str | float) -> int:
        """Append a value to a key asynchronously.

        Args:
            key (bytes | str): The key name.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: Length of the string after append.
        """
        return await self.client.append(key, value)

    async def ttl(self, name: bytes | str) -> int:
        """Get the time to live in seconds for a key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in seconds.
        """
        return await self.read_only_client.ttl(name)

    async def type(self, name: bytes | str) -> bytes | str:
        """Determine the type stored at key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Type of the key's value.
        """
        return await self.read_only_client.type(name)

    async def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> tuple[int, list[bytes | str]]:
        """Scan keys in database incrementally asynchronously.

        Args:
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Tuple of cursor and list of keys.
        """
        return await self.read_only_client.scan(cursor, match, count, _type, **kwargs)

    async def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[bytes | str]:
        """Iterate over keys in database asynchronously.

        Args:
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            Iterator[Any]: Iterator over matching keys.
        """
        return self.read_only_client.scan_iter(match, count, _type, **kwargs)
