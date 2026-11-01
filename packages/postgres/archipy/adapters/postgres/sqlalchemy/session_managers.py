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


def _build_connect_args(configs: PostgresSQLAlchemyConfig) -> dict[str, Any]:
    """Build the psycopg connection arguments from the configuration.

    Args:
        configs: PostgreSQL configuration.

    Returns:
        dict[str, Any]: Only the options that are configured (libpq defaults apply to the rest).
    """
    candidates = {
        "connect_timeout": configs.CONNECT_TIMEOUT,
        "sslmode": configs.SSL_MODE,
        "sslrootcert": configs.SSL_ROOT_CERT,
        "sslcert": configs.SSL_CERT,
        "sslkey": configs.SSL_KEY,
    }
    return {name: value for name, value in candidates.items() if value is not None}


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
            dict[str, Any]: The configured ``connect_timeout`` and TLS options, otherwise empty.
        """
        return _build_connect_args(self._configs)

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
            dict[str, Any]: The configured ``connect_timeout`` and TLS options, otherwise empty.
        """
        return _build_connect_args(self._configs)

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
