"""SQLAlchemy atomic transaction decorators.

This module provides decorators for managing SQLAlchemy transactions with automatic commit/rollback
and support for different database types (PostgreSQL, SQLite, StarRocks, MySQL).
"""

from __future__ import annotations

import asyncio
import logging
from functools import cache, wraps
from typing import TYPE_CHECKING, Any, Literal, NoReturn, TypeVar, cast, overload

from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)

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
    InvalidArgumentError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort

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
    "mysql": {
        "flag": "in_mysql_sqlalchemy_atomic_block",
        "registry": "archipy.adapters.mysql.sqlalchemy.session_manager_registry.MySQLSessionManagerRegistry",
    },
}

# Type variables for function return types
R = TypeVar("R")

# Driver error codes that need specific domain errors (PostgreSQL SQLSTATE / MySQL-compatible errno)
_PG_SERIALIZATION = "40001"
_PG_DEADLOCK = "40P01"
_PG_CONSTRAINT_STATES = frozenset({"23503", "23505"})
_MYSQL_DEADLOCK = 1213
_MYSQL_LOCK_WAIT_TIMEOUT = 1205
_MYSQL_CONSTRAINT_ERRNOS = frozenset({1062, 1451, 1452})


def _driver_error_code(exception: SQLAlchemyError) -> str | int | None:
    """Return the driver-level error code: PostgreSQL ``pgcode`` or MySQL-style ``errno`` (first arg)."""
    orig = getattr(exception, "orig", None)
    if not orig:
        return None
    pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    if pgcode:
        return pgcode
    args = getattr(orig, "args", ())
    if args and isinstance(args[0], int):
        return args[0]
    return None


def _handle_operational_error(exception: OperationalError, db_type: str) -> NoReturn:
    """Map SQLAlchemy operational errors to domain database errors."""
    code = _driver_error_code(exception)
    if code == _PG_SERIALIZATION:
        raise DatabaseSerializationError(database=db_type) from exception
    if code in (_PG_DEADLOCK, _MYSQL_DEADLOCK):
        raise DatabaseDeadlockError(database=db_type) from exception
    if code == _MYSQL_LOCK_WAIT_TIMEOUT:
        raise DatabaseTimeoutError(database=db_type) from exception

    if "database is locked" in str(exception):
        raise DatabaseDeadlockError(database=db_type) from exception

    raise DatabaseConnectionError(database=db_type) from exception


def _handle_integrity_error(exception: IntegrityError, db_type: str) -> NoReturn:
    """Map SQLAlchemy integrity errors to domain database errors."""
    code = _driver_error_code(exception)
    if code in _PG_CONSTRAINT_STATES or code in _MYSQL_CONSTRAINT_ERRNOS:
        raise DatabaseConstraintError(database=db_type) from exception
    raise DatabaseIntegrityError(database=db_type) from exception


def _handle_sqlalchemy_error(exception: SQLAlchemyError, db_type: str) -> NoReturn:
    """Map generic SQLAlchemy errors to domain database errors."""
    if "transaction" in str(exception).lower():
        raise DatabaseTransactionError(database=db_type) from exception
    raise DatabaseQueryError(database=db_type) from exception


def _handle_db_exception(exception: BaseException, db_type: str, func_name: str) -> NoReturn:
    """Handle database exceptions and raise appropriate errors.

    Args:
        exception (BaseException): The exception to handle.
        db_type (str): The database type ("postgres", "sqlite", "starrocks", or "mysql").
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
    logger.debug("Exception in %s atomic block (func: %s): %s", db_type, func_name, exception)

    if isinstance(exception, OperationalError):
        _handle_operational_error(exception, db_type)

    if isinstance(exception, IntegrityError):
        _handle_integrity_error(exception, db_type)

    if isinstance(exception, SQLAlchemyTimeoutError):
        raise DatabaseTimeoutError(database=db_type) from exception

    if isinstance(exception, SQLAlchemyError):
        _handle_sqlalchemy_error(exception, db_type)

    if isinstance(exception, BaseError):
        raise exception
    raise InternalError() from exception


def _is_control_flow_exception(exception: BaseException) -> bool:
    """Return True for exceptions that must propagate unchanged (cancellation, interpreter exit)."""
    return not isinstance(exception, Exception)


@cache
def _load_session_manager_registry(db_type: str) -> type[SessionManagerRegistry]:
    """Load the session manager registry class for a database type.

    Args:
        db_type: Database identifier key in ``ATOMIC_BLOCK_CONFIGS``.

    Returns:
        Session manager registry class for the database type.

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


async def _close_async_session(session: Any, session_manager: AsyncSessionManagerPort) -> None:
    """Close the session and drop it from the manager."""
    await session.close()
    await session_manager.remove_session()


