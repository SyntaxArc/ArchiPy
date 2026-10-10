"""StarRocks SQLAlchemy session manager implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from sqlalchemy import URL
from sqlalchemy.exc import SQLAlchemyError
from starrocks.dialect import StarRocksDialect, StarRocksSQLCompiler, StarRocksTypeCompiler

from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import StarRocksSQLAlchemyConfig
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError

if TYPE_CHECKING:
    from sqlalchemy.dialects.mysql.base import MySQLTypeCompiler
    from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.sql.compiler import SQLCompiler
    from sqlalchemy.sql.functions import Function

# Pin SQL transactions so BEGIN/COMMIT/ROLLBACK are not no-ops (StarRocks 4.x session var).
_STARROCKS_ENABLE_SQL_TRANSACTION = "SET enable_sql_transaction = TRUE"


# Patch the StarRocks type compiler to map UUID to VARCHAR at module level
# This ensures the patch is applied before any engines are created
def _patch_starrocks_uuid_mapping() -> None:
    """Patch the StarRocks type compiler to map UUID to VARCHAR.

    StarRocks doesn't support UUID type natively, so we need to map it to VARCHAR(36).
    This is patched at module level to ensure it's applied before engine creation.
    """

    def visit_UUID(self: MySQLTypeCompiler, type_: PostgresUUID, **kw: object) -> str:  # noqa: ARG001
        """Map PostgreSQL UUID to VARCHAR(36) for StarRocks."""
        return "VARCHAR(36)"

    # Patch the type compiler class
    StarRocksTypeCompiler.visit_UUID = visit_UUID


def _patch_starrocks_now_function() -> None:
    """Patch the StarRocks SQL compiler to map func.now() to CURRENT_TIMESTAMP.

    StarRocks doesn't support now() function, it requires CURRENT_TIMESTAMP instead.
    This is patched at module level to ensure it's applied before engine creation.
    """
    # Store original visit_function if it exists
    original_visit_function = getattr(StarRocksSQLCompiler, "visit_function", None)

    def visit_function(
        self: SQLCompiler,
        func: Function,
        add_to_result_map: object | None = None,
        **kw: object,
    ) -> str:
        """Map func.now() to CURRENT_TIMESTAMP for StarRocks."""
        # Check if this is func.now()
        if func.name == "now":
            return "CURRENT_TIMESTAMP"
        # For other functions, use the original handler if it exists
        if original_visit_function:
            return original_visit_function(self, func, add_to_result_map=add_to_result_map, **kw)
        # Fallback to default behavior
        return f"{func.name}()"

    # Patch the SQL compiler class
    StarRocksSQLCompiler.visit_function = visit_function


def _patch_starrocks_do_begin() -> None:
    """Patch StarRocksDialect.do_begin to emit an explicit BEGIN.

    The MySQL dialect inherited by StarRocks leaves ``do_begin`` as a no-op and
    relies on implicit transactions when autocommit is False. StarRocks requires
    an explicit ``BEGIN`` / ``START TRANSACTION`` for SQL transactions; without
    it each DML auto-commits and later ``ROLLBACK`` is a no-op.

    When the DBAPI connection is in autocommit mode (used for DDL, which StarRocks
    forbids inside an explicit transaction), skip emitting ``BEGIN``.
    """

    def do_begin(self: StarRocksDialect, dbapi_connection: DBAPIConnection) -> None:
        """Start an explicit StarRocks SQL transaction when not in autocommit."""
        if self.detect_autocommit_setting(dbapi_connection):
            return
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("BEGIN")
        finally:
            cursor.close()

    StarRocksDialect.do_begin = do_begin  # ty: ignore[invalid-assignment]


# Apply the patches when the module is imported
_patch_starrocks_uuid_mapping()
_patch_starrocks_now_function()
_patch_starrocks_do_begin()


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
    def _get_connect_args(self) -> dict:
        """Return connection arguments for StarRocks to ensure proper transaction support.

        StarRocks (using MySQL protocol) requires autocommit to be explicitly disabled
        and ``enable_sql_transaction`` enabled so BEGIN/COMMIT/ROLLBACK are not no-ops.

        Returns:
            A dictionary with autocommit=False, init_command, and connect_timeout from config.
        """
        connect_args: dict[str, object] = {
            "autocommit": False,
            "init_command": _STARROCKS_ENABLE_SQL_TRANSACTION,
        }

        # Add connect_timeout if configured
        if (
            hasattr(self, "_configs")
            and hasattr(self._configs, "CONNECT_TIMEOUT")
            and self._configs.CONNECT_TIMEOUT is not None
        ):
            connect_args["connect_timeout"] = self._configs.CONNECT_TIMEOUT

        return connect_args

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

        For async operations, StarRocks requires the starrocks+asyncmy driver
        which uses the asyncmy library for async MySQL protocol support while
        maintaining StarRocks dialect features (type mapping, compiler patches).

        Args:
            configs: StarRocks configuration.

        Returns:
            A SQLAlchemy URL object for StarRocks with async driver.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """
        try:
            return URL.create(
                drivername="starrocks+asyncmy",
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

        StarRocks (using MySQL protocol via asyncmy) requires autocommit to be explicitly
        disabled and ``enable_sql_transaction`` enabled so BEGIN/COMMIT/ROLLBACK are not
        no-ops.

        Note: asyncmy driver only supports connect_timeout, not read_timeout/write_timeout.
        These socket-level timeouts are handled differently in async drivers.

        Returns:
            A dictionary with autocommit=False, init_command, and connect_timeout.
        """
        connect_args: dict[str, object] = {
            "autocommit": False,
            "init_command": _STARROCKS_ENABLE_SQL_TRANSACTION,
        }

        # Add connect_timeout if configured
        if (
            hasattr(self, "_configs")
            and hasattr(self._configs, "CONNECT_TIMEOUT")
            and self._configs.CONNECT_TIMEOUT is not None
        ):
            connect_args["connect_timeout"] = self._configs.CONNECT_TIMEOUT

        return connect_args
