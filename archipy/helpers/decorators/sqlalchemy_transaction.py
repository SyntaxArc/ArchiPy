"""Deprecated import path; the SQLAlchemy atomic decorators live in ``archipy.adapters.base.sqlalchemy.atomic``.

SQLAlchemy is an optional extra, so every name is resolved lazily from the new module on first access.
"""

from __future__ import annotations

from typing import Any

from archipy.helpers._deprecation import warn_deprecated_name

_MOVED_NAMES = frozenset(
    {
        "mysql_sqlalchemy_atomic",
        "postgres_sqlalchemy_atomic",
        "sqlalchemy_atomic",
        "sqlite_sqlalchemy_atomic",
        "starrocks_sqlalchemy_atomic",
    },
)
"""Names that are not deprecated on their own, so the move is what the warning reports."""


def resolve(name: str) -> object:
    """Return ``name`` from ``archipy.adapters.base.sqlalchemy.atomic``, warning when the name moved.

    Names that were already deprecated (the ``*_sqlalchemy_atomic_decorator`` aliases) warn about their own
    replacement instead.

    Args:
        name: The attribute to resolve.

    Returns:
        The attribute of the new module.

    Raises:
        ImportError: If SQLAlchemy is not installed.
        AttributeError: If the new module has no such attribute.
    """
    from archipy.adapters.base.sqlalchemy import atomic

    try:
        value = getattr(atomic, name)
    except AttributeError as e:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from e
    if name in _MOVED_NAMES:
        warn_deprecated_name(
            f"archipy.helpers.decorators.{name}",
            f"archipy.adapters.base.sqlalchemy.atomic.{name}",
            stacklevel=4,
        )
    return value


def __getattr__(name: str) -> Any:  # noqa: ANN401 - lazy re-export: typed callers must see the real attribute, not object
    """Resolve names from the real implementation module on first access."""
    if name.startswith("__"):
        raise AttributeError(name)
    return resolve(name)
