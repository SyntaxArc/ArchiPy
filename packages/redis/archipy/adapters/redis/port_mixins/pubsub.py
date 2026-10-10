"""Redis port mixins for pubsub operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class RedisPubSubPort:
    """Sync Redis port for pubsub operations."""

    @abstractmethod
    def publish(self, channel: bytes | str, message: bytes | str, **kwargs: Any) -> int:
        """Publishes a message to a channel.

        Args:
            channel (bytes | str): The channel to publish to.
            message (bytes | str): The message to publish.
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: The number of subscribers that received the message.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def pubsub_channels(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Lists active channels matching a pattern.

        Args:
            pattern (bytes | str): The pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of active channels.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def pubsub(self, **kwargs: Any) -> Any:
        """Returns a pub/sub object for subscribing to channels.

        Args:
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Any: A pub/sub object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisPubSubPort:
    """Async Redis port for pubsub operations."""

    @abstractmethod
    async def publish(self, channel: bytes | str, message: bytes | str, **kwargs: Any) -> int:
        """Publishes a message to a channel asynchronously.

        Args:
            channel (bytes | str): The channel to publish to.
            message (bytes | str): The message to publish.
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: The number of subscribers that received the message.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def pubsub_channels(self, pattern: bytes | str = "*", **kwargs: Any) -> list[bytes | str]:
        """Lists active channels matching a pattern asynchronously.

        Args:
            pattern (bytes | str): The pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of active channels.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def pubsub(self, **kwargs: Any) -> Any:
        """Returns a pub/sub object for subscribing to channels asynchronously.

        Args:
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Any: A pub/sub object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
