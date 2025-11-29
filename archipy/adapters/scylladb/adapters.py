"""ScyllaDB adapter implementations for sync and async operations.

This module provides concrete implementations of the ScyllaDB port interfaces,
supporting both synchronous and asynchronous database operations.
"""

import asyncio
import threading
from typing import Any, override

from cassandra import ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import Cluster, ResponseFuture, Session
from cassandra.policies import RoundRobinPolicy, TokenAwarePolicy
from cassandra.query import BatchStatement, PreparedStatement, SimpleStatement

from archipy.adapters.scylladb.ports import AsyncScyllaDBPort, ScyllaDBPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ScyllaDBConfig


class ScyllaDBAdapter(ScyllaDBPort):
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
        self._cluster: Cluster | None = None
        self._session: Session | None = None
        self._lock = threading.Lock()

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
        # Set up authentication if credentials provided
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Set up load balancing policy with TokenAwarePolicy for shard awareness
        # Using RoundRobinPolicy as the child policy for better distribution
        # TokenAwarePolicy enables shard awareness and tablet awareness automatically
        load_balancing_policy = TokenAwarePolicy(RoundRobinPolicy())

        # Create cluster with configuration
        # Shard awareness can be disabled for Docker/Testcontainer/NAT environments
        # as the driver cannot reach individual shard ports through port mapping
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
            shard_aware_options=shard_aware_options,
        )

        return cluster

    @override
    def connect(self) -> Session:
        """Establish connection to ScyllaDB cluster and return session.

        Returns:
            Session: The active session object.
        """
        with self._lock:
            if self._session is None:
                try:
                    self._cluster = self._create_cluster()
                    self._session = self._cluster.connect()

                    # Set default timeout
                    self._session.default_timeout = self.config.REQUEST_TIMEOUT

                    # Use keyspace if specified
                    if self.config.KEYSPACE:
                        self._session.set_keyspace(self.config.KEYSPACE)

                except Exception as e:
                    raise ConnectionError(f"Failed to connect to ScyllaDB: {e}") from e

            return self._session

    @override
    def disconnect(self) -> None:
        """Close connection to ScyllaDB cluster."""
        with self._lock:
            if self._session:
                try:
                    self._session.shutdown()
                except Exception as e:
                    raise ConnectionError(f"Failed to disconnect from ScyllaDB: {e}") from e
                finally:
                    self._session = None

            if self._cluster:
                try:
                    self._cluster.shutdown()
                except Exception as e:
                    raise ConnectionError(f"Failed to shutdown cluster: {e}") from e
                finally:
                    self._cluster = None

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
            raise RuntimeError(f"Failed to execute query: {e}") from e
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
        session = self.get_session()
        try:
            prepared = session.prepare(query)
        except Exception as e:
            raise RuntimeError(f"Failed to prepare statement: {e}") from e
        else:
            return prepared

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
            raise RuntimeError(f"Failed to execute prepared statement: {e}") from e
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
            raise RuntimeError(f"Failed to create keyspace '{keyspace}': {e}") from e

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
            raise RuntimeError(f"Failed to drop keyspace '{keyspace}': {e}") from e

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
            raise RuntimeError(f"Failed to use keyspace '{keyspace}': {e}") from e

    @override
    def create_table(self, table_schema: str) -> None:
        """Create a table using raw CQL DDL.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            self.execute(table_schema)
        except Exception as e:
            raise RuntimeError(f"Failed to create table: {e}") from e

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
            raise RuntimeError(f"Failed to drop table '{table}': {e}") from e

    @override
    def insert(self, table: str, data: dict[str, Any]) -> None:
        """Insert data into a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            # Pass values as a tuple in the order of columns
            self.execute(query, tuple(data.values()))
        except Exception as e:
            raise RuntimeError(f"Failed to insert into table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to select from table '{table}': {e}") from e

    @override
    def update(self, table: str, data: dict[str, Any], conditions: dict[str, Any]) -> None:
        """Update data in a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            self.execute(query, params)
        except Exception as e:
            raise RuntimeError(f"Failed to update table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to delete from table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to execute batch: {e}") from e

    @override
    def get_session(self) -> Session:
        """Get the current session object.

        Returns:
            Session: The active session object.
        """
        if self._session is None:
            return self.connect()
        return self._session

    def __enter__(self) -> "ScyllaDBAdapter":
        """Context manager entry.

        Returns:
            ScyllaDBAdapter: The adapter instance.
        """
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        self.disconnect()


class AsyncScyllaDBAdapter(AsyncScyllaDBPort):
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
        self._cluster: Cluster | None = None
        self._session: Session | None = None
        self._lock = asyncio.Lock()

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
        # Set up authentication if credentials provided
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Set up load balancing policy with TokenAwarePolicy for shard awareness
        # Using RoundRobinPolicy as the child policy for better distribution
        # TokenAwarePolicy enables shard awareness and tablet awareness automatically
        load_balancing_policy = TokenAwarePolicy(RoundRobinPolicy())

        # Create cluster with configuration
        # Shard awareness can be disabled for Docker/Testcontainer/NAT environments
        # as the driver cannot reach individual shard ports through port mapping
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
            shard_aware_options=shard_aware_options,
        )

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
    async def connect(self) -> Session:
        """Establish connection to ScyllaDB cluster asynchronously.

        Returns:
            Session: The active session object.
        """
        async with self._lock:
            if self._session is None:
                try:
                    self._cluster = self._create_cluster()
                    self._session = self._cluster.connect()

                    # Set default timeout
                    self._session.default_timeout = self.config.REQUEST_TIMEOUT

                    # Use keyspace if specified
                    if self.config.KEYSPACE:
                        self._session.set_keyspace(self.config.KEYSPACE)

                except Exception as e:
                    raise ConnectionError(f"Failed to connect to ScyllaDB: {e}") from e

            return self._session

    @override
    async def disconnect(self) -> None:
        """Close connection to ScyllaDB cluster asynchronously."""
        async with self._lock:
            if self._session:
                try:
                    self._session.shutdown()
                except Exception as e:
                    raise ConnectionError(f"Failed to disconnect from ScyllaDB: {e}") from e
                finally:
                    self._session = None

            if self._cluster:
                try:
                    self._cluster.shutdown()
                except Exception as e:
                    raise ConnectionError(f"Failed to shutdown cluster: {e}") from e
                finally:
                    self._cluster = None

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
            raise RuntimeError(f"Failed to execute query: {e}") from e
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
        session = await self.get_session()
        try:
            # Note: prepare is synchronous even for async sessions in cassandra driver
            prepared = session.prepare(query)
        except Exception as e:
            raise RuntimeError(f"Failed to prepare statement: {e}") from e
        else:
            return prepared

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
            raise RuntimeError(f"Failed to execute prepared statement: {e}") from e
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
            raise RuntimeError(f"Failed to create keyspace '{keyspace}': {e}") from e

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
            raise RuntimeError(f"Failed to drop keyspace '{keyspace}': {e}") from e

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
            raise RuntimeError(f"Failed to use keyspace '{keyspace}': {e}") from e

    @override
    async def create_table(self, table_schema: str) -> None:
        """Create a table asynchronously.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            await self.execute(table_schema)
        except Exception as e:
            raise RuntimeError(f"Failed to create table: {e}") from e

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
            raise RuntimeError(f"Failed to drop table '{table}': {e}") from e

    @override
    async def insert(self, table: str, data: dict[str, Any]) -> None:
        """Insert data into a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["%s" for _ in data.keys()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        try:
            await self.execute(query, tuple(data.values()))
        except Exception as e:
            raise RuntimeError(f"Failed to insert into table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to select from table '{table}': {e}") from e

    @override
    async def update(self, table: str, data: dict[str, Any], conditions: dict[str, Any]) -> None:
        """Update data in a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        set_clause = ", ".join([f"{key} = %s" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = %s" for key in conditions.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            await self.execute(query, params)
        except Exception as e:
            raise RuntimeError(f"Failed to update table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to delete from table '{table}': {e}") from e

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
            raise RuntimeError(f"Failed to execute batch: {e}") from e

    @override
    async def get_session(self) -> Session:
        """Get the current session object asynchronously.

        Returns:
            Session: The active session object.
        """
        if self._session is None:
            return await self.connect()
        return self._session

    async def __aenter__(self) -> "AsyncScyllaDBAdapter":
        """Async context manager entry.

        Returns:
            AsyncScyllaDBAdapter: The adapter instance.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.

        Args:
            exc_type: Exception type.
            exc_val: Exception value.
            exc_tb: Exception traceback.
        """
        await self.disconnect()
