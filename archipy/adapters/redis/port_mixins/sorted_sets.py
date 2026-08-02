"""Redis port mixins for sorted_sets operations."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterable, Mapping
from typing import Any

RedisScoreCastType = type | Callable


class RedisSortedSetsPort:
    """Sync Redis port for sorted_sets operations."""

    @abstractmethod
    def zadd(
        self,
        name: bytes | str,
        mapping: Mapping[bytes | str, bytes | str | float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> int | float | None:
        """Adds members with scores to a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            mapping (Mapping[bytes | str, bytes | str | float]): A mapping of members to scores.
            nx (bool): If True, only add new elements. Defaults to False.
            xx (bool): If True, only update existing elements. Defaults to False.
            ch (bool): If True, return the number of changed elements. Defaults to False.
            incr (bool): If True, increment scores instead of setting. Defaults to False.
            gt (bool): If True, only update if new score is greater. Defaults to False.
            lt (bool): If True, only update if new score is less. Defaults to False.

        Returns:
            RedisResponseType: The number of elements added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zcard(self, name: bytes | str) -> int:
        """Gets the number of members in a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.

        Returns:
            RedisResponseType: The cardinality (size) of the sorted set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zcount(self, name: bytes | str, min: float | str, max: float | str) -> int:
        """Counts members in a sorted set within a score range.

        Args:
            name (bytes | str): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).

        Returns:
            RedisResponseType: The number of members within the score range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zpopmax(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Removes and returns members with the highest scores from a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zpopmin(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Removes and returns members with the lowest scores from a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
        byscore: bool = False,
        bylex: bool = False,
        offset: int | None = None,
        num: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets a range of members from a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            start (int): The starting index or score (depending on byscore).
            end (int): The ending index or score (depending on byscore).
            desc (bool): If True, sort in descending order. Defaults to False.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): If True, range by score instead of rank. Defaults to False.
            bylex (bool): If True, range by lexicographical order. Defaults to False.
            offset (int, optional): Offset for byscore or bylex.
            num (int, optional): Number of elements for byscore or bylex.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrevrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets a range of members from a sorted set in reverse order.

        Args:
            name (bytes | str): The key of the sorted set.
            start (int): The starting index.
            end (int): The ending index.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrangebyscore(
        self,
        name: bytes | str,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets members from a sorted set by score range.

        Args:
            name (bytes | str): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).
            start (int, optional): Starting offset.
            num (int, optional): Number of elements to return.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrank(self, name: bytes | str, value: bytes | str | float) -> int | list[Any] | None:
        """Gets the rank of a member in a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            value (bytes | str | float): The member to find.

        Returns:
            RedisResponseType: The rank (index) of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrem(self, name: bytes | str, *values: bytes | str | float) -> int:
        """Removes one or more members from a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zscore(self, name: bytes | str, value: bytes | str | float) -> float | None:
        """Gets the score of a member in a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            value (bytes | str | float): The member to check.

        Returns:
            RedisResponseType: The score of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zunion(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Computes the union of multiple sorted sets.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str, optional): How to combine scores across sets: "SUM", "MIN", "MAX", or the
                Redis 8.8 "COUNT" aggregator, which scores each element by the number of input sets
                containing it (or the sum of their weights, if weights are given). Defaults to "SUM".
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zinter(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Computes the intersection of multiple sorted sets.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str, optional): How to combine scores across sets: "SUM", "MIN", "MAX", or the
                Redis 8.8 "COUNT" aggregator, which scores each element by the number of input sets
                containing it (or the sum of their weights, if weights are given). Defaults to "SUM".
            withscores (bool): If True, return scores with members. Defaults to False.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zincrby(self, name: bytes | str, amount: float, value: bytes | str | float) -> float | None:
        """Increments the score of a member in a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.
            amount (float): The amount to increment by.
            value (bytes | str | float): The member to increment.

        Returns:
            RedisResponseType: The new score of the member.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisSortedSetsPort:
    """Async Redis port for sorted_sets operations."""

    @abstractmethod
    async def zadd(
        self,
        name: bytes | str,
        mapping: Mapping[bytes | str, bytes | str | float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> int | float | None:
        """Adds members with scores to a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            mapping (Mapping[bytes | str, bytes | str | float]): A mapping of members to scores.
            nx (bool): If True, only add new elements. Defaults to False.
            xx (bool): If True, only update existing elements. Defaults to False.
            ch (bool): If True, return the number of changed elements. Defaults to False.
            incr (bool): If True, increment scores instead of setting. Defaults to False.
            gt (bool): If True, only update if new score is greater. Defaults to False.
            lt (bool): If True, only update if new score is less. Defaults to False.

        Returns:
            RedisResponseType: The number of elements added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zcard(self, name: bytes | str) -> int:
        """Gets the number of members in a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.

        Returns:
            RedisResponseType: The cardinality (size) of the sorted set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zcount(self, name: bytes | str, min: float | str, max: float | str) -> int:
        """Counts members in a sorted set within a score range asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).

        Returns:
            RedisResponseType: The number of members within the score range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zpopmax(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Removes and returns members with the highest scores from a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zpopmin(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Removes and returns members with the lowest scores from a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
        byscore: bool = False,
        bylex: bool = False,
        offset: int | None = None,
        num: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets a range of members from a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            start (int): The starting index or score (depending on byscore).
            end (int): The ending index or score (depending on byscore).
            desc (bool): If True, sort in descending order. Defaults to False.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): If True, range by score instead of rank. Defaults to False.
            bylex (bool): If True, range by lexicographical order. Defaults to False.
            offset (int, optional): Offset for byscore or bylex.
            num (int, optional): Number of elements for byscore or bylex.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrevrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets a range of members from a sorted set in reverse order asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            start (int): The starting index.
            end (int): The ending index.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrangebyscore(
        self,
        name: bytes | str,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Gets members from a sorted set by score range asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).
            start (int, optional): Starting offset.
            num (int, optional): Number of elements to return.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrank(self, name: bytes | str, value: bytes | str | float) -> int | list[Any] | None:
        """Gets the rank of a member in a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            value (bytes | str | float): The member to find.

        Returns:
            RedisResponseType: The rank (index) of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrem(self, name: bytes | str, *values: bytes | str | float) -> int:
        """Removes one or more members from a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zscore(self, name: bytes | str, value: bytes | str | float) -> float | None:
        """Gets the score of a member in a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            value (bytes | str | float): The member to check.

        Returns:
            RedisResponseType: The score of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zunion(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Computes the union of multiple sorted sets asynchronously.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str, optional): How to combine scores across sets: "SUM", "MIN", "MAX", or the
                Redis 8.8 "COUNT" aggregator, which scores each element by the number of input sets
                containing it (or the sum of their weights, if weights are given). Defaults to "SUM".
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zinter(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Computes the intersection of multiple sorted sets asynchronously.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str, optional): How to combine scores across sets: "SUM", "MIN", "MAX", or the
                Redis 8.8 "COUNT" aggregator, which scores each element by the number of input sets
                containing it (or the sum of their weights, if weights are given). Defaults to "SUM".
            withscores (bool): If True, return scores with members. Defaults to False.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zincrby(self, name: bytes | str, amount: float, value: bytes | str | float) -> float | None:
        """Increments the score of a member in a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.
            amount (float): The amount to increment by.
            value (bytes | str | float): The member to increment.

        Returns:
            RedisResponseType: The new score of the member.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
