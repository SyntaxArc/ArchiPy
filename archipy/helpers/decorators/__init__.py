"""Reusable decorator helpers for ArchiPy."""

import importlib
from typing import TYPE_CHECKING

from archipy.models.errors import ConfigurationError, InvalidArgumentError

# Old module paths stay importable as thin shims; they must load before the decorator names are bound below.
from . import _legacy_modules  # noqa: F401
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


# SQLAlchemy decorators are imported lazily to avoid requiring SQLAlchemy
# when using archipy without the sqlalchemy extra (e.g., archipy[scylladb])
class _SQLAlchemyDecorators:
    """Container for lazily loaded SQLAlchemy decorators."""

    _cache: dict[str, object] | None = None


# Type stubs for IDE support - these are only used for static type checking
# The actual implementations are provided via __getattr__ at runtime
if TYPE_CHECKING:
    from .sqlalchemy_transaction import (
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
    """Lazy import for SQLAlchemy decorators.

    This function is called when an attribute is not found in the module.
    It allows us to defer importing SQLAlchemy-related decorators until they're
    actually accessed, preventing SQLAlchemy from being required when using
    archipy without the sqlalchemy extra.

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

    if _SQLAlchemyDecorators._cache is None:
        try:
            sqlalchemy_transaction = importlib.import_module(".sqlalchemy_transaction", __name__)
        except ImportError as e:
            raise ConfigurationError(operation="import", reason="sqlalchemy_extra_required") from e

        _SQLAlchemyDecorators._cache = {
            decorator_name: getattr(sqlalchemy_transaction, decorator_name)
            for decorator_name in _SQLALCHEMY_DECORATOR_NAMES
        }

    return _SQLAlchemyDecorators._cache[name]


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
