"""Redis adapter mixins for connection operations."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any

from redis import RedisCluster, Sentinel
from redis.asyncio import RedisCluster as AsyncRedisCluster, Sentinel as AsyncSentinel
from redis.asyncio.client import Pipeline as AsyncPipeline, Redis as AsyncRedis
from redis.asyncio.cluster import ClusterPipeline as AsyncClusterPipeline
from redis.client import Pipeline, Redis

from archipy.adapters.redis.adapter_mixins._shared import (
    AsyncRedisMixinBase,
    SyncRedisMixinBase,
    _redis_connection_kwargs,
    _sentinel_kwargs,
    _sentinel_redis_kwargs,
)
from archipy.adapters.redis.search import (
    AsyncRedisSearchHandle,
    RedisSearchHandle,
    list_redis_search_indexes,
    list_redis_search_indexes_async,
)
from archipy.adapters.redis.search_ports import AsyncRedisSearchHandlePort, RedisSearchHandlePort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import RedisConfig, RedisMode
from archipy.models.errors import ConfigurationError


class RedisConnectionMixin(SyncRedisMixinBase):
    """Sync Redis mixin for connection operations."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize the RedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
        """
        configs: RedisConfig = BaseConfig.global_config().REDIS if redis_config is None else redis_config
        self._configs = configs
        self._search_client: Redis | RedisCluster | None = None
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
        from redis.cluster import ClusterNode, LoadBalancingStrategy

        startup_nodes = []
        for node in configs.CLUSTER_NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            else:
                startup_nodes.append(ClusterNode(node, configs.PORT))

        cluster_kwargs: dict[str, Any] = {}
        if configs.CLUSTER_READ_FROM_REPLICAS:
            cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

        cluster_client = RedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
            protocol=configs.PROTOCOL,
            **cluster_kwargs,
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
            sentinel_kwargs=_sentinel_kwargs(configs),
        )

        self.client = sentinel.master_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs),
        )

        self.read_only_client = sentinel.slave_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs),
        )

    @staticmethod
    def _get_client(host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> Redis:
        """Create a Redis client with the specified configuration.

        Args:
            host (str): Redis host address.
            configs (RedisConfig): Configuration settings for Redis.
            decode_responses: Optional override for response decoding.

        Returns:
            Redis: Configured Redis client instance.
        """
        return Redis(
            host=host,
            port=configs.PORT,
            db=configs.DATABASE,
            **_redis_connection_kwargs(configs, decode_responses=decode_responses),
        )

    def _build_binary_client(self, configs: RedisConfig) -> Redis | RedisCluster:
        """Create a binary-safe Redis client for RediSearch operations."""
        if configs.MODE == RedisMode.SENTINEL:
            raise ConfigurationError(
                operation="redis_search",
                reason=f"RediSearch does not support sentinel mode, got {configs.MODE.value}",
            )
        if configs.MODE == RedisMode.CLUSTER:
            from redis.cluster import ClusterNode, LoadBalancingStrategy

            startup_nodes = []
            for node in configs.CLUSTER_NODES:
                if ":" in node:
                    host, port = node.split(":", 1)
                    startup_nodes.append(ClusterNode(host, int(port)))
                else:
                    startup_nodes.append(ClusterNode(node, configs.PORT))

            cluster_kwargs: dict[str, Any] = {}
            if configs.CLUSTER_READ_FROM_REPLICAS:
                cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

            return RedisCluster(
                startup_nodes=startup_nodes,
                password=configs.PASSWORD,
                decode_responses=False,
                max_connections=configs.MAX_CONNECTIONS,
                socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
                socket_timeout=configs.SOCKET_TIMEOUT,
                health_check_interval=configs.HEALTH_CHECK_INTERVAL,
                require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
                protocol=configs.PROTOCOL,
                **cluster_kwargs,
            )

        host = configs.MASTER_HOST or "localhost"
        return self._get_client(host, configs, decode_responses=False)

    def _get_search_client(self) -> Redis | RedisCluster:
        """Return a lazy binary-safe Redis client for RediSearch."""
        if self._search_client is None:
            self._search_client = self._build_binary_client(self._configs)
        return self._search_client

    def search_index(self, name: str) -> RedisSearchHandlePort:
        """Return an index-bound RediSearch handle."""
        return RedisSearchHandle(self._get_search_client(), name)

    def list_search_indexes(self) -> list[str]:
        """List RediSearch indexes available on the server."""
        return list_redis_search_indexes(self._get_search_client())

    @staticmethod
    def _ensure_sync_int(value: int | Awaitable[int]) -> int:
        """Ensure a synchronous integer result, raising if awaitable."""
        if isinstance(value, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return int(value)

    def get_pipeline(self, transaction: Any = True, shard_hint: Any = None) -> Pipeline:
        """Get a pipeline object for executing multiple commands.

        Args:
            transaction (Any): Whether to use transactions. Defaults to True.
            shard_hint (Any): Hint for sharding. Defaults to None.

        Returns:
            Pipeline: Pipeline object.
        """
        return self.client.pipeline(transaction, shard_hint)

    def ping(self) -> bool:
        """Ping the Redis server.

        Returns:
            RedisResponseType: 'PONG' if successful.
        """
        return self.client.ping()

    def flushdb(self, asynchronous: bool = False) -> bool:
        """Delete all keys in the current database.

        Args:
            asynchronous: Whether Redis should flush asynchronously. Defaults to False.

        Returns:
            bool: True if successful.
        """
        return self.client.flushdb(asynchronous=asynchronous)

    def config_set(self, name: str, value: str) -> bool:
        """Set a Redis server configuration parameter.

        Args:
            name (str): The configuration parameter name.
            value (str): The value to set.

        Returns:
            bool: True if successful.
        """
        return bool(self.client.config_set(name, value))

    def config_get(self, pattern: str = "*") -> dict[str, str]:
        """Get Redis server configuration parameters matching a pattern.

        Args:
            pattern (str): Pattern to match configuration parameter names. Defaults to "*".

        Returns:
            RedisResponseType: Dictionary of configuration parameter names to values.
        """
        result = self.read_only_client.config_get(pattern)
        if isinstance(result, Awaitable):
            raise TypeError("Unexpected awaitable from sync Redis client")
        return {str(k): str(v) for k, v in result.items()} if result else {}


class AsyncRedisConnectionMixin(AsyncRedisMixinBase):
    """Async Redis mixin for connection operations."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize the AsyncRedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
        """
        configs: RedisConfig = BaseConfig.global_config().REDIS if redis_config is None else redis_config
        self._configs = configs
        self._search_client: AsyncRedis | AsyncRedisCluster | None = None
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
        from redis.asyncio.cluster import ClusterNode, LoadBalancingStrategy

        startup_nodes = []
        for node in configs.CLUSTER_NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            else:
                startup_nodes.append(ClusterNode(node, configs.PORT))

        cluster_kwargs: dict[str, Any] = {}
        if configs.CLUSTER_READ_FROM_REPLICAS:
            cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

        cluster_client = AsyncRedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
            protocol=configs.PROTOCOL,
            **cluster_kwargs,
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
            sentinel_kwargs=_sentinel_kwargs(configs),
        )

        self.client = sentinel.master_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs),
        )

        self.read_only_client = sentinel.slave_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs),
        )

    @staticmethod
    def _get_client(host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> AsyncRedis:
        """Create an async Redis client with the specified configuration.

        Args:
            host (str): Redis host address.
            configs (RedisConfig): Configuration settings for Redis.
            decode_responses: Optional override for response decoding.

        Returns:
            AsyncRedis: Configured async Redis client instance.
        """
        return AsyncRedis(
            host=host,
            port=configs.PORT,
            db=configs.DATABASE,
            **_redis_connection_kwargs(configs, decode_responses=decode_responses),
        )

    def _build_binary_client(self, configs: RedisConfig) -> AsyncRedis | AsyncRedisCluster:
        """Create a binary-safe async Redis client for RediSearch operations."""
        if configs.MODE == RedisMode.SENTINEL:
            raise ConfigurationError(
                operation="redis_search",
                reason=f"RediSearch does not support sentinel mode, got {configs.MODE.value}",
            )
        if configs.MODE == RedisMode.CLUSTER:
            from redis.asyncio.cluster import ClusterNode, LoadBalancingStrategy

            startup_nodes = []
            for node in configs.CLUSTER_NODES:
                if ":" in node:
                    host, port = node.split(":", 1)
                    startup_nodes.append(ClusterNode(host, int(port)))
                else:
                    startup_nodes.append(ClusterNode(node, configs.PORT))

            cluster_kwargs: dict[str, Any] = {}
            if configs.CLUSTER_READ_FROM_REPLICAS:
                cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

            return AsyncRedisCluster(
                startup_nodes=startup_nodes,
                password=configs.PASSWORD,
                decode_responses=False,
                max_connections=configs.MAX_CONNECTIONS,
                socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
                socket_timeout=configs.SOCKET_TIMEOUT,
                health_check_interval=configs.HEALTH_CHECK_INTERVAL,
                require_full_coverage=configs.CLUSTER_REQUIRE_FULL_COVERAGE,
                protocol=configs.PROTOCOL,
                **cluster_kwargs,
            )

        host = configs.MASTER_HOST or "localhost"
        return self._get_client(host, configs, decode_responses=False)

    def _get_search_client(self) -> AsyncRedis | AsyncRedisCluster:
        """Return a lazy binary-safe async Redis client for RediSearch."""
        if self._search_client is None:
            self._search_client = self._build_binary_client(self._configs)
        return self._search_client

    def search_index(self, name: str) -> AsyncRedisSearchHandlePort:
        """Return an index-bound async RediSearch handle."""
        return AsyncRedisSearchHandle(self._get_search_client(), name)

    async def list_search_indexes(self) -> list[str]:
        """List RediSearch indexes available on the server asynchronously."""
        return await list_redis_search_indexes_async(self._get_search_client())

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
    async def _ensure_async_str(value: str | bytes | Awaitable[str | bytes | None] | None) -> str | None:
        """Ensure an async string result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            result = await value
            if isinstance(result, bytes):
                return result.decode("utf-8") if result else None
            if result is not None and not isinstance(result, str):
                raise TypeError(f"Expected str | None, got {type(result)}")
            return result
        if isinstance(value, bytes):
            return value.decode("utf-8") if value else None
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

    async def get_pipeline(
        self,
        transaction: Any = True,
        shard_hint: Any = None,
    ) -> AsyncPipeline | AsyncClusterPipeline:
        """Get pipeline for multiple commands asynchronously.

        Args:
            transaction (Any): Use transactions. Defaults to True.
            shard_hint (Any): Sharding hint. Defaults to None.

        Returns:
            AsyncPipeline | AsyncClusterPipeline: Pipeline object.
        """
        result = self.client.pipeline(transaction, shard_hint)
        if not isinstance(result, (AsyncPipeline, AsyncClusterPipeline)):
            raise TypeError(f"Expected AsyncPipeline, got {type(result)}")
        return result

    async def ping(self) -> bool:
        """Ping the Redis server asynchronously.

        Returns:
            RedisResponseType: 'PONG' if successful.
        """
        result = self.client.ping()
        if isinstance(result, Awaitable):
            return await result
        return result

    async def flushdb(self, asynchronous: bool = False) -> bool:
        """Delete all keys in the current database asynchronously.

        Args:
            asynchronous: Whether Redis should flush asynchronously. Defaults to False.

        Returns:
            bool: True if successful.
        """
        result = self.client.flushdb(asynchronous=asynchronous)
        if isinstance(result, Awaitable):
            return await result
        return result

    async def config_set(self, name: str, value: str) -> bool:
        """Set a Redis server configuration parameter asynchronously.

        Args:
            name (str): The configuration parameter name.
            value (str): The value to set.

        Returns:
            bool: True if successful.
        """
        result = self.client.config_set(name, value)
        if isinstance(result, Awaitable):
            result = await result
        return bool(result)

    async def config_get(self, pattern: str = "*") -> dict[str, str]:
        """Get Redis server configuration parameters matching a pattern asynchronously.

        Args:
            pattern (str): Pattern to match configuration parameter names. Defaults to "*".

        Returns:
            RedisResponseType: Dictionary of configuration parameter names to values.
        """
        result = self.read_only_client.config_get(pattern)
        if isinstance(result, Awaitable):
            result = await result
        return {str(k): str(v) for k, v in result.items()} if result else {}
