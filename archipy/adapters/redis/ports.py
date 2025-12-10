from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator, Mapping
from datetime import datetime, timedelta
from typing import Any

# Define generic type variables for better type hinting
RedisAbsExpiryType = int | datetime
RedisExpiryType = int | timedelta
RedisIntegerResponseType = int
RedisKeyType = bytes | str
RedisListResponseType = list[Any]
RedisSetResponseType = set[Any]
RedisPatternType = bytes | str
RedisResponseType = Any
RedisSetType = int | bytes | str | float
RedisScoreCastType = type | Callable


class RedisPort:
    """Interface for Redis operations providing a standardized access pattern.

    This interface defines the contract for Redis adapters, ensuring consistent
    implementation of Redis operations across different adapters. It covers all
    essential Redis functionality including key-value operations, collections
    (lists, sets, sorted sets, hashes), and pub/sub capabilities.

    Implementing classes should provide concrete implementations for all
    methods, typically by wrapping a Redis client library.
    """

    @abstractmethod
    def ping(self) -> RedisResponseType:
        """Tests the connection to the Redis server.

        Returns:
            RedisResponseType: The response from the server, typically "PONG".

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def pttl(self, name: bytes | str) -> RedisResponseType:
        """Gets the remaining time to live of a key in milliseconds.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in milliseconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def incrby(self, name: RedisKeyType, amount: int = 1) -> RedisResponseType:
        """Increments the integer value of a key by the given amount.

        Args:
            name (RedisKeyType): The key to increment.
            amount (int): The amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after incrementing.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def set(
        self,
        name: RedisKeyType,
        value: RedisSetType,
        ex: RedisExpiryType | None = None,
        px: RedisExpiryType | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: RedisAbsExpiryType | None = None,
        pxat: RedisAbsExpiryType | None = None,
    ) -> RedisResponseType:
        """Sets a key to a value with optional expiration and conditions.

        Args:
            name (RedisKeyType): The key to set.
            value (RedisSetType): The value to set for the key.
            ex (RedisExpiryType, optional): Expiration time in seconds or timedelta.
            px (RedisExpiryType, optional): Expiration time in milliseconds or timedelta.
            nx (bool): If True, set only if the key does not exist. Defaults to False.
            xx (bool): If True, set only if the key already exists. Defaults to False.
            keepttl (bool): If True, retain the existing TTL. Defaults to False.
            get (bool): If True, return the old value before setting. Defaults to False.
            exat (RedisAbsExpiryType, optional): Absolute expiration time as Unix timestamp or datetime.
            pxat (RedisAbsExpiryType, optional): Absolute expiration time in milliseconds or datetime.

        Returns:
            RedisResponseType: The result of the operation, often "OK" or the old value if get=True.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str) -> RedisResponseType:
        """Retrieves the value of a key.

        Args:
            key (str): The key to retrieve.

        Returns:
            RedisResponseType: The value associated with the key, or None if the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def mget(
        self,
        keys: RedisKeyType | Iterable[RedisKeyType],
        *args: bytes | str,
    ) -> RedisResponseType:
        """Gets the values of multiple keys.

        Args:
            keys (RedisKeyType | Iterable[RedisKeyType]): A single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: A list of values corresponding to the keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def mset(self, mapping: Mapping[RedisKeyType, bytes | str | float]) -> RedisResponseType:
        """Sets multiple keys to their respective values.

        Args:
            mapping (Mapping[RedisKeyType, bytes | str | float]): A mapping of keys to values.

        Returns:
            RedisResponseType: Typically "OK" on success.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def keys(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Returns all keys matching a pattern.

        Args:
            pattern (RedisPatternType): The pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of matching keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def getset(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Sets a key to a value and returns its old value.

        Args:
            key (RedisKeyType): The key to set.
            value (bytes | str | float): The new value to set.

        Returns:
            RedisResponseType: The old value of the key, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def getdel(self, key: bytes | str) -> RedisResponseType:
        """Gets the value of a key and deletes it.

        Args:
            key (bytes | str): The key to get and delete.

        Returns:
            RedisResponseType: The value of the key before deletion, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, *names: bytes | str) -> RedisResponseType:
        """Checks if one or more keys exist.

        Args:
            *names (bytes | str): Variable number of keys to check.

        Returns:
            RedisResponseType: The number of keys that exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, *names: bytes | str) -> RedisResponseType:
        """Deletes one or more keys.

        Args:
            *names (bytes | str): Variable number of keys to delete.

        Returns:
            RedisResponseType: The number of keys deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def append(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Appends a value to a key's string value.

        Args:
            key (RedisKeyType): The key to append to.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: The length of the string after appending.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def ttl(self, name: bytes | str) -> RedisResponseType:
        """Gets the remaining time to live of a key in seconds.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in seconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def type(self, name: bytes | str) -> RedisResponseType:
        """Determines the type of value stored at a key.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The type of the key's value (e.g., "string", "list", etc.).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def llen(self, name: str) -> RedisIntegerResponseType:
        """Gets the length of a list.

        Args:
            name (str): The key of the list.

        Returns:
            RedisIntegerResponseType: The number of items in the list.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lpop(self, name: str, count: int | None = None) -> Any:
        """Removes and returns the first element(s) of a list.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Pushes one or more values to the start of a list.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lrange(self, name: str, start: int, end: int) -> RedisListResponseType:
        """Gets a range of elements from a list.

        Args:
            name (str): The key of the list.
            start (int): The starting index (inclusive).
            end (int): The ending index (inclusive).

        Returns:
            RedisListResponseType: A list of elements in the specified range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lrem(self, name: str, count: int, value: str) -> RedisIntegerResponseType:
        """Removes occurrences of a value from a list.

        Args:
            name (str): The key of the list.
            count (int): Number of occurrences to remove (0 for all).
            value (str): The value to remove.

        Returns:
            RedisIntegerResponseType: The number of elements removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def lset(self, name: str, index: int, value: str) -> bool:
        """Sets the value of an element in a list by index.

        Args:
            name (str): The key of the list.
            index (int): The index to set.
            value (str): The new value.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def rpop(self, name: str, count: int | None = None) -> Any:
        """Removes and returns the last element(s) of a list.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def rpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Pushes one or more values to the end of a list.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> RedisResponseType:
        """Iterates over keys in the database incrementally.

        Args:
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_keys).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator:
        """Provides an iterator over keys in the database.

        Args:
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Iterator: An iterator yielding keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sscan(
        self,
        name: RedisKeyType,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> RedisResponseType:
        """Iterates over members of a set incrementally.

        Args:
            name (RedisKeyType): The key of the set.
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_members).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sscan_iter(
        self,
        name: RedisKeyType,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator:
        """Provides an iterator over members of a set.

        Args:
            name (RedisKeyType): The key of the set.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            Iterator: An iterator yielding set members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sadd(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Adds one or more members to a set.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: The number of members added (excluding duplicates).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def scard(self, name: str) -> RedisIntegerResponseType:
        """Gets the number of members in a set.

        Args:
            name (str): The key of the set.

        Returns:
            RedisIntegerResponseType: The cardinality (size) of the set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sismember(self, name: str, value: str) -> bool:
        """Checks if a value is a member of a set.

        Args:
            name (str): The key of the set.
            value (str): The value to check.

        Returns:
            bool: True if the value is a member, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def smembers(self, name: str) -> RedisSetResponseType:
        """Gets all members of a set.

        Args:
            name (str): The key of the set.

        Returns:
            RedisSetResponseType: A set of all members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Removes and returns one or more random members from a set.

        Args:
            name (str): The key of the set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            bytes | float | int | str | list | None: The popped member(s), or None if the set is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def srem(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Removes one or more members from a set.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Gets the union of multiple sets.

        Args:
            keys (RedisKeyType): Name of the first key.
            *args (bytes | str): Additional key names.

        Returns:
            RedisSetResponseType: A set containing members of the resulting union.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zadd(
        self,
        name: RedisKeyType,
        mapping: Mapping[RedisKeyType, bytes | str | float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> RedisResponseType:
        """Adds members with scores to a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            mapping (Mapping[RedisKeyType, bytes | str | float]): A mapping of members to scores.
            nx (bool): If True, only add new elements. Defaults to False.
            xx (bool): If True, only update existing elements. Defaults to False.
            ch (bool): If True, return the number of changed elements. Defaults to False.
            incr (bool): If True, increment scores instead of setting. Defaults to False.
            gt (bool): If True, only update if new score is greater. Defaults to False.
            lt (bool): If True, only update if new score is less. Defaults to False.

        Returns:
            RedisResponseType: The number of elements added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zcard(self, name: bytes | str) -> RedisResponseType:
        """Gets the number of members in a sorted set.

        Args:
            name (bytes | str): The key of the sorted set.

        Returns:
            RedisResponseType: The cardinality (size) of the sorted set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zcount(self, name: RedisKeyType, min: float | str, max: float | str) -> RedisResponseType:
        """Counts members in a sorted set within a score range.

        Args:
            name (RedisKeyType): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).

        Returns:
            RedisResponseType: The number of members within the score range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zpopmax(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Removes and returns members with the highest scores from a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zpopmin(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Removes and returns members with the lowest scores from a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
        byscore: bool = False,
        bylex: bool = False,
        offset: int | None = None,
        num: int | None = None,
    ) -> RedisResponseType:
        """Gets a range of members from a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            start (int): The starting index or score (depending on byscore).
            end (int): The ending index or score (depending on byscore).
            desc (bool): If True, sort in descending order. Defaults to False.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): If True, range by score instead of rank. Defaults to False.
            bylex (bool): If True, range by lexicographical order. Defaults to False.
            offset (int, optional): Offset for byscore or bylex.
            num (int, optional): Number of elements for byscore or bylex.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrevrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Gets a range of members from a sorted set in reverse order.

        Args:
            name (RedisKeyType): The key of the sorted set.
            start (int): The starting index.
            end (int): The ending index.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrangebyscore(
        self,
        name: RedisKeyType,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Gets members from a sorted set by score range.

        Args:
            name (RedisKeyType): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).
            start (int, optional): Starting offset.
            num (int, optional): Number of elements to return.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrank(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Gets the rank of a member in a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            value (bytes | str | float): The member to find.

        Returns:
            RedisResponseType: The rank (index) of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zrem(self, name: RedisKeyType, *values: bytes | str | float) -> RedisResponseType:
        """Removes one or more members from a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zscore(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Gets the score of a member in a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            value (bytes | str | float): The member to check.

        Returns:
            RedisResponseType: The score of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def hdel(self, name: str, *keys: str | bytes) -> RedisIntegerResponseType:
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
    def hget(self, name: str, key: str) -> str | None:
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
    def hgetall(self, name: str) -> dict[str, Any]:
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
    def hkeys(self, name: str) -> RedisListResponseType:
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
    def hlen(self, name: str) -> RedisIntegerResponseType:
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
    ) -> RedisIntegerResponseType:
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
    def hmget(self, name: str, keys: list, *args: str | bytes) -> RedisListResponseType:
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
    def hvals(self, name: str) -> RedisListResponseType:
        """Gets all values in a hash.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of values in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def publish(self, channel: RedisKeyType, message: bytes | str, **kwargs: Any) -> RedisResponseType:
        """Publishes a message to a channel.

        Args:
            channel (RedisKeyType): The channel to publish to.
            message (bytes | str): The message to publish.
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: The number of subscribers that received the message.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def pubsub_channels(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Lists active channels matching a pattern.

        Args:
            pattern (RedisPatternType): The pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of active channels.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def zincrby(self, name: RedisKeyType, amount: float, value: bytes | str | float) -> RedisResponseType:
        """Increments the score of a member in a sorted set.

        Args:
            name (RedisKeyType): The key of the sorted set.
            amount (float): The amount to increment by.
            value (bytes | str | float): The member to increment.

        Returns:
            RedisResponseType: The new score of the member.

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

    @abstractmethod
    def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> Any:
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

    # Cluster-specific methods (no-op for standalone mode)
    def cluster_info(self) -> RedisResponseType:
        """Get cluster information.

        Returns:
            RedisResponseType: Cluster information or None for standalone mode.
        """
        return None

    def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information.

        Returns:
            RedisResponseType: Cluster nodes info or None for standalone mode.
        """
        return None

    def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping.

        Returns:
            RedisResponseType: Slots mapping or None for standalone mode.
        """
        return None

    def cluster_key_slot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key.

        Args:
            key (str): The key to get slot for.

        Returns:
            RedisResponseType: Key slot or None for standalone mode.
        """
        return None

    def cluster_count_keys_in_slot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot.

        Args:
            slot (int): The slot number.

        Returns:
            RedisResponseType: Key count or None for standalone mode.
        """
        return None

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot.

        Args:
            slot (int): The slot number.
            count (int): Maximum number of keys to return.

        Returns:
            RedisResponseType: List of keys or None for standalone mode.
        """
        return None


class AsyncRedisPort:
    """Interface for asynchronous Redis operations providing a standardized access pattern.

    This interface defines the contract for asynchronous Redis adapters, ensuring consistent
    implementation of Redis operations across different adapters. It covers all
    essential Redis functionality including key-value operations, collections
    (lists, sets, sorted sets, hashes), and pub/sub capabilities.

    Implementing classes should provide concrete implementations for all
    methods, typically by wrapping an asynchronous Redis client library.
    """

    @abstractmethod
    async def ping(self) -> RedisResponseType:
        """Tests the connection to the Redis server asynchronously.

        Returns:
            RedisResponseType: The response from the server, typically "PONG".

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def pttl(self, name: bytes | str) -> RedisResponseType:
        """Gets the remaining time to live of a key in milliseconds asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in milliseconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def incrby(self, name: RedisKeyType, amount: int = 1) -> RedisResponseType:
        """Increments the integer value of a key by the given amount asynchronously.

        Args:
            name (RedisKeyType): The key to increment.
            amount (int): The amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after incrementing.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def set(
        self,
        name: RedisKeyType,
        value: RedisSetType,
        ex: RedisExpiryType | None = None,
        px: RedisExpiryType | None = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: RedisAbsExpiryType | None = None,
        pxat: RedisAbsExpiryType | None = None,
    ) -> RedisResponseType:
        """Sets a key to a value with optional expiration and conditions asynchronously.

        Args:
            name (RedisKeyType): The key to set.
            value (RedisSetType): The value to set for the key.
            ex (RedisExpiryType, optional): Expiration time in seconds or timedelta.
            px (RedisExpiryType, optional): Expiration time in milliseconds or timedelta.
            nx (bool): If True, set only if the key does not exist. Defaults to False.
            xx (bool): If True, set only if the key already exists. Defaults to False.
            keepttl (bool): If True, retain the existing TTL. Defaults to False.
            get (bool): If True, return the old value before setting. Defaults to False.
            exat (RedisAbsExpiryType, optional): Absolute expiration time as Unix timestamp or datetime.
            pxat (RedisAbsExpiryType, optional): Absolute expiration time in milliseconds or datetime.

        Returns:
            RedisResponseType: The result of the operation, often "OK" or the old value if get=True.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> RedisResponseType:
        """Retrieves the value of a key asynchronously.

        Args:
            key (str): The key to retrieve.

        Returns:
            RedisResponseType: The value associated with the key, or None if the key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def mget(
        self,
        keys: RedisKeyType | Iterable[RedisKeyType],
        *args: bytes | str,
    ) -> RedisResponseType:
        """Gets the values of multiple keys asynchronously.

        Args:
            keys (RedisKeyType | Iterable[RedisKeyType]): A single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: A list of values corresponding to the keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def mset(self, mapping: Mapping[RedisKeyType, bytes | str | float]) -> RedisResponseType:
        """Sets multiple keys to their respective values asynchronously.

        Args:
            mapping (Mapping[RedisKeyType, bytes | str | float]): A mapping of keys to values.

        Returns:
            RedisResponseType: Typically "OK" on success.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def keys(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Returns all keys matching a pattern asynchronously.

        Args:
            pattern (RedisPatternType): The pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of matching keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def getset(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Sets a key to a value and returns its old value asynchronously.

        Args:
            key (RedisKeyType): The key to set.
            value (bytes | str | float): The new value to set.

        Returns:
            RedisResponseType: The old value of the key, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def getdel(self, key: bytes | str) -> RedisResponseType:
        """Gets the value of a key and deletes it asynchronously.

        Args:
            key (bytes | str): The key to get and delete.

        Returns:
            RedisResponseType: The value of the key before deletion, or None if it didn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, *names: bytes | str) -> RedisResponseType:
        """Checks if one or more keys exist asynchronously.

        Args:
            *names (bytes | str): Variable number of keys to check.

        Returns:
            RedisResponseType: The number of keys that exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *names: bytes | str) -> RedisResponseType:
        """Deletes one or more keys asynchronously.

        Args:
            *names (bytes | str): Variable number of keys to delete.

        Returns:
            RedisResponseType: The number of keys deleted.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def append(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Appends a value to a key's string value asynchronously.

        Args:
            key (RedisKeyType): The key to append to.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: The length of the string after appending.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def ttl(self, name: bytes | str) -> RedisResponseType:
        """Gets the remaining time to live of a key in seconds asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The time to live in seconds, or -1 if no TTL, -2 if key doesn't exist.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def type(self, name: bytes | str) -> RedisResponseType:
        """Determines the type of value stored at a key asynchronously.

        Args:
            name (bytes | str): The key to check.

        Returns:
            RedisResponseType: The type of the key's value (e.g., "string", "list", etc.).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def llen(self, name: str) -> RedisIntegerResponseType:
        """Gets the length of a list asynchronously.

        Args:
            name (str): The key of the list.

        Returns:
            RedisIntegerResponseType: The number of items in the list.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lpop(self, name: str, count: int | None = None) -> Any:
        """Removes and returns the first element(s) of a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Pushes one or more values to the start of a list asynchronously.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lrange(self, name: str, start: int, end: int) -> RedisListResponseType:
        """Gets a range of elements from a list asynchronously.

        Args:
            name (str): The key of the list.
            start (int): The starting index (inclusive).
            end (int): The ending index (inclusive).

        Returns:
            RedisListResponseType: A list of elements in the specified range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lrem(self, name: str, count: int, value: str) -> RedisIntegerResponseType:
        """Removes occurrences of a value from a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int): Number of occurrences to remove (0 for all).
            value (str): The value to remove.

        Returns:
            RedisIntegerResponseType: The number of elements removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def lset(self, name: str, index: int, value: str) -> bool:
        """Sets the value of an element in a list by index asynchronously.

        Args:
            name (str): The key of the list.
            index (int): The index to set.
            value (str): The new value.

        Returns:
            bool: True if successful.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rpop(self, name: str, count: int | None = None) -> Any:
        """Removes and returns the last element(s) of a list asynchronously.

        Args:
            name (str): The key of the list.
            count (int, optional): Number of elements to pop. Defaults to None (pops 1).

        Returns:
            Any: The popped element(s), or None if the list is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def rpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Pushes one or more values to the end of a list asynchronously.

        Args:
            name (str): The key of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: The length of the list after the push.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> RedisResponseType:
        """Iterates over keys in the database incrementally asynchronously.

        Args:
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_keys).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator:
        """Provides an iterator over keys in the database asynchronously.

        Args:
            match (bytes | str, optional): Pattern to match keys against.
            count (int, optional): Hint for number of keys to return per iteration.
            _type (str, optional): Filter by type (e.g., "string", "list").
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            Iterator: An iterator yielding keys.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sscan(
        self,
        name: RedisKeyType,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> RedisResponseType:
        """Iterates over members of a set incrementally asynchronously.

        Args:
            name (RedisKeyType): The key of the set.
            cursor (int): The cursor position to start scanning. Defaults to 0.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            RedisResponseType: A tuple of (new_cursor, list_of_members).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sscan_iter(
        self,
        name: RedisKeyType,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator:
        """Provides an iterator over members of a set asynchronously.

        Args:
            name (RedisKeyType): The key of the set.
            match (bytes | str, optional): Pattern to match members against.
            count (int, optional): Hint for number of members to return per iteration.

        Returns:
            Iterator: An iterator yielding set members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sadd(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Adds one or more members to a set asynchronously.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: The number of members added (excluding duplicates).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def scard(self, name: str) -> RedisIntegerResponseType:
        """Gets the number of members in a set asynchronously.

        Args:
            name (str): The key of the set.

        Returns:
            RedisIntegerResponseType: The cardinality (size) of the set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sismember(self, name: str, value: str) -> bool:
        """Checks if a value is a member of a set asynchronously.

        Args:
            name (str): The key of the set.
            value (str): The value to check.

        Returns:
            bool: True if the value is a member, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def smembers(self, name: str) -> RedisSetResponseType:
        """Gets all members of a set asynchronously.

        Args:
            name (str): The key of the set.

        Returns:
            RedisSetResponseType: A set of all members.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Removes and returns one or more random members from a set asynchronously.

        Args:
            name (str): The key of the set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            bytes | float | int | str | list | None: The popped member(s), or None if the set is empty.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def srem(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Removes one or more members from a set asynchronously.

        Args:
            name (str): The key of the set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Gets the union of multiple sets asynchronously.

        Args:
            keys (RedisKeyType): Name of the first key.
            *args (bytes | str): Additional key names.

        Returns:
            RedisSetResponseType: A set containing members of the resulting union.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zadd(
        self,
        name: RedisKeyType,
        mapping: Mapping[RedisKeyType, bytes | str | float],
        nx: bool = False,
        xx: bool = False,
        ch: bool = False,
        incr: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> RedisResponseType:
        """Adds members with scores to a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            mapping (Mapping[RedisKeyType, bytes | str | float]): A mapping of members to scores.
            nx (bool): If True, only add new elements. Defaults to False.
            xx (bool): If True, only update existing elements. Defaults to False.
            ch (bool): If True, return the number of changed elements. Defaults to False.
            incr (bool): If True, increment scores instead of setting. Defaults to False.
            gt (bool): If True, only update if new score is greater. Defaults to False.
            lt (bool): If True, only update if new score is less. Defaults to False.

        Returns:
            RedisResponseType: The number of elements added or updated.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zcard(self, name: bytes | str) -> RedisResponseType:
        """Gets the number of members in a sorted set asynchronously.

        Args:
            name (bytes | str): The key of the sorted set.

        Returns:
            RedisResponseType: The cardinality (size) of the sorted set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zcount(self, name: RedisKeyType, min: float | str, max: float | str) -> RedisResponseType:
        """Counts members in a sorted set within a score range asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).

        Returns:
            RedisResponseType: The number of members within the score range.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zpopmax(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Removes and returns members with the highest scores from a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zpopmin(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Removes and returns members with the lowest scores from a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            count (int, optional): Number of members to pop. Defaults to None (pops 1).

        Returns:
            RedisResponseType: A list of (member, score) tuples popped.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        desc: bool = False,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
        byscore: bool = False,
        bylex: bool = False,
        offset: int | None = None,
        num: int | None = None,
    ) -> RedisResponseType:
        """Gets a range of members from a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            start (int): The starting index or score (depending on byscore).
            end (int): The ending index or score (depending on byscore).
            desc (bool): If True, sort in descending order. Defaults to False.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): If True, range by score instead of rank. Defaults to False.
            bylex (bool): If True, range by lexicographical order. Defaults to False.
            offset (int, optional): Offset for byscore or bylex.
            num (int, optional): Number of elements for byscore or bylex.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrevrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Gets a range of members from a sorted set in reverse order asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            start (int): The starting index.
            end (int): The ending index.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrangebyscore(
        self,
        name: RedisKeyType,
        min: float | str,
        max: float | str,
        start: int | None = None,
        num: int | None = None,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Gets members from a sorted set by score range asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            min (float | str): The minimum score (inclusive).
            max (float | str): The maximum score (inclusive).
            start (int, optional): Starting offset.
            num (int, optional): Number of elements to return.
            withscores (bool): If True, return scores with members. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: A list of members (and scores if withscores=True).

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrank(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Gets the rank of a member in a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            value (bytes | str | float): The member to find.

        Returns:
            RedisResponseType: The rank (index) of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zrem(self, name: RedisKeyType, *values: bytes | str | float) -> RedisResponseType:
        """Removes one or more members from a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: The number of members removed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zscore(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Gets the score of a member in a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            value (bytes | str | float): The member to check.

        Returns:
            RedisResponseType: The score of the member, or None if not found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def hdel(self, name: str, *keys: str | bytes) -> RedisIntegerResponseType:
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
    async def hget(self, name: str, key: str) -> str | None:
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
    async def hgetall(self, name: str) -> dict[str, Any]:
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
    async def hkeys(self, name: str) -> RedisListResponseType:
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
    async def hlen(self, name: str) -> RedisIntegerResponseType:
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
    ) -> RedisIntegerResponseType:
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
    async def hmget(self, name: str, keys: list, *args: str | bytes) -> RedisListResponseType:
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
    async def hvals(self, name: str) -> RedisListResponseType:
        """Gets all values in a hash asynchronously.

        Args:
            name (str): The key of the hash.

        Returns:
            RedisListResponseType: A list of values in the hash.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def publish(self, channel: RedisKeyType, message: bytes | str, **kwargs: Any) -> RedisResponseType:
        """Publishes a message to a channel asynchronously.

        Args:
            channel (RedisKeyType): The channel to publish to.
            message (bytes | str): The message to publish.
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: The number of subscribers that received the message.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def pubsub_channels(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Lists active channels matching a pattern asynchronously.

        Args:
            pattern (RedisPatternType): The pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments for the underlying implementation.

        Returns:
            RedisResponseType: A list of active channels.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def zincrby(self, name: RedisKeyType, amount: float, value: bytes | str | float) -> RedisResponseType:
        """Increments the score of a member in a sorted set asynchronously.

        Args:
            name (RedisKeyType): The key of the sorted set.
            amount (float): The amount to increment by.
            value (bytes | str | float): The member to increment.

        Returns:
            RedisResponseType: The new score of the member.

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

    @abstractmethod
    async def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> Any:
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

    # Cluster-specific methods (no-op for standalone mode)
    async def cluster_info(self) -> RedisResponseType:
        """Get cluster information asynchronously.

        Returns:
            RedisResponseType: Cluster information or None for standalone mode.
        """
        return None

    async def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information asynchronously.

        Returns:
            RedisResponseType: Cluster nodes info or None for standalone mode.
        """
        return None

    async def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping asynchronously.

        Returns:
            RedisResponseType: Slots mapping or None for standalone mode.
        """
        return None

    async def cluster_key_slot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key asynchronously.

        Args:
            key (str): The key to get slot for.

        Returns:
            RedisResponseType: Key slot or None for standalone mode.
        """
        return None

    async def cluster_count_keys_in_slot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot asynchronously.

        Args:
            slot (int): The slot number.

        Returns:
            RedisResponseType: Key count or None for standalone mode.
        """
        return None

    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot asynchronously.

        Args:
            slot (int): The slot number.
            count (int): Maximum number of keys to return.

        Returns:
            RedisResponseType: List of keys or None for standalone mode.
        """
        return None
