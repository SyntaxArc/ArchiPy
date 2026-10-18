"""Reusable decorator helpers for ArchiPy."""

from typing import TYPE_CHECKING

from archipy.models.errors import ConfigurationError, InvalidArgumentError

# Old module paths stay importable as thin shims; they must load before the decorator names are bound below.
from . import (
    _legacy_modules,  # noqa: F401
    sqlalchemy_transaction as _sqlalchemy_transaction,
)
from .deprecation_exception import class_deprecation_error, method_deprecation_error
from .deprecation_warnings import class_deprecation_warning, method_deprecation_warning
from .grpc_rate_limit_window import grpc_rate_limit, grpc_rate_limit_decorator
from .metrics import async_count_calls, async_measure_duration, count_calls, measure_duration
from .retry_policy import retry, retry_decorator
from .singleton_class import singleton, singleton_decorator
from .timeout_limit import timeout, timeout_decorator
from .timing_log import timing, timing_decorator
from .tracing import async_trace_root, async_trace_span, trace_class, trace_root, trace_span
from .ttl_caching import ttl_cache, ttl_cache_decorator

# ``sqlalchemy_atomic`` is both a decorator name and the old shim module name; resolve it lazily instead
globals().pop("sqlalchemy_atomic", None)


# SQLAlchemy decorators moved to archipy.adapters.base.sqlalchemy.atomic; they are resolved lazily from there to avoid
# requiring SQLAlchemy when using archipy without the sqlalchemy extra (e.g., archipy[scylladb])
# Type stubs for IDE support - these are only used for static type checking
# The actual implementations are provided via __getattr__ at runtime
if TYPE_CHECKING:
    from archipy.adapters.base.sqlalchemy.atomic import (
        async_mysql_sqlalchemy_atomic_decorator,
        async_postgres_sqlalchemy_atomic_decorator,
        async_sqlite_sqlalchemy_atomic_decorator,
        async_starrocks_sqlalchemy_atomic_decorator,
        mysql_sqlalchemy_atomic,
        mysql_sqlalchemy_atomic_decorator,
        postgres_sqlalchemy_atomic,
        postgres_sqlalchemy_atomic_decorator,
        sqlalchemy_atomic,
        sqlalchemy_atomic_decorator,
        sqlite_sqlalchemy_atomic,
        sqlite_sqlalchemy_atomic_decorator,
        starrocks_sqlalchemy_atomic,
        starrocks_sqlalchemy_atomic_decorator,
    )

_SQLALCHEMY_DECORATOR_NAMES = frozenset(
    {
        "async_mysql_sqlalchemy_atomic_decorator",
        "async_postgres_sqlalchemy_atomic_decorator",
        "async_sqlite_sqlalchemy_atomic_decorator",
        "async_starrocks_sqlalchemy_atomic_decorator",
        "mysql_sqlalchemy_atomic",
        "mysql_sqlalchemy_atomic_decorator",
        "postgres_sqlalchemy_atomic",
        "postgres_sqlalchemy_atomic_decorator",
        "sqlalchemy_atomic",
        "sqlalchemy_atomic_decorator",
        "sqlite_sqlalchemy_atomic",
        "sqlite_sqlalchemy_atomic_decorator",
        "starrocks_sqlalchemy_atomic",
        "starrocks_sqlalchemy_atomic_decorator",
    },
)


def __getattr__(name: str) -> object:
    """Lazy import for the deprecated SQLAlchemy decorator names.

    This function is called when an attribute is not found in the module.
    It defers importing the SQLAlchemy decorators until they're accessed,
    preventing SQLAlchemy from being required when using archipy without the
    sqlalchemy extra. Names that moved to ``archipy.adapters.base.sqlalchemy.atomic``
    emit a ``DeprecationWarning``.

    Args:
        name: The name of the attribute to import.

    Returns:
        The requested decorator.

    Raises:
        ConfigurationError: If SQLAlchemy is not installed and a SQLAlchemy decorator is requested.
        InvalidArgumentError: If the requested attribute is not a SQLAlchemy decorator.
    """
    if name not in _SQLALCHEMY_DECORATOR_NAMES:
        raise InvalidArgumentError(argument_name=name, additional_data={"module": __name__})

    try:
        return _sqlalchemy_transaction.resolve(name)
    except ImportError as e:
        raise ConfigurationError(operation="import", reason="sqlalchemy_extra_required") from e


__all__ = [
    "async_count_calls",
    "async_measure_duration",
    "async_mysql_sqlalchemy_atomic_decorator",
    "async_postgres_sqlalchemy_atomic_decorator",
    "async_sqlite_sqlalchemy_atomic_decorator",
    "async_starrocks_sqlalchemy_atomic_decorator",
    "async_trace_root",
    "async_trace_span",
    "class_deprecation_error",
    "class_deprecation_warning",
    "count_calls",
    "grpc_rate_limit",
    "grpc_rate_limit_decorator",
    "measure_duration",
    "method_deprecation_error",
    "method_deprecation_warning",
    "mysql_sqlalchemy_atomic",
    "mysql_sqlalchemy_atomic_decorator",
    "postgres_sqlalchemy_atomic",
    "postgres_sqlalchemy_atomic_decorator",
    "retry",
    "retry_decorator",
    "singleton",
    "singleton_decorator",
    "sqlalchemy_atomic",
    "sqlalchemy_atomic_decorator",
    "sqlite_sqlalchemy_atomic",
    "sqlite_sqlalchemy_atomic_decorator",
    "starrocks_sqlalchemy_atomic",
    "starrocks_sqlalchemy_atomic_decorator",
    "timeout",
    "timeout_decorator",
    "timing",
    "timing_decorator",
    "trace_class",
    "trace_root",
    "trace_span",
    "ttl_cache",
    "ttl_cache_decorator",
]
