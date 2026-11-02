"""SQLite SQLAlchemy session manager implementations."""

from typing import Any, override

from sqlalchemy import URL, Engine, event
from sqlalchemy.exc import SQLAlchemyError

from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError

_SYNC_DRIVER = "sqlite"
_ASYNC_DRIVER = "sqlite+aiosqlite"
_SYNC_DRIVERS = frozenset({"sqlite", "sqlite+pysqlite"})
# Queue-pool-only arguments; SQLite in-memory engines use SingletonThreadPool/StaticPool, which reject them.
_QUEUE_POOL_ONLY_KWARGS = frozenset({"pool_size", "max_overflow", "pool_timeout", "pool_use_lifo"})
_MEMORY_DATABASE = ":memory:"


def _uses_single_connection_pool(database: str | None) -> bool:
    """Return whether SQLAlchemy gives the SQLite database a single-connection pool.

    SQLAlchemy 2.1 selects the pool class from the database name alone: an empty name or ``:memory:`` gets
    SingletonThreadPool/StaticPool, any other name (including a ``mode=memory`` URI) gets QueuePool.

    Args:
        database: The configured SQLite database path.

    Returns:
        bool: True for ``:memory:`` or an empty path.
    """
    return not database or database == _MEMORY_DATABASE


def _is_in_memory(database: str | None) -> bool:
    """Return whether the SQLite database path refers to an in-memory database.

    Args:
        database: The configured SQLite database path.

    Returns:
        bool: True for ``:memory:``, an empty path, or a memory URI such as ``file::memory:?cache=shared`` or
        ``file:name?mode=memory&cache=shared``.
    """
    if not database:
        return True
    return _MEMORY_DATABASE in database or "mode=memory" in database


