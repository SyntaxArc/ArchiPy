"""SQLAlchemy atomic transaction decorators.

The unit of work for the SQLAlchemy adapters: it wraps a function in a transaction on the database's session manager.
This module provides decorators for managing SQLAlchemy transactions with automatic commit/rollback
and support for different database types (PostgreSQL, SQLite, StarRocks, MySQL).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
from functools import cache, wraps
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, cast, overload

from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from archipy.adapters.base.sqlalchemy.driver_errors import (
    MYSQL_CONSTRAINT_ERRNOS,
    MYSQL_DEADLOCK,
    MYSQL_LOCK_WAIT_TIMEOUT,
    PG_CONSTRAINT_STATES,
    PG_DEADLOCK,
    PG_SERIALIZATION,
    classify_by_message,
    classify_driver_error,
    driver_error_code,
    driver_error_message,
    log_driver_error,
)
from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.helpers._deprecation import deprecated_alias, warn_deprecated_name
from archipy.models.errors import (
    BaseError,
    DatabaseConfigurationError,
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

# Session marker: a nested atomic call failed, so the outer transaction must not be committed
_ROLLBACK_ONLY_FLAG = "_archipy_atomic_rollback_only"
# Number of active savepoint levels on the session
_SAVEPOINT_DEPTH_FLAG = "_archipy_atomic_savepoint_depth"
# Databases without SAVEPOINT support
_SAVEPOINT_UNSUPPORTED_DB_TYPES = frozenset({"starrocks"})

# Type variables for function return types
R = TypeVar("R")

# Driver error codes live in driver_errors; the names below are kept for backwards compatibility.
_PG_SERIALIZATION = PG_SERIALIZATION
_PG_DEADLOCK = PG_DEADLOCK
_PG_CONSTRAINT_STATES = PG_CONSTRAINT_STATES
_MYSQL_DEADLOCK = MYSQL_DEADLOCK
_MYSQL_LOCK_WAIT_TIMEOUT = MYSQL_LOCK_WAIT_TIMEOUT
_MYSQL_CONSTRAINT_ERRNOS = MYSQL_CONSTRAINT_ERRNOS
_driver_error_code = driver_error_code


def _handle_operational_error(exception: OperationalError, db_type: str) -> NoReturn:
    """Map SQLAlchemy operational errors to domain database errors."""
    code = _driver_error_code(exception)
    if code == _PG_SERIALIZATION:
        raise DatabaseSerializationError(database=db_type) from exception
    if code in (_PG_DEADLOCK, _MYSQL_DEADLOCK):
        raise DatabaseDeadlockError(database=db_type) from exception
    if code == _MYSQL_LOCK_WAIT_TIMEOUT:
        raise DatabaseTimeoutError(database=db_type) from exception

    if "database is locked" in driver_error_message(exception):
        raise DatabaseDeadlockError(database=db_type) from exception

    # Same driver-message fallback as the adapter methods, so both paths classify an error alike
    raise classify_by_message(driver_error_message(exception).lower())(database=db_type) from exception


def _handle_integrity_error(exception: IntegrityError, db_type: str) -> NoReturn:
    """Map SQLAlchemy integrity errors to domain database errors."""
    code = _driver_error_code(exception)
    if code in _PG_CONSTRAINT_STATES or code in _MYSQL_CONSTRAINT_ERRNOS:
        raise DatabaseConstraintError(database=db_type) from exception
    raise DatabaseIntegrityError(database=db_type) from exception


def _handle_sqlalchemy_error(exception: SQLAlchemyError, db_type: str) -> NoReturn:
    """Map generic SQLAlchemy errors to domain database errors."""
    if "transaction" in driver_error_message(exception).lower():
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
        DatabaseResourceExhaustedError: If the server runs out of memory or connections.
        DatabaseConstraintError: If a constraint violation occurs.
        DatabaseError: If a generic exception occurs within a database transaction.
    """
    logger.debug("Exception in %s atomic block (func: %s): %s", db_type, func_name, exception)

    if isinstance(exception, SQLAlchemyError):
        # Errors that reach the atomic block raw (flush/commit failures) never pass through an adapter method,
        # so log the driver detail here before it is hidden behind the domain error.
        error_class = classify_driver_error(exception)
        log_driver_error(exception, error_class or DatabaseQueryError, db_type)
        if error_class is not None:
            raise error_class(database=db_type) from exception

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
    """Close the session and drop it from the manager.

    Only ``close`` is shielded: the registry of the async scoped session is keyed by the current task, so
    ``remove_session`` must run in the calling task, not in the task ``asyncio.shield`` creates.
    """
    try:
        # Cleanup must finish even when the task is being cancelled
        await asyncio.shield(session.close())
    finally:
        await session_manager.remove_session()


