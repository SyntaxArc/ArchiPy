"""Driver-level error inspection shared by the SQLAlchemy adapters and the atomic decorators.

SQLAlchemy wraps every driver failure in a ``DBAPIError`` whose ``orig`` holds the driver exception. The domain
errors raised by ArchiPy (``DatabaseQueryError`` and friends) deliberately carry no driver detail, because they are
returned to API clients. This module reads the driver error code so errors can be classified by code instead of by
message text, and logs the driver detail once, server-side, at the point where the domain error is raised.

Supported code families (anything else falls back to message-based classification):

* PostgreSQL (asyncpg, psycopg, psycopg2): SQLSTATE strings, e.g. ``40001``.
* MySQL-compatible (MySQL, MariaDB, StarRocks via aiomysql/pymysql/mysqlclient): integer errno, e.g. ``1213``.
* SQLite: error names, e.g. ``SQLITE_BUSY`` (Python 3.11+).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

from sqlalchemy.exc import DBAPIError

from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseConstraintError,
    DatabaseDeadlockError,
    DatabaseError,
    DatabaseIntegrityError,
    DatabaseResourceExhaustedError,
    DatabaseSerializationError,
    DatabaseTimeoutError,
)

logger = logging.getLogger(__name__)

MAX_STATEMENT_LOG_CHARS: Final = 500

# PostgreSQL SQLSTATE
PG_SERIALIZATION: Final = "40001"
PG_DEADLOCK: Final = "40P01"
PG_QUERY_CANCELED: Final = "57014"  # statement_timeout / user cancel
PG_LOCK_NOT_AVAILABLE: Final = "55P03"  # lock_timeout / NOWAIT
PG_CONSTRAINT_STATES: Final = frozenset({"23503", "23505"})  # foreign_key_violation, unique_violation
PG_CONNECTION_CLASS: Final = "08"
PG_RESOURCE_CLASS: Final = "53"  # insufficient_resources: out_of_memory, disk_full, too_many_connections
PG_INTEGRITY_CLASS: Final = "23"

# MySQL-compatible errno
MYSQL_DEADLOCK: Final = 1213
MYSQL_LOCK_WAIT_TIMEOUT: Final = 1205
MYSQL_QUERY_TIMEOUT: Final = 3024
MYSQL_CONSTRAINT_ERRNOS: Final = frozenset({1062, 1451, 1452})
MYSQL_CONNECTION_ERRNOS: Final = frozenset({2002, 2003, 2006, 2013, 2055})
MYSQL_RESOURCE_ERRNOS: Final = frozenset({1037, 1038, 1040, 1041})  # out of memory/sort memory, max connections

# StarRocks (and some MySQL-compatible engines) report runtime resource failures under the generic errno 1064
# (ER_PARSE_ERROR), e.g. "Memory of process exceed limit. try consume:... Mem usage has exceed the limit of BE".
# The errno alone is therefore ambiguous and the message has to be inspected, but only for MySQL-family errnos.
_MYSQL_RESOURCE_MESSAGE: Final = re.compile(
    r"mem(?:ory)?\b.*\bexceed(?:ed|s)?\b.*\blimit|memory limit exceeded|mem usage has exceed|out of memory",
    re.IGNORECASE | re.DOTALL,
)

_MYSQL_SYNTAX_MESSAGE: Final = re.compile(r"error in your sql syntax", re.IGNORECASE)

# SQLite error names
SQLITE_DEADLOCK_NAMES: Final = frozenset({"SQLITE_BUSY", "SQLITE_LOCKED"})


def _driver_exception(exception: BaseException) -> BaseException | None:
    """Return the driver exception behind a SQLAlchemy error, or the error itself if it is not wrapped."""
    orig = getattr(exception, "orig", None)
    return orig if orig is not None else exception


def driver_error_code(exception: BaseException) -> str | int | None:
    """Return the driver-level error code of an exception.

    Args:
        exception: A SQLAlchemy error (its ``orig`` is inspected) or a raw driver exception.

    Returns:
        PostgreSQL SQLSTATE (``str``), MySQL-compatible errno (``int``), SQLite error name (``str``) or ``None``.
    """
    driver_error = _driver_exception(exception)
    # SQLAlchemy's asyncpg adapter exposes the code on the translated error; the raw asyncpg error is its cause.
    for candidate in (driver_error, getattr(driver_error, "__cause__", None)):
        if candidate is None:
            continue
        sqlstate = getattr(candidate, "sqlstate", None) or getattr(candidate, "pgcode", None)
        if sqlstate:
            return str(sqlstate)
        sqlite_name = getattr(candidate, "sqlite_errorname", None)
        if isinstance(sqlite_name, str):
            return sqlite_name
    args = getattr(driver_error, "args", ())
    if args and isinstance(args[0], int) and not isinstance(args[0], bool):
        return args[0]
    return None


def classify_driver_error(exception: BaseException) -> type[DatabaseError] | None:
    """Map a driver error code to a domain error class.

    Returns ``None`` when the code is missing or not recognised, so callers can fall back to other strategies.
    """
    code = driver_error_code(exception)
    if code is None:
        return None
    if isinstance(code, int):
        return _classify_errno(code) or _classify_errno_message(exception)
    if code == PG_SERIALIZATION:
        return DatabaseSerializationError
    if code == PG_DEADLOCK or code in SQLITE_DEADLOCK_NAMES:
        return DatabaseDeadlockError
    if code in (PG_QUERY_CANCELED, PG_LOCK_NOT_AVAILABLE):
        return DatabaseTimeoutError
    if code in PG_CONSTRAINT_STATES:
        return DatabaseConstraintError
    if code.startswith(PG_INTEGRITY_CLASS):
        return DatabaseIntegrityError
    if code.startswith(PG_CONNECTION_CLASS):
        return DatabaseConnectionError
    if code.startswith(PG_RESOURCE_CLASS):
        return DatabaseResourceExhaustedError
    return None


def _classify_errno(errno: int) -> type[DatabaseError] | None:
    if errno == MYSQL_DEADLOCK:
        return DatabaseDeadlockError
    if errno in (MYSQL_LOCK_WAIT_TIMEOUT, MYSQL_QUERY_TIMEOUT):
        return DatabaseTimeoutError
    if errno in MYSQL_CONSTRAINT_ERRNOS:
        return DatabaseConstraintError
    if errno in MYSQL_CONNECTION_ERRNOS:
        return DatabaseConnectionError
    if errno in MYSQL_RESOURCE_ERRNOS:
        return DatabaseResourceExhaustedError
    return None


def _classify_errno_message(exception: BaseException) -> type[DatabaseError] | None:
    """Classify MySQL-family errors whose errno is too generic (StarRocks reports memory limits as 1064)."""
    message = str(_driver_exception(exception))
    # Syntax errors quote the offending SQL, which could contain the resource keywords by chance.
    if _MYSQL_SYNTAX_MESSAGE.search(message):
        return None
    if _MYSQL_RESOURCE_MESSAGE.search(message):
        return DatabaseResourceExhaustedError
    return None


def driver_error_details(exception: BaseException) -> dict[str, Any]:
    """Collect loggable driver detail. Bind parameters are never included; the statement only at DEBUG level."""
    driver_error = _driver_exception(exception)
    root = getattr(driver_error, "__cause__", None) or driver_error
    # The statement may inline literal values, so it is only collected when DEBUG logging is enabled.
    statement = ""
    if isinstance(exception, DBAPIError) and logger.isEnabledFor(logging.DEBUG):
        statement = exception.statement or ""
    message = getattr(root, "message", None) or getattr(driver_error, "args", None) or str(root)
    if isinstance(message, tuple):
        message = " ".join(str(part) for part in message)
    return {
        "db.error_code": driver_error_code(exception),
        "db.error_class": type(root).__name__,
        "db.error_message": str(message),
        "db.error_detail": getattr(root, "detail", None),
        "db.error_hint": getattr(root, "hint", None),
        "db.constraint": getattr(root, "constraint_name", None),
        "db.table": getattr(root, "table_name", None),
        "db.column": getattr(root, "column_name", None),
        "db.statement": statement[:MAX_STATEMENT_LOG_CHARS],
        "db.statement_truncated": len(statement) > MAX_STATEMENT_LOG_CHARS,
    }


_EXPECTED_RETRYABLE: Final = (DatabaseSerializationError, DatabaseDeadlockError, DatabaseResourceExhaustedError)


def log_driver_error(
    exception: BaseException,
    domain_error: type[DatabaseError],
    database: str | None,
) -> None:
    """Log the driver detail behind a database error that is about to be re-raised as a domain error.

    Serialization failures, deadlocks and resource exhaustion are transient and retryable, so they log at
    WARNING; everything else logs at ERROR.
    """
    details = driver_error_details(exception)
    level = logging.WARNING if issubclass(domain_error, _EXPECTED_RETRYABLE) else logging.ERROR
    logger.log(
        level,
        "Database error %s (database=%s, code=%s): %s",
        domain_error.__name__,
        database,
        details["db.error_code"],
        details["db.error_message"],
        extra={"db.name": database, "db.domain_error": domain_error.__name__, **details},
    )
