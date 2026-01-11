from typing import override

from sqlalchemy import URL
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql.functions import GenericFunction
from starrocks.dialect import StarRocksSQLCompiler, StarRocksTypeCompiler

from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import StarRocksSQLAlchemyConfig
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError


# Patch the StarRocks type compiler to map UUID to VARCHAR at module level
# This ensures the patch is applied before any engines are created
def _patch_starrocks_uuid_mapping() -> None:
    """Patch the StarRocks type compiler to map UUID to VARCHAR.

    StarRocks doesn't support UUID type natively, so we need to map it to VARCHAR(36).
    This is patched at module level to ensure it's applied before engine creation.
    """

    def visit_UUID(self: StarRocksTypeCompiler, type_: PostgresUUID, **kw: object) -> str:  # noqa: ARG001
        """Map PostgreSQL UUID to VARCHAR(36) for StarRocks."""
        return "VARCHAR(36)"

    # Patch the type compiler class
    StarRocksTypeCompiler.visit_UUID = visit_UUID  # ty:ignore[invalid-assignment]


def _patch_starrocks_now_function() -> None:
    """Patch the StarRocks SQL compiler to map func.now() to CURRENT_TIMESTAMP.

    StarRocks doesn't support now() function, it requires CURRENT_TIMESTAMP instead.
    This is patched at module level to ensure it's applied before engine creation.
    """
    # Store original visit_function if it exists
    original_visit_function = getattr(StarRocksSQLCompiler, "visit_function", None)

    def visit_function(self: StarRocksSQLCompiler, func_: GenericFunction, **kw: object) -> str:
        """Map func.now() to CURRENT_TIMESTAMP for StarRocks."""
        # Check if this is func.now()
        if func_.name == "now":
            return "CURRENT_TIMESTAMP"
        # For other functions, use the original handler if it exists
        if original_visit_function:
            return original_visit_function(self, func_, **kw)
        # Fallback to default behavior
        return f"{func_.name}()"

    # Patch the SQL compiler class
    StarRocksSQLCompiler.visit_function = visit_function  # ty:ignore[invalid-assignment]


# Apply the patches when the module is imported
_patch_starrocks_uuid_mapping()
_patch_starrocks_now_function()


class StarRocksSQlAlchemySessionManager(BaseSQLAlchemySessionManager[StarRocksSQLAlchemyConfig], metaclass=Singleton):
    """Synchronous SQLAlchemy session manager for StarRocks.

    Inherits from BaseSQLAlchemySessionManager to provide StarRocks-specific session
    management, including connection URL creation and engine configuration.

    Args:
        orm_config: StarRocks-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: StarRocksSQLAlchemyConfig | None = None) -> None:
        """Initialize the StarRocks session manager.

        Args:
            orm_config: StarRocks-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().STARROCKS_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[StarRocksSQLAlchemyConfig]:
        """Return the expected configuration type for StarRocks.

        Returns:
            The StarRocksSQLAlchemyConfig class.
        """
        return StarRocksSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('starrocks').
        """
        return "starrocks"

    @override
    def _create_url(self, configs: StarRocksSQLAlchemyConfig) -> URL:
        """Create a StarRocks connection URL.

        Args:
            configs: StarRocks configuration.

        Returns:
            A SQLAlchemy URL object for StarRocks.

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


class AsyncStarRocksSQlAlchemySessionManager(
    AsyncBaseSQLAlchemySessionManager[StarRocksSQLAlchemyConfig],
    metaclass=Singleton,
):
    """Asynchronous SQLAlchemy session manager for StarRocks.

    Inherits from AsyncBaseSQLAlchemySessionManager to provide async StarRocks-specific
    session management, including connection URL creation and async engine configuration.

    Args:
        orm_config: StarRocks-specific configuration. If None, uses global config.
    """

    def __init__(self, orm_config: StarRocksSQLAlchemyConfig | None = None) -> None:
        """Initialize the async StarRocks session manager.

        Args:
            orm_config: StarRocks-specific configuration. If None, uses global config.
        """
        configs = BaseConfig.global_config().STARROCKS_SQLALCHEMY if orm_config is None else orm_config
        super().__init__(configs)

    @override
    def _expected_config_type(self) -> type[StarRocksSQLAlchemyConfig]:
        """Return the expected configuration type for StarRocks.

        Returns:
            The StarRocksSQLAlchemyConfig class.
        """
        return StarRocksSQLAlchemyConfig

    @override
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database ('starrocks').
        """
        return "starrocks"

    @override
    def _create_url(self, configs: StarRocksSQLAlchemyConfig) -> URL:
        """Create an async StarRocks connection URL.

        For async operations, StarRocks requires an async driver (mysql+aiomysql)
        instead of the sync driver (mysql+pymysql).

        Args:
            configs: StarRocks configuration.

        Returns:
            A SQLAlchemy URL object for StarRocks with async driver.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            # For async operations, use mysql+aiomysql driver
            # If the driver is mysql+pymysql or starrocks, replace with mysql+aiomysql
            async_driver = configs.DRIVER_NAME
            if async_driver in ("mysql+pymysql", "starrocks", "mysql"):
                async_driver = "mysql+aiomysql"

            return URL.create(
                drivername=async_driver,
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

    @override
    def _get_connect_args(self) -> dict:
        """Return connection arguments for async StarRocks to ensure proper transaction support.

        StarRocks (using MySQL protocol) requires autocommit to be explicitly disabled
        to ensure transactions work properly with rollback support.

        Returns:
            A dictionary with autocommit=False to ensure transaction support.
        """
        return {"autocommit": False}
