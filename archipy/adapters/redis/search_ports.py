from __future__ import annotations

from abc import abstractmethod
from typing import Any

from archipy.models.dtos.redis.search.aggregation_dto import AggregationDTO
from archipy.models.dtos.redis.search.document_dto import HashDocumentUpsertDTO, JsonDocumentUpsertDTO
from archipy.models.dtos.redis.search.index_schema_dto import IndexFieldConfig, IndexSchemaDTO
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO
from archipy.models.dtos.redis.search.search_result_dto import SearchResultDTO
from archipy.models.types.redis_search_types import RedisIndexType


class RedisSearchHandlePort:
    """Index-bound RediSearch operations contract."""

    @abstractmethod
    def create_index(
        self,
        schema: IndexSchemaDTO,
        prefix: str,
        index_type: RedisIndexType | None = None,
        **kwargs: Any,
    ) -> bool:
        """Create a RediSearch index."""
        raise NotImplementedError

    @abstractmethod
    def drop_index(self, delete_documents: bool = False) -> bool:
        """Drop the RediSearch index."""
        raise NotImplementedError

    @abstractmethod
    def info(self) -> dict[str, Any]:
        """Return index metadata."""
        raise NotImplementedError

    @abstractmethod
    def alter_schema_add(
        self,
        fields: IndexFieldConfig | list[IndexFieldConfig],
        *,
        index_type: RedisIndexType | None = None,
    ) -> bool:
        """Add fields to an existing index schema."""
        raise NotImplementedError

    @abstractmethod
    def upsert_hash(
        self,
        doc_id: str,
        fields: dict[str, str | int | float],
        vector_field: str | None = None,
        vector: list[float] | None = None,
        *,
        replace: bool = True,
    ) -> bool:
        """Upsert a HASH document and index it."""
        raise NotImplementedError

    @abstractmethod
    def upsert_hash_dto(self, document: HashDocumentUpsertDTO, *, replace: bool = True) -> bool:
        """Upsert a HASH document from a DTO."""
        raise NotImplementedError

    @abstractmethod
    def upsert_json(
        self,
        doc_id: str,
        payload: dict[str, str | int | float | list[float]],
        json_path: str = "$",
    ) -> bool:
        """Upsert a JSON document."""
        raise NotImplementedError

    @abstractmethod
    def upsert_json_dto(self, document: JsonDocumentUpsertDTO) -> bool:
        """Upsert a JSON document from a DTO."""
        raise NotImplementedError

    @abstractmethod
    def get_document(self, doc_id: str) -> dict[str, Any]:
        """Load a document by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete_document(self, doc_id: str, *, delete_actual_document: bool = True) -> int:
        """Remove a document from the index."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query: SearchQueryDTO, **kwargs: Any) -> SearchResultDTO:
        """Execute a RediSearch query (text, KNN, or hybrid)."""
        raise NotImplementedError

    @abstractmethod
    def aggregate(self, aggregation: AggregationDTO, **kwargs: Any) -> dict[str, Any]:
        """Execute a RediSearch aggregation."""
        raise NotImplementedError

    @abstractmethod
    def add_alias(self, alias: str) -> bool:
        """Add an alias for the index."""
        raise NotImplementedError

    @abstractmethod
    def update_alias(self, alias: str) -> bool:
        """Update an alias to point to this index."""
        raise NotImplementedError

    @abstractmethod
    def delete_alias(self, alias: str) -> bool:
        """Delete an alias."""
        raise NotImplementedError


class AsyncRedisSearchHandlePort:
    """Asynchronous index-bound RediSearch operations contract."""

    @abstractmethod
    async def create_index(
        self,
        schema: IndexSchemaDTO,
        prefix: str,
        index_type: RedisIndexType | None = None,
        **kwargs: Any,
    ) -> bool:
        """Create a RediSearch index asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def drop_index(self, delete_documents: bool = False) -> bool:
        """Drop the RediSearch index asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def info(self) -> dict[str, Any]:
        """Return index metadata asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def alter_schema_add(
        self,
        fields: IndexFieldConfig | list[IndexFieldConfig],
        *,
        index_type: RedisIndexType | None = None,
    ) -> bool:
        """Add fields to an existing index schema asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_hash(
        self,
        doc_id: str,
        fields: dict[str, str | int | float],
        vector_field: str | None = None,
        vector: list[float] | None = None,
        *,
        replace: bool = True,
    ) -> bool:
        """Upsert a HASH document and index it asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_hash_dto(self, document: HashDocumentUpsertDTO, *, replace: bool = True) -> bool:
        """Upsert a HASH document from a DTO asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_json(
        self,
        doc_id: str,
        payload: dict[str, str | int | float | list[float]],
        json_path: str = "$",
    ) -> bool:
        """Upsert a JSON document asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def upsert_json_dto(self, document: JsonDocumentUpsertDTO) -> bool:
        """Upsert a JSON document from a DTO asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def get_document(self, doc_id: str) -> dict[str, Any]:
        """Load a document by ID asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def delete_document(self, doc_id: str, *, delete_actual_document: bool = True) -> int:
        """Remove a document from the index asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def search(self, query: SearchQueryDTO, **kwargs: Any) -> SearchResultDTO:
        """Execute a RediSearch query asynchronously (text, KNN, or hybrid)."""
        raise NotImplementedError

    @abstractmethod
    async def aggregate(self, aggregation: AggregationDTO, **kwargs: Any) -> dict[str, Any]:
        """Execute a RediSearch aggregation asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def add_alias(self, alias: str) -> bool:
        """Add an alias for the index asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def update_alias(self, alias: str) -> bool:
        """Update an alias to point to this index asynchronously."""
        raise NotImplementedError

    @abstractmethod
    async def delete_alias(self, alias: str) -> bool:
        """Delete an alias asynchronously."""
        raise NotImplementedError
