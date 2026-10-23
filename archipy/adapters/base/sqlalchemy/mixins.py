"""Query mixins shared by the sync and async base SQLAlchemy adapters: errors, filtering, pagination, sorting."""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar

from sqlalchemy import Delete, Executable, Update, func, inspect, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.visitors import InternalTraversal

from archipy.adapters.base.sqlalchemy.driver_errors import classify_driver_error, log_driver_error
from archipy.configs.config_template import SQLAlchemyConfig
from archipy.models.entities import BaseEntity
from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseConstraintError,
    DatabaseError,
    DatabaseIntegrityError,
    DatabaseQueryError,
    DatabaseTimeoutError,
    DatabaseTransactionError,
    InvalidArgumentError,
)
from archipy.models.types.base_types import FilterOperationType
from archipy.models.types.sort_order_type import SortOrderType

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.engine import Dialect
    from sqlalchemy.orm import InstrumentedAttribute
    from sqlalchemy.sql import ColumnElement, Select
    from sqlalchemy.sql.compiler import SQLCompiler

    from archipy.models.dtos.pagination_dto import PaginationDTO
    from archipy.models.dtos.sort_dto import SortDTO

# Generic type variable for BaseEntity subclasses
T = TypeVar("T", bound=BaseEntity)
ConfigT = TypeVar("ConfigT", bound=SQLAlchemyConfig)


class SQLAlchemyExceptionHandlerMixin:
    """Mixin providing centralized exception handling for SQLAlchemy operations.

    This mixin provides a standard method for handling database exceptions and
    converting them to appropriate application-specific exceptions.
    """

    @classmethod
    def _handle_db_exception(cls, exception: Exception, db_name: str | None = None) -> NoReturn:
        """Handle database exceptions and raise appropriate errors.

        Args:
            exception: The exception to handle.
            db_name: Optional database name for error context.

        Raises:
            DatabaseSerializationError: If a serialization failure (SQLSTATE 40001) is detected.
            DatabaseDeadlockError: If a deadlock (SQLSTATE 40P01, MySQL 1213, SQLITE_BUSY/LOCKED) is detected.
            DatabaseResourceExhaustedError: If the server ran out of memory or connections.
            DatabaseTimeoutError: If a timeout is detected.
            DatabaseConnectionError: If a connection error is detected.
            DatabaseTransactionError: If a transaction error is detected.
            DatabaseIntegrityError: If an integrity violation is detected.
            DatabaseConstraintError: If a constraint violation is detected.
            DatabaseQueryError: For other database errors.
        """
        # Classify by driver error code first (SQLSTATE / errno); message matching is only the fallback.
        error_class = classify_driver_error(exception) or cls._classify_by_message(str(exception).lower())
        log_driver_error(exception, error_class, db_name)
        raise error_class(database=db_name) from exception

    @staticmethod
    def _classify_by_message(message: str) -> type[DatabaseError]:
        """Fallback classification for drivers that expose no usable error code."""
        if "timeout" in message:
            return DatabaseTimeoutError
        if "integrity" in message:
            return DatabaseIntegrityError
        if "constraint" in message:
            return DatabaseConstraintError
        if "connection" in message:
            return DatabaseConnectionError
        if "transaction" in message:
            return DatabaseTransactionError
        return DatabaseQueryError


# Operations that need no validation, mapped to the SQLAlchemy expression they build.
_FILTER_EXPRESSIONS: dict[FilterOperationType, Callable[[InstrumentedAttribute, Any], ColumnElement[bool]]] = {
    FilterOperationType.EQUAL: lambda field, value: field == value,
    FilterOperationType.NOT_EQUAL: lambda field, value: field != value,
    FilterOperationType.LESS_THAN: lambda field, value: field < value,
    FilterOperationType.LESS_THAN_OR_EQUAL: lambda field, value: field <= value,
    FilterOperationType.GREATER_THAN: lambda field, value: field > value,
    FilterOperationType.GREATER_THAN_OR_EQUAL: lambda field, value: field >= value,
    FilterOperationType.LIKE: lambda field, value: field.like(f"%{value}%"),
    FilterOperationType.ILIKE: lambda field, value: field.ilike(f"%{value}%"),
    FilterOperationType.STARTS_WITH: lambda field, value: field.startswith(value),
    FilterOperationType.ENDS_WITH: lambda field, value: field.endswith(value),
    FilterOperationType.CONTAINS: lambda field, value: field.contains(value),
    FilterOperationType.IS_NULL: lambda field, _value: field.is_(None),
    FilterOperationType.IS_NOT_NULL: lambda field, _value: field.is_not(None),
}


