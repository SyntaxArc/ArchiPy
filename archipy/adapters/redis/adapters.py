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
            self.client: Redis = self._get_client(redis_master_host, configs)
        if redis_slave_host := configs.SLAVE_HOST:
            self.read_only_client: Redis = self._get_client(redis_slave_host, configs)
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
        self.client = cluster_client
        self.read_only_client = cluster_client

    def _set_sentinel_clients(self, configs: RedisConfig) -> None:
        """Set up Redis sentinel clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis sentinel.
        """
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL_NODES]

        sentinel = Sentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL_SOCKET_TIMEOUT,
            password=configs.PASSWORD,
        )

        self.client = sentinel.master_for(
            configs.SENTINEL_SERVICE_NAME,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

        self.read_only_client = sentinel.slave_for(
            configs.SENTINEL_SERVICE_NAME,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

    # Override cluster methods to work when in cluster mode
    @override
    def cluster_info(self) -> RedisResponseType:
        """Get cluster information."""
        if hasattr(self.client, "cluster_info"):
            return self.client.cluster_info()
        return None

    @override
    def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information."""
        if hasattr(self.client, "cluster_nodes"):
            return self.client.cluster_nodes()
        return None

    @override
    def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping."""
        if hasattr(self.client, "cluster_slots"):
            return self.client.cluster_slots()
        return None

    @override
    def cluster_keyslot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key."""
        if hasattr(self.client, "cluster_keyslot"):
            return self.client.cluster_keyslot(key)
        return None

    @override
    def cluster_countkeysinslot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot."""
        if hasattr(self.client, "cluster_countkeysinslot"):
            return self.client.cluster_countkeysinslot(slot)
        return None

    @override
    def cluster_getkeysinslot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot."""
        if hasattr(self.client, "cluster_getkeysinslot"):
            return self.client.cluster_getkeysinslot(slot, count)
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
        return self.client.mset(mapping)

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
        return self.read_only_client.llen(name)

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
        return self.client.lpush(name, *values)

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
        return self.read_only_client.lrange(name, start, end)

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
        return self.client.lrem(name, count, value)

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
        return self.client.rpush(name, *values)

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
        return self.client.sadd(name, *values)

    @override
    def scard(self, name: str) -> RedisIntegerResponseType:
        """Get the number of members in a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        return self.client.scard(name)

    @override
    def sismember(self, name: str, value: str) -> Awaitable[bool] | bool:
        """Check if a value is a member of a set.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            Awaitable[bool] | bool: True if value is a member, False otherwise.
        """
        result = self.read_only_client.sismember(name, value)
        return result

    @override
    def smembers(self, name: str) -> RedisSetResponseType:
        """Get all members of a set.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        return self.read_only_client.smembers(name)

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
        return self.client.srem(name, *values)

    @override
    def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Get the union of multiple sets.

        Args:
            keys (RedisKeyType): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        result = self.client.sunion(keys, *args)
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
        return self.client.zadd(name, mapping, nx, xx, ch, incr, gt, lt)

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
        return self.client.hdel(name, *keys)

    @override
    def hexists(self, name: str, key: str) -> Awaitable[bool] | bool:
        """Check if a field exists in a hash.

        Args:
            name (str): The hash key name.
            key (str): Field to check.

        Returns:
            Awaitable[bool] | bool: True if field exists, False otherwise.
        """
        return self.read_only_client.hexists(name, key)

    @override
    def hget(self, name: str, key: str) -> Awaitable[str | None] | str | None:
        """Get the value of a field in a hash.

        Args:
            name (str): The hash key name.
            key (str): Field to get.

        Returns:
            Awaitable[str | None] | str | None: Value of the field or None.
        """
        return self.read_only_client.hget(name, key)

    @override
    def hgetall(self, name: str) -> Awaitable[dict] | dict:
        """Get all fields and values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            Awaitable[dict] | dict: Dictionary of field-value pairs.
        """
        return self.read_only_client.hgetall(name)

    @override
    def hkeys(self, name: str) -> RedisListResponseType:
        """Get all fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        return self.read_only_client.hkeys(name)

    @override
    def hlen(self, name: str) -> RedisIntegerResponseType:
        """Get the number of fields in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        return self.read_only_client.hlen(name)

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
        return self.client.hset(name, key, value, mapping, items)

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
        return self.read_only_client.hmget(name, keys, *args)

    @override
    def hvals(self, name: str) -> RedisListResponseType:
        """Get all values in a hash.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        return self.read_only_client.hvals(name)

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
            self.client: AsyncRedis = self._get_client(redis_master_host, configs)
        if redis_slave_host := configs.SLAVE_HOST:
            self.read_only_client: AsyncRedis = self._get_client(redis_slave_host, configs)
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
        self.client = cluster_client
        self.read_only_client = cluster_client

    def _set_sentinel_clients(self, configs: RedisConfig) -> None:
        """Set up async Redis sentinel clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis sentinel.
        """
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL_NODES]

        sentinel = AsyncSentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL_SOCKET_TIMEOUT,
            password=configs.PASSWORD,
        )

        self.client = sentinel.master_for(
            configs.SENTINEL_SERVICE_NAME,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

        self.read_only_client = sentinel.slave_for(
            configs.SENTINEL_SERVICE_NAME,
            socket_timeout=configs.SOCKET_TIMEOUT,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
        )

    # Override cluster methods to work when in cluster mode
    @override
    async def cluster_info(self) -> RedisResponseType:
        """Get cluster information asynchronously."""
        if hasattr(self.client, "cluster_info"):
            return await self.client.cluster_info()
        return None

    @override
    async def cluster_nodes(self) -> RedisResponseType:
        """Get cluster nodes information asynchronously."""
        if hasattr(self.client, "cluster_nodes"):
            return await self.client.cluster_nodes()
        return None

    @override
    async def cluster_slots(self) -> RedisResponseType:
        """Get cluster slots mapping asynchronously."""
        if hasattr(self.client, "cluster_slots"):
            return await self.client.cluster_slots()
        return None

    @override
    async def cluster_keyslot(self, key: str) -> RedisResponseType:
        """Get the hash slot for a key asynchronously."""
        if hasattr(self.client, "cluster_keyslot"):
            return await self.client.cluster_keyslot(key)
        return None

    @override
    async def cluster_countkeysinslot(self, slot: int) -> RedisResponseType:
        """Count keys in a specific slot asynchronously."""
        if hasattr(self.client, "cluster_countkeysinslot"):
            return await self.client.cluster_countkeysinslot(slot)
        return None

    @override
    async def cluster_getkeysinslot(self, slot: int, count: int) -> RedisResponseType:
        """Get keys in a specific slot asynchronously."""
        if hasattr(self.client, "cluster_getkeysinslot"):
            return await self.client.cluster_getkeysinslot(slot, count)
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
        return await self.client.mset(mapping)

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
        return await self.read_only_client.llen(name)

    @override
    async def lpop(self, name: str, count: int | None = None) -> Any:
        """Remove and return elements from list left asynchronously.

        Args:
            name (str): The key name of the list.
            count (int | None): Number of elements to pop. Defaults to None.

        Returns:
            Any: Popped element(s) or None if list is empty.
        """
        return await self.client.lpop(name, count)

    @override
    async def lpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to list left asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        return await self.client.lpush(name, *values)

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
        return await self.read_only_client.lrange(name, start, end)

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
        return await self.client.lrem(name, count, value)

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
        result = await self.client.lset(name, index, value)
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
        return await self.client.rpop(name, count)

    @override
    async def rpush(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Push elements to list right asynchronously.

        Args:
            name (str): The key name of the list.
            *values (bytes | str | float): Values to push.

        Returns:
            RedisIntegerResponseType: Length of the list after push.
        """
        return await self.client.rpush(name, *values)

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
        return self.read_only_client.scan_iter(match, count, _type, **kwargs)

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
        return await self.read_only_client.sscan(name, cursor, match, count)

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
        return self.read_only_client.sscan_iter(name, match, count)

    @override
    async def sadd(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Add members to a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to add.

        Returns:
            RedisIntegerResponseType: Number of elements added.
        """
        return await self.client.sadd(name, *values)

    @override
    async def scard(self, name: str) -> RedisIntegerResponseType:
        """Get number of members in a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisIntegerResponseType: Number of members.
        """
        return await self.client.scard(name)

    @override
    async def sismember(self, name: str, value: str) -> Awaitable[bool] | bool:
        """Check if value is in set asynchronously.

        Args:
            name (str): The set key name.
            value (str): Value to check.

        Returns:
            Awaitable[bool] | bool: True if value is member, False otherwise.
        """
        result = await self.read_only_client.sismember(name, value)
        return result

    @override
    async def smembers(self, name: str) -> RedisSetResponseType:
        """Get all members of a set asynchronously.

        Args:
            name (str): The set key name.

        Returns:
            RedisSetResponseType: Set of all members.
        """
        return await self.read_only_client.smembers(name)

    @override
    async def spop(self, name: str, count: int | None = None) -> bytes | float | int | str | list | None:
        """Remove and return random set members asynchronously.

        Args:
            name (str): The set key name.
            count (int | None): Number of members to pop. Defaults to None.

        Returns:
            bytes | float | int | str | list | None: Popped member(s) or None.
        """
        return await self.client.spop(name, count)

    @override
    async def srem(self, name: str, *values: bytes | str | float) -> RedisIntegerResponseType:
        """Remove members from a set asynchronously.

        Args:
            name (str): The set key name.
            *values (bytes | str | float): Members to remove.

        Returns:
            RedisIntegerResponseType: Number of members removed.
        """
        return await self.client.srem(name, *values)

    @override
    async def sunion(self, keys: RedisKeyType, *args: bytes | str) -> RedisSetResponseType:
        """Get union of multiple sets asynchronously.

        Args:
            keys (RedisKeyType): First set key.
            *args (bytes | str): Additional set keys.

        Returns:
            RedisSetResponseType: Set containing union of all sets.
        """
        result = await self.client.sunion(keys, *args)
        return set(result) if result else set()

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
        return await self.client.zadd(name, mapping, nx, xx, ch, incr, gt, lt)

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
        return await self.client.hdel(name, *keys)

    @override
    async def hexists(self, name: str, key: str) -> Awaitable[bool] | bool:
        """Check if field exists in hash asynchronously.

        Args:
            name (str): The hash key name.
            key (str): Field to check.

        Returns:
            Awaitable[bool] | bool: True if exists, False otherwise.
        """
        return await self.read_only_client.hexists(name, key)

    @override
    async def hget(self, name: str, key: str) -> Awaitable[str | None] | str | None:
        """Get field value from hash asynchronously.

        Args:
            name (str): The hash key name.
            key (str): Field to get.

        Returns:
            Awaitable[str | None] | str | None: Value or None.
        """
        return await self.read_only_client.hget(name, key)

    @override
    async def hgetall(self, name: str) -> Awaitable[dict] | dict:
        """Get all fields and values from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            Awaitable[dict] | dict: Dictionary of field-value pairs.
        """
        return await self.read_only_client.hgetall(name)

    @override
    async def hkeys(self, name: str) -> RedisListResponseType:
        """Get all fields from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of field names.
        """
        return await self.read_only_client.hkeys(name)

    @override
    async def hlen(self, name: str) -> RedisIntegerResponseType:
        """Get number of fields in hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisIntegerResponseType: Number of fields.
        """
        return await self.read_only_client.hlen(name)

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
        return await self.client.hset(name, key, value, mapping, items)

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
        return await self.read_only_client.hmget(name, keys, *args)

    @override
    async def hvals(self, name: str) -> RedisListResponseType:
        """Get all values from hash asynchronously.

        Args:
            name (str): The hash key name.

        Returns:
            RedisListResponseType: List of values.
        """
        return await self.read_only_client.hvals(name)

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
        return await self.client.publish(channel, message, **kwargs)

    @override
    async def pubsub_channels(self, pattern: RedisPatternType = "*", **kwargs: Any) -> RedisResponseType:
        """List active channels matching pattern asynchronously.

        Args:
            pattern (RedisPatternType): Pattern to match. Defaults to "*".
            **kwargs (Any): Additional arguments.

        Returns:
            RedisResponseType: List of channel names.
        """
        return await self.client.pubsub_channels(pattern, **kwargs)

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
        return self.client.pubsub(**kwargs)

    @override
    async def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> AsyncPipeline:
        """Get pipeline for multiple commands asynchronously.

        Args:
            transaction (Any): Use transactions. Defaults to True.
            shard_hint (Any): Sharding hint. Defaults to None.

        Returns:
            AsyncPipeline: Pipeline object.
        """
        return self.client.pipeline(transaction, shard_hint)

    @override
    async def ping(self) -> RedisResponseType:
        """Ping the Redis server asynchronously.

        Returns:
            RedisResponseType: 'PONG' if successful.
        """
        return await self.client.ping()
