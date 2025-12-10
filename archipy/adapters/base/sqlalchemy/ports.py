from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import Executable, Result, ScalarResult, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from archipy.models.dtos.pagination_dto import PaginationDTO
from archipy.models.dtos.sort_dto import SortDTO
from archipy.models.entities import BaseEntity

_CoreSingleExecuteParams = Mapping[str, Any]
_CoreMultiExecuteParams = Sequence[_CoreSingleExecuteParams]
AnyExecuteParams = _CoreMultiExecuteParams | _CoreSingleExecuteParams


class SQLAlchemyPort:
    """Abstract interface defining synchronous SQLAlchemy database operations.

    This interface defines the contract that all synchronous SQLAlchemy adapters must
    implement, providing standard methods for database operations like create,
    read, update, delete (CRUD), as well as search and transaction management.

    Implementations of this interface are responsible for handling the specific
    details of database interactions and connection management.
    """

    @abstractmethod
    def get_session(self) -> Session:
        """Retrieves a SQLAlchemy session for database operations.

        Returns:
            Session: A SQLAlchemy session object
        """
        raise NotImplementedError

    @abstractmethod
    def execute_search_query(
        self,
        entity: type[BaseEntity],
        query: Select,
        pagination: PaginationDTO | None = None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
    ) -> tuple[list[BaseEntity], int]:
        """Executes a search query with pagination and sorting.

        Args:
            entity: The entity class to query
            query: The SQLAlchemy SELECT query
            pagination: Optional pagination settings
            sort_info: Optional sorting information
            has_multiple_entities: Optional bool.

        Returns:
            A tuple containing the list of entities and the total count
        """
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: BaseEntity) -> BaseEntity | None:
        """Creates a new entity in the database.

        Args:
            entity: The entity to create

        Returns:
            The created entity (with updated attributes) or None if creation failed
        """
        raise NotImplementedError

    @abstractmethod
    def bulk_create(self, entities: list[BaseEntity]) -> list[BaseEntity] | None:
        """Creates multiple entities in the database.

        Args:
            entities: List of entities to create

        Returns:
            The list of created entities or None if creation failed
        """
        raise NotImplementedError

    @abstractmethod
    def get_by_uuid(self, entity_type: type[BaseEntity], entity_uuid: UUID) -> BaseEntity | None:
        """Retrieves an entity by its UUID.

        Args:
            entity_type: The type of entity to retrieve
            entity_uuid: The UUID of the entity

        Returns:
            The entity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity: BaseEntity) -> None:
        """Deletes an entity from the database.

        Args:
            entity: The entity to delete
        """
        raise NotImplementedError

    @abstractmethod
    def bulk_delete(self, entities: list[BaseEntity]) -> None:
        """Deletes multiple entities from the database.

        Args:
            entities: List of entities to delete
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, statement: Executable, params: AnyExecuteParams | None = None) -> Result[Any]:
        """Executes a raw SQL statement.

        Args:
            statement: The SQL statement to execute
            params: Optional parameters for the SQL statement

        Returns:
            The result of the execution
        """
        raise NotImplementedError

    @abstractmethod
    def scalars(self, statement: Executable, params: AnyExecuteParams | None = None) -> ScalarResult[Any]:
        """Executes a statement and returns the scalar result.

        Args:
            statement: The SQL statement to execute
            params: Optional parameters for the SQL statement

        Returns:
            The scalar result of the execution
        """
        raise NotImplementedError


class AsyncSQLAlchemyPort:
    """Abstract interface defining asynchronous SQLAlchemy database operations.

    This interface defines the contract that all asynchronous SQLAlchemy adapters must
    implement, providing standard methods for database operations like create,
    read, update, delete (CRUD), as well as search and transaction management.

    Implementations of this interface are responsible for handling the specific
    details of asynchronous database interactions and connection management.
    """

    @abstractmethod
    def get_session(self) -> AsyncSession:
        """Retrieves an asynchronous SQLAlchemy session for database operations.

        Returns:
            AsyncSession: An asynchronous SQLAlchemy session object
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_search_query(
        self,
        entity: type[BaseEntity],
        query: Select,
        pagination: PaginationDTO | None,
        sort_info: SortDTO | None = None,
        has_multiple_entities: bool = False,
    ) -> tuple[list[BaseEntity], int]:
        """Executes a search query with pagination and sorting asynchronously.

        Args:
            entity: The entity class to query
            query: The SQLAlchemy SELECT query
            pagination: Optional pagination settings
            sort_info: Optional sorting information
            has_multiple_entities: Optional bool

        Returns:
            A tuple containing the list of entities and the total count
        """
        raise NotImplementedError

    @abstractmethod
    async def create(self, entity: BaseEntity) -> BaseEntity | None:
        """Creates a new entity in the database asynchronously.

        Args:
            entity: The entity to create

        Returns:
            The created entity (with updated attributes) or None if creation failed
        """
        raise NotImplementedError

    @abstractmethod
    async def bulk_create(self, entities: list[BaseEntity]) -> list[BaseEntity] | None:
        """Creates multiple entities in the database asynchronously.

        Args:
            entities: List of entities to create

        Returns:
            The list of created entities or None if creation failed
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_uuid(self, entity_type: type[BaseEntity], entity_uuid: UUID) -> BaseEntity | None:
        """Retrieves an entity by its UUID asynchronously.

        Args:
            entity_type: The type of entity to retrieve
            entity_uuid: The UUID of the entity

        Returns:
            The entity if found, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity: BaseEntity) -> None:
        """Deletes an entity from the database asynchronously.

        Args:
            entity: The entity to delete
        """
        raise NotImplementedError

    @abstractmethod
    async def bulk_delete(self, entities: list[BaseEntity]) -> None:
        """Deletes multiple entities from the database asynchronously.

        Args:
            entities: List of entities to delete
        """
        raise NotImplementedError

    @abstractmethod
    async def execute(self, statement: Executable, params: AnyExecuteParams | None = None) -> Result[Any]:
        """Executes a raw SQL statement asynchronously.

        Args:
            statement: The SQL statement to execute
            params: Optional parameters for the SQL statement

        Returns:
            The result of the execution
        """
        raise NotImplementedError

    @abstractmethod
    async def scalars(self, statement: Executable, params: AnyExecuteParams | None = None) -> ScalarResult[Any]:
        """Executes a statement and returns the scalar result asynchronously.

        Args:
            statement: The SQL statement to execute
            params: Optional parameters for the SQL statement

        Returns:
            The scalar result of the execution
        """
        raise NotImplementedError