class SQLAlchemyFilterMixin:
    """Mixin providing filtering capabilities for SQLAlchemy queries.

    Supports equality, inequality, string operations, list operations, and NULL checks.
    """

    @staticmethod
    def _validate_list_operation(
        value: str | float | bool | Decimal | list[Any] | UUID | datetime | date | Enum | None,
        operation: FilterOperationType,
    ) -> list[Any]:
        """Validate that value is a list for list operations."""
        if not isinstance(value, list):
            raise InvalidArgumentError(
                argument_name="value",
                additional_data={
                    "operation": operation.value,
                    "expected_type": "list",
                    "got": type(value).__name__,
                },
            )
        return value

    @staticmethod
    def _apply_filter(
        query: Select | Update | Delete,
        field: InstrumentedAttribute,
        value: str | float | bool | Decimal | list[Any] | UUID | datetime | date | Enum | None,
        operation: FilterOperationType,
    ) -> Select | Update | Delete:
        """Apply a filter to a SQLAlchemy query based on the specified operation.

        Args:
            query: The SQLAlchemy query to apply the filter to.
            field: The model attribute/column to filter on.
            value: The value to compare against.
            operation: The type of filter operation to apply.

        Returns:
            The updated query with the filter applied.
        """
        # Skip filter if value is None (except for IS_NULL/IS_NOT_NULL operations)
        if value is None and operation not in (FilterOperationType.IS_NULL, FilterOperationType.IS_NOT_NULL):
            return query

        if operation in (FilterOperationType.IN_LIST, FilterOperationType.NOT_IN_LIST):
            expression = field.in_(SQLAlchemyFilterMixin._validate_list_operation(value, operation))
            return query.where(~expression if operation == FilterOperationType.NOT_IN_LIST else expression)

        build_expression = _FILTER_EXPRESSIONS.get(operation)
        if build_expression is None:
            return query
        return query.where(build_expression(field, value))


class _ExplainJson(Executable, ClauseElement):
    """``EXPLAIN (FORMAT JSON)`` of a SELECT, compiled by SQLAlchemy so bound values keep their type handling."""

    inherit_cache = False
    _traverse_internals = [("stmt", InternalTraversal.dp_clauseelement)]  # noqa: RUF012

    def __init__(self, stmt: Select) -> None:
        self.stmt = stmt

    @property
    def _all_selected_columns(self) -> list[Any]:
        """Declare no selectable columns: SQLAlchemy reads this when it reuses cached result metadata."""
        return []


@compiles(_ExplainJson, "postgresql")
def _compile_explain_json(element: _ExplainJson, compiler: SQLCompiler, **kw: object) -> str:
    return "EXPLAIN (FORMAT JSON) " + compiler.process(element.stmt, **kw)


