"""Redis port mixins for hashes operations."""

from __future__ import annotations

from abc import abstractmethod


class RedisHashesPort:
    """Sync Redis port for hashes operations."""

    @abstractmethod
    def hdel(self, name: str, *keys: str | bytes) -> int:
        """Deletes one or more fields from a hash.

        Args:
            name (str): The key of the hash.
            *keys (str | bytes): Fields to delete.

        Returns:
            RedisIntegerResponseType: The number of fields deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hexists(self, name: str, key: str) -> bool:
        """Checks if a field exists in a hash.

        Args:
            name (str): The key of the hash.
            key (str): The field to check.

        Returns:
            bool: True if the field exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hget(self, name: str, key: str) -> bytes | str | None:
        """Gets the value of a field in a hash.

        Args:
            name (str): The key of the hash.
            key (str): The field to get.

        Returns:
            str | None: The value of the field, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hgetall(self, name: str) -> dict[bytes | str, bytes | str]:
        """Gets all fields and values in a hash.

        Args:
            name (str): The key of the hash.

        Returns:
            dict[str, Any]: A dictionary of field/value pairs.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hkeys(self, name: str) -> list[bytes | str]:
        """Gets all fields in a hash.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of fields in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hlen(self, name: str) -> int:
        """Gets the number of fields in a hash.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisIntegerResponseType: The number of fields in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> int:
        """Sets one or more fields in a hash.

        Args:
            name (str): The key of the hash.
            key (str | bytes, optional): A single field to set.
            value (str | bytes, optional): The value for the single field.
            mapping (dict, optional): A dictionary of field/value pairs.
            items (list, optional): A list of field/value pairs.

        Returns:
            RedisIntegerResponseType: The number of fields added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hmget(self, name: str, keys: list, *args: str | bytes) -> list[bytes | str | None]:
        """Gets the values of multiple fields in a hash.

        Args:
            name (str): The key of the hash.
            keys (list): A list of fields to get.
            *args (str | bytes): Additional fields to get.

        Returns:
            RedisListResponseType: A list of values for the specified fields.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hvals(self, name: str) -> list[bytes | str]:
        """Gets all values in a hash.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of values in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncRedisHashesPort:
    """Async Redis port for hashes operations."""

    @abstractmethod
    async def hdel(self, name: str, *keys: str | bytes) -> int:
        """Deletes one or more fields from a hash asynchronously.

        Args:
            name (str): The key of the hash.
            *keys (str | bytes): Fields to delete.

        Returns:
            RedisIntegerResponseType: The number of fields deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hexists(self, name: str, key: str) -> bool:
        """Checks if a field exists in a hash asynchronously.

        Args:
            name (str): The key of the hash.
            key (str): The field to check.

        Returns:
            bool: True if the field exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hget(self, name: str, key: str) -> bytes | str | None:
        """Gets the value of a field in a hash asynchronously.

        Args:
            name (str): The key of the hash.
            key (str): The field to get.

        Returns:
            str | None: The value of the field, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hgetall(self, name: str) -> dict[bytes | str, bytes | str]:
        """Gets all fields and values in a hash asynchronously.

        Args:
            name (str): The key of the hash.

        Returns:
            dict[str, Any]: A dictionary of field/value pairs.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hkeys(self, name: str) -> list[bytes | str]:
        """Gets all fields in a hash asynchronously.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of fields in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hlen(self, name: str) -> int:
        """Gets the number of fields in a hash asynchronously.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisIntegerResponseType: The number of fields in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> int:
        """Sets one or more fields in a hash asynchronously.

        Args:
            name (str): The key of the hash.
            key (str | bytes, optional): A single field to set.
            value (str | bytes, optional): The value for the single field.
            mapping (dict, optional): A dictionary of field/value pairs.
            items (list, optional): A list of field/value pairs.

        Returns:
            RedisIntegerResponseType: The number of fields added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hmget(self, name: str, keys: list, *args: str | bytes) -> list[bytes | str | None]:
        """Gets the values of multiple fields in a hash asynchronously.

        Args:
            name (str): The key of the hash.
            keys (list): A list of fields to get.
            *args (str | bytes): Additional fields to get.

        Returns:
            RedisListResponseType: A list of values for the specified fields.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hvals(self, name: str) -> list[bytes | str]:
        """Gets all values in a hash asynchronously.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of values in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
