"""SQLite SQLAlchemy session manager implementations."""

from typing import override

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
    def _create_url(self, configs: SQLiteSQLAlchemyConfig) -> URL:
        """Create a SQLite connection URL.

        Args:
            configs: SQLite configuration.

        Returns:
            A SQLAlchemy URL object for SQLite.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=configs.DRIVER_NAME,
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
    def _create_url(self, configs: SQLiteSQLAlchemyConfig) -> URL:
        """Create an async SQLite connection URL.

        Args:
            configs: SQLite configuration.

        Returns:
            A SQLAlchemy URL object for SQLite.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=configs.DRIVER_NAME,
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e
