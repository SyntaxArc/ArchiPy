"""Redis stream ports."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.typing import KeyT, StreamIdT, XReadGroupResponse, XReadResponse


class RedisStreamsPort:
    """Synchronous Redis stream operations."""

    @abstractmethod
    def xread(
        self,
        streams: dict[KeyT, StreamIdT],
        *,
        count: int | None = None,
        block: int | None = None,
        max_count: int | None = None,
        max_size: int | None = None,
    ) -> XReadResponse:
        """Read stream entries, optionally waiting for new ones.

        The Redis 8.10+ limits apply across all streams in the request.
        """
        raise NotImplementedError

    @abstractmethod
    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[KeyT, StreamIdT],
        *,
        count: int | None = None,
        block: int | None = None,
        noack: bool = False,
        claim_min_idle_time: int | None = None,
        max_count: int | None = None,
        max_size: int | None = None,
    ) -> XReadGroupResponse:
        """Read stream entries for a consumer group.

        The Redis 8.10+ limits apply across all streams in the request.
        """
        raise NotImplementedError


class AsyncRedisStreamsPort:
    """Asynchronous Redis stream operations."""

    @abstractmethod
    async def xread(
        self,
        streams: dict[KeyT, StreamIdT],
        *,
        count: int | None = None,
        block: int | None = None,
        max_count: int | None = None,
        max_size: int | None = None,
    ) -> XReadResponse:
        """Read stream entries, optionally waiting for new ones.

        The Redis 8.10+ limits apply across all streams in the request.
        """
        raise NotImplementedError

    @abstractmethod
    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[KeyT, StreamIdT],
        *,
        count: int | None = None,
        block: int | None = None,
        noack: bool = False,
        claim_min_idle_time: int | None = None,
        max_count: int | None = None,
        max_size: int | None = None,
    ) -> XReadGroupResponse:
        """Read stream entries for a consumer group.

        The Redis 8.10+ limits apply across all streams in the request.
        """
        raise NotImplementedError