async def _run_async_savepoint[R](
    session: Any,
    func: Callable[..., Awaitable[R]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> R:
    """Run ``func`` inside a savepoint and release or roll it back."""
    depth = session.info.get(_SAVEPOINT_DEPTH_FLAG, 0)
    savepoint_tx = await session.begin_nested()
    session.info[_SAVEPOINT_DEPTH_FLAG] = depth + 1
    try:
        result = await func(*args, **kwargs)
    except BaseException:
        if savepoint_tx.is_active:
            await savepoint_tx.rollback()
        raise
    else:
        if savepoint_tx.is_active:
            await savepoint_tx.commit()
        return result
    finally:
        session.info[_SAVEPOINT_DEPTH_FLAG] = depth


def _run_sync_savepoint[R](
    session: Any,
    func: Callable[..., R],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> R:
    """Run ``func`` inside a savepoint and release or roll it back."""
    depth = session.info.get(_SAVEPOINT_DEPTH_FLAG, 0)
    savepoint_tx = session.begin_nested()
    session.info[_SAVEPOINT_DEPTH_FLAG] = depth + 1
    try:
        result = func(*args, **kwargs)
    except BaseException:
        if savepoint_tx.is_active:
            savepoint_tx.rollback()
        raise
    else:
        if savepoint_tx.is_active:
            savepoint_tx.commit()
        return result
    finally:
        session.info[_SAVEPOINT_DEPTH_FLAG] = depth


async def _run_async_scope[R](
    session: Any,
    func: Callable[..., Awaitable[R]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    is_nested: bool,
    savepoint: bool,
    db_type: str,
) -> R:
    """Run ``func`` in the outer transaction or inside it as a nested call."""
    if is_nested:
        if savepoint:
            return await _run_async_savepoint(session, func, args, kwargs)
        # Nested calls join the outer transaction; a failure rolls that transaction back
        return await func(*args, **kwargs)
    if session.in_transaction():
        result = await func(*args, **kwargs)
        if session.info.get(_ROLLBACK_ONLY_FLAG, False):
            raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})
        await session.commit()
        return result
    async with session.begin():
        result = await func(*args, **kwargs)
        if session.info.get(_ROLLBACK_ONLY_FLAG, False):
            raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})
        return result


def _run_sync_scope[R](
    session: Any,
    func: Callable[..., R],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    is_nested: bool,
    savepoint: bool,
    db_type: str,
) -> R:
    """Run ``func`` in the outer transaction or inside it as a nested call."""
    if is_nested:
        if savepoint:
            return _run_sync_savepoint(session, func, args, kwargs)
        # Nested calls join the outer transaction; a failure rolls that transaction back
        return func(*args, **kwargs)
    if session.in_transaction():
        result = func(*args, **kwargs)
        if session.info.get(_ROLLBACK_ONLY_FLAG, False):
            raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})
        session.commit()
        return result
    with session.begin():
        result = func(*args, **kwargs)
        if session.info.get(_ROLLBACK_ONLY_FLAG, False):
            raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})
        return result


async def _rollback_outer_after_nested_failure(session: Any, db_type: str) -> NoReturn:
    """Roll back the outer transaction and raise when a nested atomic call failed."""
    await session.rollback()
    raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})


def _rollback_outer_after_nested_failure_sync(session: Any, db_type: str) -> NoReturn:
    """Roll back the outer transaction and raise when a nested atomic call failed."""
    session.rollback()
    raise DatabaseTransactionError(database=db_type, additional_data={"reason": "nested_atomic_failed"})