def _create_async_atomic_wrapper[R](
    func: Callable[..., Awaitable[R]],
    *,
    db_type: str,
    atomic_flag: str,
) -> Callable[..., Awaitable[R]]:
    """Wrap an async function with atomic transaction management."""

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> R:
        """Async wrapper for managing database transactions."""
        registry = _load_session_manager_registry(db_type)
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
            async with session.begin():
                return await func(*args, **kwargs)
        except BaseException as exception:
            try:
                await session.rollback()
            except Exception:
                logger.exception("Rollback failed in %s atomic block; re-raising the original error", db_type)
            if _is_control_flow_exception(exception):
                raise
            func_name = getattr(func, "__name__", "unknown")
            _handle_db_exception(exception, db_type, func_name)
            raise
        finally:
            if not is_nested:
                session.info.pop(atomic_flag, None)
            if not session.in_transaction():
                # Cleanup must finish even when the task is being cancelled
                await asyncio.shield(_close_async_session(session, session_manager))

    return async_wrapper


def _create_sync_atomic_wrapper[R](
    func: Callable[..., R],
    *,
    db_type: str,
    atomic_flag: str,
) -> Callable[..., R]:
    """Wrap a sync function with atomic transaction management."""

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> R:
        """Synchronous wrapper for managing database transactions."""
        registry = _load_session_manager_registry(db_type)
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
            with session.begin():
                return func(*args, **kwargs)
        except BaseException as exception:
            try:
                session.rollback()
            except Exception:
                logger.exception("Rollback failed in %s atomic block; re-raising the original error", db_type)
            if _is_control_flow_exception(exception):
                raise
            func_name = getattr(func, "__name__", "unknown")
            _handle_db_exception(exception, db_type, func_name)
            raise
        finally:
            if not is_nested:
                session.info.pop(atomic_flag, None)
            if not session.in_transaction():
                session.close()
                session_manager.remove_session()

    return sync_wrapper


def _bind_function(db_type: str, *, is_async: bool) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Return a decorator that applies the atomic wrapper to the function it receives.

    ``functools.partial`` cannot be used here: the decorated function would be passed
    positionally and collide with ``db_type``.
    """

    def apply(function: Callable[..., Any]) -> Callable[..., Any]:
        return sqlalchemy_atomic_decorator(db_type=db_type, is_async=is_async, function=function)

    return apply


@overload
def sqlalchemy_atomic_decorator[R](
    db_type: str,
    is_async: Literal[False] = False,
    function: Callable[..., R] = ...,
) -> Callable[..., R]: ...


@overload
def sqlalchemy_atomic_decorator[R](
    db_type: str,
    is_async: Literal[True],
    function: Callable[..., Awaitable[R]] = ...,
) -> Callable[..., Awaitable[R]]: ...


@overload
def sqlalchemy_atomic_decorator(
    db_type: str,
    is_async: bool = False,
    function: None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]: ...


def sqlalchemy_atomic_decorator[R](
    db_type: str,
    is_async: bool = False,
    function: Callable[..., R] | Callable[..., Awaitable[R]] | None = None,
) -> Callable[..., R] | Callable[..., Awaitable[R]] | Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Factory for creating SQLAlchemy atomic transaction decorators.

    This decorator ensures that a function runs within a database transaction for the specified
    database type. If the function succeeds, the transaction is committed; otherwise, it is rolled back.
    Supports both synchronous and asynchronous functions.

    Args:
        db_type (str): The database type ("postgres", "sqlite", "starrocks", or "mysql").
        is_async (bool): Whether the function is asynchronous. Defaults to False.
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.

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
        raise InvalidArgumentError(
            argument_name="db_type",
            additional_data={"valid_values": list(ATOMIC_BLOCK_CONFIGS.keys())},
        )

    atomic_flag = ATOMIC_BLOCK_CONFIGS[db_type]["flag"]

    if is_async:
        if function is not None:
            return _create_async_atomic_wrapper(
                cast("Callable[..., Awaitable[R]]", function),
                db_type=db_type,
                atomic_flag=atomic_flag,
            )
        return _bind_function(db_type, is_async=True)

    if function is not None:
        return _create_sync_atomic_wrapper(
            cast("Callable[..., R]", function),
            db_type=db_type,
            atomic_flag=atomic_flag,
        )
    return _bind_function(db_type, is_async=False)


def postgres_sqlalchemy_atomic_decorator(function: Callable[..., Any] | None = None) -> Callable[..., Any]:
    """Decorator for PostgreSQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="postgres", function=function)


def async_postgres_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for asynchronous PostgreSQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="postgres", is_async=True, function=function)


def sqlite_sqlalchemy_atomic_decorator(function: Callable[..., Any] | None = None) -> Callable[..., Any]:
    """Decorator for SQLite atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="sqlite", function=function)


def async_sqlite_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for asynchronous SQLite atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="sqlite", is_async=True, function=function)


def starrocks_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for StarRocks atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="starrocks", function=function)


def async_starrocks_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for asynchronous StarRocks atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="starrocks", is_async=True, function=function)


def mysql_sqlalchemy_atomic_decorator(function: Callable[..., Any] | None = None) -> Callable[..., Any]:
    """Decorator for MySQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="mysql", function=function)


def async_mysql_sqlalchemy_atomic_decorator(
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for asynchronous MySQL atomic transactions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return sqlalchemy_atomic_decorator(db_type="mysql", is_async=True, function=function)
