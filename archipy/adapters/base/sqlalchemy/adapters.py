"""Base SQLAlchemy adapter implementations."""

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, override

from sqlalchemy import Delete, Executable, Result, ScalarResult, Update, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.visitors import InternalTraversal

from archipy.adapters.base.sqlalchemy.ports import AnyExecuteParams, AsyncSQLAlchemyPort, SQLAlchemyPort
from archipy.configs.config_template import SQLAlchemyConfig
from archipy.models.dtos.sort_dto import SortDTO
from archipy.models.entities import BaseEntity
from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseConstraintError,
    DatabaseIntegrityError,
    DatabaseQueryError,
    DatabaseTimeoutError,
    DatabaseTransactionError,
    InvalidArgumentError,
    InvalidEntityTypeError,
)
from archipy.models.types.base_types import FilterOperationType
from archipy.models.types.sort_order_type import SortOrderType

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    from sqlalchemy.engine import Dialect
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import InstrumentedAttribute, Session
    from sqlalchemy.sql import ColumnElement, Select
    from sqlalchemy.sql.compiler import SQLCompiler

    from archipy.adapters.base.sqlalchemy.session_managers import (
        AsyncBaseSQLAlchemySessionManager,
        BaseSQLAlchemySessionManager,
    )
    from archipy.models.dtos.pagination_dto import PaginationDTO

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
            DatabaseTimeoutError: If a timeout is detected.
            DatabaseConnectionError: If a connection error is detected.
            DatabaseTransactionError: If a transaction error is detected.
            DatabaseIntegrityError: If an integrity violation is detected.
            DatabaseConstraintError: If a constraint violation is detected.
            DatabaseQueryError: For other database errors.
        """
        message = str(exception).lower()
        if "timeout" in message:
            raise DatabaseTimeoutError(database=db_name) from exception
        if "integrity" in message:
            raise DatabaseIntegrityError(database=db_name) from exception
        if "constraint" in message:
            raise DatabaseConstraintError(database=db_name) from exception
        if "connection" in message:
            raise DatabaseConnectionError(database=db_name) from exception
        if "transaction" in message:
            raise DatabaseTransactionError(database=db_name) from exception

        # Default error if no specific error is detected
        raise DatabaseQueryError(database=db_name) from exception


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
        value: str | float | bool | Decimal | list | UUID | datetime | date | Enum | None,
        operation: FilterOperationType,
    ) -> list:
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
        value: str | float | bool | Decimal | list | UUID | datetime | date | Enum | None,
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


def _released_compute() -> NoReturn:
    raise RuntimeError("The count request was already run")  # noqa: TRY003


class _CountRequest:
    """A count to compute, hashed and compared by its cache key only.

    The cache decorators key on every argument. The session and the query are not part of the identity of a count,
    so they travel inside ``compute`` and stay out of the key. The runner releases ``compute`` after the count, so a
    cached key never keeps the session or the query alive.
    """

    __slots__ = ("compute", "key")

    def __init__(self, key: tuple[str, str, int | None], compute: Callable[[], Any]) -> None:
        self.key = key
        self.compute = compute

    def __hash__(self) -> int:
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _CountRequest) and self.key == other.key


def _run_count_request(request: _CountRequest) -> int:
    try:
        return request.compute()
    finally:
        request.compute = _released_compute


async def _run_async_count_request(request: _CountRequest) -> int:
    try:
        return await request.compute()
    finally:
        request.compute = _released_compute


def _build_count_cache(config: SQLAlchemyConfig) -> Callable[[_CountRequest], int] | None:
    """Create the cached count runner when the config enables it (needs the ``cache`` extra)."""
    if not config.COUNT_CACHE_ENABLED:
        return None
    from archipy.helpers.decorators.ttl_caching import ttl_cache  # noqa: PLC0415  # optional "cache" extra

    return ttl_cache(ttl_seconds=config.COUNT_CACHE_TTL_SECONDS, maxsize=config.COUNT_CACHE_MAX_SIZE)(
        _run_count_request,
    )


def _build_async_count_cache(config: SQLAlchemyConfig) -> Callable[[_CountRequest], Awaitable[int]] | None:
    """Create the cached async count runner when the config enables it (needs the ``cache`` extra)."""
    if not config.COUNT_CACHE_ENABLED:
        return None
    from async_lru import alru_cache  # noqa: PLC0415  # optional "cache" extra

    return alru_cache(ttl=config.COUNT_CACHE_TTL_SECONDS, maxsize=config.COUNT_CACHE_MAX_SIZE)(
        _run_async_count_request,
    )


def _ensure_entity(entity: object) -> None:
    """Raise if the object is not a BaseEntity instance.

    Raises:
        InvalidEntityTypeError: If the object is not a BaseEntity instance.
    """
    if not isinstance(entity, BaseEntity):
        raise InvalidEntityTypeError(
            message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
            expected_type="BaseEntity",
            actual_type=type(entity).__name__,
        )


def _ensure_entities(entities: list[Any]) -> None:
    """Raise if any item is not a BaseEntity instance.

    Raises:
        InvalidEntityTypeError: If any item is not a BaseEntity instance.
    """
    if not all(isinstance(entity, BaseEntity) for entity in entities):
        raise InvalidEntityTypeError(
            message="All entities must be BaseEntity subclasses",
            expected_type="BaseEntity",
            actual_type="mixed",
        )


def _ensure_entity_type(entity_type: type) -> None:
    """Raise if the class is not a BaseEntity subclass.

    Raises:
        InvalidEntityTypeError: If the class is not a BaseEntity subclass.
    """
    if not issubclass(entity_type, BaseEntity):
        raise InvalidEntityTypeError(
            message=f"Expected BaseEntity subclass, got {entity_type.__name__}",
            expected_type="BaseEntity",
            actual_type=entity_type.__name__,
        )


def _extract_entities[E: BaseEntity](result_set: Result[Any], entity: type[E], has_multiple_entities: bool) -> list[E]:
    """Extract entities of the requested type from a search result.

    Args:
        result_set: The executed search result.
        entity: The entity class the query selects.
        has_multiple_entities: True when the query selects several entities (for example through joins).
            Only the first column of each row is returned, and values that are not instances of ``entity`` are dropped.

    Returns:
        The extracted entities.
    """
    entities = result_set.scalars().all()
    if has_multiple_entities:
        return [item for item in entities if isinstance(item, entity)]
    return list(entities)


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


class BaseSQLAlchemyAdapter[ConfigT: SQLAlchemyConfig](
    SQLAlchemyPort,
    SQLAlchemyPaginationMixin,
    SQLAlchemySortMixin,
    SQLAlchemyFilterMixin,
    SQLAlchemyExceptionHandlerMixin,
):
    """Base synchronous SQLAlchemy adapter for ORM operations.

    Provides a standardized interface for CRUD operations, pagination, sorting, and filtering.
    Specific database adapters should inherit from this class and provide their own session manager.

    Args:
        orm_config: Configuration for SQLAlchemy. If None, uses global config.
    """

    def __init__(self, orm_config: ConfigT) -> None:
        """Initialize the base adapter with a session manager.

        Args:
            orm_config: Configuration for SQLAlchemy. Subclasses resolve the
                appropriate default from global config when not provided.
        """
        self.session_manager: BaseSQLAlchemySessionManager[ConfigT] = self._create_session_manager(
            orm_config,
        )
        self._cached_count = _build_count_cache(orm_config)
        self._count_threshold = orm_config.COUNT_THRESHOLD

    def _create_session_manager(self, configs: ConfigT) -> BaseSQLAlchemySessionManager[ConfigT]:
        """Create a session manager for the specific database.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            A session manager instance.
        """
        raise NotImplementedError("Subclasses must implement _create_session_manager")

    def _count_total(
        self,
        session: Session,
        entity: type[T],
        query: Select,
        count_threshold: int | None,
    ) -> int:
        """Return the total of a search query, from the count cache when it is enabled and still valid."""
        if self._cached_count is None:
            return self._count_rows(session, entity, query, count_threshold)
        key = self._count_cache_key(self._build_count_source(entity, query), count_threshold)
        return self._cached_count(_CountRequest(key, lambda: self._count_rows(session, entity, query, count_threshold)))

    def _count_rows(
        self,
        session: Session,
        entity: type[T],
        query: Select,
        count_threshold: int | None,
    ) -> int:
        """Count the rows of a search query, bounded and estimated above ``count_threshold`` when it is set."""
        if count_threshold is None:
            return session.execute(self._build_count_query(self._build_count_source(entity, query))).scalar_one()
        bounded = session.execute(
            self._build_count_query(self._build_count_source(entity, query, limit=count_threshold + 1)),
        ).scalar_one()
        if bounded <= count_threshold:
            return bounded
        statement = self._build_estimate_statement(self._build_count_source(entity, query), session.get_bind().dialect)
        if statement is not None:
            estimate = self._parse_estimate(session.execute(statement).scalar())
            if estimate is not None:
                return max(estimate, bounded)
        return session.execute(self._build_count_query(self._build_count_source(entity, query))).scalar_one()

    @override
    def execute_search_query(
        self,
        entity: type[T],
        query: Select,
        pagination: PaginationDTO | None = None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
        *,
        count_threshold: int | None = None,
    ) -> tuple[list[T], int]:
        """Execute a search query with pagination and sorting.

        Args:
            entity: The entity class to query.
            query: The SQLAlchemy SELECT query.
            pagination: Optional pagination settings.
            sort_info: Optional sorting information.
            has_multiple_entities: Set when the query selects several entities; only instances of ``entity``
                from the first column of each row are returned.
            count_threshold: When set, the total is exact up to this many rows. Above it the total is a database
                estimate (PostgreSQL) so large tables are never counted in full. Other databases count exactly.
                Defaults to the ``COUNT_THRESHOLD`` config value.

        Returns:
            Tuple of the list of entities and the total count.

        Raises:
            DatabaseQueryError: If the database query fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            sort_info = sort_info or SortDTO.default()
            session = self.get_session()
            sorted_query = self._apply_sorting(entity, query, sort_info)
            paginated_query = self._apply_pagination(sorted_query, pagination)
            result_set = session.execute(paginated_query)
            results = _extract_entities(result_set, entity, has_multiple_entities)
            total_count = self._total_from_page(results, pagination, has_multiple_entities)
            if total_count is None:
                total_count = self._count_total(
                    session,
                    entity,
                    query,
                    count_threshold if count_threshold is not None else self._count_threshold,
                )
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            # Type: results is list[T] where T extends BaseEntity, total_count is int
            return results, total_count

    @override
    def get_session(self) -> Session:
        """Get a database session.

        Returns:
            Session: A SQLAlchemy session.

        Raises:
            DatabaseConnectionError: If there's an error getting the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        return self.session_manager.get_session()

    @override
    def create(self, entity: T) -> T | None:
        """Create a new entity in the database.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with updated attributes, preserving the original type.

        Raises:
            InvalidEntityTypeError: If the entity type is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity(entity)

        try:
            session = self.get_session()
            session.add(entity)
            session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entity

    @override
    def bulk_create(self, entities: list[T]) -> list[T] | None:
        """Creates multiple entities in a single database operation.

        Args:
            entities: List of entities to create.

        Returns:
            List of created entities with updated attributes, preserving original types.

        Raises:
            InvalidEntityTypeError: If any entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entities(entities)

        try:
            session = self.get_session()
            session.add_all(entities)
            session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entities

    @override
    def get_by_uuid(self, entity_type: type[T], entity_uuid: UUID) -> BaseEntity | None:
        """Retrieve an entity by its UUID.

        Args:
            entity_type: The type of entity to retrieve.
            entity_uuid: The UUID of the entity.

        Returns:
            The entity if found, None otherwise.

        Raises:
            InvalidEntityTypeError: If the entity type is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity_type(entity_type)

        try:
            session = self.get_session()
            result = session.get(entity_type, entity_uuid)
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            # result is T | None where T extends BaseEntity, compatible with BaseEntity | None
            # The type checker needs explicit type annotation to understand the relationship
            typed_result: BaseEntity | None = result
            return typed_result

    @override
    def delete(self, entity: T) -> None:
        """Delete an entity from the database.

        Args:
            entity: The entity to delete.

        Raises:
            InvalidEntityTypeError: If the entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity(entity)

        try:
            session = self.get_session()
            session.delete(entity)
            session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())

    @override
    def bulk_delete(self, entities: list[T]) -> None:
        """Delete multiple entities from the database.

        Args:
            entities: List of entities to delete.

        Raises:
            InvalidEntityTypeError: If any entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entities(entities)

        try:
            session = self.get_session()
            for entity in entities:
                session.delete(entity)
            session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())

    @override
    def execute(self, statement: Executable, params: AnyExecuteParams | None = None) -> Result[Any]:
        """Execute a SQLAlchemy statement.

        Args:
            statement: The SQLAlchemy statement to execute.
            params: Optional parameters for the statement.

        Returns:
            The result of the execution.

        Raises:
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            session = self.get_session()
            result = session.execute(statement, params or {})
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

    @override
    def scalars(self, statement: Executable, params: AnyExecuteParams | None = None) -> ScalarResult[Any]:
        """Execute a SQLAlchemy statement and return scalar results.

        Args:
            statement: The SQLAlchemy statement to execute.
            params: Optional parameters for the statement.

        Returns:
            The scalar results of the execution.

        Raises:
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            session = self.get_session()
            result = session.scalars(statement, params or {})
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result


