"""Base asynchronous SQLAlchemy adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from sqlalchemy.exc import SQLAlchemyError

from archipy.adapters.base.sqlalchemy.mixins import (
    SQLAlchemyExceptionHandlerMixin,
    SQLAlchemyFilterMixin,
    SQLAlchemyPaginationMixin,
    SQLAlchemySortMixin,
    T,
)
from archipy.adapters.base.sqlalchemy.ports import AnyExecuteParams, AsyncSQLAlchemyPort
from archipy.adapters.base.sqlalchemy.query_helpers import (
    _build_async_count_cache,
    _CountRequest,
    _ensure_entities,
    _ensure_entity,
    _ensure_entity_type,
    _extract_entities,
)
from archipy.configs.config_template import SQLAlchemyConfig
from archipy.models.dtos.sort_dto import SortDTO

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy import Executable, Result, ScalarResult
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.sql import Select

    from archipy.adapters.base.sqlalchemy.session_managers import AsyncBaseSQLAlchemySessionManager
    from archipy.models.dtos.pagination_dto import PaginationDTO
    from archipy.models.entities import BaseEntity


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
