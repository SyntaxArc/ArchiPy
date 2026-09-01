"""PostgreSQL SQLAlchemy adapter implementations."""

from typing import override

from archipy.adapters.base.sqlalchemy.adapters import AsyncBaseSQLAlchemyAdapter, BaseSQLAlchemyAdapter
from archipy.adapters.postgres.sqlalchemy.session_managers import (
    AsyncPostgresSQlAlchemySessionManager,
    PostgresSQlAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import PostgresSQLAlchemyConfig


class PostgresSQLAlchemyAdapter(BaseSQLAlchemyAdapter[PostgresSQLAlchemyConfig]):
    """Synchronous SQLAlchemy adapter for PostgreSQL.

    Inherits from BaseSQLAlchemyAdapter to provide PostgreSQL-specific session management
    and database operations.

    Args:
        orm_config: PostgreSQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the PostgreSQL adapter with a session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().POSTGRES_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _create_session_manager(self, configs: PostgresSQLAlchemyConfig) -> PostgresSQlAlchemySessionManager:
        """Create a PostgreSQL-specific session manager.

        Args:
            configs: PostgreSQL configuration.

        Returns:
            A PostgreSQL session manager instance.
        """
        return PostgresSQlAlchemySessionManager(configs)


class AsyncPostgresSQLAlchemyAdapter(AsyncBaseSQLAlchemyAdapter[PostgresSQLAlchemyConfig]):
    """Asynchronous SQLAlchemy adapter for PostgreSQL.

    Inherits from AsyncBaseSQLAlchemyAdapter to provide async PostgreSQL-specific session
    management and database operations.

    Args:
        orm_config: PostgreSQL-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: PostgresSQLAlchemyConfig | None = None) -> None:
        """Initialize the async PostgreSQL adapter with a session manager.

        Args:
            orm_config: PostgreSQL-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().POSTGRES_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _create_async_session_manager(self, configs: PostgresSQLAlchemyConfig) -> AsyncPostgresSQlAlchemySessionManager:
        """Create an async PostgreSQL-specific session manager.

        Args:
            configs: PostgreSQL configuration.

        Returns:
            An async PostgreSQL session manager instance.
        """
        return AsyncPostgresSQlAlchemySessionManager(configs)
