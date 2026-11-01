"""Redis port mixins for connection operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from redis.asyncio.client import Pipeline as AsyncPipeline
    from redis.asyncio.cluster import ClusterPipeline as AsyncClusterPipeline
    from redis.client import Pipeline

    from archipy.adapters.redis.search_ports import (
        AsyncRedisSearchHandlePort,
        RedisSearchHandlePort,
    )


class RedisConnectionPort:
    """Sync Redis port for connection operations."""

    @abstractmethod
    def close(self) -> None:
        """Close every client and connection pool the adapter opened.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    def __enter__(self) -> Self:
        """Enter the context manager and return the adapter."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close the adapter when leaving the context manager."""
        self.close()

    @abstractmethod
    def ping(self) -> bool:
        """Tests the connection to the Redis server.

        Returns:
            RedisResponseType: The response from the server, typically "PONG".

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def flushdb(self, asynchronous: bool = False) -> bool:
        """Delete all keys in the current database.

        Args:
            asynchronous: Whether Redis should flush asynchronously. Defaults to False.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> Pipeline:
        """Returns a pipeline object for batching commands.

        Args:
            transaction (Any): If True, execute commands in a transaction. Defaults to True.
            shard_hint (Any, optional): Hint for sharding in clustered Redis.

        Returns:
            Any: A pipeline object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def config_set(self, name: str, value: str) -> bool:
        """Sets a Redis server configuration parameter.

        Commonly used to enable keyspace/subkey notifications via ``notify-keyspace-events``.

        Args:
            name (str): The configuration parameter name.
            value (str): The value to set.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def config_get(self, pattern: str = "*") -> dict[str, str]:
        """Gets Redis server configuration parameters matching a pattern.

        Args:
            pattern (str): Pattern to match configuration parameter names. Defaults to "*".

        Returns:
            RedisResponseType: A dictionary of configuration parameter names to values.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def search_index(self, name: str) -> RedisSearchHandlePort:
        """Return an index-bound RediSearch handle.

        Args:
            name: RediSearch index name.

        Returns:
            RedisSearchHandlePort: Handle for index-scoped RediSearch operations.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisConnectionPort:
    """Async Redis port for connection operations."""

    @abstractmethod
    async def aclose(self) -> None:
        """Close every client and connection pool the adapter opened asynchronously.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    async def __aenter__(self) -> Self:
        """Enter the async context manager and return the adapter."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the adapter when leaving the async context manager."""
        await self.aclose()

    @abstractmethod
    async def ping(self) -> bool:
        """Tests the connection to the Redis server asynchronously.

        Returns:
            RedisResponseType: The response from the server, typically "PONG".

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def flushdb(self, asynchronous: bool = False) -> bool:
        """Delete all keys in the current database asynchronously.

        Args:
            asynchronous: Whether Redis should flush asynchronously. Defaults to False.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_pipeline(
        self,
        transaction: Any = True,
        shard_hint: Any = None,
    ) -> AsyncPipeline | AsyncClusterPipeline:
        """Returns a pipeline object for batching commands asynchronously.

        Args:
            transaction (Any): If True, execute commands in a transaction. Defaults to True.
            shard_hint (Any, optional): Hint for sharding in clustered Redis.

        Returns:
            Any: A pipeline object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def config_set(self, name: str, value: str) -> bool:
        """Sets a Redis server configuration parameter asynchronously.

        Commonly used to enable keyspace/subkey notifications via ``notify-keyspace-events``.

        Args:
            name (str): The configuration parameter name.
            value (str): The value to set.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def config_get(self, pattern: str = "*") -> dict[str, str]:
        """Gets Redis server configuration parameters matching a pattern asynchronously.

        Args:
            pattern (str): Pattern to match configuration parameter names. Defaults to "*".

        Returns:
            RedisResponseType: A dictionary of configuration parameter names to values.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def search_index(self, name: str) -> AsyncRedisSearchHandlePort:
        """Return an index-bound async RediSearch handle.

        Args:
            name: RediSearch index name.

        Returns:
            AsyncRedisSearchHandlePort: Handle for index-scoped async RediSearch operations.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
