"""Port interfaces for ScyllaDB adapter.

This module defines the abstract interfaces for ScyllaDB operations, providing
a standardized contract for implementations to follow. It includes both
synchronous and asynchronous port definitions.
"""

from abc import ABC, abstractmethod
from typing import Any


class ScyllaDBPort(ABC):
    """Interface for synchronous ScyllaDB operations.

    This interface defines the contract for ScyllaDB adapters, ensuring consistent
    implementation of database operations across different adapters. It covers
    CQL execution and CRUD operations.

    Note: Connection is established automatically during adapter initialization.
    Use the context manager (with statement) for automatic cleanup.
    """

    @abstractmethod
    def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a CQL query.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | None): Query parameters for parameterized queries.

        Returns:
            Any: The query result set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def prepare(self, query: str) -> Any:
        """Prepare a CQL statement for repeated execution.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            Any: The prepared statement object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def execute_prepared(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        """Execute a prepared statement.

        Args:
            statement (Any): The prepared statement object.
            params (dict[str, Any] | None): Parameters to bind to the statement.

        Returns:
            Any: The query result set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def create_keyspace(self, keyspace: str, replication_factor: int = 1) -> None:
        """Create a keyspace with simple replication strategy.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int): The replication factor. Defaults to 1.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace.

        Args:
            keyspace (str): The name of the keyspace to drop.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context.

        Args:
            keyspace (str): The name of the keyspace to use.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def create_table(self, table_schema: str) -> None:
        """Create a table using raw CQL DDL.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def drop_table(self, table: str) -> None:
        """Drop a table.

        Args:
            table (str): The name of the table to drop.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def insert(self, table: str, data: dict[str, Any], ttl: int | None = None, if_not_exists: bool = False) -> None:
        """Insert data into a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
            if_not_exists (bool): If True, use lightweight transaction (INSERT ... IF NOT EXISTS).
                              This prevents errors on duplicate primary keys but is slow

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, table: str, data: dict[str, Any], conditions: dict[str, Any], ttl: int | None = None) -> None:
        """Update data in a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def batch_execute(self, statements: list[str]) -> None:
        """Execute multiple CQL statements in a batch.

        Args:
            statements (list[str]): List of CQL statements to execute in batch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get_session(self) -> Any:
        """Get the current session object.

        Returns:
            Any: The active session object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncScyllaDBPort(ABC):
    """Interface for asynchronous ScyllaDB operations.

    This interface defines the contract for async ScyllaDB adapters, ensuring consistent
    implementation of database operations. All methods are async variants of the
    synchronous port.

    Note: Connection is established automatically during adapter initialization.
    Use the async context manager (async with statement) for automatic cleanup.
    """

    @abstractmethod
    async def execute(self, query: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a CQL query asynchronously.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | None): Query parameters for parameterized queries.

        Returns:
            Any: The query result set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def prepare(self, query: str) -> Any:
        """Prepare a CQL statement asynchronously.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            Any: The prepared statement object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_prepared(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        """Execute a prepared statement asynchronously.

        Args:
            statement (Any): The prepared statement object.
            params (dict[str, Any] | None): Parameters to bind to the statement.

        Returns:
            Any: The query result set.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_keyspace(self, keyspace: str, replication_factor: int = 1) -> None:
        """Create a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int): The replication factor. Defaults to 1.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to drop.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context asynchronously.

        Args:
            keyspace (str): The name of the keyspace to use.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_table(self, table_schema: str) -> None:
        """Create a table asynchronously.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def drop_table(self, table: str) -> None:
        """Drop a table asynchronously.

        Args:
            table (str): The name of the table to drop.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
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

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def batch_execute(self, statements: list[str]) -> None:
        """Execute multiple CQL statements in a batch asynchronously.

        Args:
            statements (list[str]): List of CQL statements to execute in batch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_session(self) -> Any:
        """Get the current session object asynchronously.

        Returns:
            Any: The active session object.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics asynchronously.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