async def _handle_async_atomic_failure(
    session: Any,
    exception: BaseException,
    db_type: str,
    func: Callable[..., Any],
    *,
    is_nested: bool,
    savepoint: bool,
) -> NoReturn:
    """Roll back and translate an exception raised inside an async atomic block."""
    should_rollback = True
    if is_nested and savepoint:
        # The savepoint already rolled back; the outer transaction stays usable
        should_rollback = False
    elif is_nested:
        session.info[_ROLLBACK_ONLY_FLAG] = True
        # Defer a full rollback while a savepoint ancestor is unwinding
        should_rollback = session.info.get(_SAVEPOINT_DEPTH_FLAG, 0) == 0
    if should_rollback:
        try:
            await session.rollback()
        except Exception:
            logger.exception("Rollback failed in %s atomic block; re-raising the original error", db_type)
    if _is_control_flow_exception(exception):
        raise exception
    func_name = getattr(func, "__name__", "unknown")
    _handle_db_exception(exception, db_type, func_name)
    raise exception


def _handle_sync_atomic_failure(
    session: Any,
    exception: BaseException,
    db_type: str,
    func: Callable[..., Any],
    *,
    is_nested: bool,
    savepoint: bool,
) -> NoReturn:
    """Roll back and translate an exception raised inside a sync atomic block."""
    should_rollback = True
    if is_nested and savepoint:
        # The savepoint already rolled back; the outer transaction stays usable
        should_rollback = False
    elif is_nested:
        session.info[_ROLLBACK_ONLY_FLAG] = True
        # Defer a full rollback while a savepoint ancestor is unwinding
        should_rollback = session.info.get(_SAVEPOINT_DEPTH_FLAG, 0) == 0
    if should_rollback:
        try:
            session.rollback()
        except Exception:
            logger.exception("Rollback failed in %s atomic block; re-raising the original error", db_type)
    if _is_control_flow_exception(exception):
        raise exception
    func_name = getattr(func, "__name__", "unknown")
    _handle_db_exception(exception, db_type, func_name)
    raise exception


def _create_async_atomic_wrapper[R](
    func: Callable[..., Awaitable[R]],
    *,
    db_type: str,
    atomic_flag: str,
    savepoint: bool = False,
    registry_override: type[SessionManagerRegistry] | None = None,
) -> Callable[..., Awaitable[R]]:
    """Wrap an async function with atomic transaction management."""

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> R:
        """Async wrapper for managing database transactions."""
        registry = registry_override or _load_session_manager_registry(db_type)
        session_manager: AsyncSessionManagerPort = registry.get_async_manager()
        session = session_manager.get_session()
        is_nested = session.info.get(atomic_flag, False)
        if not is_nested:
            session.info[atomic_flag] = True

        try:
            result = await _run_async_scope(
                session,
                func,
                args,
                kwargs,
                is_nested=is_nested,
                savepoint=savepoint,
                db_type=db_type,
            )
        except BaseException as exception:  # noqa: BLE001  # translate every atomic failure
            await _handle_async_atomic_failure(
                session,
                exception,
                db_type,
                func,
                is_nested=is_nested,
                savepoint=savepoint,
            )
        else:
            if not is_nested and session.info.pop(_ROLLBACK_ONLY_FLAG, False):
                await _rollback_outer_after_nested_failure(session, db_type)
            return result
        finally:
            if not is_nested:
                session.info.pop(atomic_flag, None)
                session.info.pop(_ROLLBACK_ONLY_FLAG, None)
            if not is_nested and not session.in_transaction():
                await _close_async_session(session, session_manager)

    return async_wrapper


def _create_sync_atomic_wrapper[R](
    func: Callable[..., R],
    *,
    db_type: str,
    atomic_flag: str,
    savepoint: bool = False,
    registry_override: type[SessionManagerRegistry] | None = None,
) -> Callable[..., R]:
    """Wrap a sync function with atomic transaction management."""

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> R:
        """Synchronous wrapper for managing database transactions."""
        registry = registry_override or _load_session_manager_registry(db_type)
        session_manager: SessionManagerPort = registry.get_sync_manager()
        session = session_manager.get_session()
        is_nested = session.info.get(atomic_flag, False)
        if not is_nested:
            session.info[atomic_flag] = True

        try:
            result = _run_sync_scope(
                session,
                func,
                args,
                kwargs,
                is_nested=is_nested,
                savepoint=savepoint,
                db_type=db_type,
            )
        except BaseException as exception:  # noqa: BLE001  # translate every atomic failure
            _handle_sync_atomic_failure(session, exception, db_type, func, is_nested=is_nested, savepoint=savepoint)
        else:
            if not is_nested and session.info.pop(_ROLLBACK_ONLY_FLAG, False):
                _rollback_outer_after_nested_failure_sync(session, db_type)
            return result
        finally:
            if not is_nested:
                session.info.pop(atomic_flag, None)
                session.info.pop(_ROLLBACK_ONLY_FLAG, None)
            if not is_nested and not session.in_transaction():
                session.close()
                session_manager.remove_session()

    return sync_wrapper


