"""Redis adapter mixins for sorted_sets operations."""

from __future__ import annotations

from collections.abc import Awaitable, Iterable, Mapping
from typing import Any

from archipy.adapters.redis.adapter_mixins._shared import (
    AsyncRedisMixinBase,
    SyncRedisMixinBase,
    _normalize_zset_keys,
)
from archipy.adapters.redis.port_mixins.sorted_sets import RedisScoreCastType


class RedisSortedSetsMixin(SyncRedisMixinBase):
    """Sync Redis mixin for sorted_sets operations."""

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
        """Add members to a sorted set with scores.

        Args:
            name (bytes | str): The sorted set key name.
            mapping (Mapping[bytes | str, bytes | str | float]): Member-score pairs.
            nx (bool): Only add new elements. Defaults to False.
            xx (bool): Only update existing elements. Defaults to False.
            ch (bool): Return number of changed elements. Defaults to False.
            incr (bool): Increment existing scores. Defaults to False.
            gt (bool): Only update if score is greater. Defaults to False.
            lt (bool): Only update if score is less. Defaults to False.

        Returns:
            RedisResponseType: Number of elements added or modified.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        str_name = str(name)
        return self.client.zadd(str_name, dict_mapping, nx, xx, ch, incr, gt, lt)

    def zcard(self, name: bytes | str) -> int:
        """Get the number of members in a sorted set.

        Args:
            name (bytes | str): The sorted set key name.

        Returns:
            RedisResponseType: Number of members.
        """
        return self.client.zcard(name)

    def zcount(self, name: bytes | str, min: float | str, max: float | str) -> int:
        """Count members in a sorted set with scores in range.

        Args:
            name (bytes | str): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.

        Returns:
            RedisResponseType: Number of members in range.
        """
        return self.client.zcount(name, min, max)

    def zpopmax(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Remove and return members with highest scores from sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return self.client.zpopmax(name, count)

    def zpopmin(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Remove and return members with lowest scores from sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return self.client.zpopmin(name, count)

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
        """Get a range of members from a sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            start (int): Start index or score.
            end (int): End index or score.
            desc (bool): Sort in descending order. Defaults to False.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): Range by score. Defaults to False.
            bylex (bool): Range by lexicographical order. Defaults to False.
            offset (int | None): Offset for byscore/bylex. Defaults to None.
            num (int | None): Count for byscore/bylex. Defaults to None.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrange(
            name,
            start,
            end,
            desc,
            withscores,
            score_cast_func,
            byscore,
            bylex,
            offset,
            num,
        )

    def zrevrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Get a range of members from a sorted set in reverse order.

        Args:
            name (bytes | str): The sorted set key name.
            start (int): Start index.
            end (int): End index.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrevrange(name, start, end, withscores, score_cast_func)

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
        """Get members from a sorted set by score range.

        Args:
            name (bytes | str): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.
            start (int | None): Offset. Defaults to None.
            num (int | None): Count. Defaults to None.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrangebyscore(name, min, max, start, num, withscores, score_cast_func)

    def zrank(self, name: bytes | str, value: bytes | str | float) -> int | list[Any] | None:
        """Get the rank of a member in a sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            value (bytes | str | float): Member to find rank for.

        Returns:
            RedisResponseType: Rank of the member or None if not found.
        """
        return self.client.zrank(name, value)

    def zrem(self, name: bytes | str, *values: bytes | str | float) -> int:
        """Remove members from a sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: Number of members removed.
        """
        return self.client.zrem(name, *values)

    def zscore(self, name: bytes | str, value: bytes | str | float) -> float | None:
        """Get the score of a member in a sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            value (bytes | str | float): Member to get score for.

        Returns:
            RedisResponseType: Score of the member or None if not found.
        """
        return self.client.zscore(name, value)

    def zunion(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Compute the union of multiple sorted sets.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str | None): "SUM", "MIN", "MAX", or "COUNT". Defaults to "SUM".
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zunion(_normalize_zset_keys(keys), aggregate, withscores, score_cast_func)

    def zinter(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Compute the intersection of multiple sorted sets.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str | None): "SUM", "MIN", "MAX", or "COUNT". Defaults to "SUM".
            withscores (bool): Include scores in result. Defaults to False.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zinter(_normalize_zset_keys(keys), aggregate, withscores)

    def zincrby(self, name: bytes | str, amount: float, value: bytes | str | float) -> float | None:
        """Increment the score of a member in a sorted set.

        Args:
            name (bytes | str): The sorted set key name.
            amount (float): Amount to increment by.
            value (bytes | str | float): Member to increment.

        Returns:
            RedisResponseType: New score of the member.
        """
        return self.client.zincrby(name, amount, value)


class AsyncRedisSortedSetsMixin(AsyncRedisMixinBase):
    """Async Redis mixin for sorted_sets operations."""

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
        """Add members to sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            mapping (Mapping[bytes | str, bytes | str | float]): Member-score pairs.
            nx (bool): Only add new elements. Defaults to False.
            xx (bool): Only update existing. Defaults to False.
            ch (bool): Return changed count. Defaults to False.
            incr (bool): Increment scores. Defaults to False.
            gt (bool): Only if greater. Defaults to False.
            lt (bool): Only if less. Defaults to False.

        Returns:
            RedisResponseType: Number of elements added or modified.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        if isinstance(mapping, dict):
            dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        else:
            dict_mapping = {str(k): v for k, v in mapping.items()}
        str_name = str(name)
        result = self.client.zadd(str_name, dict_mapping, nx, xx, ch, incr, gt, lt)
        if isinstance(result, Awaitable):
            return await result
        return result

    async def zcard(self, name: bytes | str) -> int:
        """Get number of members in sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.

        Returns:
            RedisResponseType: Number of members.
        """
        return await self.client.zcard(name)

    async def zcount(self, name: bytes | str, min: float | str, max: float | str) -> int:
        """Count members in score range asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.

        Returns:
            RedisResponseType: Number of members in range.
        """
        return await self.client.zcount(name, min, max)

    async def zpopmax(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Pop highest scored members asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            count (int | None): Number to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return await self.client.zpopmax(name, count)

    async def zpopmin(
        self,
        name: bytes | str,
        count: int | None = None,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Pop lowest scored members asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            count (int | None): Number to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return await self.client.zpopmin(name, count)

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
        """Get range from sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            start (int): Start index or score.
            end (int): End index or score.
            desc (bool): Descending order. Defaults to False.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.
            byscore (bool): Range by score. Defaults to False.
            bylex (bool): Range by lex. Defaults to False.
            offset (int | None): Offset for byscore/bylex. Defaults to None.
            num (int | None): Count for byscore/bylex. Defaults to None.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrange(
            name,
            start,
            end,
            desc,
            withscores,
            score_cast_func,
            byscore,
            bylex,
            offset,
            num,
        )

    async def zrevrange(
        self,
        name: bytes | str,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Get reverse range from sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            start (int): Start index.
            end (int): End index.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrevrange(name, start, end, withscores, score_cast_func)

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
        """Get members by score range asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.
            start (int | None): Offset. Defaults to None.
            num (int | None): Count. Defaults to None.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrangebyscore(name, min, max, start, num, withscores, score_cast_func)

    async def zrank(self, name: bytes | str, value: bytes | str | float) -> int | list[Any] | None:
        """Get rank of member in sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            value (bytes | str | float): Member to find rank for.

        Returns:
            RedisResponseType: Rank or None if not found.
        """
        return await self.client.zrank(name, value)

    async def zrem(self, name: bytes | str, *values: bytes | str | float) -> int:
        """Remove members from sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: Number of members removed.
        """
        return await self.client.zrem(name, *values)

    async def zscore(self, name: bytes | str, value: bytes | str | float) -> float | None:
        """Get score of member in sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            value (bytes | str | float): Member to get score for.

        Returns:
            RedisResponseType: Score or None if not found.
        """
        return await self.client.zscore(name, value)

    async def zunion(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Compute the union of multiple sorted sets asynchronously.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str | None): "SUM", "MIN", "MAX", or "COUNT". Defaults to "SUM".
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zunion(_normalize_zset_keys(keys), aggregate, withscores, score_cast_func)

    async def zinter(
        self,
        keys: Mapping[bytes | str, float] | Iterable[bytes | str],
        aggregate: str | None = None,
        withscores: bool = False,
    ) -> list[bytes | str] | list[tuple[bytes | str, Any]] | list[list[Any]]:
        """Compute the intersection of multiple sorted sets asynchronously.

        Args:
            keys (Mapping[bytes | str, float] | Iterable[bytes | str]): Sorted set keys, optionally
                mapped to per-set weights.
            aggregate (str | None): "SUM", "MIN", "MAX", or "COUNT". Defaults to "SUM".
            withscores (bool): Include scores in result. Defaults to False.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zinter(_normalize_zset_keys(keys), aggregate, withscores)

    async def zincrby(self, name: bytes | str, amount: float, value: bytes | str | float) -> float | None:
        """Increment member score in sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.
            amount (float): Amount to increment by.
            value (bytes | str | float): Member to increment.

        Returns:
            RedisResponseType: New score of the member.
        """
        return await self.client.zincrby(name, amount, value)
