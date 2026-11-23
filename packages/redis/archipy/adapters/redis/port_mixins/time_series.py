"""Redis time series ports."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, TypedDict, Unpack

if TYPE_CHECKING:
    from collections.abc import Iterable

    from redis.typing import KeyT, TimeSeriesMRangeResponse, TimeSeriesNRangeResponse, TimeSeriesRangeResponse


class TimeSeriesNRangeOptions(TypedDict, total=False):
    """Optional arguments for a timestamp-aligned multi-key range query."""

    count: int | None
    aggregators: str | list[str] | None
    bucket_size_msec: int | None
    filter_by_ts: list[int] | None
    filter_by_min_value: int | None
    filter_by_max_value: int | None
    align: int | str | None
    latest: bool | None
    bucket_timestamp: str | None
    empty: bool | None


class TimeSeriesMRangeOptions(TypedDict, total=False):
    """Optional arguments for a label-filtered range query."""

    count: int | None
    aggregation_type: str | list[str] | None
    bucket_size_msec: int | None
    with_labels: bool | None
    filter_by_ts: list[int] | None
    filter_by_min_value: int | None
    filter_by_max_value: int | None
    groupby: str | None
    reduce: str | None
    select_labels: list[str] | None
    align: int | str | None
    latest: bool | None
    bucket_timestamp: str | None
    empty: bool | None
    exclude_empty: bool | None


class RedisTimeSeriesPort:
    """Synchronous Redis time series operations."""

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def ts_querylabels(
        self,
        *,
        label: str | None = None,
        filters: Iterable[str] | None = None,
    ) -> set[bytes | str]:
        """List matching label names or values for a requested label."""
        raise NotImplementedError

    @abstractmethod
    def ts_nrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in ascending order."""
        raise NotImplementedError

    @abstractmethod
    def ts_nrevrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in descending order."""
        raise NotImplementedError

    @abstractmethod
    def ts_mrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in ascending order."""
        raise NotImplementedError

    @abstractmethod
    def ts_mrevrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in descending order."""
        raise NotImplementedError


class AsyncRedisTimeSeriesPort:
    """Asynchronous Redis time series operations."""

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def ts_querylabels(
        self,
        *,
        label: str | None = None,
        filters: Iterable[str] | None = None,
    ) -> set[bytes | str]:
        """List matching label names or values for a requested label."""
        raise NotImplementedError

    @abstractmethod
    async def ts_nrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in ascending order."""
        raise NotImplementedError

    @abstractmethod
    async def ts_nrevrange(
        self,
        keys: list[KeyT],
        from_time: int | str,
        to_time: int | str,
        **options: Unpack[TimeSeriesNRangeOptions],
    ) -> TimeSeriesNRangeResponse:
        """Read timestamp-aligned samples in descending order."""
        raise NotImplementedError

    @abstractmethod
    async def ts_mrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in ascending order."""
        raise NotImplementedError

    @abstractmethod
    async def ts_mrevrange(
        self,
        from_time: int | str,
        to_time: int | str,
        filters: list[str],
        **options: Unpack[TimeSeriesMRangeOptions],
    ) -> TimeSeriesMRangeResponse:
        """Read series matching label filters in descending order."""
        raise NotImplementedError
