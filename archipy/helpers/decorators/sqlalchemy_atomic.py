"""SQLAlchemy atomic transaction decorators.

This module provides decorators for managing SQLAlchemy transactions with automatic commit/rollback
and support for different database types (PostgreSQL, SQLite, StarRocks).
"""

import logging
from collections.abc import Awaitable, Callable
from functools import partial, wraps
from typing import Any, TypeVar, overload

from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort
from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.models.errors import (
    BaseError,
    DatabaseConfigurationError,
    DatabaseConnectionError,
    DatabaseConstraintError,
    DatabaseDeadlockError,
    DatabaseIntegrityError,
    DatabaseQueryError,
    DatabaseSerializationError,
    DatabaseTimeoutError,
    DatabaseTransactionError,
    InternalError,
)

logger = logging.getLogger(__name__)

# Constants for tracking atomic blocks and their corresponding registries
ATOMIC_BLOCK_CONFIGS = {
    "postgres": {
        "flag": "in_postgres_sqlalchemy_atomic_block",
        "registry": "archipy.adapters.postgres.sqlalchemy.session_manager_registry.PostgresSessionManagerRegistry",
    },
    "sqlite": {
        "flag": "in_sqlite_sqlalchemy_atomic_block",
        "registry": "archipy.adapters.sqlite.sqlalchemy.session_manager_registry.SQLiteSessionManagerRegistry",
    },
    "starrocks": {
        "flag": "in_starrocks_sqlalchemy_atomic_block",
        "registry": "archipy.adapters.starrocks.sqlalchemy.session_manager_registry.StarRocksSessionManagerRegistry",
    },
}

# Type variables for function return types
R = TypeVar("R")


def _handle_db_exception(exception: Exception, db_type: str, func_name: str) -> None:
    """Handle database exceptions and raise appropriate errors.

    Args:
        exception (Exception): The exception to handle.
        db_type (str): The database type ("postgres", "sqlite", or "starrocks").
        func_name (str): The name of the function being executed.

    Raises:
        DatabaseSerializationError: If a serialization failure is detected.
        DatabaseDeadlockError: If a deadlock or database lock is detected.
        DatabaseTransactionError: If a transaction-related error occurs.
        DatabaseQueryError: If a query-related error occurs.
        DatabaseConnectionError: If a connection-related error occurs.
        DatabaseIntegrityError: If an integrity constraint violation occurs.
        DatabaseTimeoutError: If a database operation times out.
        DatabaseConstraintError: If a constraint violation occurs.
        DatabaseError: If a generic exception occurs within a database transaction.
    """
    logger.debug(f"Exception in {db_type} atomic block (func: {func_name}): {exception}")

    # Handle specific SQLAlchemy errors
    if isinstance(exception, OperationalError):
        if hasattr(exception, "orig") and exception.orig:
            sqlstate = getattr(exception.orig, "pgcode", None)
            if sqlstate == "40001":  # Serialization failure
                raise DatabaseSerializationError(database=db_type) from exception
            if sqlstate == "40P01":  # Deadlock detected
                raise DatabaseDeadlockError(database=db_type) from exception

        # SQLite-specific errors
        if "database is locked" in str(exception):
            raise DatabaseDeadlockError(database=db_type) from exception

        # Generic operational errors
        raise DatabaseConnectionError(database=db_type) from exception

    # Handle integrity errors
    if isinstance(exception, IntegrityError):
        if hasattr(exception, "orig") and exception.orig:
            sqlstate = getattr(exception.orig, "pgcode", None)
            if sqlstate in ("23503", "23505"):  # Foreign key or unique constraint violation
                raise DatabaseConstraintError(database=db_type) from exception
        raise DatabaseIntegrityError(database=db_type) from exception

    # Handle timeout errors
    if isinstance(exception, SQLAlchemyTimeoutError):
        raise DatabaseTimeoutError(database=db_type) from exception

    # Handle other SQLAlchemy errors
    if isinstance(exception, SQLAlchemyError):
        if "transaction" in str(exception).lower():
            raise DatabaseTransactionError(database=db_type) from exception
        else:
            raise DatabaseQueryError(database=db_type) from exception

    # Wrap normal exceptions with DatabaseError
    # Check if the exception is one of our database-specific errors
    if isinstance(exception, BaseError):
        raise exception
    raise InternalError() from exception


@overload
def sqlalchemy_atomic_decorator[R](
    db_type: str,
    is_async: bool = False,
    function: Callable[..., R] = ...,
) -> Callable[..., R]: ...


@overload
def sqlalchemy_atomic_decorator(
    db_type: str,
    is_async: bool = False,
    function: None = None,
) -> partial[Callable[..., Any]]: ...


