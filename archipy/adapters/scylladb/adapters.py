"""ScyllaDB adapter implementations for sync and async operations.

This module provides concrete implementations of the ScyllaDB port interfaces,
supporting both synchronous and asynchronous database operations.
"""

import asyncio
import logging
import time
from typing import Any, override

from async_lru import alru_cache
from cassandra import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, ResponseFuture, Session
from cassandra.policies import (
    ExponentialBackoffRetryPolicy,
    FallthroughRetryPolicy,
    RoundRobinPolicy,
    TokenAwarePolicy,
)
from cassandra.query import BatchStatement, PreparedStatement, SimpleStatement

from archipy.adapters.scylladb.ports import AsyncScyllaDBPort, ScyllaDBPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ScyllaDBConfig
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.errors import (
    ConfigurationError,
    ConnectionTimeoutError,
    DatabaseConnectionError,
    DatabaseQueryError,
    InvalidArgumentError,
    InvalidCredentialsError,
    NetworkError,
    NotFoundError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class ScyllaDBExceptionHandlerMixin:
    """Mixin class to handle ScyllaDB/Cassandra exceptions in a consistent way."""

    @classmethod
    def _handle_scylladb_exception(cls, exception: Exception, operation: str) -> None:
        """Handle ScyllaDB/Cassandra exceptions and map them to appropriate application errors.

        Args:
            exception: The original exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_msg = str(exception).lower()

        if "unconfigured table" in error_msg:
            table_name = operation if operation else "unknown"
            raise NotFoundError(
                resource_type="table",
                additional_data={"table_name": table_name},
            ) from exception

        try:
            from cassandra import (
                AuthenticationFailed,
                InvalidRequest,
                OperationTimedOut,
                ProtocolException,
                Unavailable,
            )
            from cassandra.cluster import NoHostAvailable

            if isinstance(exception, Unavailable) or "unavailable" in error_msg:
                raise ServiceUnavailableError(service="ScyllaDB") from exception

            if isinstance(exception, OperationTimedOut) or "timeout" in error_msg:
                raise ConnectionTimeoutError(service="ScyllaDB", timeout=None) from exception

            if isinstance(exception, AuthenticationFailed) or "authentication" in error_msg:
                raise InvalidCredentialsError() from exception

            if isinstance(exception, InvalidRequest):
                raise InvalidArgumentError(argument_name=operation) from exception

            if isinstance(exception, ProtocolException) or "protocol" in error_msg:
                raise ConfigurationError(operation="scylladb", reason="Protocol error") from exception

            # NoHostAvailable
            if isinstance(exception, NoHostAvailable) or "no host available" in error_msg:
                raise ServiceUnavailableError(service="ScyllaDB") from exception

        except ImportError:
            pass

        if "network" in error_msg or "connection" in error_msg or "socket" in error_msg:
            raise NetworkError(service="ScyllaDB") from exception

        if "configuration" in error_msg or ("config" in error_msg and "unconfigured" not in error_msg):
            raise ConfigurationError(operation="scylladb", reason="Configuration error") from exception

        if "connection" in operation.lower() or "connect" in operation.lower():
            raise DatabaseConnectionError(database="scylladb") from exception
        raise DatabaseQueryError(database="scylladb") from exception


class ScyllaDBAdapter(ScyllaDBPort, ScyllaDBExceptionHandlerMixin):
    """Synchronous adapter for ScyllaDB operations.

    This adapter implements the ScyllaDBPort interface to provide a consistent
    way to interact with ScyllaDB, abstracting the underlying driver implementation.
    It supports connection pooling, prepared statements, and batch operations.

    Args:
        config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, config: ScyllaDBConfig | None = None) -> None:
        """Initialize the ScyllaDBAdapter with configuration settings.

        Args:
            config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
                If None, retrieves from global config. Defaults to None.
        """
        if config is not None:
            self.config = config
        else:
            try:
                self.config = BaseConfig.global_config().SCYLLADB
            except AttributeError:
                # SCYLLADB not configured, use defaults
                self.config = ScyllaDBConfig()
        self.__post_init__()
        try:
            self._cluster = self._create_cluster()
            self._session = self._cluster.connect()
            self._session.default_timeout = self.config.REQUEST_TIMEOUT
            if self.config.KEYSPACE:
                self._session.set_keyspace(self.config.KEYSPACE)

        except Exception as e:
            self._handle_scylladb_exception(e, "connect")
            raise

    def _get_consistency_level(self) -> ConsistencyLevel:
        """Get ConsistencyLevel enum from config string.

        Returns:
            ConsistencyLevel: The consistency level enum value.
        """
        consistency_map = {
            "ONE": ConsistencyLevel.ONE,
            "TWO": ConsistencyLevel.TWO,
            "THREE": ConsistencyLevel.THREE,
            "QUORUM": ConsistencyLevel.QUORUM,
            "ALL": ConsistencyLevel.ALL,
            "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
            "EACH_QUORUM": ConsistencyLevel.EACH_QUORUM,
            "LOCAL_ONE": ConsistencyLevel.LOCAL_ONE,
            "ANY": ConsistencyLevel.ANY,
        }
        return consistency_map.get(self.config.CONSISTENCY_LEVEL.upper(), ConsistencyLevel.ONE)

    def _create_cluster(self) -> Cluster:
        """Create and configure the Cluster instance.

        Returns:
            Cluster: Configured cluster instance.
        """
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Configure load balancing policy with optional datacenter awareness
        if self.config.LOCAL_DC:
            from cassandra.policies import DCAwareRoundRobinPolicy

            base_policy = DCAwareRoundRobinPolicy(local_dc=self.config.LOCAL_DC)
        else:
            base_policy = RoundRobinPolicy()

        load_balancing_policy = TokenAwarePolicy(base_policy)

        if self.config.RETRY_POLICY == "FALLTHROUGH":
            retry_policy = FallthroughRetryPolicy()
        else:  # EXPONENTIAL_BACKOFF (default)
            retry_policy = ExponentialBackoffRetryPolicy(
                max_num_retries=self.config.RETRY_MAX_NUM_RETRIES,
                min_interval=self.config.RETRY_MIN_INTERVAL,
                max_interval=self.config.RETRY_MAX_INTERVAL,
            )
        # Shard awareness disabled for Docker/NAT environments
        shard_aware_options = None
        if self.config.DISABLE_SHARD_AWARENESS:
            shard_aware_options = {"disable": True}

        cluster = Cluster(
            contact_points=self.config.CONTACT_POINTS,
            port=self.config.PORT,
            auth_provider=auth_provider,
            protocol_version=self.config.PROTOCOL_VERSION,
            compression=True if self.config.COMPRESSION else False,
            connect_timeout=self.config.CONNECT_TIMEOUT,
            load_balancing_policy=load_balancing_policy,
            default_retry_policy=retry_policy,
            shard_aware_options=shard_aware_options,
        )

        # Configure connection pool settings

        profile = cluster.profile_manager.default
        profile.request_timeout = self.config.REQUEST_TIMEOUT

        # Set pool configuration
        cluster.connection_class.max_requests_per_connection = self.config.MAX_REQUESTS_PER_CONNECTION

        return cluster

    @override
    def execute(self, query: str, params: dict[str, Any] | tuple | list | None = None) -> Any:
        """Execute a CQL query.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | tuple | list | None): Query parameters for parameterized queries.

        Returns:
            Any: The query result set.
        """
        session = self.get_session()
        try:
            if params:
                result = session.execute(query, params)
            else:
                result = session.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "execute")
            raise
        else:
            return result

    @override
    def prepare(self, query: str) -> PreparedStatement:
        """Prepare a CQL statement for repeated execution.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        return self._prepare_internal(query)

    def _prepare_internal(self, query: str) -> PreparedStatement:
        """Internal method to prepare a CQL statement (used by cache decorator).

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        session = self.get_session()
        try:
            prepared = session.prepare(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "prepare")
            raise
        else:
            return prepared

    def __post_init__(self) -> None:
        """Post-initialization hook to apply cache decorator if enabled."""
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            # Apply cache decorator to the bound method
            original_method = self._prepare_internal
            self._prepare_internal = ttl_cache_decorator(  # type: ignore[method-assign]
                ttl_seconds=self.config.PREPARED_STATEMENT_CACHE_TTL_SECONDS,
                maxsize=self.config.PREPARED_STATEMENT_CACHE_SIZE,
            )(original_method)

    @override
    def execute_prepared(self, statement: PreparedStatement, params: dict[str, Any] | None = None) -> Any:
        """Execute a prepared statement.

        Args:
            statement (PreparedStatement): The prepared statement object.
            params (dict[str, Any] | None): Parameters to bind to the statement.

        Returns:
            Any: The query result set.
        """
        session = self.get_session()
        try:
            if params:
                result = session.execute(statement, params)
            else:
                result = session.execute(statement)
        except Exception as e:
            self._handle_scylladb_exception(e, "execute_prepared")
            raise
        else:
            return result

    @override
    def create_keyspace(self, keyspace: str, replication_factor: int = 1) -> None:
        """Create a keyspace with simple replication strategy.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int): The replication factor. Defaults to 1.
        """
        query = f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': {replication_factor}}}
        """
        try:
            self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "create_keyspace")
            raise

    @override
    def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace.

        Args:
            keyspace (str): The name of the keyspace to drop.
        """
        query = f"DROP KEYSPACE IF EXISTS {keyspace}"
        try:
            self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "drop_keyspace")
            raise

    @override
    def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context.

        Args:
            keyspace (str): The name of the keyspace to use.
        """
        session = self.get_session()
        try:
            session.set_keyspace(keyspace)
        except Exception as e:
            self._handle_scylladb_exception(e, "use_keyspace")
            raise

    @override
    def create_table(self, table_schema: str) -> None:
        """Create a table using raw CQL DDL.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            self.execute(table_schema)
        except Exception as e:
            self._handle_scylladb_exception(e, "create_table")
            raise

    @override
    def drop_table(self, table: str) -> None:
        """Drop a table.

        Args:
            table (str): The name of the table to drop.
        """
        query = f"DROP TABLE IF EXISTS {table}"
        try:
            self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "drop_table")
            raise

    @override
    def insert(self, table: str, data: dict[str, Any], ttl: int | None = None, if_not_exists: bool = False) -> None:
        """Insert data into a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
            if_not_exists (bool): If True, use lightweight transaction (INSERT ... IF NOT EXISTS).
                              This prevents errors on duplicate primary keys but is slow
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        if if_not_exists:
            query += " IF NOT EXISTS"

        if ttl is not None:
            query += f" USING TTL {ttl}"

        try:
            self.execute(query, tuple(data.values()))
        except Exception as e:
            self._handle_scylladb_exception(e, "insert")
            raise

    @override
    def select(
        self,
        table: str,
        columns: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Select data from a table.

        Args:
            table (str): The name of the table.
            columns (list[str] | None): List of columns to select. If None, selects all (*).
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            list[Any]: List of result rows.
        """
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table}"

        params = None
        if conditions:
            where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
            query += f" WHERE {where_clause}"
            params = tuple(conditions.values())

        try:
            result = self.execute(query, params)
            return list(result)
        except Exception as e:
            self._handle_scylladb_exception(e, "select")
            raise

    @override
    def update(self, table: str, data: dict[str, Any], conditions: dict[str, Any], ttl: int | None = None) -> None:
        """Update data in a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
        """
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"UPDATE {table}"

        if ttl is not None:
            query += f" USING TTL {ttl}"

        query += f" SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            self.execute(query, params)
        except Exception as e:
            self._handle_scylladb_exception(e, "update")
            raise

    @override
    def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"

        try:
            self.execute(query, tuple(conditions.values()))
        except Exception as e:
            self._handle_scylladb_exception(e, "delete")
            raise

    @override
    def batch_execute(self, statements: list[str]) -> None:
        """Execute multiple CQL statements in a batch.

        Args:
            statements (list[str]): List of CQL statements to execute in batch.
        """
        session = self.get_session()
        batch = BatchStatement(consistency_level=self._get_consistency_level())

        try:
            for stmt in statements:
                batch.add(SimpleStatement(stmt))

            session.execute(batch)
        except Exception as e:
            self._handle_scylladb_exception(e, "batch_execute")
            raise

    @override
    def get_session(self) -> Session:
        """Get the current session object.

        Returns:
            Session: The active session object.
        """
        return self._session

    @override
    def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._session is not None and not self._session.is_shutdown

    def close(self) -> None:
        """Close the connection and clean up resources.

        This method should be called when the adapter is no longer needed
        to properly release resources.
        """
        try:
            if hasattr(self, "_session") and self._session is not None:
                self._session.shutdown()
            if hasattr(self, "_cluster") and self._cluster is not None:
                self._cluster.shutdown()
        except Exception as e:
            # Ignore errors during cleanup, but log them
            logger.debug(f"Error during ScyllaDB adapter cleanup: {e}")

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        try:
            self.close()
        except Exception as e:
            # Ignore errors during destructor cleanup
            logger.debug(f"Error in ScyllaDB adapter destructor: {e}")

    @override
    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.
        """
        if not self.is_connected():
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": "Not connected to cluster",
            }

        try:
            start_time = time.time()
            session = self.get_session()
            original_timeout = session.default_timeout
            session.default_timeout = self.config.HEALTH_CHECK_TIMEOUT
            try:
                session.execute("SELECT now() FROM system.local")
            finally:
                session.default_timeout = original_timeout
            latency_ms = (time.time() - start_time) * 1000
        except Exception as e:
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": str(e),
            }
        else:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "error": None,
            }

    @override
    def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.
        """
        query = f"SELECT COUNT(*) FROM {table}"

        params = None
        if conditions:
            where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
            query += f" WHERE {where_clause} ALLOW FILTERING"
            params = tuple(conditions.values())

        try:
            result = self.execute(query, params)
            row = result.one()
        except Exception as e:
            self._handle_scylladb_exception(e, "count")
            raise
        else:
            return row.count if row else 0

    @override
    def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.
        """
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause} LIMIT 1 ALLOW FILTERING"

        try:
            result = self.execute(query, tuple(conditions.values()))
            row = result.one()
        except Exception as e:
            self._handle_scylladb_exception(e, "exists")
            raise
        else:
            return row.count > 0 if row else False

    @override
    def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.
        """
        if not self.config.ENABLE_CONNECTION_POOL_MONITORING:
            return {
                "monitoring_enabled": False,
                "message": "Connection pool monitoring is disabled",
            }

        stats: dict[str, Any] = {"monitoring_enabled": True}

        try:
            session = self.get_session()
            cluster = self._cluster

            # Get pool state for each host
            hosts_stats = []
            for host in cluster.metadata.all_hosts():
                host_pool = session.get_pool_state(host)
                if host_pool:
                    hosts_stats.append(
                        {
                            "host": str(host),
                            "open_connections": host_pool.get("open_count", 0),
                            "in_flight_queries": host_pool.get("in_flight", 0),
                        },
                    )

            stats["hosts"] = hosts_stats
            stats["total_hosts"] = len(hosts_stats)
            stats["total_open_connections"] = sum(h.get("open_connections", 0) for h in hosts_stats)
            stats["total_in_flight_queries"] = sum(h.get("in_flight_queries", 0) for h in hosts_stats)

        except Exception as e:
            stats["error"] = str(e)

        return stats


