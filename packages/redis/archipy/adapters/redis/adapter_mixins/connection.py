"""Redis adapter mixins for connection operations."""

from __future__ import annotations

__lazy_modules__ = ["archipy.configs.base_config"]

from collections.abc import Awaitable, Iterable, Iterator, Sequence
from typing import TYPE_CHECKING, Any, Self

from redis import RedisCluster, Sentinel
from redis.asyncio import RedisCluster as AsyncRedisCluster, Sentinel as AsyncSentinel
from redis.asyncio.client import Pipeline as AsyncPipeline, Redis as AsyncRedis
from redis.asyncio.cluster import (
    ClusterNode as AsyncClusterNode,
    ClusterPipeline as AsyncClusterPipeline,
    LoadBalancingStrategy as AsyncLoadBalancingStrategy,
)
from redis.client import Pipeline, Redis
from redis.cluster import ClusterNode, LoadBalancingStrategy
from redis.utils import check_protocol_version

from archipy.adapters.redis.adapter_mixins._shared import (
    AsyncRedisMixinBase,
    SyncRedisMixinBase,
    _redis_connection_kwargs,
    _resilience_kwargs,
    _sentinel_kwargs,
    _sentinel_redis_kwargs,
    _tls_acl_kwargs,
)
from archipy.adapters.redis.search import (
    AsyncRedisSearchHandle,
    RedisSearchHandle,
    list_redis_search_indexes,
    list_redis_search_indexes_async,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import RedisConfig, RedisMode
from archipy.models.errors import (
    ConfigurationError,
    InternalError,
    InvalidArgumentError,
)

if TYPE_CHECKING:
    from redis.cache import CacheConfig
    from redis.commands.metadata import AsyncMetadataResolver, MetadataResolver
    from redis.typing import EncodableT, KeyT

    from archipy.adapters.redis.search_ports import (
        AsyncRedisSearchHandlePort,
        RedisSearchHandlePort,
    )


class RedisConnectionMixin(SyncRedisMixinBase):
    """Sync Redis mixin for connection operations."""

    def client_list_iter(
        self, client_type: str | None = None, *, client_ids: Sequence[EncodableT] = ()
    ) -> Iterator[dict[str, str]]:
        """Iterate over parsed records from the server's client list."""
        return self.client.client_list_iter(_type=client_type, client_id=list(client_ids))

    def backup_start(self) -> bytes | str:
        """Start a coordinated backup on the server."""
        return self.client.backup_start()

    def backup_status(self) -> dict[str | bytes, Any]:
        """Return the server's current backup status."""
        return self.client.backup_status()

    def backup_list(self) -> list[bytes | str]:
        """List files generated for the active backup."""
        return self.client.backup_list()

    def backup_seal(self) -> bytes | str:
        """Seal the backup so its files can be copied."""
        return self.client.backup_seal()

    def backup_abort(self) -> bytes | str:
        """Abort the active backup."""
        return self.client.backup_abort()

    def backup_cleanup(self) -> bytes | str:
        """Remove temporary artifacts of the last backup."""
        return self.client.backup_cleanup()

    def cms_initbydim(self, key: KeyT, width: int, depth: int, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch with fixed dimensions and optional counter width."""
        return self.client.cms().initbydim(key, width, depth, cell_size=cell_size)

    def cms_initbyprob(self, key: KeyT, error: float, probability: float, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch sized by error bounds and optional counter width."""
        return self.client.cms().initbyprob(key, error, probability, cell_size=cell_size)

    _sentinel: Sentinel | None = None

    def __init__(
        self,
        redis_config: RedisConfig | None = None,
        *,
        cache_config: CacheConfig | None = None,
        metadata_resolver: MetadataResolver | None = None,
    ) -> None:
        """Initialize the RedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
            cache_config: Client-side cache settings for standalone or cluster mode. Requires RESP3.
            metadata_resolver: Optional command metadata for cached reads and cluster routing.
        """
        configs: RedisConfig = redis_config or BaseConfig.global_config().REDIS
        if configs.MODE == RedisMode.SENTINEL and (cache_config is not None or metadata_resolver is not None):
            raise ConfigurationError(operation="redis_connect", reason="sentinel_cache_or_metadata_unsupported")
        if cache_config is not None and (configs.PROTOCOL is None or not check_protocol_version(configs.PROTOCOL, 3)):
            raise ConfigurationError(operation="redis_connect", reason="client_side_cache_requires_explicit_resp3")
        self._configs = configs
        self._cache_config = cache_config
        self._metadata_resolver = metadata_resolver
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
                raise ConfigurationError(
                    operation="redis_connect",
                    reason="unsupported_mode",
                    additional_data={"mode": str(configs.MODE)},
                )

    def _set_standalone_clients(self, configs: RedisConfig) -> None:
        """Set up standalone Redis clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        if redis_master_host := configs.MASTER_HOST or configs.UNIX_SOCKET_PATH:
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
        startup_nodes = []
        for node in configs.CLUSTER.NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            else:
                startup_nodes.append(ClusterNode(node, configs.PORT))

        cluster_kwargs: dict[str, Any] = {}
        if configs.CLUSTER.READ_FROM_REPLICAS:
            cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

        cluster_client = RedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            require_full_coverage=configs.CLUSTER.REQUIRE_FULL_COVERAGE,
            protocol=configs.PROTOCOL,
            topology_refresh_min_interval=configs.CLUSTER.TOPOLOGY_REFRESH_MIN_INTERVAL,
            cache_config=self._cache_config,
            metadata_resolver=self._metadata_resolver,
            **_tls_acl_kwargs(configs),
            **_resilience_kwargs(configs, is_async=False),
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
        sentinel_service_name = configs.SENTINEL.SERVICE_NAME
        if not sentinel_service_name:
            raise InvalidArgumentError(argument_name="SENTINEL_SERVICE_NAME")
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL.NODES]

        sentinel_connection = Sentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL.SOCKET_TIMEOUT,
            password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
            sentinel_kwargs=_sentinel_kwargs(configs),
        )

        self._sentinel = sentinel_connection
        self.client = sentinel_connection.master_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs, is_async=False),
        )

        self.read_only_client = sentinel_connection.replica_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs, is_async=False),
        )

    def _get_client(self, host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> Redis:
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
            unix_socket_path=configs.UNIX_SOCKET_PATH,
            cache_config=self._cache_config if decode_responses is not False else None,
            metadata_resolver=self._metadata_resolver if decode_responses is not False else None,
            **_redis_connection_kwargs(configs, decode_responses=decode_responses, is_async=False),
        )

    def _build_binary_client(self, configs: RedisConfig) -> Redis | RedisCluster:
        """Create a binary-safe Redis client for RediSearch operations."""
        if configs.MODE == RedisMode.SENTINEL:
            raise ConfigurationError(
                operation="redis_search",
                reason=f"RediSearch does not support sentinel mode, got {configs.MODE.value}",
            )
        if configs.MODE == RedisMode.CLUSTER:
            startup_nodes = []
            for node in configs.CLUSTER.NODES:
                if ":" in node:
                    host, port = node.split(":", 1)
                    startup_nodes.append(ClusterNode(host, int(port)))
                else:
                    startup_nodes.append(ClusterNode(node, configs.PORT))

            cluster_kwargs: dict[str, Any] = {}
            if configs.CLUSTER.READ_FROM_REPLICAS:
                cluster_kwargs["load_balancing_strategy"] = LoadBalancingStrategy.ROUND_ROBIN

            return RedisCluster(
                startup_nodes=startup_nodes,
                password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
                decode_responses=False,
                max_connections=configs.MAX_CONNECTIONS,
                socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
                socket_timeout=configs.SOCKET_TIMEOUT,
                health_check_interval=configs.HEALTH_CHECK_INTERVAL,
                require_full_coverage=configs.CLUSTER.REQUIRE_FULL_COVERAGE,
                protocol=configs.PROTOCOL,
                topology_refresh_min_interval=configs.CLUSTER.TOPOLOGY_REFRESH_MIN_INTERVAL,
                metadata_resolver=self._metadata_resolver,
                **_tls_acl_kwargs(configs),
                **_resilience_kwargs(configs, is_async=False),
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
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
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

    def _open_clients(self) -> list[Redis | RedisCluster]:
        """Return each distinct client this adapter created (write, read-only, search)."""
        candidates = [
            getattr(self, "client", None),
            getattr(self, "read_only_client", None),
            self._search_client,
        ]
        unique: dict[int, Redis | RedisCluster] = {id(c): c for c in candidates if c is not None}
        return list(unique.values())

    def close(self) -> None:
        """Close the write, read-only and search clients and their connection pools.

        Safe to call more than once. A search client created later is rebuilt on demand.
        """
        for client in self._open_clients():
            client.close()
            if not isinstance(client, RedisCluster):
                client.connection_pool.disconnect()
        if self._sentinel is not None:
            self._sentinel.close()
        self._search_client = None

    def __enter__(self) -> Self:
        """Enter the context manager and return the adapter."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Close the clients when leaving the context manager."""
        self.close()

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
            raise InternalError(error_code="SYNC_REDIS_AWAITABLE")
        return {str(k): str(v) for k, v in result.items()} if result else {}


class AsyncRedisConnectionMixin(AsyncRedisMixinBase):
    """Async Redis mixin for connection operations."""

    async def client_list_iter(
        self, client_type: str | None = None, *, client_ids: Sequence[EncodableT] = ()
    ) -> Iterator[dict[str, str]]:
        """Iterate over parsed records from the server's client list."""
        return await self.client.client_list_iter(_type=client_type, client_id=list(client_ids))

    async def backup_start(self) -> bytes | str:
        """Start a coordinated backup on the server."""
        return await self.client.backup_start()

    async def backup_status(self) -> dict[str | bytes, Any]:
        """Return the server's current backup status."""
        return await self.client.backup_status()

    async def backup_list(self) -> list[bytes | str]:
        """List files generated for the active backup."""
        return await self.client.backup_list()

    async def backup_seal(self) -> bytes | str:
        """Seal the backup so its files can be copied."""
        return await self.client.backup_seal()

    async def backup_abort(self) -> bytes | str:
        """Abort the active backup."""
        return await self.client.backup_abort()

    async def backup_cleanup(self) -> bytes | str:
        """Remove temporary artifacts of the last backup."""
        return await self.client.backup_cleanup()

    async def cms_initbydim(self, key: KeyT, width: int, depth: int, *, cell_size: int | None = None) -> bool:
        """Create a Count-Min Sketch with fixed dimensions and optional counter width."""
        return await self._ensure_async_bool(self.client.cms().initbydim(key, width, depth, cell_size=cell_size))

    async def cms_initbyprob(
        self, key: KeyT, error: float, probability: float, *, cell_size: int | None = None
    ) -> bool:
        """Create a Count-Min Sketch sized by error bounds and optional counter width."""
        return await self._ensure_async_bool(self.client.cms().initbyprob(key, error, probability, cell_size=cell_size))

    _sentinel: AsyncSentinel | None = None

    def __init__(
        self,
        redis_config: RedisConfig | None = None,
        *,
        metadata_resolver: AsyncMetadataResolver | None = None,
    ) -> None:
        """Initialize the AsyncRedisAdapter with configuration settings.

        Args:
            redis_config (RedisConfig, optional): Configuration settings for Redis.
                If None, retrieves from global config. Defaults to None.
            metadata_resolver: Optional command metadata for asynchronous cluster routing.
        """
        configs: RedisConfig = redis_config or BaseConfig.global_config().REDIS
        if metadata_resolver is not None and configs.MODE != RedisMode.CLUSTER:
            raise ConfigurationError(operation="redis_connect", reason="async_metadata_requires_cluster")
        self._configs = configs
        self._metadata_resolver = metadata_resolver
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
                raise ConfigurationError(
                    operation="redis_connect",
                    reason="unsupported_mode",
                    additional_data={"mode": str(configs.MODE)},
                )

    def _set_standalone_clients(self, configs: RedisConfig) -> None:
        """Set up standalone async Redis clients.

        Args:
            configs (RedisConfig): Configuration settings for Redis.
        """
        if redis_master_host := configs.MASTER_HOST or configs.UNIX_SOCKET_PATH:
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
        startup_nodes = []
        for node in configs.CLUSTER.NODES:
            if ":" in node:
                host, port = node.split(":", 1)
                startup_nodes.append(AsyncClusterNode(host, int(port)))
            else:
                startup_nodes.append(AsyncClusterNode(node, configs.PORT))

        cluster_kwargs: dict[str, Any] = {}
        if configs.CLUSTER.READ_FROM_REPLICAS:
            cluster_kwargs["load_balancing_strategy"] = AsyncLoadBalancingStrategy.ROUND_ROBIN

        cluster_client = AsyncRedisCluster(
            startup_nodes=startup_nodes,
            password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
            decode_responses=configs.DECODE_RESPONSES,
            max_connections=configs.MAX_CONNECTIONS,
            socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
            socket_timeout=configs.SOCKET_TIMEOUT,
            health_check_interval=configs.HEALTH_CHECK_INTERVAL,
            require_full_coverage=configs.CLUSTER.REQUIRE_FULL_COVERAGE,
            protocol=configs.PROTOCOL,
            topology_refresh_min_interval=configs.CLUSTER.TOPOLOGY_REFRESH_MIN_INTERVAL,
            metadata_resolver=self._metadata_resolver,
            **_tls_acl_kwargs(configs),
            **_resilience_kwargs(configs, is_async=True),
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
        sentinel_service_name = configs.SENTINEL.SERVICE_NAME
        if not sentinel_service_name:
            raise InvalidArgumentError(argument_name="SENTINEL_SERVICE_NAME")
        sentinel_nodes = [(node.split(":")[0], int(node.split(":")[1])) for node in configs.SENTINEL.NODES]

        sentinel_connection = AsyncSentinel(
            sentinel_nodes,
            socket_timeout=configs.SENTINEL.SOCKET_TIMEOUT,
            password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
            sentinel_kwargs=_sentinel_kwargs(configs),
        )

        self._sentinel = sentinel_connection
        self.client = sentinel_connection.master_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs, is_async=True),
        )

        self.read_only_client = sentinel_connection.replica_for(
            sentinel_service_name,
            **_sentinel_redis_kwargs(configs, is_async=True),
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
            unix_socket_path=configs.UNIX_SOCKET_PATH,
            **_redis_connection_kwargs(configs, decode_responses=decode_responses, is_async=True),
        )

    def _build_binary_client(self, configs: RedisConfig) -> AsyncRedis | AsyncRedisCluster:
        """Create a binary-safe async Redis client for RediSearch operations."""
        if configs.MODE == RedisMode.SENTINEL:
            raise ConfigurationError(
                operation="redis_search",
                reason=f"RediSearch does not support sentinel mode, got {configs.MODE.value}",
            )
        if configs.MODE == RedisMode.CLUSTER:
            startup_nodes = []
            for node in configs.CLUSTER.NODES:
                if ":" in node:
                    host, port = node.split(":", 1)
                    startup_nodes.append(AsyncClusterNode(host, int(port)))
                else:
                    startup_nodes.append(AsyncClusterNode(node, configs.PORT))

            cluster_kwargs: dict[str, Any] = {}
            if configs.CLUSTER.READ_FROM_REPLICAS:
                cluster_kwargs["load_balancing_strategy"] = AsyncLoadBalancingStrategy.ROUND_ROBIN

            return AsyncRedisCluster(
                startup_nodes=startup_nodes,
                password=configs.PASSWORD.get_secret_value() if configs.PASSWORD else None,
                decode_responses=False,
                max_connections=configs.MAX_CONNECTIONS,
                socket_connect_timeout=configs.SOCKET_CONNECT_TIMEOUT,
                socket_timeout=configs.SOCKET_TIMEOUT,
                health_check_interval=configs.HEALTH_CHECK_INTERVAL,
                require_full_coverage=configs.CLUSTER.REQUIRE_FULL_COVERAGE,
                protocol=configs.PROTOCOL,
                topology_refresh_min_interval=configs.CLUSTER.TOPOLOGY_REFRESH_MIN_INTERVAL,
                metadata_resolver=self._metadata_resolver,
                **_tls_acl_kwargs(configs),
                **_resilience_kwargs(configs, is_async=True),
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
                raise InvalidArgumentError(
                    argument_name="value",
                    additional_data={
                        "expected": "int",
                        "got": type(awaited_value).__name__,
                    },
                )
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
    async def _ensure_async_str(
        value: str | bytes | Awaitable[str | bytes | None] | None,
    ) -> str | None:
        """Ensure an async string result, awaiting if necessary."""
        if isinstance(value, Awaitable):
            result = await value
            if isinstance(result, bytes):
                return result.decode("utf-8") if result else None
            if result is not None and not isinstance(result, str):
                raise InvalidArgumentError(
                    argument_name="value",
                    additional_data={
                        "expected": "str | None",
                        "got": type(result).__name__,
                    },
                )
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
            if isinstance(result, Iterable):
                return list(result)
            return []
        if value is None:
            return []
        if isinstance(value, list):
            return value
        # Type narrowing: value is iterable but not a list
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
            raise InvalidArgumentError(
                argument_name="pipeline",
                additional_data={
                    "expected": "AsyncPipeline",
                    "got": type(result).__name__,
                },
            )
        return result

    def _open_clients(self) -> list[AsyncRedis | AsyncRedisCluster]:
        """Return each distinct client this adapter created (write, read-only, search)."""
        candidates = [
            getattr(self, "client", None),
            getattr(self, "read_only_client", None),
            self._search_client,
        ]
        unique: dict[int, AsyncRedis | AsyncRedisCluster] = {id(c): c for c in candidates if c is not None}
        return list(unique.values())

    async def close(self) -> None:
        """Close the write, read-only and search clients and their connection pools.

        Safe to call more than once. A search client created later is rebuilt on demand.
        """
        for client in self._open_clients():
            if isinstance(client, AsyncRedisCluster):
                await client.aclose()
            else:
                await client.aclose(close_connection_pool=True)
        if self._sentinel is not None:
            await self._sentinel.aclose()
        self._search_client = None

    async def __aenter__(self) -> Self:
        """Enter the async context manager and return the adapter."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Close the clients when leaving the async context manager."""
        await self.close()

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