def _bind_db_type[**P, R](
    db_type: str,
    registry: type[SessionManagerRegistry] | None,
    savepoint: bool,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Return a decorator that applies the atomic wrapper for ``db_type`` to the function it receives.

    ``functools.partial`` cannot be used here: the decorated function would be passed
    positionally and collide with ``db_type``.
    """

    def apply(function: Callable[P, R]) -> Callable[P, R]:
        return sqlalchemy_atomic(db_type, function, registry=registry, savepoint=savepoint)

    return apply


def _atomic_for(
    db_type: str,
    function: Callable[..., Any] | None,
    registry: type[SessionManagerRegistry] | None,
    savepoint: bool = False,
) -> Any:
    """Apply :func:`sqlalchemy_atomic` for a shortcut (typed by the shortcut's own overloads)."""
    return sqlalchemy_atomic(db_type, function, registry=registry, savepoint=savepoint)


@overload
def sqlalchemy_atomic[**P, R](
    db_type: str,
    function: Callable[P, R],
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R]: ...


@overload
def sqlalchemy_atomic[**P, R](
    db_type: str,
    function: None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def sqlalchemy_atomic[**P, R](
    db_type: str,
    function: Callable[P, R] | None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Run a function inside a SQLAlchemy transaction for the given database type.

    If the function succeeds, the transaction is committed; otherwise it is rolled back and the
    error is mapped to a domain database error. Synchronous and ``async def`` functions are both
    supported; the kind is detected automatically.

    Args:
        db_type (str): The database type ("postgres", "sqlite", "starrocks", or "mysql").
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.
        registry (type[SessionManagerRegistry] | None): Registry that supplies the session manager. Defaults to the
            registry of ``db_type``, which reads the global config; pass a registry subclass to run on another
            database of the same type (see the multiple databases section of the docs).
        savepoint (bool): Run a nested call in a savepoint. Defaults to False, where a nested failure rolls back the
            whole transaction. Ignored on the outermost call and unsupported on StarRocks.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.

    Raises:
        InvalidArgumentError: If an invalid db_type is provided.
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
        @sqlalchemy_atomic("postgres")
        def update_user(id: int, name: str) -> None:
            # Database operations
            pass

        # Asynchronous SQLite example
        @sqlalchemy_atomic("sqlite")
        async def update_record(id: int, data: str) -> None:
            # Async database operations
            pass
    """
    if db_type not in ATOMIC_BLOCK_CONFIGS:
        raise InvalidArgumentError(
            argument_name="db_type",
            additional_data={"valid_values": list(ATOMIC_BLOCK_CONFIGS.keys())},
        )
    if savepoint and db_type in _SAVEPOINT_UNSUPPORTED_DB_TYPES:
        raise InvalidArgumentError(
            argument_name="savepoint",
            additional_data={"db_type": db_type, "reason": "savepoint_not_supported"},
        )

    if function is None:
        return cast(
            "Callable[[Callable[P, R]], Callable[P, R]]",
            _bind_db_type(db_type, registry, savepoint),
        )

    atomic_flag = ATOMIC_BLOCK_CONFIGS[db_type]["flag"]
    if inspect.iscoroutinefunction(function):
        return cast(
            "Callable[P, R]",
            _create_async_atomic_wrapper(
                function,
                db_type=db_type,
                atomic_flag=atomic_flag,
                savepoint=savepoint,
                registry_override=registry,
            ),
        )
    return _create_sync_atomic_wrapper(
        function,
        db_type=db_type,
        atomic_flag=atomic_flag,
        savepoint=savepoint,
        registry_override=registry,
    )


@overload
def postgres_sqlalchemy_atomic[**P, R](
    function: Callable[P, R],
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R]: ...


@overload
def postgres_sqlalchemy_atomic[**P, R](
    function: None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def postgres_sqlalchemy_atomic[**P, R](
    function: Callable[P, R] | None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for PostgreSQL atomic transactions; works for sync and ``async def`` functions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.
        registry (type[SessionManagerRegistry] | None): Registry for another database of the same type; defaults to
            the registry that reads the global config.
        savepoint (bool): Run a nested call in a savepoint instead of rolling back the whole transaction.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return _atomic_for("postgres", function, registry, savepoint)


@overload
def sqlite_sqlalchemy_atomic[**P, R](
    function: Callable[P, R],
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R]: ...


@overload
def sqlite_sqlalchemy_atomic[**P, R](
    function: None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def sqlite_sqlalchemy_atomic[**P, R](
    function: Callable[P, R] | None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for SQLite atomic transactions; works for sync and ``async def`` functions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.
        registry (type[SessionManagerRegistry] | None): Registry for another database of the same type; defaults to
            the registry that reads the global config.
        savepoint (bool): Run a nested call in a savepoint instead of rolling back the whole transaction.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return _atomic_for("sqlite", function, registry, savepoint)


@overload
def starrocks_sqlalchemy_atomic[**P, R](
    function: Callable[P, R],
    *,
    registry: type[SessionManagerRegistry] | None = None,
) -> Callable[P, R]: ...


@overload
def starrocks_sqlalchemy_atomic[**P, R](
    function: None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def starrocks_sqlalchemy_atomic[**P, R](
    function: Callable[P, R] | None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for StarRocks atomic transactions; works for sync and ``async def`` functions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.
        registry (type[SessionManagerRegistry] | None): Registry for another database of the same type; defaults to
            the registry that reads the global config.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return _atomic_for("starrocks", function, registry)


@overload
def mysql_sqlalchemy_atomic[**P, R](
    function: Callable[P, R],
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R]: ...


@overload
def mysql_sqlalchemy_atomic[**P, R](
    function: None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def mysql_sqlalchemy_atomic[**P, R](
    function: Callable[P, R] | None = None,
    *,
    registry: type[SessionManagerRegistry] | None = None,
    savepoint: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for MySQL atomic transactions; works for sync and ``async def`` functions.

    Args:
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.
        registry (type[SessionManagerRegistry] | None): Registry for another database of the same type; defaults to
            the registry that reads the global config.
        savepoint (bool): Run a nested call in a savepoint instead of rolling back the whole transaction.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    return _atomic_for("mysql", function, registry, savepoint)


def sqlalchemy_atomic_decorator(
    db_type: str,
    is_async: bool = False,
    function: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Deprecated: use :func:`sqlalchemy_atomic`, which detects async functions itself.

    Args:
        db_type (str): The database type ("postgres", "sqlite", "starrocks", or "mysql").
        is_async (bool): Ignored; the function kind is detected automatically.
        function (Callable | None): The function to wrap. If None, returns a decorator to apply later.

    Returns:
        Callable: The wrapped function, or a decorator to apply later when ``function`` is None.
    """
    del is_async
    warn_deprecated_name("sqlalchemy_atomic_decorator", "sqlalchemy_atomic")
    return sqlalchemy_atomic(db_type, function)


postgres_sqlalchemy_atomic_decorator = deprecated_alias(
    "postgres_sqlalchemy_atomic_decorator",
    postgres_sqlalchemy_atomic,
)

async_postgres_sqlalchemy_atomic_decorator = deprecated_alias(
    "async_postgres_sqlalchemy_atomic_decorator",
    postgres_sqlalchemy_atomic,
)

sqlite_sqlalchemy_atomic_decorator = deprecated_alias("sqlite_sqlalchemy_atomic_decorator", sqlite_sqlalchemy_atomic)

async_sqlite_sqlalchemy_atomic_decorator = deprecated_alias(
    "async_sqlite_sqlalchemy_atomic_decorator",
    sqlite_sqlalchemy_atomic,
)

starrocks_sqlalchemy_atomic_decorator = deprecated_alias(
    "starrocks_sqlalchemy_atomic_decorator",
    starrocks_sqlalchemy_atomic,
)

async_starrocks_sqlalchemy_atomic_decorator = deprecated_alias(
    "async_starrocks_sqlalchemy_atomic_decorator",
    starrocks_sqlalchemy_atomic,
)

mysql_sqlalchemy_atomic_decorator = deprecated_alias("mysql_sqlalchemy_atomic_decorator", mysql_sqlalchemy_atomic)

async_mysql_sqlalchemy_atomic_decorator = deprecated_alias(
    "async_mysql_sqlalchemy_atomic_decorator",
    mysql_sqlalchemy_atomic,
)