def _sqlite_pool_kwargs(configs: SQLiteSQLAlchemyConfig, pool_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop pool arguments that SQLite in-memory databases cannot use.

    Recycling closes the connection, and closing the last connection to an in-memory database discards it, so
    ``pool_recycle`` is never passed for one. Single-connection pools also reject queue-pool arguments.

    Args:
        configs: SQLite configuration.
        pool_kwargs: Pool arguments built by the base session manager.

    Returns:
        dict[str, Any]: Pool arguments valid for the pool class SQLAlchemy selects.
    """
    if not _is_in_memory(configs.DATABASE):
        return pool_kwargs
    dropped = {"pool_recycle"}
    if _uses_single_connection_pool(configs.DATABASE):
        dropped |= _QUEUE_POOL_ONLY_KWARGS
    return {key: value for key, value in pool_kwargs.items() if key not in dropped}


def _build_connect_args(configs: SQLiteSQLAlchemyConfig, *, sync_driver: bool) -> dict[str, Any]:
    """Build the sqlite3 connection arguments from the configuration.

    Args:
        configs: SQLite configuration.
        sync_driver: Whether the sync driver is used (``check_same_thread`` has no meaning for aiosqlite,
            which runs its own connection thread).

    Returns:
        dict[str, Any]: Only the options that are configured (the sqlite3 defaults apply to the rest).
    """
    connect_args: dict[str, Any] = {}
    if configs.TIMEOUT is not None:
        connect_args["timeout"] = configs.TIMEOUT
    if sync_driver and configs.CHECK_SAME_THREAD is not None:
        connect_args["check_same_thread"] = configs.CHECK_SAME_THREAD
    return connect_args


def _enable_foreign_keys(engine: Engine) -> None:
    """Turn on foreign key enforcement for every connection the engine opens (SQLite has it off by default)."""

    @event.listens_for(engine, "connect")
    def set_foreign_keys_pragma(dbapi_connection: Any, _connection_record: object) -> None:  # noqa: ANN401
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()


class SQLiteSQLAlchemySessionManager(BaseSQLAlchemySessionManager[SQLiteSQLAlchemyConfig], metaclass=Singleton):
    """Synchronous SQLAlchemy session manager for SQLite.

    Inherits from BaseSQLAlchemySessionManager to provide SQLite-specific session
    management, including connection URL creation and engine configuration.

    Args:
        orm_config: SQLite-specific configuration. If None, uses global config.
    """

    @classmethod
    @override
    def _default_config(cls) -> SQLiteSQLAlchemyConfig:
        """Return the global config's SQLITE_SQLALCHEMY section."""
        return BaseConfig.global_config().SQLITE_SQLALCHEMY

    def __init__(self, orm_config: SQLiteSQLAlchemyConfig | None = None) -> None:
        """Initialize the SQLite session manager.

        Args:
            orm_config: SQLite-specific configuration. If None, uses global config.
        """
        configs = orm_config or self._default_config()
        self._configs = configs  # read by _get_connect_args, which the base initializer calls
        super().__init__(configs)
        if configs.FOREIGN_KEYS:
            _enable_foreign_keys(self.engine)

    @override
    def _expected_config_type(self) -> type[SQLiteSQLAlchemyConfig]:
        """Return the expected configuration type for SQLite.

        Returns:
            The SQLiteSQLAlchemyConfig class.
        """
        return SQLiteSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('sqlite').
        """
        return "sqlite"

    @override
    def _get_connect_args(self) -> dict[str, Any]:
        """Return the sqlite3 connection arguments.

        Returns:
            dict[str, Any]: The configured busy timeout and thread check, otherwise empty.
        """
        return _build_connect_args(self._configs, sync_driver=True)

    @override
    def _get_pool_kwargs(self, configs: SQLiteSQLAlchemyConfig) -> dict[str, Any]:
        """Return pool arguments valid for the SQLite pool class.

        Args:
            configs: SQLite configuration.

        Returns:
            dict[str, Any]: Pool arguments without queue-pool options for in-memory databases.
        """
        return _sqlite_pool_kwargs(configs, super()._get_pool_kwargs(configs))

    @override
    def _create_url(self, configs: SQLiteSQLAlchemyConfig) -> URL:
        """Create a SQLite connection URL.

        Args:
            configs: SQLite configuration.

        Returns:
            A SQLAlchemy URL object for SQLite. An async driver such as ``sqlite+aiosqlite``
            is swapped for the sync ``sqlite`` driver.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=(_SYNC_DRIVER if configs.DRIVER_NAME == _ASYNC_DRIVER else configs.DRIVER_NAME),
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e


class AsyncSQLiteSQLAlchemySessionManager(
    AsyncBaseSQLAlchemySessionManager[SQLiteSQLAlchemyConfig],
    metaclass=Singleton,
):
    """Asynchronous SQLAlchemy session manager for SQLite.

    Inherits from AsyncBaseSQLAlchemySessionManager to provide async SQLite-specific
    session management, including connection URL creation and async engine configuration.

    Args:
        orm_config: SQLite-specific configuration. If None, uses global config.
    """

    @classmethod
    @override
    def _default_config(cls) -> SQLiteSQLAlchemyConfig:
        """Return the global config's SQLITE_SQLALCHEMY section."""
        return BaseConfig.global_config().SQLITE_SQLALCHEMY

    def __init__(self, orm_config: SQLiteSQLAlchemyConfig | None = None) -> None:
        """Initialize the async SQLite session manager.

        Args:
            orm_config: SQLite-specific configuration. If None, uses global config.
        """
        configs = orm_config or self._default_config()
        self._configs = configs  # read by _get_connect_args, which the base initializer calls
        super().__init__(configs)
        if configs.FOREIGN_KEYS:
            _enable_foreign_keys(self.engine.sync_engine)

    @override
    def _expected_config_type(self) -> type[SQLiteSQLAlchemyConfig]:
        """Return the expected configuration type for SQLite.

        Returns:
            The SQLiteSQLAlchemyConfig class.
        """
        return SQLiteSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('sqlite').
        """
        return "sqlite"

    @override
    def _get_connect_args(self) -> dict[str, Any]:
        """Return the sqlite3 connection arguments.

        Returns:
            dict[str, Any]: The configured busy timeout, otherwise empty.
        """
        return _build_connect_args(self._configs, sync_driver=False)

    @override
    def _get_pool_kwargs(self, configs: SQLiteSQLAlchemyConfig) -> dict[str, Any]:
        """Return pool arguments valid for the SQLite pool class.

        Args:
            configs: SQLite configuration.

        Returns:
            dict[str, Any]: Pool arguments without queue-pool options for in-memory databases.
        """
        return _sqlite_pool_kwargs(configs, super()._get_pool_kwargs(configs))

    @override
    def _create_url(self, configs: SQLiteSQLAlchemyConfig) -> URL:
        """Create an async SQLite connection URL.

        Args:
            configs: SQLite configuration.

        Returns:
            A SQLAlchemy URL object for SQLite. A sync driver such as ``sqlite`` is swapped
            for the async ``sqlite+aiosqlite`` driver.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=(_ASYNC_DRIVER if configs.DRIVER_NAME in _SYNC_DRIVERS else configs.DRIVER_NAME),
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e
