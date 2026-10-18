"""Deprecated import path; use ``archipy.adapters.base.sqlalchemy.atomic`` and the ``*_sqlalchemy_atomic`` names.

SQLAlchemy is an optional extra, so everything is resolved lazily from ``sqlalchemy_transaction``.
"""

from typing import Any

from archipy.helpers.decorators.sqlalchemy_transaction import resolve


def __getattr__(name: str) -> Any:
    """Resolve names from the real implementation module on first access."""
    if name.startswith("__"):
        raise AttributeError(name)
    return resolve(name)
