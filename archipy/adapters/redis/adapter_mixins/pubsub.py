"""Redis adapter mixins for pubsub operations."""

from __future__ import annotations

from typing import Any

from redis.asyncio.client import PubSub as AsyncPubSub
from redis.client import PubSub

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase


class RedisPubSubMixin(SyncRedisMixinBase):
    """Sync Redis mixin for pubsub operations."""

    def publish(self, channel: bytes | str, message: bytes | str, **kwargs: Any) -> int:
        """Publish a message to a channel.

        Args:
            channel (bytes | str): Channel name.
            message (bytes | str): Message to publish.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Number of subscribers that received the message.
        """
        return self.client.publish(channel, message, **kwargs)

    def pubsub_channels(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """List active channels matching a pattern.

        Args:
            pattern (bytes | str): Pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of channel names.
        """
        return self.client.pubsub_channels(pattern, **kwargs)

    def pubsub(self, **kwargs: Any) -> PubSub:
        """Get a PubSub object for subscribing to channels.

        Args:
            **kwargs (Any): Additional arguments.

        Returns:
            PubSub: PubSub object.
        """
        return self.client.pubsub(**kwargs)


class AsyncRedisPubSubMixin(AsyncRedisMixinBase):
    """Async Redis mixin for pubsub operations."""

    async def publish(self, channel: bytes | str, message: bytes | str, **kwargs: Any) -> int:
        """Publish message to channel asynchronously.

        Args:
            channel (bytes | str): Channel name.
            message (bytes | str): Message to publish.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Number of subscribers received message.
        """
        return await self.client.publish(channel, message, **kwargs)

    async def pubsub_channels(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """List active channels matching pattern asynchronously.

        Args:
            pattern (bytes | str): Pattern to match. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of channel names.
        """
        return await self.client.pubsub_channels(pattern, **kwargs)

    async def pubsub(self, **kwargs: Any) -> AsyncPubSub:
        """Get PubSub object for channel subscription asynchronously.

        Args:
            **kwargs (Any): Additional arguments.

        Returns:
            AsyncPubSub: PubSub object.
        """
        return self.client.pubsub(**kwargs)