class AsyncBaseSQLAlchemyAdapter[ConfigT: SQLAlchemyConfig](
    AsyncSQLAlchemyPort,
    SQLAlchemyPaginationMixin,
    SQLAlchemySortMixin,
    SQLAlchemyFilterMixin,
    SQLAlchemyExceptionHandlerMixin,
):
    """Base asynchronous SQLAlchemy adapter for ORM operations.

    Provides a standardized interface for CRUD operations, pagination, sorting, and filtering.
    Specific database adapters should inherit from this class and provide their own session manager.

    Args:
        orm_config: Configuration for SQLAlchemy. If None, uses global config.
    """

    def __init__(self, orm_config: ConfigT) -> None:
        """Initialize the base async adapter with a session manager.

        Args:
            orm_config: Configuration for SQLAlchemy. Subclasses resolve the
                appropriate default from global config when not provided.
        """
        self.session_manager: AsyncBaseSQLAlchemySessionManager[ConfigT] = self._create_async_session_manager(
            orm_config,
        )
        self._cached_count = _build_async_count_cache(orm_config)
        self._count_threshold = orm_config.COUNT_THRESHOLD

    def _create_async_session_manager(self, configs: ConfigT) -> AsyncBaseSQLAlchemySessionManager[ConfigT]:
        """Create an async session manager for the specific database.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            An async session manager instance.
        """
        raise NotImplementedError("Subclasses must implement _create_async_session_manager")

    async def _count_total(
        self,
        session: AsyncSession,
        entity: type[T],
        query: Select,
        count_threshold: int | None,
    ) -> int:
        """Return the total of a search query, from the count cache when it is enabled and still valid."""
        if self._cached_count is None:
            return await self._count_rows(session, entity, query, count_threshold)
        key = self._count_cache_key(self._build_count_source(entity, query), count_threshold)
        return await self._cached_count(
            _CountRequest(key, lambda: self._count_rows(session, entity, query, count_threshold)),
        )

    async def _count_rows(
        self,
        session: AsyncSession,
        entity: type[T],
        query: Select,
        count_threshold: int | None,
    ) -> int:
        """Count the rows of a search query, bounded and estimated above ``count_threshold`` when it is set."""
        if count_threshold is None:
            return (
                await session.execute(self._build_count_query(self._build_count_source(entity, query)))
            ).scalar_one()
        bounded = (
            await session.execute(
                self._build_count_query(self._build_count_source(entity, query, limit=count_threshold + 1)),
            )
        ).scalar_one()
        if bounded <= count_threshold:
            return bounded
        statement = self._build_estimate_statement(self._build_count_source(entity, query), session.get_bind().dialect)
        if statement is not None:
            estimate = self._parse_estimate((await session.execute(statement)).scalar())
            if estimate is not None:
                return max(estimate, bounded)
        return (await session.execute(self._build_count_query(self._build_count_source(entity, query)))).scalar_one()

    @override
    async def execute_search_query(
        self,
        entity: type[T],
        query: Select,
        pagination: PaginationDTO | None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
        *,
        count_threshold: int | None = None,
    ) -> tuple[list[T], int]:
        """Execute a search query with pagination and sorting.

        Args:
            entity: The entity class to query.
            query: The SQLAlchemy SELECT query.
            pagination: Optional pagination settings.
            sort_info: Optional sorting information.
            has_multiple_entities: Set when the query selects several entities; only instances of ``entity``
                from the first column of each row are returned.
            count_threshold: When set, the total is exact up to this many rows. Above it the total is a database
                estimate (PostgreSQL) so large tables are never counted in full. Other databases count exactly.
                Defaults to the ``COUNT_THRESHOLD`` config value.

        Returns:
            Tuple of the list of entities and the total count.

        Raises:
            DatabaseQueryError: If the database query fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            sort_info = sort_info or SortDTO.default()
            session = self.get_session()
            sorted_query = self._apply_sorting(entity, query, sort_info)
            paginated_query = self._apply_pagination(sorted_query, pagination)
            result_set = await session.execute(paginated_query)
            results = _extract_entities(result_set, entity, has_multiple_entities)
            total_count = self._total_from_page(results, pagination, has_multiple_entities)
            if total_count is None:
                total_count = await self._count_total(
                    session,
                    entity,
                    query,
                    count_threshold if count_threshold is not None else self._count_threshold,
                )
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            # Type: results is list[T] where T extends BaseEntity, total_count is int
            return results, total_count

    @override
    def get_session(self) -> AsyncSession:
        """Get a database session.

        Returns:
            AsyncSession: A SQLAlchemy async session.

        Raises:
            DatabaseConnectionError: If there's an error getting the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        return self.session_manager.get_session()

    @override
    async def create(self, entity: T) -> T | None:
        """Create a new entity in the database.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with updated attributes, preserving the original type.

        Raises:
            InvalidEntityTypeError: If the entity type is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity(entity)

        try:
            session = self.get_session()
            session.add(entity)
            await session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entity

    @override
    async def bulk_create(self, entities: list[T]) -> list[T] | None:
        """Creates multiple entities in a single database operation.

        Args:
            entities: List of entities to create.

        Returns:
            List of created entities with updated attributes, preserving original types.

        Raises:
            InvalidEntityTypeError: If any entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entities(entities)

        try:
            session = self.get_session()
            session.add_all(entities)
            await session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entities

    @override
    async def get_by_uuid(self, entity_type: type[T], entity_uuid: UUID) -> BaseEntity | None:
        """Retrieve an entity by its UUID.

        Args:
            entity_type: The type of entity to retrieve.
            entity_uuid: The UUID of the entity.

        Returns:
            The entity if found, None otherwise.

        Raises:
            InvalidEntityTypeError: If the entity type is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity_type(entity_type)

        try:
            session = self.get_session()
            result = await session.get(entity_type, entity_uuid)
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            # result is T | None where T extends BaseEntity, compatible with BaseEntity | None
            # The type checker needs explicit type annotation to understand the relationship
            typed_result: BaseEntity | None = result
            return typed_result

    @override
    async def delete(self, entity: BaseEntity) -> None:
        """Delete an entity from the database.

        Args:
            entity: The entity to delete.

        Raises:
            InvalidEntityTypeError: If the entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entity(entity)

        try:
            session = self.get_session()
            await session.delete(entity)
            await session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())

    @override
    async def bulk_delete(self, entities: list[T]) -> None:
        """Delete multiple entities from the database.

        Args:
            entities: List of entities to delete.

        Raises:
            InvalidEntityTypeError: If any entity is not a valid SQLAlchemy model.
            DatabaseQueryError: If the database operation fails.
            DatabaseIntegrityError: If there's an integrity constraint violation.
            DatabaseConstraintError: If there's a constraint violation.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        _ensure_entities(entities)

        try:
            session = self.get_session()
            for entity in entities:
                await session.delete(entity)
            await session.flush()
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())

    @override
    async def execute(self, statement: Executable, params: AnyExecuteParams | None = None) -> Result[Any]:
        """Execute a SQLAlchemy statement.

        Args:
            statement: The SQLAlchemy statement to execute.
            params: Optional parameters for the statement.

        Returns:
            The result of the execution.

        Raises:
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            session = self.get_session()
            result = await session.execute(statement, params or {})
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

    @override
    async def scalars(self, statement: Executable, params: AnyExecuteParams | None = None) -> ScalarResult[Any]:
        """Execute a SQLAlchemy statement and return scalar results.

        Args:
            statement: The SQLAlchemy statement to execute.
            params: Optional parameters for the statement.

        Returns:
            The scalar results of the execution.

        Raises:
            DatabaseQueryError: If the database operation fails.
            DatabaseTimeoutError: If the query times out.
            DatabaseConnectionError: If there's a connection error.
            DatabaseTransactionError: If there's a transaction error.
        """
        try:
            session = self.get_session()
            result = await session.scalars(statement, params or {})
        except SQLAlchemyError as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result
