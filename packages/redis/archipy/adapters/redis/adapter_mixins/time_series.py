"""Redis time series adapter methods."""

from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Unpack

from redis import RedisCluster
from redis.asyncio import RedisCluster as AsyncRedisCluster
from redis.exceptions import RedisClusterException

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase

if TYPE_CHECKING:
    from collections.abc import Iterable

    from redis.commands.timeseries import AsyncTimeSeries, TimeSeries
    from redis.typing import KeyT, TimeSeriesMRangeResponse, TimeSeriesNRangeResponse, TimeSeriesRangeResponse

    from archipy.adapters.redis.port_mixins.time_series import TimeSeriesMRangeOptions, TimeSeriesNRangeOptions


class RedisTimeSeriesMixin(SyncRedisMixinBase):
    """Synchronous Redis time series operations."""

    def _time_series_query(self) -> TimeSeries:
        """Route keyless queries through a primary, which coordinates all shards."""
        client = self.client
        series = client.ts()
        if isinstance(client, RedisCluster):
            primaries = client.get_primaries()
            if not primaries:
                msg = "No Redis primary available for a TimeSeries query"
                raise RedisClusterException(msg)
            series.execute_command = partial(client.execute_command, target_nodes=primaries[0])
        return series

    def ts_read(
        self,
        key: KeyT,
        timestamp: int | str,
        *,
        block_milliseconds: int | None = None,
        block_min_count: int | None = None,
        max_count: int | None = None,
    ) -> TimeSeriesRangeResponse:
        """Read samples after a timestamp, optionally blocking."""
        result = self.client.ts().read(
            key, timestamp, block_milliseconds=block_milliseconds, block_min_count=block_min_count, max_count=max_count
        )
        return result

    def ts_querylabels(
        self,
        *,
        label: str | None = None,
        filters: Iterable[str] | None = None,
    ) -> set[bytes | str]:
        """List matching label names or values for a requested label."""
        series = self._time_series_query()
        result = series.querylabels(label=label, filters=filters)
        return result

    def ts_nrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in ascending order."""
        result = self.client.ts().nrange(keys, from_time, to_time, **options)
        return result

    def ts_nrevrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in descending order."""
        result = self.client.ts().nrevrange(keys, from_time, to_time, **options)
        return result

    def ts_mrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in ascending order."""
        series = self._time_series_query()
        result = series.mrange(from_time, to_time, filters, **options)
        return result

    def ts_mrevrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in descending order."""
        series = self._time_series_query()
        result = series.mrevrange(from_time, to_time, filters, **options)
        return result


class AsyncRedisTimeSeriesMixin(AsyncRedisMixinBase):
    """Asynchronous Redis time series operations."""

    async def _time_series_query(self) -> AsyncTimeSeries:
        """Route keyless queries through a primary, which coordinates all shards."""
        client = self.client
        series = client.ts()
        if isinstance(client, AsyncRedisCluster):
            await client.initialize()
            primaries = client.get_primaries()
            if not primaries:
                msg = "No Redis primary available for a TimeSeries query"
                raise RedisClusterException(msg)
            series.execute_command = partial(client.execute_command, target_nodes=primaries[0])
        return series

    async def ts_read(
        self,
        key: KeyT,
        timestamp: int | str,
        *,
        block_milliseconds: int | None = None,
        block_min_count: int | None = None,
        max_count: int | None = None,
    ) -> TimeSeriesRangeResponse:
        """Read samples after a timestamp, optionally blocking."""
        result = self.client.ts().read(
            key, timestamp, block_milliseconds=block_milliseconds, block_min_count=block_min_count, max_count=max_count
        )
        return await result

    async def ts_querylabels(
        self,
        *,
        label: str | None = None,
        filters: Iterable[str] | None = None,
    ) -> set[bytes | str]:
        """List matching label names or values for a requested label."""
        series = await self._time_series_query()
        result = series.querylabels(label=label, filters=filters)
        return await result

    async def ts_nrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in ascending order."""
        result = self.client.ts().nrange(keys, from_time, to_time, **options)
        return await result

    async def ts_nrevrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in descending order."""
        result = self.client.ts().nrevrange(keys, from_time, to_time, **options)
        return await result

    async def ts_mrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in ascending order."""
        series = await self._time_series_query()
        result = series.mrange(from_time, to_time, filters, **options)
        return await result

    async def ts_mrevrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in descending order."""
        series = await self._time_series_query()
        result = series.mrevrange(from_time, to_time, filters, **options)
        return await result
