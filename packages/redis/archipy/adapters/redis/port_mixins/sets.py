"""Redis port mixins for sets operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from redis.commands.core import SetDataPersistOptions
    from redis.typing import AbsExpiryT, ExpiryT, FieldT, KeyT

    from archipy.adapters.redis.async_iteration import AwaitableAsyncIterator

_set = set


class RedisSetsPort:
    """Sync Redis port for sets operations."""

    @abstractmethod
    def saddex(
        self,
        name: KeyT,
        *members: FieldT,
        ex: ExpiryT | str | None = None,
        px: ExpiryT | str | None = None,
        exat: AbsExpiryT | None = None,
        pxat: AbsExpiryT | None = None,
        data_persist_option: SetDataPersistOptions | None = None,
        keepttl: bool = False,
    ) -> int:
        """Add set members with optional expiration and existence conditions."""
        raise NotImplementedError

    @abstractmethod
    def sexpire(
        self,
        name: KeyT,
        seconds: ExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration in seconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    def spexpire(
        self,
        name: KeyT,
        milliseconds: ExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration in milliseconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    def sexpireat(
        self,
        name: KeyT,
        unix_time_seconds: AbsExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration at a Unix timestamp in seconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    def spexpireat(
        self,
        name: KeyT,
        unix_time_milliseconds: AbsExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration at a Unix timestamp in milliseconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    def sttl(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's remaining lifetime in seconds."""
        raise NotImplementedError

    @abstractmethod
    def spttl(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's remaining lifetime in milliseconds."""
        raise NotImplementedError

    @abstractmethod
    def sexpiretime(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's expiration as a Unix timestamp in seconds."""
        raise NotImplementedError

    @abstractmethod
    def spexpiretime(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's expiration as a Unix timestamp in milliseconds."""
        raise NotImplementedError

    @abstractmethod
    def spersist(self, name: KeyT, *members: FieldT) -> list[int]:
        """Remove expiration from the members and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    def sdiffcard(
        self,
        keys: Sequence[bytes | str],
        *,
        limit: int = 0,
    ) -> int:
        """Return the cardinality of the set difference."""
        raise NotImplementedError

    @abstractmethod
    def sunioncard(
        self,
        keys: Sequence[bytes | str],
        *,
        limit: int = 0,
        approx: bool = False,
    ) -> int:
        """Return the cardinality of the set union."""
        raise NotImplementedError

    @abstractmethod
    def sscan(
        self,
        name: bytes | str,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[bytes | str]]:
        """Iterates over members of a set incrementally.

        Args:
            name (bytes | str): The key of the set.
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_members).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sscan_iter(
        self,
        name: bytes | str,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator[bytes | str]:
        """Provides an iterator over members of a set.

        Args:
            name (bytes | str): The key of the set.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            Iterator: An iterator yielding set members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sadd(self, name: str, *values: bytes | str | float) -> int:
        """Adds one or more members to a set.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: The number of members added (excluding duplicates).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scard(self, name: str) -> int:
        """Gets the number of members in a set.

        Args:
            name (str): The key of the set.

        Returns:
            RedisIntegerResponseType: The cardinality (size) of the set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sismember(self, name: str, value: str) -> bool:
        """Checks if a value is a member of a set.

        Args:
            name (str): The key of the set.
            value (str): The value to check.

        Returns:
            bool: True if the value is a member, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def smembers(self, name: str) -> _set[bytes | str]:
        """Gets all members of a set.

        Args:
            name (str): The key of the set.

        Returns:
            RedisSetResponseType: A set of all members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Removes and returns one or more random members from a set.

        Args:
            name (str): The key of the set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            bytes | float | int | str | list | None: The popped member(s), or None if the set is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def srem(self, name: str, *values: bytes | str | float) -> int:
        """Removes one or more members from a set.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sunion(self, keys: bytes | str, *args: bytes | str) -> _set[bytes | str]:
        """Gets the union of multiple sets.

        Args:
            keys (bytes | str): Name of the first key.
            *args (bytes | str): Additional key names.

        Returns:
            RedisSetResponseType: A set containing members of the resulting union.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisSetsPort:
    """Async Redis port for sets operations."""

    @abstractmethod
    async def saddex(
        self,
        name: KeyT,
        *members: FieldT,
        ex: ExpiryT | str | None = None,
        px: ExpiryT | str | None = None,
        exat: AbsExpiryT | None = None,
        pxat: AbsExpiryT | None = None,
        data_persist_option: SetDataPersistOptions | None = None,
        keepttl: bool = False,
    ) -> int:
        """Add set members with optional expiration and existence conditions."""
        raise NotImplementedError

    @abstractmethod
    async def sexpire(
        self,
        name: KeyT,
        seconds: ExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration in seconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    async def spexpire(
        self,
        name: KeyT,
        milliseconds: ExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration in milliseconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    async def sexpireat(
        self,
        name: KeyT,
        unix_time_seconds: AbsExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration at a Unix timestamp in seconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    async def spexpireat(
        self,
        name: KeyT,
        unix_time_milliseconds: AbsExpiryT,
        *members: FieldT,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> list[int]:
        """Set member expiration at a Unix timestamp in milliseconds and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    async def sttl(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's remaining lifetime in seconds."""
        raise NotImplementedError

    @abstractmethod
    async def spttl(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's remaining lifetime in milliseconds."""
        raise NotImplementedError

    @abstractmethod
    async def sexpiretime(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's expiration as a Unix timestamp in seconds."""
        raise NotImplementedError

    @abstractmethod
    async def spexpiretime(self, name: KeyT, *members: FieldT) -> list[int]:
        """Return each member's expiration as a Unix timestamp in milliseconds."""
        raise NotImplementedError

    @abstractmethod
    async def spersist(self, name: KeyT, *members: FieldT) -> list[int]:
        """Remove expiration from the members and return per-member status codes."""
        raise NotImplementedError

    @abstractmethod
    async def sdiffcard(
        self,
        keys: Sequence[bytes | str],
        *,
        limit: int = 0,
    ) -> int:
        """Return the cardinality of the set difference."""
        raise NotImplementedError

    @abstractmethod
    async def sunioncard(
        self,
        keys: Sequence[bytes | str],
        *,
        limit: int = 0,
        approx: bool = False,
    ) -> int:
        """Return the cardinality of the set union."""
        raise NotImplementedError

    @abstractmethod
    async def sscan(
        self,
        name: bytes | str,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> tuple[int, list[bytes | str]]:
        """Iterates over members of a set incrementally asynchronously.

        Args:
            name (bytes | str): The key of the set.
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_members).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sscan_iter(
        self,
        name: bytes | str,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> AwaitableAsyncIterator[bytes | str]:
        """Provides an iterator over members of a set asynchronously.

        Args:
            name (bytes | str): The key of the set.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            Iterator: An iterator yielding set members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sadd(self, name: str, *values: bytes | str | float) -> int:
        """Adds one or more members to a set asynchronously.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: The number of members added (excluding duplicates).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scard(self, name: str) -> int:
        """Gets the number of members in a set asynchronously.

        Args:
            name (str): The key of the set.

        Returns:
            RedisIntegerResponseType: The cardinality (size) of the set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sismember(self, name: str, value: str) -> bool:
        """Checks if a value is a member of a set asynchronously.

        Args:
            name (str): The key of the set.
            value (str): The value to check.

        Returns:
            bool: True if the value is a member, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def smembers(self, name: str) -> _set[bytes | str]:
        """Gets all members of a set asynchronously.

        Args:
            name (str): The key of the set.

        Returns:
            RedisSetResponseType: A set of all members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Removes and returns one or more random members from a set asynchronously.

        Args:
            name (str): The key of the set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            bytes | float | int | str | list | None: The popped member(s), or None if the set is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def srem(self, name: str, *values: bytes | str | float) -> int:
        """Removes one or more members from a set asynchronously.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sunion(self, keys: bytes | str, *args: bytes | str) -> _set[bytes | str]:
        """Gets the union of multiple sets asynchronously.

        Args:
            keys (bytes | str): Name of the first key.
            *args (bytes | str): Additional key names.

        Returns:
            RedisSetResponseType: A set containing members of the resulting union.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
