"""SQLite SQLAlchemy session manager implementations."""

from typing import Any, override

from sqlalchemy import URL
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


def _is_in_memory(database: str | None) -> bool:
    """Return whether the SQLite database path refers to an in-memory database.

    Args:
        database: The configured SQLite database path.

    Returns:
        bool: True for ``:memory:``, an empty path, or a ``mode=memory`` URI.
    """
    return not database or database == ":memory:" or "mode=memory" in database


def _sqlite_pool_kwargs(configs: SQLiteSQLAlchemyConfig, pool_kwargs: dict[str, Any]) -> dict[str, Any]:
    """Drop queue-pool arguments that SQLite in-memory pools do not accept.

    Args:
        configs: SQLite configuration.
        pool_kwargs: Pool arguments built by the base session manager.

    Returns:
        dict[str, Any]: Pool arguments valid for the pool class SQLAlchemy selects.
    """
    if not _is_in_memory(configs.DATABASE):
        return pool_kwargs
    return {key: value for key, value in pool_kwargs.items() if key not in _QUEUE_POOL_ONLY_KWARGS}


class SQLiteSQLAlchemySessionManager(BaseSQLAlchemySessionManager[SQLiteSQLAlchemyConfig], metaclass=Singleton):
    """Synchronous SQLAlchemy session manager for SQLite.

    Inherits from BaseSQLAlchemySessionManager to provide SQLite-specific session
    management, including connection URL creation and engine configuration.

    Args:
        orm_config: SQLite-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: SQLiteSQLAlchemyConfig | None = None) -> None:
        """Initialize the SQLite session manager.

        Args:
            orm_config: SQLite-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().SQLITE_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

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
                drivername=_SYNC_DRIVER if configs.DRIVER_NAME == _ASYNC_DRIVER else configs.DRIVER_NAME,
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

    def __init__(self, orm_config: SQLiteSQLAlchemyConfig | None = None) -> None:
        """Initialize the async SQLite session manager.

        Args:
            orm_config: SQLite-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().SQLITE_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

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
                drivername=_ASYNC_DRIVER if configs.DRIVER_NAME in _SYNC_DRIVERS else configs.DRIVER_NAME,
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e