def sqlalchemy_atomic_decorator[R](
    db_type: str,
    is_async: bool = False,
    function: Callable[..., R] | None = None,
) -> Callable[..., R] | partial[Callable[..., Any]]:
    """Factory for creating SQLAlchemy atomic transaction decorators.

    This decorator ensures that a function runs within a database transaction for the specified
    database type. If the function succeeds, the transaction is committed; otherwise, it is rolled back.
    Supports both synchronous and asynchronous functions.

    Args:
        db_type (str): The database type ("postgres", "sqlite", or "starrocks").
        is_async (bool): Whether the function is asynchronous. Defaults to False.
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.

    Raises:
        ValueError: If an invalid db_type is provided.
        DatabaseSerializationError: If a serialization failure is detected.
        DatabaseDeadlockError: If an operational error occurs due to a deadlock.
        DatabaseTransactionError: If a transaction-related error occurs.
        DatabaseQueryError: If a query-related error occurs.
        DatabaseConnectionError: If a connection-related error occurs.
        DatabaseConstraintError: If a constraint violation is detected.
        DatabaseIntegrityError: If an integrity violation is detected.
        DatabaseTimeoutError: If a database operation times out.
        DatabaseConfigurationError: If there's an error in the database configuration.

    Example:
        # Synchronous PostgreSQL example
        @sqlalchemy_atomic_decorator(db_type="postgres")
        def update_user(id: int, name: str) -> None:
            # Database operations
            pass

        # Asynchronous SQLite example
        @sqlalchemy_atomic_decorator(db_type="sqlite", is_async=True)
        async def update_record(id: int, data: str) -> None:
            # Async database operations
            pass
    """
    if db_type not in ATOMIC_BLOCK_CONFIGS:
        raise ValueError(f"Invalid db_type: {db_type}. Must be one of {list(ATOMIC_BLOCK_CONFIGS.keys())}")

    atomic_flag = ATOMIC_BLOCK_CONFIGS[db_type]["flag"]

    # Dynamically import the registry class
    def get_registry() -> type[SessionManagerRegistry]:
        """Get the session manager registry for the specified database type.

        Returns:
            type[SessionManagerRegistry]: The session manager registry class.

        Raises:
            DatabaseConfigurationError: If the registry cannot be loaded.
        """
        try:
            import importlib

            module_path, class_name = ATOMIC_BLOCK_CONFIGS[db_type]["registry"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            registry_class = getattr(module, class_name)
            if not isinstance(registry_class, type) or not issubclass(registry_class, SessionManagerRegistry):
                raise DatabaseConfigurationError(
                    database=db_type,
                    additional_data={"registry_path": ATOMIC_BLOCK_CONFIGS[db_type]["registry"]},
                )
        except (ImportError, AttributeError) as e:
            raise DatabaseConfigurationError(
                database=db_type,
                additional_data={"registry_path": ATOMIC_BLOCK_CONFIGS[db_type]["registry"]},
            ) from e
        else:
            return registry_class

    if is_async:

        def async_decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
            """Create an async transaction-aware wrapper for the given function.

            Args:
                func: The async function to wrap with transaction management.

            Returns:
                The wrapped async function that manages transactions.
            """

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> R:
                """Async wrapper for managing database transactions."""
                registry = get_registry()
                session_manager: AsyncSessionManagerPort = registry.get_async_manager()
                session = session_manager.get_session()
                is_nested = session.info.get(atomic_flag, False)
                if not is_nested:
                    session.info[atomic_flag] = True

                try:
                    if session.in_transaction():
                        result = await func(*args, **kwargs)
                        if not is_nested:
                            await session.commit()
                        return result
                    else:
                        async with session.begin():
                            result = await func(*args, **kwargs)
                            return result
                except Exception as exception:
                    await session.rollback()
                    func_name = getattr(func, "__name__", "unknown")
                    _handle_db_exception(exception, db_type, func_name)
                    # _handle_db_exception always raises, but add this for type checker
                    raise
                finally:
                    if not session.in_transaction():
                        await session.close()
                        await session_manager.remove_session()

            return async_wrapper

        if function is not None:
            return async_decorator(function)  # type: ignore[arg-type, return-value]
        return partial(sqlalchemy_atomic_decorator, db_type=db_type, is_async=is_async)

    else:

        def sync_decorator(func: Callable[..., R]) -> Callable[..., R]:
            """Create a sync transaction-aware wrapper for the given function.

            Args:
                func: The sync function to wrap with transaction management.

            Returns:
                The wrapped sync function that manages transactions.
            """

            @wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> R:
                """Synchronous wrapper for managing database transactions."""
                registry = get_registry()
                session_manager: SessionManagerPort = registry.get_sync_manager()
                session = session_manager.get_session()
                is_nested = session.info.get(atomic_flag, False)
                if not is_nested:
                    session.info[atomic_flag] = True

                try:
                    if session.in_transaction():
                        result = func(*args, **kwargs)
                        if not is_nested:
                            session.commit()
                        return result
                    else:
                        with session.begin():
                            return func(*args, **kwargs)
                except Exception as exception:
                    session.rollback()
                    func_name = getattr(func, "__name__", "unknown")
                    _handle_db_exception(exception, db_type, func_name)
                    # _handle_db_exception always raises, but add this for type checker
                    raise
                finally:
                    if not session.in_transaction():
                        session.close()
                        session_manager.remove_session()

            return sync_wrapper

        if function is not None:
            return sync_decorator(function)
        return partial(sqlalchemy_atomic_decorator, db_type=db_type, is_async=is_async)


def postgres_sqlalchemy_atomic_decorator(function: Callable[..., Any] | None = None) -> Callable[..., Any] | partial:
    """Decorator for PostgreSQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="postgres", function=function)


def async_postgres_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any] | partial:
    """Decorator for asynchronous PostgreSQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="postgres", is_async=True, function=function)


def sqlite_sqlalchemy_atomic_decorator(function: Callable[..., Any] | None = None) -> Callable[..., Any] | partial:
    """Decorator for SQLite atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="sqlite", function=function)


def async_sqlite_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any] | partial:
    """Decorator for asynchronous SQLite atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="sqlite", is_async=True, function=function)


def starrocks_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any] | partial:
    """Decorator for StarRocks atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="starrocks", function=function)


def async_starrocks_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any] | partial:
    """Decorator for asynchronous StarRocks atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a partial function.

    Returns:
        Callable | partial: The wrapped function or a partial function for later use.
    """
    return sqlalchemy_atomic_decorator(db_type="starrocks", is_async=True, function=function)
