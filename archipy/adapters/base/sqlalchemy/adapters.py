from enum import Enum
from typing import Any, TypeVar, override
from uuid import UUID

from sqlalchemy import Delete, Executable, Result, ScalarResult, Update, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql import Select

from archipy.adapters.base.sqlalchemy.ports import AnyExecuteParams, AsyncSQLAlchemyPort, SQLAlchemyPort
from archipy.adapters.base.sqlalchemy.session_managers import (
    AsyncBaseSQLAlchemySessionManager,
    BaseSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SQLAlchemyConfig
from archipy.models.dtos.pagination_dto import PaginationDTO
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

# Generic type variable for BaseEntity subclasses
T = TypeVar("T", bound=BaseEntity)
ConfigT = TypeVar("ConfigT", bound=SQLAlchemyConfig)


class SQLAlchemyExceptionHandlerMixin:
    """Mixin providing centralized exception handling for SQLAlchemy operations.

    This mixin provides a standard method for handling database exceptions and
    converting them to appropriate application-specific exceptions.
    """

    @classmethod
    def _handle_db_exception(cls, exception: Exception, db_name: str | None = None) -> None:
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
        if "timeout" in str(exception).lower():
            raise DatabaseTimeoutError(database=db_name) from exception
        if "integrity" in str(exception).lower():
            raise DatabaseIntegrityError(database=db_name) from exception
        if "constraint" in str(exception).lower():
            raise DatabaseConstraintError(database=db_name) from exception
        if "connection" in str(exception).lower():
            raise DatabaseConnectionError(database=db_name) from exception
        if "transaction" in str(exception).lower():
            raise DatabaseTransactionError(database=db_name) from exception

        # Default error if no specific error is detected
        raise DatabaseQueryError(database=db_name) from exception


class SQLAlchemyFilterMixin:
    """Mixin providing filtering capabilities for SQLAlchemy queries.

    Supports equality, inequality, string operations, list operations, and NULL checks.
    """

    @staticmethod
    def _apply_filter(
        query: Select | Update | Delete,
        field: InstrumentedAttribute,
        value: str | int | float | bool | list | None,
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
        if value is not None or operation in [FilterOperationType.IS_NULL, FilterOperationType.IS_NOT_NULL]:
            match operation:
                case FilterOperationType.EQUAL:
                    return query.where(field == value)
                case FilterOperationType.NOT_EQUAL:
                    return query.where(field != value)
                case FilterOperationType.LESS_THAN:
                    return query.where(field < value)
                case FilterOperationType.LESS_THAN_OR_EQUAL:
                    return query.where(field <= value)
                case FilterOperationType.GREATER_THAN:
                    return query.where(field > value)
                case FilterOperationType.GREATER_THAN_OR_EQUAL:
                    return query.where(field >= value)
                case FilterOperationType.IN_LIST:
                    if not isinstance(value, list):
                        raise InvalidArgumentError(f"IN_LIST operation requires a list, got {type(value)}")
                    return query.where(field.in_(value))
                case FilterOperationType.NOT_IN_LIST:
                    if not isinstance(value, list):
                        raise InvalidArgumentError(f"NOT_IN_LIST operation requires a list, got {type(value)}")
                    return query.where(~field.in_(value))
                case FilterOperationType.LIKE:
                    return query.where(field.like(f"%{value}%"))
                case FilterOperationType.ILIKE:
                    return query.where(field.ilike(f"%{value}%"))
                case FilterOperationType.STARTS_WITH:
                    return query.where(field.startswith(value))
                case FilterOperationType.ENDS_WITH:
                    return query.where(field.endswith(value))
                case FilterOperationType.CONTAINS:
                    return query.where(field.contains(value))
                case FilterOperationType.IS_NULL:
                    return query.where(field.is_(None))
                case FilterOperationType.IS_NOT_NULL:
                    return query.where(field.isnot(None))
        return query


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

    def __init__(self, orm_config: ConfigT | None = None) -> None:
        """Initialize the base adapter with a session manager.

        Args:
            orm_config: Configuration for SQLAlchemy. If None, uses global config.
        """
        configs = BaseConfig.global_config().SQLALCHEMY if orm_config is None else orm_config
        # Cast to ConfigT since subclasses will ensure the proper type
        self.session_manager: BaseSQLAlchemySessionManager[ConfigT] = self._create_session_manager(configs)  # type: ignore[arg-type]

    def _create_session_manager(self, configs: ConfigT) -> BaseSQLAlchemySessionManager[ConfigT]:
        """Create a session manager for the specific database.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            A session manager instance.
        """
        raise NotImplementedError("Subclasses must implement _create_session_manager")

    @override
    def execute_search_query(
        self,
        entity: type[T],
        query: Select,
        pagination: PaginationDTO | None = None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
    ) -> tuple[list[T], int]:
        """Execute a search query with pagination and sorting.

        Args:
            entity: The entity class to query.
            query: The SQLAlchemy SELECT query.
            pagination: Optional pagination settings.
            sort_info: Optional sorting information.
            has_multiple_entities: Optional bool.

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
            if has_multiple_entities:
                results = list(result_set.fetchall())
            else:
                results = list(result_set.scalars().all())
            count_query = select(func.count()).select_from(query.subquery())
            total_count = session.execute(count_query).scalar_one()
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return results, total_count  # type: ignore[return-value]

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
        if not isinstance(entity, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
                expected_type="BaseEntity",
                actual_type=type(entity).__name__,
            )

        try:
            session = self.get_session()
            session.add(entity)
            session.flush()
        except Exception as e:
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
        if not all(isinstance(entity, BaseEntity) for entity in entities):
            raise InvalidEntityTypeError(
                message="All entities must be BaseEntity subclasses",
                expected_type="BaseEntity",
                actual_type="mixed",
            )

        try:
            session = self.get_session()
            session.add_all(entities)
            session.flush()
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entities

    @override
    def get_by_uuid(self, entity_type: type[T], entity_uuid: UUID) -> T | None:
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
        if not issubclass(entity_type, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {entity_type.__name__}",
                expected_type="BaseEntity",
                actual_type=entity_type.__name__,
            )

        try:
            session = self.get_session()
            result = session.get(entity_type, entity_uuid)
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

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
        if not isinstance(entity, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
                expected_type="BaseEntity",
                actual_type=type(entity).__name__,
            )

        try:
            session = self.get_session()
            session.delete(entity)
            session.flush()
        except Exception as e:
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
        if not all(isinstance(entity, BaseEntity) for entity in entities):
            raise InvalidEntityTypeError(
                message="All entities must be BaseEntity subclasses",
                expected_type="BaseEntity",
                actual_type="mixed",
            )

        try:
            session = self.get_session()
            for entity in entities:
                session.delete(entity)
            session.flush()
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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

    def __init__(self, orm_config: ConfigT | None = None) -> None:
        """Initialize the base async adapter with a session manager.

        Args:
            orm_config: Configuration for SQLAlchemy. If None, uses global config.
        """
        configs = BaseConfig.global_config().SQLALCHEMY if orm_config is None else orm_config
        # Cast to ConfigT since subclasses will ensure the proper type
        self.session_manager: AsyncBaseSQLAlchemySessionManager[ConfigT] = self._create_async_session_manager(configs)  # type: ignore[arg-type]

    def _create_async_session_manager(self, configs: ConfigT) -> AsyncBaseSQLAlchemySessionManager[ConfigT]:
        """Create an async session manager for the specific database.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            An async session manager instance.
        """
        raise NotImplementedError("Subclasses must implement _create_async_session_manager")

    @override
    async def execute_search_query(
        self,
        entity: type[T],
        query: Select,
        pagination: PaginationDTO | None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
    ) -> tuple[list[T], int]:
        """Execute a search query with pagination and sorting.

        Args:
            entity: The entity class to query.
            query: The SQLAlchemy SELECT query.
            pagination: Optional pagination settings.
            sort_info: Optional sorting information.
            has_multiple_entities: Optional bool

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
            if has_multiple_entities:
                results = list(result_set.fetchall())
            else:
                results = list(result_set.scalars().all())
            count_query = select(func.count()).select_from(query.subquery())
            total_count_result = await session.execute(count_query)
            total_count = total_count_result.scalar_one()
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return results, total_count  # type: ignore[return-value]

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
        if not isinstance(entity, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
                expected_type="BaseEntity",
                actual_type=type(entity).__name__,
            )

        try:
            session = self.get_session()
            session.add(entity)
            await session.flush()
        except Exception as e:
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
        if not all(isinstance(entity, BaseEntity) for entity in entities):
            raise InvalidEntityTypeError(
                message="All entities must be BaseEntity subclasses",
                expected_type="BaseEntity",
                actual_type="mixed",
            )

        try:
            session = self.get_session()
            session.add_all(entities)
            await session.flush()
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return entities

    @override
    async def get_by_uuid(self, entity_type: type[T], entity_uuid: UUID) -> T | None:
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
        if not issubclass(entity_type, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {entity_type.__name__}",
                expected_type="BaseEntity",
                actual_type=entity_type.__name__,
            )

        try:
            session = self.get_session()
            result = await session.get(entity_type, entity_uuid)
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

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
        if not isinstance(entity, BaseEntity):
            raise InvalidEntityTypeError(
                message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
                expected_type="BaseEntity",
                actual_type=type(entity).__name__,
            )

        try:
            session = self.get_session()
            await session.delete(entity)
            await session.flush()
        except Exception as e:
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
        if not all(isinstance(entity, BaseEntity) for entity in entities):
            raise InvalidEntityTypeError(
                message="All entities must be BaseEntity subclasses",
                expected_type="BaseEntity",
                actual_type="mixed",
            )

        try:
            session = self.get_session()
            for entity in entities:
                await session.delete(entity)
            await session.flush()
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
            self._handle_db_exception(e, self.session_manager._get_database_name())
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result
