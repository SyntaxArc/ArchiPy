"""Redis port mixins for arrays operations."""

from __future__ import annotations

from abc import abstractmethod


class RedisArraysPort:
    """Sync Redis port for arrays operations."""

    @abstractmethod
    def arset(self, name: bytes | str, index: int, *values: bytes | str | float) -> int:
        """Sets one or more contiguous values in the array stored at a key.

        Values are stored at consecutive indices beginning at ``index`` in the Redis 8.8 array data
        structure, an index-addressable, sparse-friendly container.

        Args:
            name (bytes | str): The key of the array.
            index (int): The starting index (0 to 2**64-1) to set values at.
            *values (bytes | str | float): The values to store at consecutive indices.

        Returns:
            RedisResponseType: The number of previously empty slots that were set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def arget(self, name: bytes | str, index: int) -> bytes | str | None:
        """Gets the value at an index in the array stored at a key.

        Args:
            name (bytes | str): The key of the array.
            index (int): The index to read.

        Returns:
            RedisResponseType: The value at the index, or None if unset or the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def arlen(self, name: bytes | str) -> int:
        """Gets the number of populated elements in an array.

        Args:
            name (bytes | str): The key of the array.

        Returns:
            RedisResponseType: The number of populated elements.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def ardel(self, name: bytes | str, *indices: int) -> int:
        """Deletes one or more indices from an array.

        Args:
            name (bytes | str): The key of the array.
            *indices (int): The indices to delete.

        Returns:
            RedisResponseType: The number of elements deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def arring(self, name: bytes | str, size: int, *values: bytes | str | float) -> int:
        """Inserts values into an array as a fixed-size ring buffer (sliding window).

        Each value is placed at ``insert_idx % size``, wrapping back to index 0 and overwriting
        older values once full, in a single atomic operation equivalent to ``RPUSH`` + ``LTRIM``.

        Args:
            name (bytes | str): The key of the array.
            size (int): The fixed size of the ring buffer.
            *values (bytes | str | float): The values to insert.

        Returns:
            RedisResponseType: The last index where a value was inserted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisArraysPort:
    """Async Redis port for arrays operations."""

    @abstractmethod
    async def arset(self, name: bytes | str, index: int, *values: bytes | str | float) -> int:
        """Sets one or more contiguous values in the array stored at a key asynchronously.

        Values are stored at consecutive indices beginning at ``index`` in the Redis 8.8 array data
        structure, an index-addressable, sparse-friendly container.

        Args:
            name (bytes | str): The key of the array.
            index (int): The starting index (0 to 2**64-1) to set values at.
            *values (bytes | str | float): The values to store at consecutive indices.

        Returns:
            RedisResponseType: The number of previously empty slots that were set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def arget(self, name: bytes | str, index: int) -> bytes | str | None:
        """Gets the value at an index in the array stored at a key asynchronously.

        Args:
            name (bytes | str): The key of the array.
            index (int): The index to read.

        Returns:
            RedisResponseType: The value at the index, or None if unset or the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def arlen(self, name: bytes | str) -> int:
        """Gets the number of populated elements in an array asynchronously.

        Args:
            name (bytes | str): The key of the array.

        Returns:
            RedisResponseType: The number of populated elements.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def ardel(self, name: bytes | str, *indices: int) -> int:
        """Deletes one or more indices from an array asynchronously.

        Args:
            name (bytes | str): The key of the array.
            *indices (int): The indices to delete.

        Returns:
            RedisResponseType: The number of elements deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def arring(self, name: bytes | str, size: int, *values: bytes | str | float) -> int:
        """Inserts values into an array as a fixed-size ring buffer (sliding window) asynchronously.

        Each value is placed at ``insert_idx % size``, wrapping back to index 0 and overwriting
        older values once full, in a single atomic operation equivalent to ``RPUSH`` + ``LTRIM``.

        Args:
            name (bytes | str): The key of the array.
            size (int): The fixed size of the ring buffer.
            *values (bytes | str | float): The values to insert.

        Returns:
            RedisResponseType: The last index where a value was inserted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
