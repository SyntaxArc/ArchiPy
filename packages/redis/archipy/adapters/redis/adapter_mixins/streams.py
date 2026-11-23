"""Redis stream adapter methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase

if TYPE_CHECKING:
    from redis.typing import KeyT, StreamIdT, XReadGroupResponse, XReadResponse


class RedisStreamsMixin(SyncRedisMixinBase):
    """Synchronous Redis stream operations."""

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
        result = self.client.xread(
            streams,
            count=count,
            block=block,
            max_count=max_count,
            max_size=max_size,
        )
        return result

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
        result = self.client.xreadgroup(
            groupname,
            consumername,
            streams,
            count=count,
            block=block,
            noack=noack,
            claim_min_idle_time=claim_min_idle_time,
            max_count=max_count,
            max_size=max_size,
        )
        return result


class AsyncRedisStreamsMixin(AsyncRedisMixinBase):
    """Asynchronous Redis stream operations."""

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
        result = self.client.xread(
            streams,
            count=count,
            block=block,
            max_count=max_count,
            max_size=max_size,
        )
        return await result

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
        result = self.client.xreadgroup(
            groupname,
            consumername,
            streams,
            count=count,
            block=block,
            noack=noack,
            claim_min_idle_time=claim_min_idle_time,
            max_count=max_count,
            max_size=max_size,
        )
        return await result