class SQLAlchemyPaginationMixin:
    """Mixin providing pagination capabilities for SQLAlchemy queries.

    Supports limiting results and applying offsets for paginated queries.
    """

    @staticmethod
    def _apply_pagination(query: Select, pagination: PaginationDTO | None) -> Select:
        """Apply pagination to a SQLAlchemy query.

        Args:
            query: The SQLAlchemy query to paginate.
            pagination: Pagination settings (page size and offset).

        Returns:
            The paginated query.
        """
        if pagination is None:
            return query
        return query.limit(pagination.page_size).offset(pagination.offset)

    @staticmethod
    def _total_from_page(
        results: list[Any],
        pagination: PaginationDTO | None,
        has_multiple_entities: bool,
    ) -> int | None:
        """Return the total count when the fetched page already proves it, otherwise None.

        The page proves the total when nothing was paginated, or when the first page is not full.
        Skipping the COUNT query then saves a full scan of the filtered rows.

        Args:
            results: The fetched page.
            pagination: Pagination settings used for the query.
            has_multiple_entities: True when rows may have been dropped while extracting entities.

        Returns:
            The total count, or None when a COUNT query is needed.
        """
        if has_multiple_entities:
            return None
        if pagination is None or (pagination.offset == 0 and len(results) < pagination.page_size):
            return len(results)
        return None

    @staticmethod
    def _build_count_source(entity: type[BaseEntity], query: Select, limit: int | None = None) -> Select:
        """Build the inner SELECT that a COUNT runs over.

        Drops the ordering, and selects only the primary key of ``entity`` so the database can answer from the
        primary key index instead of reading every selected column. The columns are kept as they are when they
        change the row count (DISTINCT, GROUP BY, HAVING, LIMIT, OFFSET).

        Args:
            entity: The entity class the query selects.
            query: The unpaginated search query.
            limit: Optional cap on the rows counted. Ignored when the query has its own LIMIT or OFFSET.

        Returns:
            The inner SELECT.
        """
        source = query.order_by(None)
        shapes_rows = (
            source._distinct
            or source._group_by_clauses
            or source._having_criteria
            or source._limit_clause is not None
            or source._offset_clause is not None
        )
        if not shapes_rows:
            source = source.with_only_columns(*inspect(entity).primary_key, maintain_column_froms=True)
            if limit is not None:
                source = source.limit(limit)
        return source

    @staticmethod
    def _count_cache_key(source: Select, count_threshold: int | None) -> tuple[str, str, int | None]:
        """Build the cache key of a count query from its SQL text and bound values."""
        compiled = source.compile()
        return str(compiled), repr(sorted(compiled.params.items())), count_threshold

    @staticmethod
    def _build_count_query(source: Select) -> Select:
        """Wrap an inner SELECT in a COUNT.

        Args:
            source: The inner SELECT from ``_build_count_source``.

        Returns:
            The COUNT query.
        """
        return select(func.count()).select_from(source.subquery())

    @staticmethod
    def _build_estimate_statement(source: Select, dialect: Dialect) -> Executable | None:
        """Build the statement that estimates the rows of an inner SELECT.

        Args:
            source: The inner SELECT from ``_build_count_source``, without a LIMIT.
            dialect: The dialect of the connected database.

        Returns:
            An EXPLAIN statement, or None when the dialect has no supported estimate.
        """
        if dialect.name != "postgresql":
            return None
        return _ExplainJson(source)

    @staticmethod
    def _parse_estimate(plan: object) -> int | None:
        """Read the estimated row count from a PostgreSQL JSON plan.

        Args:
            plan: The first column of the EXPLAIN result, a JSON string or an already parsed list.

        Returns:
            The estimated rows, or None when the plan has an unexpected shape.
        """
        try:
            parsed: Any = json.loads(plan) if isinstance(plan, str | bytes) else plan
            return int(parsed[0]["Plan"]["Plan Rows"])
        except KeyError, IndexError, TypeError, ValueError:
            return None


class SQLAlchemySortMixin:
    """Mixin providing sorting capabilities for SQLAlchemy queries.

    Supports dynamic column selection and ascending/descending order.
    """

    @staticmethod
    def _apply_sorting(entity: type[T], query: Select, sort_info: SortDTO | None) -> Select:
        """Apply sorting to a SQLAlchemy query.

        Args:
            entity: The entity class to query.
            query: The SQLAlchemy query to sort.
            sort_info: Sorting information (column and direction).

        Returns:
            The sorted query.

        Raises:
            InvalidArgumentError: If the sort order is invalid.
        """
        if sort_info is None:
            return query
        if isinstance(sort_info.column, str):
            sort_column = getattr(entity, sort_info.column)
        elif isinstance(sort_info.column, Enum):
            sort_column = getattr(entity, sort_info.column.name.lower())
        else:
            sort_column = sort_info.column

        order_value = sort_info.order.value if isinstance(sort_info.order, Enum) else sort_info.order
        match order_value:
            case SortOrderType.ASCENDING.value:
                return query.order_by(sort_column.asc())
            case SortOrderType.DESCENDING.value:
                return query.order_by(sort_column.desc())
            case _:
                raise InvalidArgumentError(argument_name="sort_info.order")
