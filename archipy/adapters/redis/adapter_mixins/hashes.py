"""Redis adapter mixins for hashes operations."""

from __future__ import annotations

from collections.abc import Awaitable

from archipy.adapters.redis.adapter_mixins._shared import AsyncRedisMixinBase, SyncRedisMixinBase
from archipy.models.errors import InternalError


class RedisHashesMixin(SyncRedisMixinBase):
    """Sync Redis mixin for hashes operations."""

    def hdel(self, name: str, *keys: str | bytes) -> int:
        """Delete fields from a hash.

        Args:
            name (str): The hash key name.
            *keys (str | bytes): Fields to delete.

        Returns:
            RedisIntegerResponseType: Number of fields deleted.
        """
        # Convert keys to str for type compatibility with Redis client
        str_keys: tuple[str, ...] = tuple(str(k) if isinstance(k, bytes) else k for k in keys)
        result = self.client.hdel(name, *str_keys)
        return self._ensure_sync_int(result)

    def hexists(self, name: str, key: str) -> bool:
        """Check if a field exists in a hash.

        Args:
            name (str): The hash key name.
            key (str): Field to check.

        Returns:
            bool: True if field exists, False otherwise.
        """
        result = self.read_only_client.hexists(name, key)
        return bool(result)

    def hget(self, name: str, key: str) -> bytes | str | None:
        """Get the value of a field in a hash.

        Args:
            name (str): The hash key name.
            key (str): Field to get.

        Returns:
            str | None: Value of the field or None.
        """
        return self.read_only_client.hget(name, key)

    def hgetall(self, name: str) -> dict[bytes | str, bytes | str]:
        """Get all fields and values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            dict[str, Any]: Dictionary of field-value pairs.
        """
        result = self.read_only_client.hgetall(name)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        if result:
            return {str(k): v for k, v in result.items()}
        return {}

    def hkeys(self, name: str) -> list[bytes | str]:
        """Get all fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        result = self.read_only_client.hkeys(name)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return list(result) if result else []

    def hlen(self, name: str) -> int:
        """Get the number of fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        result = self.read_only_client.hlen(name)
        return self._ensure_sync_int(result)

    def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> int:
        """Set fields in a hash.

        Args:
            name (str): The hash key name.
            key (str | bytes | None): Single field name. Defaults to None.
            value (str | bytes | None): Single field value. Defaults to None.
            mapping (dict | None): Dictionary of field-value pairs. Defaults to None.
            items (list | None): List of field-value pairs. Defaults to None.

        Returns:
            RedisIntegerResponseType: Number of fields set.
        """
        # Convert bytes to str for type compatibility with Redis client
        str_key: str | None = str(key) if key is not None and isinstance(key, bytes) else key
        str_value: str | None = str(value) if value is not None and isinstance(value, bytes) else value
        result = self.client.hset(name, str_key, str_value, mapping, items)
        return self._ensure_sync_int(result)

    def hmget(self, name: str, keys: list, *args: str | bytes) -> list[bytes | str | None]:
        """Get values of multiple fields in a hash.

        Args:
            name (str): The hash key name.
            keys (list): List of field names.
            *args (str | bytes): Additional field names.

        Returns:
            RedisListResponseType: List of field values.
        """
        # Convert keys list and args for type compatibility, combine into single list
        keys_list: list[str] = [str(k) for k in keys] + [str(arg) if isinstance(arg, bytes) else arg for arg in args]
        result = self.read_only_client.hmget(name, keys_list)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return list(result) if result else []

    def hvals(self, name: str) -> list[bytes | str]:
        """Get all values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        result = self.read_only_client.hvals(name)
        if isinstance(result, Awaitable):
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return list(result) if result else []


class AsyncRedisHashesMixin(AsyncRedisMixinBase):
    """Async Redis mixin for hashes operations."""

    async def hdel(self, name: str, *keys: str | bytes) -> int:
        """Delete fields from hash asynchronously.

        Args:
            name (str): The hash key name.
            *keys (str | bytes): Fields to delete.

        Returns:
            RedisIntegerResponseType: Number of fields deleted.
        """
        # Convert keys to str for type compatibility
        str_keys: tuple[str, ...] = tuple(str(k) if isinstance(k, bytes) else k for k in keys)
        result = self.client.hdel(name, *str_keys)
        return await self._ensure_async_int(result)

    async def hexists(self, name: str, key: str) -> bool:
        """Check if field exists in hash asynchronously.

        Args:
            name (str): The hash key name.
            key (str): Field to check.

        Returns:
            bool: True if exists, False otherwise.
        """
        result = self.read_only_client.hexists(name, key)
        return await self._ensure_async_bool(result)

    async def hget(self, name: str, key: str) -> bytes | str | None:
        """Get field value from hash asynchronously.

        Args:
            name (str): The hash key name.
            key (str): Field to get.

        Returns:
            str | None: Value or None.
        """
        result = self.read_only_client.hget(name, key)
        resolved = await self._ensure_async_str(result)
        return str(resolved) if resolved is not None else None

    async def hgetall(self, name: str) -> dict[bytes | str, bytes | str]:
        """Get all fields and values from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            dict[str, Any]: Dictionary of field-value pairs.
        """
        result = self.read_only_client.hgetall(name)
        if isinstance(result, Awaitable):
            awaited_result = await result
            if awaited_result is None:
                return {}
            if isinstance(awaited_result, dict):
                return {str(k): v for k, v in awaited_result.items()}
            from collections.abc import Mapping

            if isinstance(awaited_result, Mapping):
                return {str(k): v for k, v in awaited_result.items()}
            return {}
        if result is None:
            return {}
        if isinstance(result, dict):
            return {str(k): v for k, v in result.items()}
        from collections.abc import Mapping

        if isinstance(result, Mapping):
            return {str(k): v for k, v in result.items()}
        return {}

    async def hkeys(self, name: str) -> list[bytes | str]:
        """Get all fields from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        result = self.read_only_client.hkeys(name)
        return await self._ensure_async_list(result)

    async def hlen(self, name: str) -> int:
        """Get number of fields in hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        result = self.read_only_client.hlen(name)
        return await self._ensure_async_int(result)

    async def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> int:
        """Set fields in hash asynchronously.

        Args:
            name (str): The hash key name.
            key (str | bytes | None): Single field name. Defaults to None.
            value (str | bytes | None): Single field value. Defaults to None.
            mapping (dict | None): Field-value pairs dict. Defaults to None.
            items (list | None): Field-value pairs list. Defaults to None.

        Returns:
            RedisIntegerResponseType: Number of fields set.
        """
        # Convert bytes to str for type compatibility with Redis client
        str_key: str | None = str(key) if key is not None and isinstance(key, bytes) else key
        str_value: str | None = str(value) if value is not None and isinstance(value, bytes) else value
        result = self.client.hset(name, str_key, str_value, mapping, items)
        return await self._ensure_async_int(result)

    async def hmget(self, name: str, keys: list, *args: str | bytes) -> list[bytes | str | None]:
        """Get multiple field values from hash asynchronously.

        Args:
            name (str): The hash key name.
            keys (list): List of field names.
            *args (str | bytes): Additional field names.

        Returns:
            RedisListResponseType: List of field values.
        """
        # Convert keys list and args for type compatibility, combine into single list
        keys_list: list[str] = [str(k) for k in keys] + [str(arg) if isinstance(arg, bytes) else arg for arg in args]
        result = self.read_only_client.hmget(name, keys_list)
        return await self._ensure_async_list(result)

    async def hvals(self, name: str) -> list[bytes | str]:
        """Get all values from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        result = self.read_only_client.hvals(name)
        return await self._ensure_async_list(result)
