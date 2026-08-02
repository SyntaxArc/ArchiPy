from typing import TYPE_CHECKING, Any, override

from sqlalchemy import URL
from sqlalchemy.dialects.mysql.base import MySQLTypeCompiler
from sqlalchemy.exc import SQLAlchemyError

from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import MySQLSQLAlchemyConfig
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError

if TYPE_CHECKING:
    from sqlalchemy.dialects.postgresql import UUID as PostgresUUID


def _patch_mysql_uuid_mapping() -> None:
    """Patch the MySQL type compiler to map UUID to VARCHAR.

    MySQL does not support a native UUID column type, so PostgreSQL UUID
    columns used in shared entity models must be mapped to VARCHAR(36).
    This is patched at module level to ensure it is applied before engine creation.
    """

    def visit_UUID(self: MySQLTypeCompiler, type_: PostgresUUID, **kw: Any) -> str:  # noqa: ARG001, ANN401
        """Map PostgreSQL UUID to VARCHAR(36) for MySQL."""
        return "VARCHAR(36)"

    MySQLTypeCompiler.visit_UUID = visit_UUID


# Apply the patch when the module is imported
_patch_mysql_uuid_mapping()


class MySQLSQlAlchemySessionManager(BaseSQLAlchemySessionManager[MySQLSQLAlchemyConfig], metaclass=Singleton):
    """Synchronous SQLAlchemy session manager for MySQL.

    Inherits from BaseSQLAlchemySessionManager to provide MySQL-specific session
    management, including connection URL creation and engine configuration.

    Args:
        orm_config: MySQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: MySQLSQLAlchemyConfig | None = None) -> None:
        """Initialize the MySQL session manager.

        Args:
            orm_config: MySQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().MYSQL_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[MySQLSQLAlchemyConfig]:
        """Return the expected configuration type for MySQL.

        Returns:
            The MySQLSQLAlchemyConfig class.
        """
        return MySQLSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('mysql').
        """
        return "mysql"

    @override
    def _create_url(self, configs: MySQLSQLAlchemyConfig) -> URL:
        """Create a MySQL connection URL.

        Args:
            configs: MySQL configuration.

        Returns:
            A SQLAlchemy URL object for MySQL.

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


class AsyncMySQLSQlAlchemySessionManager(
    AsyncBaseSQLAlchemySessionManager[MySQLSQLAlchemyConfig],
    metaclass=Singleton,
):
    """Asynchronous SQLAlchemy session manager for MySQL.

    Inherits from AsyncBaseSQLAlchemySessionManager to provide async MySQL-specific
    session management, including connection URL creation and async engine configuration.

    Args:
        orm_config: MySQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: MySQLSQLAlchemyConfig | None = None) -> None:
        """Initialize the async MySQL session manager.

        Args:
            orm_config: MySQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().MYSQL_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[MySQLSQLAlchemyConfig]:
        """Return the expected configuration type for MySQL.

        Returns:
            The MySQLSQLAlchemyConfig class.
        """
        return MySQLSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('mysql').
        """
        return "mysql"

    @override
    def _create_url(self, configs: MySQLSQLAlchemyConfig) -> URL:
        """Create an async MySQL connection URL.

        For async operations, MySQL uses the mysql+asyncmy driver which is provided
        by the asyncmy2 package.

        Args:
            configs: MySQL configuration.

        Returns:
            A SQLAlchemy URL object for MySQL with async driver.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername="mysql+asyncmy",
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
