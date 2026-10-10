"""MySQL SQLAlchemy adapter implementations."""

from typing import override

from archipy.adapters.base.sqlalchemy.adapters import AsyncBaseSQLAlchemyAdapter, BaseSQLAlchemyAdapter
from archipy.adapters.mysql.sqlalchemy.session_managers import (
    AsyncMySQLSQlAlchemySessionManager,
    MySQLSQlAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import MySQLSQLAlchemyConfig


class MySQLSQLAlchemyAdapter(BaseSQLAlchemyAdapter[MySQLSQLAlchemyConfig]):
    """Synchronous SQLAlchemy adapter for MySQL.

    Inherits from BaseSQLAlchemyAdapter to provide MySQL-specific session management
    and database operations.

    Args:
        orm_config: MySQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: MySQLSQLAlchemyConfig | None = None) -> None:
        """Initialize the MySQL adapter with a session manager.

        Args:
            orm_config: MySQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().MYSQL_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _create_session_manager(self, configs: MySQLSQLAlchemyConfig) -> MySQLSQlAlchemySessionManager:
        """Create a MySQL-specific session manager.

        Args:
            configs: MySQL configuration.

        Returns:
            A MySQL session manager instance.
        """
        return MySQLSQlAlchemySessionManager(configs)


class AsyncMySQLSQLAlchemyAdapter(AsyncBaseSQLAlchemyAdapter[MySQLSQLAlchemyConfig]):
    """Asynchronous SQLAlchemy adapter for MySQL.

    Inherits from AsyncBaseSQLAlchemyAdapter to provide async MySQL-specific session
    management and database operations.

    Args:
        orm_config: MySQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: MySQLSQLAlchemyConfig | None = None) -> None:
        """Initialize the async MySQL adapter with a session manager.

        Args:
            orm_config: MySQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().MYSQL_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _create_async_session_manager(self, configs: MySQLSQLAlchemyConfig) -> AsyncMySQLSQlAlchemySessionManager:
        """Create an async MySQL-specific session manager.

        Args:
            configs: MySQL configuration.

        Returns:
            An async MySQL session manager instance.
        """
        return AsyncMySQLSQlAlchemySessionManager(configs)
