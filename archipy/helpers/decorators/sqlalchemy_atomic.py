"""Deprecated import path; use ``archipy.helpers.decorators`` and the ``*_sqlalchemy_atomic`` names instead.

SQLAlchemy is an optional extra, so everything is resolved lazily from ``sqlalchemy_transaction``.
"""

import importlib
from typing import Any


def __getattr__(name: str) -> Any:
    """Resolve names from the real implementation module on first access."""
    sqlalchemy_transaction = importlib.import_module("archipy.helpers.decorators.sqlalchemy_transaction")

    try:
        return getattr(sqlalchemy_transaction, name)
    except AttributeError as e:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from e
