"""Redis port mixins for lists operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Literal


class RedisListsPort:
    """Sync Redis port for lists operations."""

    @abstractmethod
    def lmovem(
        self,
        first_list: str,
        second_list: str,
        *,
        src: Literal["LEFT", "RIGHT"] = "LEFT",
        dest: Literal["LEFT", "RIGHT"] = "RIGHT",
        count: int | None = None,
        mode: Literal["COUNT", "EXACTLY"] | None = None,
        ordering: Literal["OBO", "BULK"] | None = None,
    ) -> list[bytes | str] | None:
        """Atomically move elements from one list to another.

        A count requires an ordering. In Cluster, both keys must share a slot.
        """
        raise NotImplementedError

    @abstractmethod
    def blmovem(
        self,
        first_list: str,
        second_list: str,
        timeout_seconds: float,
        *,
        src: Literal["LEFT", "RIGHT"] = "LEFT",
        dest: Literal["LEFT", "RIGHT"] = "RIGHT",
        count: int | None = None,
        mode: Literal["COUNT", "EXACTLY"] | None = None,
        ordering: Literal["OBO", "BULK"] | None = None,
    ) -> list[bytes | str] | None:
        """Wait for a source list and atomically move elements to a destination list.

        A count requires an ordering. In Cluster, both keys must share a slot.
        """
        raise NotImplementedError

    @abstractmethod
    def llen(self, name: str) -> int:
        """Gets the length of a list.

        Args:
            name (str): The key of the list.

        Returns:
            RedisIntegerResponseType: The number of items in the list.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Removes and returns the first element(s) of a list.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lpush(self, name: str, *values: bytes | str | float) -> int:
        """Pushes one or more values to the start of a list.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lrange(self, name: str, start: int, end: int) -> list[bytes | str]:
        """Gets a range of elements from a list.

        Args:
            name (str): The key of the list.
            start (int): The starting index (inclusive).
            end (int): The ending index (inclusive).

        Returns:
            RedisListResponseType: A list of elements in the specified range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lrem(self, name: str, count: int, value: str) -> int:
        """Removes occurrences of a value from a list.

        Args:
            name (str): The key of the list.
            count (int): Number of occurrences to remove (0 for all).
            value (str): The value to remove.

        Returns:
            RedisIntegerResponseType: The number of elements removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lset(self, name: str, index: int, value: str) -> bool:
        """Sets the value of an element in a list by index.

        Args:
            name (str): The key of the list.
            index (int): The index to set.
            value (str): The new value.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def rpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Removes and returns the last element(s) of a list.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def rpush(self, name: str, *values: bytes | str | float) -> int:
        """Pushes one or more values to the end of a list.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisListsPort:
    """Async Redis port for lists operations."""

    @abstractmethod
    async def lmovem(
        self,
        first_list: str,
        second_list: str,
        *,
        src: Literal["LEFT", "RIGHT"] = "LEFT",
        dest: Literal["LEFT", "RIGHT"] = "RIGHT",
        count: int | None = None,
        mode: Literal["COUNT", "EXACTLY"] | None = None,
        ordering: Literal["OBO", "BULK"] | None = None,
    ) -> list[bytes | str] | None:
        """Atomically move elements from one list to another.

        A count requires an ordering. In Cluster, both keys must share a slot.
        """
        raise NotImplementedError

    @abstractmethod
    async def blmovem(
        self,
        first_list: str,
        second_list: str,
        timeout_seconds: float,
        *,
        src: Literal["LEFT", "RIGHT"] = "LEFT",
        dest: Literal["LEFT", "RIGHT"] = "RIGHT",
        count: int | None = None,
        mode: Literal["COUNT", "EXACTLY"] | None = None,
        ordering: Literal["OBO", "BULK"] | None = None,
    ) -> list[bytes | str] | None:
        """Wait for a source list and atomically move elements to a destination list.

        A count requires an ordering. In Cluster, both keys must share a slot.
        """
        raise NotImplementedError

    @abstractmethod
    async def llen(self, name: str) -> int:
        """Gets the length of a list asynchronously.

        Args:
            name (str): The key of the list.

        Returns:
            RedisIntegerResponseType: The number of items in the list.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Removes and returns the first element(s) of a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lpush(self, name: str, *values: bytes | str | float) -> int:
        """Pushes one or more values to the start of a list asynchronously.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lrange(self, name: str, start: int, end: int) -> list[bytes | str]:
        """Gets a range of elements from a list asynchronously.

        Args:
            name (str): The key of the list.
            start (int): The starting index (inclusive).
            end (int): The ending index (inclusive).

        Returns:
            RedisListResponseType: A list of elements in the specified range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lrem(self, name: str, count: int, value: str) -> int:
        """Removes occurrences of a value from a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int): Number of occurrences to remove (0 for all).
            value (str): The value to remove.

        Returns:
            RedisIntegerResponseType: The number of elements removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lset(self, name: str, index: int, value: str) -> bool:
        """Sets the value of an element in a list by index asynchronously.

        Args:
            name (str): The key of the list.
            index (int): The index to set.
            value (str): The new value.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rpop(self, name: str, count: int | None = None) -> bytes | str | list[bytes | str] | None:
        """Removes and returns the last element(s) of a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rpush(self, name: str, *values: bytes | str | float) -> int:
        """Pushes one or more values to the end of a list asynchronously.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
