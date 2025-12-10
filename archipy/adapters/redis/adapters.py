from collections.abc import Awaitable, Iterable, Iterator, Mapping
from typing import Any, override

from redis import RedisCluster, Sentinel
from redis.asyncio import RedisCluster as AsyncRedisCluster, Sentinel as AsyncSentinel
from redis.asyncio.client import Pipeline as AsyncPipeline, PubSub as AsyncPubSub, Redis as AsyncRedis
from redis.client import Pipeline, PubSub, Redis

from archipy.adapters.redis.ports import (
    AsyncRedisPort,
    RedisAbsExpiryType,
    RedisExpiryType,
    RedisIntegerResponseType,
    RedisKeyType,
    RedisListResponseType,
    RedisPatternType,
    RedisPort,
    RedisResponseType,
    RedisScoreCastType,
    RedisSetResponseType,
    RedisSetType,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import RedisConfig, RedisMode


class RedisAdapter(RedisPort):
    """Adapter for Redis operations providing a standardized interface.

    This adapter implements the RedisPort interface to provide a consistent
    way to interact with Redis, abstracting the underlying Redis client
    implementation. It supports all common Redis operations including key-value
    operations, lists, sets, sorted sets, hashes, and pub/sub functionality.

    The adapter maintains separate connections for read and write operations,
    which can be used to implement read replicas for better performance.

    Args:
        redis_config (RedisConfig, optional): Configuration settings for Redis.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize the RedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
        """
        configs: RedisConfig = BaseConfig.global_config().REDIS if redis_config is None else redis_config
        self._set_clients(configs)

    def _set_clients(self, configs: RedisConfig) -> None:
        """Set up Redis clients based on the configured mode.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        match configs.MODE:
            case RedisMode.CLUSTER:
                self._set_cluster_clients(configs)
            case RedisMode.SENTINEL:
                self._set_sentinel_clients(configs)
            case RedisMode.STANDALONE:
                self._set_standalone_clients(configs)
            case _:
                raise ValueError(f"Unsupported Redis mode: {configs.MODE}")

    def _set_standalone_clients(self, configs: RedisConfig) -> None:
        """Set up standalone Redis clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        if redis_master_host := configs.MASTER_HOST:
            self.client: Redis | RedisCluster = self._get_client(redis_master_host, configs)
        if redis_slave_host := configs.SLAVE_HOST:
            self.read_only_client: Redis | RedisCluster = self._get_client(redis_slave_host, configs)
        else:
            self.read_only_client = self.client

    def _set_cluster_clients(self, configs: RedisConfig) -> None:
        """Set up Redis cluster clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis cluster.
        """
        from redis.cluster import ClusterNode

        startup_nodes = []
        for node in configs.CLUSTER_NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            else:
                startup_nodes.append(ClusterNode(node, configs.PORT))

        cluster_client = RedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            read_from_replicas=configs.CLUSTER_READ_FROM_REPLICAS,
            require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
        )

        # In cluster mode, both clients point to the cluster
        self.client: Redis | RedisCluster = cluster_client
        self.read_only_client: Redis | RedisCluster = cluster_client

    def _set_sentinel_clients(self, configs: RedisConfig) -> None:
        """Set up Redis sentinel clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis sentinel.
        """
        sentinel_service_name = configs.SENTINEL_SERVICE_NAME
        if not sentinel_service_name:
            raise ValueError("SENTINEL_SERVICE_NAME must be provided for sentinel mode")
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL_NODES]

        sentinel = Sentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL_SOCKET_TIMEOUT,
            password=configs.PASSWORD,
        )

        self.client = sentinel.master_for(
            sentinel_service_name,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

        self.read_only_client = sentinel.slave_for(
            sentinel_service_name,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

    # Override cluster methods to work when in cluster mode
    @override
    def cluster_info(self) -> RedisResponseType:
        """Get cluster information."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_info()
        return None

    @override
    def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_nodes()
        return None

    @override
    def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_slots()
        return None

    @override
    def cluster_key_slot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_keyslot(key)
        return None

    @override
    def cluster_count_keys_in_slot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_countkeysinslot(slot)
        return None

    @override
    def cluster_get_keys_in_slot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot."""
        if isinstance(self.client, RedisCluster):
            return self.client.cluster_get_keys_in_slot(slot, count)
        return None

    @staticmethod
    def _get_client(host: str, configs: RedisConfig) -> Redis:
        """Create a Redis client with the specified configuration.

        Args:
            host (str): Redis host address.
            configs (RedisConfig): Configuration settings for Redis.

        Returns:
            Redis: Configured Redis client instance.
        """
        return Redis(
            host=host,
            port=configs.PORT,
            db=configs.DATABASE,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
        )

    @staticmethod
    def _ensure_sync_int(value: int | Awaitable[int]) -> int:
        """Ensure a synchronous integer result, raising if awaitable."""
        if isinstance(value, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return int(value)

    @override
    def pttl(self, name: bytes | str) -> RedisResponseType:
        """Get the time to live in milliseconds for a key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in milliseconds.
        """
        return self.read_only_client.pttl(name)

    @override
    def incrby(self, name: RedisKeyType, amount: int = 1) -> RedisResponseType:
        """Increment the integer value of a key by the given amount.

        Args:
            name (RedisKeyType): The key name.
            amount (int): Amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after increment.
        """
        return self.client.incrby(name, amount)

    @override
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
        """Set the value of a key with optional expiration and conditions.

        Args:
            name (RedisKeyType): The key name.
            value (RedisSetType): The value to set.
            ex (RedisExpiryType | None): Expire time in seconds.
            px (RedisExpiryType | None): Expire time in milliseconds.
            nx (bool): Only set if key doesn't exist.
            xx (bool): Only set if key exists.
            keepttl (bool): Retain the TTL from the previous value.
            get (bool): Return the old value.
            exat (RedisAbsExpiryType | None): Absolute expiration time in seconds.
            pxat (RedisAbsExpiryType | None): Absolute expiration time in milliseconds.

        Returns:
            RedisResponseType: Result of the operation.
        """
        return self.client.set(name, value, ex, px, nx, xx, keepttl, get, exat, pxat)

    @override
    def get(self, key: str) -> RedisResponseType:
        """Get the value of a key.

        Args:
            key (str): The key name.

        Returns:
            RedisResponseType: The value of the key or None if not exists.
        """
        return self.read_only_client.get(key)

    @override
    def mget(
        self,
        keys: RedisKeyType | Iterable[RedisKeyType],
        *args: bytes | str,
    ) -> RedisResponseType:
        """Get the values of multiple keys.

        Args:
            keys (RedisKeyType | Iterable[RedisKeyType]): Single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: List of values.
        """
        return self.read_only_client.mget(keys, *args)

    @override
    def mset(self, mapping: Mapping[RedisKeyType, bytes | str | float]) -> RedisResponseType:
        """Set multiple keys to their respective values.

        Args:
            mapping (Mapping[RedisKeyType, bytes | str | float]): Dictionary of key-value pairs.

        Returns:
            RedisResponseType: Always returns 'OK'.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        return self.client.mset(dict_mapping)

    @override
    def keys(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Find all keys matching the given pattern.

        Args:
            pattern (RedisPatternType): Pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of matching keys.
        """
        return self.read_only_client.keys(pattern, **kwargs)

    @override
    def getset(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Set the value of a key and return its old value.

        Args:
            key (RedisKeyType): The key name.
            value (bytes | str | float): The new value.

        Returns:
            RedisResponseType: The previous value or None.
        """
        return self.client.getset(key, value)

    @override
    def getdel(self, key: bytes | str) -> RedisResponseType:
        """Get the value of a key and delete it.

        Args:
            key (bytes | str): The key name.

        Returns:
            RedisResponseType: The value of the key or None.
        """
        return self.client.getdel(key)

    @override
    def exists(self, *names: bytes | str) -> RedisResponseType:
        """Check if one or more keys exist.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys that exist.
        """
        return self.read_only_client.exists(*names)

    @override
    def delete(self, *names: bytes | str) -> RedisResponseType:
        """Delete one or more keys.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys deleted.
        """
        return self.client.delete(*names)

    @override
    def append(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Append a value to a key.

        Args:
            key (RedisKeyType): The key name.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: Length of the string after append.
        """
        return self.client.append(key, value)

    @override
    def ttl(self, name: bytes | str) -> RedisResponseType:
        """Get the time to live in seconds for a key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in seconds.
        """
        return self.read_only_client.ttl(name)

    @override
    def type(self, name: bytes | str) -> RedisResponseType:
        """Determine the type stored at key.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Type of the key's value.
        """
        return self.read_only_client.type(name)

    @override
    def llen(self, name: str) -> RedisIntegerResponseType:
        """Get the length of a list.

        Args:
            name (str): The key name of the list.

        Returns:
            RedisIntegerResponseType: Length of the list.
        """
        client: Redis | RedisCluster = self.read_only_client
        result = client.llen(name)
        return self._ensure_sync_int(result)

    @override
    def lpop(self, name: str, count: int | None = None) -> Any:
        """Remove and return elements from the left of a list.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        return self.client.lpop(name, count)

    @override
    def lpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to the left of a list.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.lpush(name, *values)
        return self._ensure_sync_int(result)

    @override
    def lrange(self, name: str, start: int, end: int) -> RedisListResponseType:
        """Get a range of elements from a list.

        Args:
            name (str): The key name of the list.
            start (int): Start index.
            end (int): End index.

        Returns:
            RedisListResponseType: List of elements in the specified range.
        """
        result = self.read_only_client.lrange(name, start, end)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return list(result)

    @override
    def lrem(self, name: str, count: int, value: str) -> RedisIntegerResponseType:
        """Remove elements from a list.

        Args:
            name (str): The key name of the list.
            count (int): Number of occurrences to remove.
            value (str): Value to remove.

        Returns:
            RedisIntegerResponseType: Number of elements removed.
        """
        result = self.client.lrem(name, count, value)
        return self._ensure_sync_int(result)

    @override
    def lset(self, name: str, index: int, value: str) -> bool:
        """Set the value of an element in a list by its index.

        Args:
            name (str): The key name of the list.
            index (int): Index of the element.
            value (str): New value.

        Returns:
            bool: True if successful.
        """
        return bool(self.client.lset(name, index, value))

    @override
    def rpop(self, name: str, count: int | None = None) -> Any:
        """Remove and return elements from the right of a list.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        return self.client.rpop(name, count)

    @override
    def rpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to the right of a list.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.rpush(name, *values)
        return self._ensure_sync_int(result)

    @override
    def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> RedisResponseType:
        """Scan keys in the database incrementally.

        Args:
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys to return. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Tuple of cursor and list of keys.
        """
        return self.read_only_client.scan(cursor, match, count, _type, **kwargs)

    @override
    def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator:
        """Iterate over keys in the database.

        Args:
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys to return. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            Iterator: Iterator over matching keys.
        """
        return self.read_only_client.scan_iter(match, count, _type, **kwargs)

    @override
    def sscan(
        self,
        name: RedisKeyType,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> RedisResponseType:
        """Scan members of a set incrementally.

        Args:
            name (RedisKeyType): The set key name.
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            RedisResponseType: Tuple of cursor and list of members.
        """
        return self.read_only_client.sscan(name, cursor, match, count)

    @override
    def sscan_iter(
        self,
        name: RedisKeyType,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator:
        """Iterate over members of a set.

        Args:
            name (RedisKeyType): The set key name.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            Iterator: Iterator over set members.
        """
        return self.read_only_client.sscan_iter(name, match, count)

    @override
    def sadd(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Add members to a set.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: Number of elements added.
        """
        result = self.client.sadd(name, *values)
        return self._ensure_sync_int(result)

    @override
    def scard(self, name: str) -> RedisIntegerResponseType:
        """Get the number of members in a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        result = self.client.scard(name)
        return self._ensure_sync_int(result)

    @override
    def sismember(self, name: str, value: str) -> bool:
        """Check if a value is a member of a set.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            bool: True if value is a member, False otherwise.
        """
        result = self.read_only_client.sismember(name, value)
        return bool(result)

    @override
    def smembers(self, name: str) -> RedisSetResponseType:
        """Get all members of a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        result = self.read_only_client.smembers(name)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return set(result) if result else set()

    @override
    def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Remove and return random members from a set.

        Args:
            name (str): The set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            bytes | float | int | str | list | None: Popped member(s) or None.
        """
        return self.client.spop(name, count)

    @override
    def srem(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Remove members from a set.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: Number of members removed.
        """
        result = self.client.srem(name, *values)
        return self._ensure_sync_int(result)

    @override
    def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Get the union of multiple sets.

        Args:
            keys (RedisKeyType): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        # Redis sunion expects a list of keys as first argument
        keys_list: list[str | bytes] = [keys, *list(args)]
        result = self.client.sunion(keys_list)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return set(result) if result else set()

    @override
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
        """Add members to a sorted set with scores.

        Args:
            name (RedisKeyType): The sorted set key name.
            mapping (Mapping[RedisKeyType, bytes | str | float]): Member-score pairs.
            nx (bool): Only add new elements. Defaults to False.
            xx (bool): Only update existing elements. Defaults to False.
            ch (bool): Return number of changed elements. Defaults to False.
            incr (bool): Increment existing scores. Defaults to False.
            gt (bool): Only update if score is greater. Defaults to False.
            lt (bool): Only update if score is less. Defaults to False.

        Returns:
            RedisResponseType: Number of elements added or modified.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        str_name = str(name)
        return self.client.zadd(str_name, dict_mapping, nx, xx, ch, incr, gt, lt)

    @override
    def zcard(self, name: bytes | str) -> RedisResponseType:
        """Get the number of members in a sorted set.

        Args:
            name (bytes | str): The sorted set key name.

        Returns:
            RedisResponseType: Number of members.
        """
        return self.client.zcard(name)

    @override
    def zcount(self, name: RedisKeyType, min: float | str, max: float | str) -> RedisResponseType:
        """Count members in a sorted set with scores in range.

        Args:
            name (RedisKeyType): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.

        Returns:
            RedisResponseType: Number of members in range.
        """
        return self.client.zcount(name, min, max)

    @override
    def zpopmax(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Remove and return members with highest scores from sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return self.client.zpopmax(name, count)

    @override
    def zpopmin(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Remove and return members with lowest scores from sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return self.client.zpopmin(name, count)

    @override
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
        """Get a range of members from a sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            start (int): Start index or score.
            end (int): End index or score.
            desc (bool): Sort in descending order. Defaults to False.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.
            byscore (bool): Range by score. Defaults to False.
            bylex (bool): Range by lexicographical order. Defaults to False.
            offset (int | None): Offset for byscore/bylex. Defaults to None.
            num (int | None): Count for byscore/bylex. Defaults to None.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrange(
            name,
            start,
            end,
            desc,
            withscores,
            score_cast_func,
            byscore,
            bylex,
            offset,
            num,
        )

    @override
    def zrevrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Get a range of members from a sorted set in reverse order.

        Args:
            name (RedisKeyType): The sorted set key name.
            start (int): Start index.
            end (int): End index.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrevrange(name, start, end, withscores, score_cast_func)

    @override
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
        """Get members from a sorted set by score range.

        Args:
            name (RedisKeyType): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.
            start (int | None): Offset. Defaults to None.
            num (int | None): Count. Defaults to None.
            withscores (bool): Include scores in result. Defaults to False.
            score_cast_func (RedisScoreCastType): Function to cast scores. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return self.client.zrangebyscore(name, min, max, start, num, withscores, score_cast_func)

    @override
    def zrank(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Get the rank of a member in a sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            value (bytes | str | float): Member to find rank for.

        Returns:
            RedisResponseType: Rank of the member or None if not found.
        """
        return self.client.zrank(name, value)

    @override
    def zrem(self, name: RedisKeyType, *values: bytes | str | float) -> RedisResponseType:
        """Remove members from a sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: Number of members removed.
        """
        return self.client.zrem(name, *values)

    @override
    def zscore(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Get the score of a member in a sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            value (bytes | str | float): Member to get score for.

        Returns:
            RedisResponseType: Score of the member or None if not found.
        """
        return self.client.zscore(name, value)

    @override
    def hdel(self, name: str, *keys: str | bytes) -> RedisIntegerResponseType:
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

    @override
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

    @override
    def hget(self, name: str, key: str) -> str | None:
        """Get the value of a field in a hash.

        Args:
            name (str): The hash key name.
            key (str): Field to get.

        Returns:
            str | None: Value of the field or None.
        """
        result = self.read_only_client.hget(name, key)
        return str(result) if result is not None else None

    @override
    def hgetall(self, name: str) -> dict[str, Any]:
        """Get all fields and values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            dict[str, Any]: Dictionary of field-value pairs.
        """
        result = self.read_only_client.hgetall(name)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        if result:
            return {str(k): v for k, v in result.items()}
        return {}

    @override
    def hkeys(self, name: str) -> RedisListResponseType:
        """Get all fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        result = self.read_only_client.hkeys(name)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return list(result) if result else []

    @override
    def hlen(self, name: str) -> RedisIntegerResponseType:
        """Get the number of fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        result = self.read_only_client.hlen(name)
        return self._ensure_sync_int(result)

    @override
    def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> RedisIntegerResponseType:
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

    @override
    def hmget(self, name: str, keys: list, *args: str | bytes) -> RedisListResponseType:
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
            raise TypeError("Unexpected awaitable from sync Redis client")
        return list(result) if result else []

    @override
    def hvals(self, name: str) -> RedisListResponseType:
        """Get all values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        result = self.read_only_client.hvals(name)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return list(result) if result else []

    @override
    def publish(self, channel: RedisKeyType, message: bytes | str, **kwargs: Any) -> RedisResponseType:
        """Publish a message to a channel.

        Args:
            channel (RedisKeyType): Channel name.
            message (bytes | str): Message to publish.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Number of subscribers that received the message.
        """
        return self.client.publish(channel, message, **kwargs)

    @override
    def pubsub_channels(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """List active channels matching a pattern.

        Args:
            pattern (RedisPatternType): Pattern to match channels. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of channel names.
        """
        return self.client.pubsub_channels(pattern, **kwargs)

    @override
    def zincrby(self, name: RedisKeyType, amount: float, value: bytes | str | float) -> RedisResponseType:
        """Increment the score of a member in a sorted set.

        Args:
            name (RedisKeyType): The sorted set key name.
            amount (float): Amount to increment by.
            value (bytes | str | float): Member to increment.

        Returns:
            RedisResponseType: New score of the member.
        """
        return self.client.zincrby(name, amount, value)

    @override
    def pubsub(self, **kwargs: Any) -> PubSub:
        """Get a PubSub object for subscribing to channels.

        Args:
            **kwargs (Any): Additional arguments.

        Returns:
            PubSub: PubSub object.
        """
        return self.client.pubsub(**kwargs)

    @override
    def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> Pipeline:
        """Get a pipeline object for executing multiple commands.

        Args:
            transaction (Any): Whether to use transactions. Defaults to True.
            shard_hint (Any): Hint for sharding. Defaults to None.

        Returns:
            Pipeline: Pipeline object.
        """
        return self.client.pipeline(transaction, shard_hint)

    @override
    def ping(self) -> RedisResponseType:
        """Ping the Redis server.

        Returns:
            RedisResponseType: 'PONG' if successful.
        """
        return self.client.ping()


class AsyncRedisAdapter(AsyncRedisPort):
    """Async adapter for Redis operations providing a standardized interface.

    This adapter implements the AsyncRedisPort interface to provide a consistent
    way to interact with Redis asynchronously, abstracting the underlying Redis
    client implementation. It supports all common Redis operations including
    key-value operations, lists, sets, sorted sets, hashes, and pub/sub functionality.

    The adapter maintains separate connections for read and write operations,
    which can be used to implement read replicas for better performance.

    Args:
        redis_config (RedisConfig, optional): Configuration settings for Redis.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize the AsyncRedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
        """
        configs: RedisConfig = BaseConfig.global_config().REDIS if redis_config is None else redis_config
        self._set_clients(configs)

    def _set_clients(self, configs: RedisConfig) -> None:
        """Set up async Redis clients based on the configured mode.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        match configs.MODE:
            case RedisMode.CLUSTER:
                self._set_cluster_clients(configs)
            case RedisMode.SENTINEL:
                self._set_sentinel_clients(configs)
            case RedisMode.STANDALONE:
                self._set_standalone_clients(configs)
            case _:
                raise ValueError(f"Unsupported Redis mode: {configs.MODE}")

    def _set_standalone_clients(self, configs: RedisConfig) -> None:
        """Set up standalone async Redis clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        if redis_master_host := configs.MASTER_HOST:
            self.client: AsyncRedis | AsyncRedisCluster = self._get_client(redis_master_host, configs)
        if redis_slave_host := configs.SLAVE_HOST:
            self.read_only_client: AsyncRedis | AsyncRedisCluster = self._get_client(redis_slave_host, configs)
        else:
            self.read_only_client = self.client

    def _set_cluster_clients(self, configs: RedisConfig) -> None:
        """Set up async Redis cluster clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis cluster.
        """
        from redis.cluster import ClusterNode

        startup_nodes = []
        for node in configs.CLUSTER_NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            else:
                startup_nodes.append(ClusterNode(node, configs.PORT))

        cluster_client = AsyncRedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            read_from_replicas=configs.CLUSTER_READ_FROM_REPLICAS,
            require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
        )

        # In cluster mode, both clients point to the cluster
        self.client: AsyncRedis | AsyncRedisCluster = cluster_client
        self.read_only_client: AsyncRedis | AsyncRedisCluster = cluster_client

    def _set_sentinel_clients(self, configs: RedisConfig) -> None:
        """Set up async Redis sentinel clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis sentinel.
        """
        sentinel_service_name = configs.SENTINEL_SERVICE_NAME
        if not sentinel_service_name:
            raise ValueError("SENTINEL_SERVICE_NAME must be provided for sentinel mode")
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL_NODES]

        sentinel = AsyncSentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL_SOCKET_TIMEOUT,
            password=configs.PASSWORD,
        )

        self.client = sentinel.master_for(
            sentinel_service_name,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

        self.read_only_client = sentinel.slave_for(
            sentinel_service_name,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

    # Override cluster methods to work when in cluster mode
    @override
    async def cluster_info(self) -> RedisResponseType:
        """Get cluster information asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_info()
        return None

    @override
    async def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_nodes()
        return None

    @override
    async def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_slots()
        return None

    @override
    async def cluster_key_slot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_keyslot(key)
        return None

    @override
    async def cluster_count_keys_in_slot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_countkeysinslot(slot)
        return None

    @override
    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot asynchronously."""
        if isinstance(self.client, AsyncRedisCluster):
            return await self.client.cluster_get_keys_in_slot(slot, count)
        return None

    @staticmethod
    def _get_client(host: str, configs: RedisConfig) -> AsyncRedis:
        """Create an async Redis client with the specified configuration.

        Args:
            host (str): Redis host address.
            configs (RedisConfig): Configuration settings for Redis.

        Returns:
            AsyncRedis: Configured async Redis client instance.
        """
        return AsyncRedis(
            host=host,
            port=configs.PORT,
            db=configs.DATABASE,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
        )

    @staticmethod
    async def _ensure_async_int(value: int | Awaitable[int]) -> int:
        """Ensure an async integer result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            awaited_value = await value
            if not isinstance(awaited_value, int):
                raise TypeError(f"Expected int, got {type(awaited_value)}")
            return awaited_value
        return value

    @staticmethod
    async def _ensure_async_bool(value: bool | Awaitable[bool]) -> bool:
        """Ensure an async boolean result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            awaited_value = await value
            return bool(awaited_value)
        return bool(value)

    @staticmethod
    async def _ensure_async_str(value: str | None | Awaitable[str | None]) -> str | None:
        """Ensure an async string result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            result = await value
            if result is not None and not isinstance(result, str):
                raise TypeError(f"Expected str | None, got {type(result)}")
            return result
        return value

    @staticmethod
    async def _ensure_async_list(value: list[Any] | Awaitable[list[Any]]) -> list[Any]:
        """Ensure an async list result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            result = await value
            if result is None:
                return []
            if isinstance(result, list):
                return result
            # Type narrowing: result is iterable but not a list
            from collections.abc import Iterable

            if isinstance(result, Iterable):
                return list(result)
            return []
        if value is None:
            return []
        if isinstance(value, list):
            return value
        # Type narrowing: value is iterable but not a list
        from collections.abc import Iterable

        if isinstance(value, Iterable):
            return list(value)
        return []

    @override
    async def pttl(self, name: bytes | str) -> RedisResponseType:
        """Get the time to live in milliseconds for a key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in milliseconds.
        """
        return await self.read_only_client.pttl(name)

    @override
    async def incrby(self, name: RedisKeyType, amount: int = 1) -> RedisResponseType:
        """Increment the integer value of a key by the given amount asynchronously.

        Args:
            name (RedisKeyType): The key name.
            amount (int): Amount to increment by. Defaults to 1.

        Returns:
            RedisResponseType: The new value after increment.
        """
        return await self.client.incrby(name, amount)

    @override
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
        """Set the value of a key with optional expiration asynchronously.

        Args:
            name (RedisKeyType): The key name.
            value (RedisSetType): The value to set.
            ex (RedisExpiryType | None): Expire time in seconds.
            px (RedisExpiryType | None): Expire time in milliseconds.
            nx (bool): Only set if key doesn't exist.
            xx (bool): Only set if key exists.
            keepttl (bool): Retain the TTL from the previous value.
            get (bool): Return the old value.
            exat (RedisAbsExpiryType | None): Absolute expiration time in seconds.
            pxat (RedisAbsExpiryType | None): Absolute expiration time in milliseconds.

        Returns:
            RedisResponseType: Result of the operation.
        """
        return await self.client.set(name, value, ex, px, nx, xx, keepttl, get, exat, pxat)

    @override
    async def get(self, key: str) -> RedisResponseType:
        """Get the value of a key asynchronously.

        Args:
            key (str): The key name.

        Returns:
            RedisResponseType: The value of the key or None if not exists.
        """
        return await self.read_only_client.get(key)

    @override
    async def mget(
        self,
        keys: RedisKeyType | Iterable[RedisKeyType],
        *args: bytes | str,
    ) -> RedisResponseType:
        """Get the values of multiple keys asynchronously.

        Args:
            keys (RedisKeyType | Iterable[RedisKeyType]): Single key or iterable of keys.
            *args (bytes | str): Additional keys.

        Returns:
            RedisResponseType: List of values.
        """
        return await self.read_only_client.mget(keys, *args)

    @override
    async def mset(self, mapping: Mapping[RedisKeyType, bytes | str | float]) -> RedisResponseType:
        """Set multiple keys to their values asynchronously.

        Args:
            mapping (Mapping[RedisKeyType, bytes | str | float]): Dictionary of key-value pairs.

        Returns:
            RedisResponseType: Always returns 'OK'.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        return await self.client.mset(dict_mapping)

    @override
    async def keys(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """Find all keys matching the pattern asynchronously.

        Args:
            pattern (RedisPatternType): Pattern to match keys against. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of matching keys.
        """
        return await self.read_only_client.keys(pattern, **kwargs)

    @override
    async def getset(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Set a key's value and return its old value asynchronously.

        Args:
            key (RedisKeyType): The key name.
            value (bytes | str | float): The new value.

        Returns:
            RedisResponseType: The previous value or None.
        """
        return await self.client.getset(key, value)

    @override
    async def getdel(self, key: bytes | str) -> RedisResponseType:
        """Get a key's value and delete it asynchronously.

        Args:
            key (bytes | str): The key name.

        Returns:
            RedisResponseType: The value of the key or None.
        """
        return await self.client.getdel(key)

    @override
    async def exists(self, *names: bytes | str) -> RedisResponseType:
        """Check if keys exist asynchronously.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys that exist.
        """
        return await self.read_only_client.exists(*names)

    @override
    async def delete(self, *names: bytes | str) -> RedisResponseType:
        """Delete keys asynchronously.

        Args:
            *names (bytes | str): Variable number of key names.

        Returns:
            RedisResponseType: Number of keys deleted.
        """
        return await self.client.delete(*names)

    @override
    async def append(self, key: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Append a value to a key asynchronously.

        Args:
            key (RedisKeyType): The key name.
            value (bytes | str | float): The value to append.

        Returns:
            RedisResponseType: Length of the string after append.
        """
        return await self.client.append(key, value)

    @override
    async def ttl(self, name: bytes | str) -> RedisResponseType:
        """Get the time to live in seconds for a key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Time to live in seconds.
        """
        return await self.read_only_client.ttl(name)

    @override
    async def type(self, name: bytes | str) -> RedisResponseType:
        """Determine the type stored at key asynchronously.

        Args:
            name (bytes | str): The key name.

        Returns:
            RedisResponseType: Type of the key's value.
        """
        return await self.read_only_client.type(name)

    @override
    async def llen(self, name: str) -> RedisIntegerResponseType:
        """Get the length of a list asynchronously.

        Args:
            name (str): The key name of the list.

        Returns:
            RedisIntegerResponseType: Length of the list.
        """
        result = self.read_only_client.llen(name)
        return await self._ensure_async_int(result)

    @override
    async def lpop(self, name: str, count: int | None = None) -> Any:
        """Remove and return elements from list left asynchronously.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        result = self.client.lpop(name, count)
        if isinstance(result, Awaitable):
            return await result
        return result

    @override
    async def lpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to list left asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.lpush(name, *values)
        return await self._ensure_async_int(result)

    @override
    async def lrange(self, name: str, start: int, end: int) -> RedisListResponseType:
        """Get a range of elements from a list asynchronously.

        Args:
            name (str): The key name of the list.
            start (int): Start index.
            end (int): End index.

        Returns:
            RedisListResponseType: List of elements in range.
        """
        result = self.read_only_client.lrange(name, start, end)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return []
        if isinstance(result, list):
            return result
        from collections.abc import Iterable

        if isinstance(result, Iterable):
            return list(result)
        return []

    @override
    async def lrem(self, name: str, count: int, value: str) -> RedisIntegerResponseType:
        """Remove elements from a list asynchronously.

        Args:
            name (str): The key name of the list.
            count (int): Number of occurrences to remove.
            value (str): Value to remove.

        Returns:
            RedisIntegerResponseType: Number of elements removed.
        """
        result = self.client.lrem(name, count, value)
        return await self._ensure_async_int(result)

    @override
    async def lset(self, name: str, index: int, value: str) -> bool:
        """Set list element by index asynchronously.

        Args:
            name (str): The key name of the list.
            index (int): Index of the element.
            value (str): New value.

        Returns:
            bool: True if successful.
        """
        result = self.client.lset(name, index, value)
        if isinstance(result, Awaitable):
            result = await result
        return bool(result)

    @override
    async def rpop(self, name: str, count: int | None = None) -> Any:
        """Remove and return elements from list right asynchronously.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        result = self.client.rpop(name, count)
        if isinstance(result, Awaitable):
            return await result
        return result

    @override
    async def rpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to list right asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        result = self.client.rpush(name, *values)
        return await self._ensure_async_int(result)

    @override
    async def scan(
        self,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> RedisResponseType:
        """Scan keys in database incrementally asynchronously.

        Args:
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Tuple of cursor and list of keys.
        """
        return await self.read_only_client.scan(cursor, match, count, _type, **kwargs)

    @override
    async def scan_iter(
        self,
        match: bytes | str | None = None,
        count: int | None = None,
        _type: str | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Iterate over keys in database asynchronously.

        Args:
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of keys. Defaults to None.
            _type (str | None): Filter by type. Defaults to None.
            **kwargs (Any): Additional arguments.

        Returns:
            Iterator[Any]: Iterator over matching keys.
        """
        result = self.read_only_client.scan_iter(match, count, _type, **kwargs)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        # Type narrowing: result is an Iterator
        if not isinstance(result, Iterator):
            raise TypeError(f"Expected Iterator, got {type(result)}")
        return result

    @override
    async def sscan(
        self,
        name: RedisKeyType,
        cursor: int = 0,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> RedisResponseType:
        """Scan set members incrementally asynchronously.

        Args:
            name (RedisKeyType): The set key name.
            cursor (int): Cursor position. Defaults to 0.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            RedisResponseType: Tuple of cursor and list of members.
        """
        result = self.read_only_client.sscan(name, cursor, match, count)
        if isinstance(result, Awaitable):
            awaited_result: RedisResponseType = await result
            return awaited_result
        return result

    @override
    async def sscan_iter(
        self,
        name: RedisKeyType,
        match: bytes | str | None = None,
        count: int | None = None,
    ) -> Iterator[Any]:
        """Iterate over set members asynchronously.

        Args:
            name (RedisKeyType): The set key name.
            match (bytes | str | None): Pattern to match. Defaults to None.
            count (int | None): Hint for number of elements. Defaults to None.

        Returns:
            Iterator[Any]: Iterator over set members.
        """
        result = self.read_only_client.sscan_iter(name, match, count)
        if isinstance(result, Awaitable):
            awaited_result = await result
            if not isinstance(awaited_result, Iterator):
                raise TypeError(f"Expected Iterator, got {type(awaited_result)}")
            return awaited_result
        # Type narrowing: result is an Iterator
        if not isinstance(result, Iterator):
            raise TypeError(f"Expected Iterator, got {type(result)}")
        return result

    @override
    async def sadd(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Add members to a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: Number of elements added.
        """
        result = self.client.sadd(name, *values)
        return await self._ensure_async_int(result)

    @override
    async def scard(self, name: str) -> RedisIntegerResponseType:
        """Get number of members in a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        result = self.client.scard(name)
        return await self._ensure_async_int(result)

    @override
    async def sismember(self, name: str, value: str) -> bool:
        """Check if value is in set asynchronously.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            bool: True if value is member, False otherwise.
        """
        result = self.read_only_client.sismember(name, value)
        if isinstance(result, Awaitable):
            result = await result
        return bool(result)

    @override
    async def smembers(self, name: str) -> RedisSetResponseType:
        """Get all members of a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        result = self.read_only_client.smembers(name)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return set()
        if isinstance(result, set):
            return result
        from collections.abc import Iterable

        if isinstance(result, Iterable):
            return set(result)
        return set()

    @override
    async def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Remove and return random set members asynchronously.

        Args:
            name (str): The set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            bytes | float | int | str | list | None: Popped member(s) or None.
        """
        result = self.client.spop(name, count)
        if isinstance(result, Awaitable):
            awaited_result = await result
            # Type narrowing: result can be any of the return types
            if awaited_result is None or isinstance(awaited_result, (bytes, float, int, str, list)):
                return awaited_result
            raise TypeError(f"Unexpected type from spop: {type(awaited_result)}")
        return result

    @override
    async def srem(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Remove members from a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: Number of members removed.
        """
        result = self.client.srem(name, *values)
        return await self._ensure_async_int(result)

    @override
    async def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Get union of multiple sets asynchronously.

        Args:
            keys (RedisKeyType): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        # Convert keys to str for type compatibility, combine into list
        keys_list: list[str] = [str(keys)] + [str(arg) if isinstance(arg, bytes) else arg for arg in args]
        result = self.client.sunion(keys_list)
        if isinstance(result, Awaitable):
            result = await result
        if result is None:
            return set()
        if isinstance(result, set):
            return result
        from collections.abc import Iterable

        if isinstance(result, Iterable):
            return set(result)
        return set()

    @override
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
        """Add members to sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            mapping (Mapping[RedisKeyType, bytes | str | float]): Member-score pairs.
            nx (bool): Only add new elements. Defaults to False.
            xx (bool): Only update existing. Defaults to False.
            ch (bool): Return changed count. Defaults to False.
            incr (bool): Increment scores. Defaults to False.
            gt (bool): Only if greater. Defaults to False.
            lt (bool): Only if less. Defaults to False.

        Returns:
            RedisResponseType: Number of elements added or modified.
        """
        # Convert Mapping to dict for type compatibility with Redis client
        if isinstance(mapping, dict):
            dict_mapping: dict[str, bytes | str | float] = {str(k): v for k, v in mapping.items()}
        else:
            dict_mapping = {str(k): v for k, v in mapping.items()}
        str_name = str(name)
        result = self.client.zadd(str_name, dict_mapping, nx, xx, ch, incr, gt, lt)
        if isinstance(result, Awaitable):
            return await result
        return result

    @override
    async def zcard(self, name: bytes | str) -> RedisResponseType:
        """Get number of members in sorted set asynchronously.

        Args:
            name (bytes | str): The sorted set key name.

        Returns:
            RedisResponseType: Number of members.
        """
        return await self.client.zcard(name)

    @override
    async def zcount(self, name: RedisKeyType, min: float | str, max: float | str) -> RedisResponseType:
        """Count members in score range asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.

        Returns:
            RedisResponseType: Number of members in range.
        """
        return await self.client.zcount(name, min, max)

    @override
    async def zpopmax(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Pop highest scored members asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            count (int | None): Number to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return await self.client.zpopmax(name, count)

    @override
    async def zpopmin(self, name: RedisKeyType, count: int | None = None) -> RedisResponseType:
        """Pop lowest scored members asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            count (int | None): Number to pop. Defaults to None.

        Returns:
            RedisResponseType: List of popped member-score pairs.
        """
        return await self.client.zpopmin(name, count)

    @override
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
        """Get range from sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            start (int): Start index or score.
            end (int): End index or score.
            desc (bool): Descending order. Defaults to False.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.
            byscore (bool): Range by score. Defaults to False.
            bylex (bool): Range by lex. Defaults to False.
            offset (int | None): Offset for byscore/bylex. Defaults to None.
            num (int | None): Count for byscore/bylex. Defaults to None.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrange(
            name,
            start,
            end,
            desc,
            withscores,
            score_cast_func,
            byscore,
            bylex,
            offset,
            num,
        )

    @override
    async def zrevrange(
        self,
        name: RedisKeyType,
        start: int,
        end: int,
        withscores: bool = False,
        score_cast_func: RedisScoreCastType = float,
    ) -> RedisResponseType:
        """Get reverse range from sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            start (int): Start index.
            end (int): End index.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrevrange(name, start, end, withscores, score_cast_func)

    @override
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
        """Get members by score range asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            min (float | str): Minimum score.
            max (float | str): Maximum score.
            start (int | None): Offset. Defaults to None.
            num (int | None): Count. Defaults to None.
            withscores (bool): Include scores. Defaults to False.
            score_cast_func (RedisScoreCastType): Score cast function. Defaults to float.

        Returns:
            RedisResponseType: List of members or member-score pairs.
        """
        return await self.client.zrangebyscore(name, min, max, start, num, withscores, score_cast_func)

    @override
    async def zrank(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Get rank of member in sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            value (bytes | str | float): Member to find rank for.

        Returns:
            RedisResponseType: Rank or None if not found.
        """
        return await self.client.zrank(name, value)

    @override
    async def zrem(self, name: RedisKeyType, *values: bytes | str | float) -> RedisResponseType:
        """Remove members from sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisResponseType: Number of members removed.
        """
        return await self.client.zrem(name, *values)

    @override
    async def zscore(self, name: RedisKeyType, value: bytes | str | float) -> RedisResponseType:
        """Get score of member in sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            value (bytes | str | float): Member to get score for.

        Returns:
            RedisResponseType: Score or None if not found.
        """
        return await self.client.zscore(name, value)

    @override
    async def hdel(self, name: str, *keys: str | bytes) -> RedisIntegerResponseType:
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

    @override
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

    @override
    async def hget(self, name: str, key: str) -> str | None:
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

    @override
    async def hgetall(self, name: str) -> dict[str, Any]:
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

    @override
    async def hkeys(self, name: str) -> RedisListResponseType:
        """Get all fields from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        result = self.read_only_client.hkeys(name)
        return await self._ensure_async_list(result)

    @override
    async def hlen(self, name: str) -> RedisIntegerResponseType:
        """Get number of fields in hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        result = self.read_only_client.hlen(name)
        return await self._ensure_async_int(result)

    @override
    async def hset(
        self,
        name: str,
        key: str | bytes | None = None,
        value: str | bytes | None = None,
        mapping: dict | None = None,
        items: list | None = None,
    ) -> RedisIntegerResponseType:
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

    @override
    async def hmget(self, name: str, keys: list, *args: str | bytes) -> RedisListResponseType:
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

    @override
    async def hvals(self, name: str) -> RedisListResponseType:
        """Get all values from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        result = self.read_only_client.hvals(name)
        return await self._ensure_async_list(result)

    @override
    async def publish(self, channel: RedisKeyType, message: bytes | str, **kwargs: Any) -> RedisResponseType:
        """Publish message to channel asynchronously.

        Args:
            channel (RedisKeyType): Channel name.
            message (bytes | str): Message to publish.
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: Number of subscribers received message.
        """
        # AsyncRedis client has publish method, type stubs may be incomplete
        publish_method = getattr(self.client, "publish", None)
        if publish_method and callable(publish_method):
            result = publish_method(channel, message, **kwargs)
            if isinstance(result, Awaitable):
                return await result
            return result
        raise AttributeError("publish method not available on Redis client")

    @override
    async def pubsub_channels(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """List active channels matching pattern asynchronously.

        Args:
            pattern (RedisPatternType): Pattern to match. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of channel names.
        """
        # AsyncRedis client has pubsub_channels method, type stubs may be incomplete
        pubsub_channels_method = getattr(self.client, "pubsub_channels", None)
        if pubsub_channels_method and callable(pubsub_channels_method):
            result = pubsub_channels_method(pattern, **kwargs)
            if isinstance(result, Awaitable):
                return await result
            return result
        raise AttributeError("pubsub_channels method not available on Redis client")

    @override
    async def zincrby(self, name: RedisKeyType, amount: float, value: bytes | str | float) -> RedisResponseType:
        """Increment member score in sorted set asynchronously.

        Args:
            name (RedisKeyType): The sorted set key name.
            amount (float): Amount to increment by.
            value (bytes | str | float): Member to increment.

        Returns:
            RedisResponseType: New score of the member.
        """
        return await self.client.zincrby(name, amount, value)

    @override
    async def pubsub(self, **kwargs: Any) -> AsyncPubSub:
        """Get PubSub object for channel subscription asynchronously.

        Args:
            **kwargs (Any): Additional arguments.

        Returns:
            AsyncPubSub: PubSub object.
        """
        # Redis client has pubsub method, type stubs may be incomplete
        pubsub_method = getattr(self.client, "pubsub", None)
        if pubsub_method and callable(pubsub_method):
            return pubsub_method(**kwargs)
        raise AttributeError("pubsub method not available on Redis client")

    @override
    async def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> AsyncPipeline:
        """Get pipeline for multiple commands asynchronously.

        Args:
            transaction (Any): Use transactions. Defaults to True.
            shard_hint (Any): Sharding hint. Defaults to None.

        Returns:
            AsyncPipeline: Pipeline object.
        """
        result = self.client.pipeline(transaction, shard_hint)
        # Type narrowing: result is an AsyncPipeline
        if not isinstance(result, AsyncPipeline):
            raise TypeError(f"Expected AsyncPipeline, got {type(result)}")
        return result

    @override
    async def ping(self) -> RedisResponseType:
        """Ping the Redis server asynchronously.

        Returns:
            RedisResponseType: 'PONG' if successful.
        """
        result = self.client.ping()
        if isinstance(result, Awaitable):
            return await result
        return result