class AsyncScyllaDBAdapter(AsyncScyllaDBPort, ScyllaDBExceptionHandlerMixin):
    """Asynchronous adapter for ScyllaDB operations.

    This adapter implements the AsyncScyllaDBPort interface to provide async
    database operations using the ScyllaDB driver's async capabilities.

    Args:
        config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, config: ScyllaDBConfig | None = None) -> None:
        """Initialize the AsyncScyllaDBAdapter with configuration settings.

        Args:
            config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
                If None, retrieves from global config. Defaults to None.
        """
        if config is not None:
            self.config = config
        else:
            try:
                self.config = BaseConfig.global_config().SCYLLADB
            except AttributeError:
                # SCYLLADB not configured, use defaults
                self.config = ScyllaDBConfig()
        self.__post_init__()
        try:
            self._cluster = self._create_cluster()
            self._session = self._cluster.connect()
            self._session.default_timeout = self.config.REQUEST_TIMEOUT
            if self.config.KEYSPACE:
                self._session.set_keyspace(self.config.KEYSPACE)

        except Exception as e:
            self._handle_scylladb_exception(e, "connect")
            raise

    def _get_consistency_level(self) -> ConsistencyLevel:
        """Get ConsistencyLevel enum from config string.

        Returns:
            ConsistencyLevel: The consistency level enum value.
        """
        consistency_map = {
            "ONE": ConsistencyLevel.ONE,
            "TWO": ConsistencyLevel.TWO,
            "THREE": ConsistencyLevel.THREE,
            "QUORUM": ConsistencyLevel.QUORUM,
            "ALL": ConsistencyLevel.ALL,
            "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
            "EACH_QUORUM": ConsistencyLevel.EACH_QUORUM,
            "LOCAL_ONE": ConsistencyLevel.LOCAL_ONE,
            "ANY": ConsistencyLevel.ANY,
        }
        return consistency_map.get(self.config.CONSISTENCY_LEVEL.upper(), ConsistencyLevel.ONE)

    def _create_cluster(self) -> Cluster:
        """Create and configure the Cluster instance.

        Returns:
            Cluster: Configured cluster instance.
        """
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Configure load balancing policy with optional datacenter awareness
        if self.config.LOCAL_DC:
            from cassandra.policies import DCAwareRoundRobinPolicy

            base_policy = DCAwareRoundRobinPolicy(local_dc=self.config.LOCAL_DC)
        else:
            base_policy = RoundRobinPolicy()

        load_balancing_policy = TokenAwarePolicy(base_policy)

        if self.config.RETRY_POLICY == "FALLTHROUGH":
            retry_policy = FallthroughRetryPolicy()
        else:  # EXPONENTIAL_BACKOFF (default)
            retry_policy = ExponentialBackoffRetryPolicy(
                max_num_retries=self.config.RETRY_MAX_NUM_RETRIES,
                min_interval=self.config.RETRY_MIN_INTERVAL,
                max_interval=self.config.RETRY_MAX_INTERVAL,
            )
        # Shard awareness disabled for Docker/NAT environments
        shard_aware_options = None
        if self.config.DISABLE_SHARD_AWARENESS:
            shard_aware_options = {"disable": True}

        cluster = Cluster(
            contact_points=self.config.CONTACT_POINTS,
            port=self.config.PORT,
            auth_provider=auth_provider,
            protocol_version=self.config.PROTOCOL_VERSION,
            compression=True if self.config.COMPRESSION else False,
            connect_timeout=self.config.CONNECT_TIMEOUT,
            load_balancing_policy=load_balancing_policy,
            default_retry_policy=retry_policy,
            shard_aware_options=shard_aware_options,
        )

        # Configure connection pool settings

        profile = cluster.profile_manager.default
        profile.request_timeout = self.config.REQUEST_TIMEOUT

        # Set pool configuration
        cluster.connection_class.max_requests_per_connection = self.config.MAX_REQUESTS_PER_CONNECTION

        return cluster

    async def _await_future(self, future: ResponseFuture) -> Any:
        """Convert ResponseFuture to awaitable.

        Args:
            future (ResponseFuture): The response future from async execution.

        Returns:
            Any: The result from the future.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, future.result)

    @override
    async def execute(self, query: str, params: dict[str, Any] | tuple | list | None = None) -> Any:
        """Execute a CQL query asynchronously.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | tuple | list | None): Query parameters for parameterized queries.

        Returns:
            Any: The query result set.
        """
        session = await self.get_session()
        try:
            if params:
                future = session.execute_async(query, params)
            else:
                future = session.execute_async(query)
            result = await self._await_future(future)
        except Exception as e:
            self._handle_scylladb_exception(e, "execute")
            raise
        else:
            return result

    @override
    async def prepare(self, query: str) -> PreparedStatement:
        """Prepare a CQL statement asynchronously.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        return await self._prepare_internal(query)

    async def _prepare_internal(self, query: str) -> PreparedStatement:
        """Internal method to prepare a CQL statement (used by cache decorator).

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        session = await self.get_session()
        try:
            prepared = session.prepare(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "prepare")
            raise
        else:
            return prepared

    def __post_init__(self) -> None:
        """Post-initialization hook to apply cache decorator if enabled."""
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            # Apply cache decorator to the bound method
            original_method = self._prepare_internal
            self._prepare_internal = alru_cache(  # type: ignore[method-assign]
                ttl=self.config.PREPARED_STATEMENT_CACHE_TTL_SECONDS,
                maxsize=self.config.PREPARED_STATEMENT_CACHE_SIZE,
            )(original_method)

    @override
    async def execute_prepared(self, statement: PreparedStatement, params: dict[str, Any] | None = None) -> Any:
        """Execute a prepared statement asynchronously.

        Args:
            statement (PreparedStatement): The prepared statement object.
            params (dict[str, Any] | None): Parameters to bind to the statement.

        Returns:
            Any: The query result set.
        """
        session = await self.get_session()
        try:
            if params:
                future = session.execute_async(statement, params)
            else:
                future = session.execute_async(statement)
            result = await self._await_future(future)
        except Exception as e:
            self._handle_scylladb_exception(e, "execute_prepared")
            raise
        else:
            return result

    @override
    async def create_keyspace(self, keyspace: str, replication_factor: int = 1) -> None:
        """Create a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int): The replication factor. Defaults to 1.
        """
        query = f"""
            CREATE KEYSPACE IF NOT EXISTS {keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': {replication_factor}}}
        """
        try:
            await self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "create_keyspace")
            raise

    @override
    async def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to drop.
        """
        query = f"DROP KEYSPACE IF EXISTS {keyspace}"
        try:
            await self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "drop_keyspace")
            raise

    @override
    async def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context asynchronously.

        Args:
            keyspace (str): The name of the keyspace to use.
        """
        session = await self.get_session()
        try:
            session.set_keyspace(keyspace)
        except Exception as e:
            self._handle_scylladb_exception(e, "use_keyspace")
            raise

    @override
    async def create_table(self, table_schema: str) -> None:
        """Create a table asynchronously.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            await self.execute(table_schema)
        except Exception as e:
            self._handle_scylladb_exception(e, "create_table")
            raise

    @override
    async def drop_table(self, table: str) -> None:
        """Drop a table asynchronously.

        Args:
            table (str): The name of the table to drop.
        """
        query = f"DROP TABLE IF EXISTS {table}"
        try:
            await self.execute(query)
        except Exception as e:
            self._handle_scylladb_exception(e, "drop_table")
            raise

    @override
    async def insert(
        self,
        table: str,
        data: dict[str, Any],
        ttl: int | None = None,
        if_not_exists: bool = False,
    ) -> None:
        """Insert data into a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
            if_not_exists (bool): If True, use lightweight transaction (INSERT ... IF NOT EXISTS).
                              This prevents errors on duplicate primary keys but is slow
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        if if_not_exists:
            query += " IF NOT EXISTS"

        if ttl is not None:
            query += f" USING TTL {ttl}"

        try:
            await self.execute(query, tuple(data.values()))
        except Exception as e:
            self._handle_scylladb_exception(e, "insert")
            raise

    @override
    async def select(
        self,
        table: str,
        columns: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> list[Any]:
        """Select data from a table asynchronously.

        Args:
            table (str): The name of the table.
            columns (list[str] | None): List of columns to select. If None, selects all (*).
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            list[Any]: List of result rows.
        """
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table}"

        params = None
        if conditions:
            where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
            query += f" WHERE {where_clause}"
            params = tuple(conditions.values())

        try:
            result = await self.execute(query, params)
            return list(result)
        except Exception as e:
            self._handle_scylladb_exception(e, "select")
            raise

    @override
    async def update(
        self,
        table: str,
        data: dict[str, Any],
        conditions: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Update data in a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
        """
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"UPDATE {table}"

        if ttl is not None:
            query += f" USING TTL {ttl}"

        query += f" SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            await self.execute(query, params)
        except Exception as e:
            self._handle_scylladb_exception(e, "update")
            raise

    @override
    async def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"DELETE FROM {table} WHERE {where_clause}"

        try:
            await self.execute(query, tuple(conditions.values()))
        except Exception as e:
            self._handle_scylladb_exception(e, "delete")
            raise

    @override
    async def batch_execute(self, statements: list[str]) -> None:
        """Execute multiple CQL statements in a batch asynchronously.

        Args:
            statements (list[str]): List of CQL statements to execute in batch.
        """
        session = await self.get_session()
        batch = BatchStatement(consistency_level=self._get_consistency_level())

        try:
            for stmt in statements:
                batch.add(SimpleStatement(stmt))

            future = session.execute_async(batch)
            await self._await_future(future)
        except Exception as e:
            self._handle_scylladb_exception(e, "batch_execute")
            raise

    @override
    async def get_session(self) -> Session:
        """Get the current session object asynchronously.

        Returns:
            Session: The active session object.
        """
        return self._session

    @override
    async def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._session is not None and not self._session.is_shutdown

    async def close(self) -> None:
        """Close the connection and clean up resources asynchronously.

        This method should be called when the adapter is no longer needed
        to properly release resources.
        """
        try:
            if hasattr(self, "_session") and self._session is not None:
                self._session.shutdown()
            if hasattr(self, "_cluster") and self._cluster is not None:
                self._cluster.shutdown()
        except Exception as e:
            # Ignore errors during cleanup, but log them
            logger.debug(f"Error during async ScyllaDB adapter cleanup: {e}")

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        try:
            if hasattr(self, "_session") and self._session is not None:
                self._session.shutdown()
            if hasattr(self, "_cluster") and self._cluster is not None:
                self._cluster.shutdown()
        except Exception as e:
            # Ignore errors during destructor cleanup
            logger.debug(f"Error in async ScyllaDB adapter destructor: {e}")

    @override
    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.
        """
        if not await self.is_connected():
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": "Not connected to cluster",
            }

        try:
            start_time = time.time()
            session = await self.get_session()
            original_timeout = session.default_timeout
            session.default_timeout = self.config.HEALTH_CHECK_TIMEOUT
            try:
                future = session.execute_async("SELECT now() FROM system.local")
                await self._await_future(future)
            finally:
                session.default_timeout = original_timeout
            latency_ms = (time.time() - start_time) * 1000
        except Exception as e:
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": str(e),
            }
        else:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "error": None,
            }

    @override
    async def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.
        """
        query = f"SELECT COUNT(*) FROM {table}"

        params = None
        if conditions:
            where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
            query += f" WHERE {where_clause} ALLOW FILTERING"
            params = tuple(conditions.values())

        try:
            result = await self.execute(query, params)
            row = result.one()
        except Exception as e:
            self._handle_scylladb_exception(e, "count")
            raise
        else:
            return row.count if row else 0

    @override
    async def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.
        """
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"SELECT COUNT(*) FROM {table} WHERE {where_clause} LIMIT 1 ALLOW FILTERING"

        try:
            result = await self.execute(query, tuple(conditions.values()))
            row = result.one()
        except Exception as e:
            self._handle_scylladb_exception(e, "exists")
            raise
        else:
            return row.count > 0 if row else False

    @override
    async def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics asynchronously.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.
        """
        if not self.config.ENABLE_CONNECTION_POOL_MONITORING:
            return {
                "monitoring_enabled": False,
                "message": "Connection pool monitoring is disabled",
            }

        stats: dict[str, Any] = {"monitoring_enabled": True}

        try:
            session = await self.get_session()
            cluster = self._cluster

            # Get pool state for each host
            hosts_stats = []
            for host in cluster.metadata.all_hosts():
                host_pool = session.get_pool_state(host)
                if host_pool:
                    hosts_stats.append(
                        {
                            "host": str(host),
                            "open_connections": host_pool.get("open_count", 0),
                            "in_flight_queries": host_pool.get("in_flight", 0),
                        },
                    )

            stats["hosts"] = hosts_stats
            stats["total_hosts"] = len(hosts_stats)
            stats["total_open_connections"] = sum(h.get("open_connections", 0) for h in hosts_stats)
            stats["total_in_flight_queries"] = sum(h.get("in_flight_queries", 0) for h in hosts_stats)

        except Exception as e:
            stats["error"] = str(e)

        return stats
