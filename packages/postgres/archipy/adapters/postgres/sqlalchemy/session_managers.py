"""PostgreSQL SQLAlchemy session manager implementations."""

from typing import Any, override

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

    @classmethod
    @override
    def _default_config(cls) -> PostgresSQLAlchemyConfig:
        """Return the global config's POSTGRES_SQLALCHEMY section."""
        return BaseConfig.global_config().POSTGRES_SQLALCHEMY

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the PostgreSQL session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = orm_config or self._default_config()
        self._configs = configs  # read by _get_connect_args, which the base initializer calls
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
    def _get_connect_args(self) -> dict[str, Any]:
        """Return the psycopg connection arguments.

        Returns:
            dict[str, Any]: ``connect_timeout`` when configured, otherwise empty (libpq waits indefinitely).
        """
        return {} if self._configs.CONNECT_TIMEOUT is None else {"connect_timeout": self._configs.CONNECT_TIMEOUT}

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

    @classmethod
    @override
    def _default_config(cls) -> PostgresSQLAlchemyConfig:
        """Return the global config's POSTGRES_SQLALCHEMY section."""
        return BaseConfig.global_config().POSTGRES_SQLALCHEMY

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the async PostgreSQL session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = orm_config or self._default_config()
        self._configs = configs  # read by _get_connect_args, which the base initializer calls
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
    def _get_connect_args(self) -> dict[str, Any]:
        """Return the psycopg connection arguments.

        Returns:
            dict[str, Any]: ``connect_timeout`` when configured, otherwise empty (libpq waits indefinitely).
        """
        return {} if self._configs.CONNECT_TIMEOUT is None else {"connect_timeout": self._configs.CONNECT_TIMEOUT}

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
