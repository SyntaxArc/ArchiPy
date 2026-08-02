"""Redis port mixins for keys operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterable, Iterator, Mapping
    from datetime import datetime, timedelta


class RedisKeysPort:
    """Sync Redis port for keys operations."""

    @abstractmethod
    def pttl(self, name: bytes | str) -> int:
        """Gets the remaining time to live of a key in milliseconds.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in milliseconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def incrby(self, name: bytes | str, amount: int = 1) -> int:
        """Increments the integer value of a key by the given amount.

        Args:
            name (bytes | str): The key to increment.
            amount (int): The amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after incrementing.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Increments a windowed counter with bounds and expiration control (window counter rate limiter).

        This wraps the Redis 8.8 ``INCREX`` command, a generalized form of ``INCR``/``INCRBY``/
        ``INCRBYFLOAT`` with added support for value bounds and conditional expiration, making it
        suitable for implementing rate limiters directly on the server.

        Args:
            name (bytes | str): The key to increment. Created if it doesn't already exist.
            byfloat (float, optional): Increment amount as a float. Mutually exclusive with byint.
            byint (int, optional): Increment amount as an int. Defaults to 1 if neither is set.
            lbound (float | int, optional): Lower bound the resulting value must satisfy.
            ubound (float | int, optional): Upper bound the resulting value must satisfy (token capacity).
            saturate (bool): If True, clamp out-of-bounds results to the bound instead of rejecting
                the request. Defaults to False.
            ex (int | timedelta, optional): Expiration time in seconds.
            px (int | timedelta, optional): Expiration time in milliseconds.
            exat (int | datetime, optional): Absolute expiration time in seconds.
            pxat (int | datetime, optional): Absolute expiration time in milliseconds.
            persist (bool): If True, remove any existing expiration. Defaults to False.
            enx (bool): If True, set the expiration only when the key does not already have one,
                preserving the window's original TTL. Defaults to False.

        Returns:
            RedisResponseType: A two-element list of ``[new_value, actual_increment_applied]``.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Sets a key to a value with optional expiration and conditions.

        Args:
            name (bytes | str): The key to set.
            value (int | bytes | str | float): The value to set for the key.
            ex (int | timedelta, optional): Expiration time in seconds or timedelta.
            px (int | timedelta, optional): Expiration time in milliseconds or timedelta.
            nx (bool): If True, set only if the key does not exist. Defaults to False.
            xx (bool): If True, set only if the key already exists. Defaults to False.
            keepttl (bool): If True, retain the existing TTL. Defaults to False.
            get (bool): If True, return the old value before setting. Defaults to False.
            exat (int | datetime, optional): Absolute expiration time as Unix timestamp or datetime.
            pxat (int | datetime, optional): Absolute expiration time in milliseconds or datetime.

        Returns:
            RedisResponseType: The result of the operation, often "OK" or the old value if get=True.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> bytes | str | None:
        """Retrieves the value of a key.

        Args:
            key (str): The key to retrieve.

        Returns:
            RedisResponseType: The value associated with the key, or None if the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def mget(
        self,
        keys: bytes | str | Iterable[bytes | str],
        *args: bytes | str,
    ) -> list[bytes | str | None]:
        """Gets the values of multiple keys.

        Args:
            keys (bytes | str | Iterable[bytes | str]): A single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: A list of values corresponding to the keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def mset(self, mapping: Mapping[bytes | str, bytes | str | float]) -> bool:
        """Sets multiple keys to their respective values.

        Args:
            mapping (Mapping[bytes | str, bytes | str | float]): A mapping of keys to values.

        Returns:
            RedisResponseType: Typically "OK" on success.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Returns all keys matching a pattern.

        Args:
            pattern (bytes | str): The pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of matching keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def getset(self, key: bytes | str, value: bytes | str | float) -> bytes | str | None:
        """Sets a key to a value and returns its old value.

        Args:
            key (bytes | str): The key to set.
            value (bytes | str | float): The new value to set.

        Returns:
            RedisResponseType: The old value of the key, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def getdel(self, key: bytes | str) -> bytes | str | None:
        """Gets the value of a key and deletes it.

        Args:
            key (bytes | str): The key to get and delete.

        Returns:
            RedisResponseType: The value of the key before deletion, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, *names: bytes | str) -> int:
        """Checks if one or more keys exist.

        Args:
            *names (bytes | str): Variable number of keys to check.

        Returns:
            RedisResponseType: The number of keys that exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, *names: bytes | str) -> int:
        """Deletes one or more keys.

        Args:
            *names (bytes | str): Variable number of keys to delete.

        Returns:
            RedisResponseType: The number of keys deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def append(self, key: bytes | str, value: bytes | str | float) -> int:
        """Appends a value to a key's string value.

        Args:
            key (bytes | str): The key to append to.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: The length of the string after appending.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def ttl(self, name: bytes | str) -> int:
        """Gets the remaining time to live of a key in seconds.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in seconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def type(self, name: bytes | str) -> bytes | str:
        """Determines the type of value stored at a key.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The type of the key's value (e.g., "string", "list", etc.).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> tuple[int, list[bytes | str]]:
        """Iterates over keys in the database incrementally.

        Args:
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_keys).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator[bytes | str]:
        """Provides an iterator over keys in the database.

        Args:
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Iterator: An iterator yielding keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisKeysPort:
    """Async Redis port for keys operations."""

    @abstractmethod
    async def pttl(self, name: bytes | str) -> int:
        """Gets the remaining time to live of a key in milliseconds asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in milliseconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def incrby(self, name: bytes | str, amount: int = 1) -> int:
        """Increments the integer value of a key by the given amount asynchronously.

        Args:
            name (bytes | str): The key to increment.
            amount (int): The amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after incrementing.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Increments a windowed counter with bounds and expiration control (window counter rate limiter).

        This wraps the Redis 8.8 ``INCREX`` command, a generalized form of ``INCR``/``INCRBY``/
        ``INCRBYFLOAT`` with added support for value bounds and conditional expiration, making it
        suitable for implementing rate limiters directly on the server.

        Args:
            name (bytes | str): The key to increment. Created if it doesn't already exist.
            byfloat (float, optional): Increment amount as a float. Mutually exclusive with byint.
            byint (int, optional): Increment amount as an int. Defaults to 1 if neither is set.
            lbound (float | int, optional): Lower bound the resulting value must satisfy.
            ubound (float | int, optional): Upper bound the resulting value must satisfy (token capacity).
            saturate (bool): If True, clamp out-of-bounds results to the bound instead of rejecting
                the request. Defaults to False.
            ex (int | timedelta, optional): Expiration time in seconds.
            px (int | timedelta, optional): Expiration time in milliseconds.
            exat (int | datetime, optional): Absolute expiration time in seconds.
            pxat (int | datetime, optional): Absolute expiration time in milliseconds.
            persist (bool): If True, remove any existing expiration. Defaults to False.
            enx (bool): If True, set the expiration only when the key does not already have one,
                preserving the window's original TTL. Defaults to False.

        Returns:
            RedisResponseType: A two-element list of ``[new_value, actual_increment_applied]``.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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
        """Sets a key to a value with optional expiration and conditions asynchronously.

        Args:
            name (bytes | str): The key to set.
            value (int | bytes | str | float): The value to set for the key.
            ex (int | timedelta, optional): Expiration time in seconds or timedelta.
            px (int | timedelta, optional): Expiration time in milliseconds or timedelta.
            nx (bool): If True, set only if the key does not exist. Defaults to False.
            xx (bool): If True, set only if the key already exists. Defaults to False.
            keepttl (bool): If True, retain the existing TTL. Defaults to False.
            get (bool): If True, return the old value before setting. Defaults to False.
            exat (int | datetime, optional): Absolute expiration time as Unix timestamp or datetime.
            pxat (int | datetime, optional): Absolute expiration time in milliseconds or datetime.

        Returns:
            RedisResponseType: The result of the operation, often "OK" or the old value if get=True.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> bytes | str | None:
        """Retrieves the value of a key asynchronously.

        Args:
            key (str): The key to retrieve.

        Returns:
            RedisResponseType: The value associated with the key, or None if the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def mget(
        self,
        keys: bytes | str | Iterable[bytes | str],
        *args: bytes | str,
    ) -> list[bytes | str | None]:
        """Gets the values of multiple keys asynchronously.

        Args:
            keys (bytes | str | Iterable[bytes | str]): A single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: A list of values corresponding to the keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def mset(self, mapping: Mapping[bytes | str, bytes | str | float]) -> bool:
        """Sets multiple keys to their respective values asynchronously.

        Args:
            mapping (Mapping[bytes | str, bytes | str | float]): A mapping of keys to values.

        Returns:
            RedisResponseType: Typically "OK" on success.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def keys(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Returns all keys matching a pattern asynchronously.

        Args:
            pattern (bytes | str): The pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of matching keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def getset(self, key: bytes | str, value: bytes | str | float) -> bytes | str | None:
        """Sets a key to a value and returns its old value asynchronously.

        Args:
            key (bytes | str): The key to set.
            value (bytes | str | float): The new value to set.

        Returns:
            RedisResponseType: The old value of the key, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def getdel(self, key: bytes | str) -> bytes | str | None:
        """Gets the value of a key and deletes it asynchronously.

        Args:
            key (bytes | str): The key to get and delete.

        Returns:
            RedisResponseType: The value of the key before deletion, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, *names: bytes | str) -> int:
        """Checks if one or more keys exist asynchronously.

        Args:
            *names (bytes | str): Variable number of keys to check.

        Returns:
            RedisResponseType: The number of keys that exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *names: bytes | str) -> int:
        """Deletes one or more keys asynchronously.

        Args:
            *names (bytes | str): Variable number of keys to delete.

        Returns:
            RedisResponseType: The number of keys deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def append(self, key: bytes | str, value: bytes | str | float) -> int:
        """Appends a value to a key's string value asynchronously.

        Args:
            key (bytes | str): The key to append to.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: The length of the string after appending.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def ttl(self, name: bytes | str) -> int:
        """Gets the remaining time to live of a key in seconds asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in seconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def type(self, name: bytes | str) -> bytes | str:
        """Determines the type of value stored at a key asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The type of the key's value (e.g., "string", "list", etc.).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> tuple[int, list[bytes | str]]:
        """Iterates over keys in the database incrementally asynchronously.

        Args:
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_keys).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[bytes | str]:
        """Provides an iterator over keys in the database asynchronously.

        Args:
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Iterator: An iterator yielding keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
