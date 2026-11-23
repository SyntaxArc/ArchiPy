"""Redis port mixins for connection operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from redis.asyncio.client import Pipeline as AsyncPipeline
    from redis.asyncio.cluster import ClusterPipeline as AsyncClusterPipeline
    from redis.client import Pipeline
    from redis.typing import EncodableT, KeyT

    from archipy.adapters.redis.search_ports import (
        AsyncRedisSearchHandlePort,
        RedisSearchHandlePort,
    )


class RedisConnectionPort:
    """Sync Redis port for connection operations."""

    @abstractmethod
    def client_list_iter(
        self, client_type: str | None = None, *, client_ids: Sequence[EncodableT] = ()
    ) -> Iterator[dict[str, str]]:
        """Iterate over parsed records from the server's client list."""
        raise NotImplementedError

    @abstractmethod
    def backup_start(self) -> bytes | str:
        """Start a coordinated backup on the server."""
        raise NotImplementedError

    @abstractmethod
    def backup_status(self) -> dict[str | bytes, Any]:
        """Return the server's current backup status."""
        raise NotImplementedError

    @abstractmethod
    def backup_list(self) -> list[bytes | str]:
        """List files generated for the active backup."""
        raise NotImplementedError

    @abstractmethod
    def backup_seal(self) -> bytes | str:
        """Seal the backup so its files can be copied."""
        raise NotImplementedError

    @abstractmethod
    def backup_abort(self) -> bytes | str:
        """Abort the active backup."""
        raise NotImplementedError

    @abstractmethod
    def backup_cleanup(self) -> bytes | str:
        """Remove temporary artifacts of the last backup."""
        raise NotImplementedError

    @abstractmethod
    def cms_initbydim(self, key: KeyT, width: int, depth: int, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch with fixed dimensions and optional counter width."""
        raise NotImplementedError

    @abstractmethod
    def cms_initbyprob(self, key: KeyT, error: float, probability: float, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch sized by error bounds and optional counter width."""
        raise NotImplementedError

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
    async def client_list_iter(
        self, client_type: str | None = None, *, client_ids: Sequence[EncodableT] = ()
    ) -> Iterator[dict[str, str]]:
        """Iterate over parsed records from the server's client list."""
        raise NotImplementedError

    @abstractmethod
    async def backup_start(self) -> bytes | str:
        """Start a coordinated backup on the server."""
        raise NotImplementedError

    @abstractmethod
    async def backup_status(self) -> dict[str | bytes, Any]:
        """Return the server's current backup status."""
        raise NotImplementedError

    @abstractmethod
    async def backup_list(self) -> list[bytes | str]:
        """List files generated for the active backup."""
        raise NotImplementedError

    @abstractmethod
    async def backup_seal(self) -> bytes | str:
        """Seal the backup so its files can be copied."""
        raise NotImplementedError

    @abstractmethod
    async def backup_abort(self) -> bytes | str:
        """Abort the active backup."""
        raise NotImplementedError

    @abstractmethod
    async def backup_cleanup(self) -> bytes | str:
        """Remove temporary artifacts of the last backup."""
        raise NotImplementedError

    @abstractmethod
    async def cms_initbydim(self, key: KeyT, width: int, depth: int, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch with fixed dimensions and optional counter width."""
        raise NotImplementedError

    @abstractmethod
    async def cms_initbyprob(
        self, key: KeyT, error: float, probability: float, *, cell_size: int | None = None
    ) -> bool:
        """Create a Count-Min Sketch sized by error bounds and optional counter width."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
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
        await self.close()

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
