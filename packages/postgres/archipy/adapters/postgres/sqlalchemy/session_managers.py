"""PostgreSQL SQLAlchemy session manager implementations."""

from typing import override

from sqlalchemy import URL
from sqlalchemy.exc import SQLAlchemyError

from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import PostgresSQLAlchemyConfig
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError


class PostgresSQlAlchemySessionManager(BaseSQLAlchemySessionManager[PostgresSQLAlchemyConfig], metaclass=Singleton):
    """Synchronous SQLAlchemy session manager for PostgreSQL.

    Inherits from BaseSQLAlchemySessionManager to provide PostgreSQL-specific session
    management, including connection URL creation and engine configuration.

    Args:
        orm_config: PostgreSQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the PostgreSQL session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().POSTGRES_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[PostgresSQLAlchemyConfig]:
        """Return the expected configuration type for PostgreSQL.

        Returns:
            The PostgresSQLAlchemyConfig class.
        """
        return PostgresSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('postgresql').
        """
        return "postgresql"

    @override
    def _create_url(self, configs: PostgresSQLAlchemyConfig) -> URL:
        """Create a PostgreSQL connection URL.

        Args:
            configs: PostgreSQL configuration.

        Returns:
            A SQLAlchemy URL object for PostgreSQL.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=configs.DRIVER_NAME,
                username=configs.USERNAME,
                password=configs.PASSWORD,
                host=configs.HOST,
                port=configs.PORT,
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e


class AsyncPostgresSQlAlchemySessionManager(
    AsyncBaseSQLAlchemySessionManager[PostgresSQLAlchemyConfig],
    metaclass=Singleton,
):
    """Asynchronous SQLAlchemy session manager for PostgreSQL.

    Inherits from AsyncBaseSQLAlchemySessionManager to provide async PostgreSQL-specific
    session management, including connection URL creation and async engine configuration.

    Args:
        orm_config: PostgreSQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the async PostgreSQL session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().POSTGRES_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[PostgresSQLAlchemyConfig]:
        """Return the expected configuration type for PostgreSQL.

        Returns:
            The PostgresSQLAlchemyConfig class.
        """
        return PostgresSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('postgresql').
        """
        return "postgresql"

    @override
    def _create_url(self, configs: PostgresSQLAlchemyConfig) -> URL:
        """Create an async PostgreSQL connection URL.

        Args:
            configs: PostgreSQL configuration.

        Returns:
            A SQLAlchemy URL object for PostgreSQL.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername=configs.DRIVER_NAME,
                username=configs.USERNAME,
                password=configs.PASSWORD,
                host=configs.HOST,
                port=configs.PORT,
                database=configs.DATABASE,
            )
        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e
