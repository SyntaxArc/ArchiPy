from abc import abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, List, Optional, Type
from uuid import UUID

from sqlalchemy import Executable, Select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from archipy.models.dtos import PaginationDTO, SortDTO
from archipy.models.entities import BaseEntity

_CoreSingleExecuteParams = Mapping[str, Any]
_CoreMultiExecuteParams = Sequence[_CoreSingleExecuteParams]
AnyExecuteParams = _CoreMultiExecuteParams | _CoreSingleExecuteParams


class SqlAlchemyPort:
    @abstractmethod
    def get_session(self) -> Session:
        raise NotImplementedError

    @abstractmethod
    def execute_search_query(
        self,
        entity: Type[BaseEntity],
        query: Select,
        pagination: PaginationDTO | None = None,
        sort_info: SortDTO | None = SortDTO.default(),
    ) -> tuple[list[BaseEntity], int]:
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: BaseEntity) -> BaseEntity | None:
        raise NotImplementedError

    @abstractmethod
    def bulk_create(self, entities: list[BaseEntity]) -> list[BaseEntity] | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_uuid(self, entity_type: type, entity_uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity: BaseEntity) -> None:
        raise NotImplementedError

    @abstractmethod
    def bulk_delete(self, entities: list[BaseEntity]) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute(self, statement: Executable, params: AnyExecuteParams | None = None):
        raise NotImplementedError

    @abstractmethod
    def scalars(self, statement: Executable, params: AnyExecuteParams | None = None):
        raise NotImplementedError


class AsyncSqlAlchemyPort:
    @abstractmethod
    def get_session(self) -> AsyncSession:
        raise NotImplementedError

    @abstractmethod
    async def execute_search_query(
        self,
        entity: Type[BaseEntity],
        query: Select,
        pagination: PaginationDTO | None,
        sort_info: SortDTO | None = SortDTO.default(),
    ) -> tuple[list[BaseEntity], int]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, entity: BaseEntity) -> Optional[BaseEntity]:
        raise NotImplementedError

    @abstractmethod
    async def bulk_create(self, entities: List[BaseEntity]) -> Optional[List[BaseEntity]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_uuid(self, entity_type: type, entity_uuid: UUID):
        raise NotImplementedError

    @abstractmethod
    async def delete(self, entity: BaseEntity) -> None:
        raise NotImplementedError

    @abstractmethod
    async def bulk_delete(self, entities: List[BaseEntity]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, statement, params: Optional[dict] = None):
        raise NotImplementedError

    @abstractmethod
    async def scalars(self, statement, params: Optional[dict] = None):
        raise NotImplementedError
