"""Base SQLAlchemy adapter implementations.

The implementation lives in focused modules; every name is re-exported here so existing imports keep working:

- ``mixins``: exception handling, filtering, pagination and sorting mixins.
- ``query_helpers``: count cache and entity validation helpers.
- ``sync_adapter``: ``BaseSQLAlchemyAdapter``.
- ``async_adapter``: ``AsyncBaseSQLAlchemyAdapter``.
"""

from archipy.adapters.base.sqlalchemy.async_adapter import AsyncBaseSQLAlchemyAdapter
from archipy.adapters.base.sqlalchemy.mixins import (
    _FILTER_EXPRESSIONS,
    ConfigT,
    SQLAlchemyExceptionHandlerMixin,
    SQLAlchemyFilterMixin,
    SQLAlchemyPaginationMixin,
    SQLAlchemySortMixin,
    T,
    _compile_explain_json,
    _ExplainJson,
)
from archipy.adapters.base.sqlalchemy.query_helpers import (
    _build_async_count_cache,
    _build_count_cache,
    _CountRequest,
    _ensure_entities,
    _ensure_entity,
    _ensure_entity_type,
    _extract_entities,
    _released_compute,
    _run_async_count_request,
    _run_count_request,
)
from archipy.adapters.base.sqlalchemy.sync_adapter import BaseSQLAlchemyAdapter

__all__ = [
    "_FILTER_EXPRESSIONS",
    "AsyncBaseSQLAlchemyAdapter",
    "BaseSQLAlchemyAdapter",
    "ConfigT",
    "SQLAlchemyExceptionHandlerMixin",
    "SQLAlchemyFilterMixin",
    "SQLAlchemyPaginationMixin",
    "SQLAlchemySortMixin",
    "T",
    "_CountRequest",
    "_ExplainJson",
    "_build_async_count_cache",
    "_build_count_cache",
    "_compile_explain_json",
    "_ensure_entities",
    "_ensure_entity",
    "_ensure_entity_type",
    "_extract_entities",
    "_released_compute",
    "_run_async_count_request",
    "_run_count_request",
]
