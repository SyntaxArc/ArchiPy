from __future__ import annotations

import struct
from collections.abc import Awaitable
from typing import Any, cast, override

from redis.asyncio.client import Redis as AsyncRedis
from redis.client import Redis
from redis.commands.search import Search
from redis.commands.search.aggregation import AggregateRequest, Asc, Desc
from redis.commands.search.field import NumericField, TagField, TextField, VectorField
from redis.commands.search.hybrid_query import HybridQuery, HybridSearchQuery, HybridVsimQuery, VectorSearchMethods
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.commands.search.reducers import count as agg_count
from redis.commands.search.result import Result

from archipy.adapters.redis.search_ports import AsyncRedisSearchHandlePort, RedisSearchHandlePort
from archipy.models.dtos.redis.search.aggregation_dto import AggregationDTO
from archipy.models.dtos.redis.search.document_dto import HashDocumentUpsertDTO, JsonDocumentUpsertDTO
from archipy.models.dtos.redis.search.index_schema_dto import (
    IndexFieldConfig,
    IndexSchemaDTO,
    NumericFieldConfig,
    TagFieldConfig,
    TextFieldConfig,
    VectorFieldConfig,
)
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO
from archipy.models.dtos.redis.search.search_result_dto import SearchHitDTO, SearchResultDTO
from archipy.models.types.redis_search_types import RedisIndexType


def pack_vector(vector: list[float]) -> bytes:
    """Pack a float vector into float32 little-endian bytes for RediSearch.

    Args:
        vector: Embedding values.

    Returns:
        Binary blob suitable for Redis VECTOR fields and KNN params.
    """
    return struct.pack(f"{len(vector)}f", *vector)


def unpack_vector(blob: bytes, dim: int) -> list[float]:
    """Unpack float32 little-endian bytes into a vector.

    Args:
        blob: Binary vector data from Redis.
        dim: Expected vector dimensionality.

    Returns:
        Decoded embedding values.
    """
    return list(struct.unpack(f"{dim}f", blob))


def _build_redis_fields(
    fields: list[IndexFieldConfig],
    *,
    index_type: RedisIndexType | None = None,
) -> list[Any]:
    """Convert DTO field configs into redis-py Field objects."""
    is_json = index_type == RedisIndexType.JSON
    redis_fields: list[Any] = []
    for field in fields:
        field_name = f"$.{field.name}" if is_json else field.name
        as_name = field.name if is_json else None
        match field:
            case TextFieldConfig():
                redis_fields.append(TextField(field_name, as_name=as_name))
            case TagFieldConfig():
                if field.separator is not None:
                    redis_fields.append(TagField(field_name, separator=field.separator, as_name=as_name))
                else:
                    redis_fields.append(TagField(field_name, as_name=as_name))
            case NumericFieldConfig():
                redis_fields.append(NumericField(field_name, as_name=as_name))
            case VectorFieldConfig():
                redis_fields.append(
                    VectorField(
                        field_name,
                        field.algorithm.value,
                        {
                            "TYPE": "FLOAT32",
                            "DIM": field.dim,
                            "DISTANCE_METRIC": field.distance_metric.value,
                        },
                        as_name=as_name,
                    ),
                )
    return redis_fields


def _resolve_index_type(index_type: RedisIndexType) -> IndexType:
    """Map ArchiPy index type enum to redis-py IndexType."""
    if index_type == RedisIndexType.JSON:
        return IndexType.JSON
    return IndexType.HASH


def _document_fields(document: Any) -> dict[str, Any]:
    """Extract document fields from a redis-py Document object."""
    fields: dict[str, Any] = {}
    for key, value in document.__dict__.items():
        if key in {"id", "payload"}:
            continue
        fields[key] = value
    return fields


def _normalize_key_type(key_type: Any) -> str:
    """Normalize a Redis TYPE response to a string."""
    return key_type.decode() if isinstance(key_type, bytes) else str(key_type)


def _normalize_json_payload(payload: Any) -> dict[str, Any]:
    """Normalize a RedisJSON root-path response into a document dict."""
    if isinstance(payload, list):
        payload = payload[0] if payload else {}
    return payload if isinstance(payload, dict) else {}


def _normalize_info_value(value: Any) -> Any:
    """Recursively normalize FT.INFO values to Python strings where applicable."""
    if isinstance(value, bytes):
        return value.decode()
    if isinstance(value, list):
        return [_normalize_info_value(item) for item in value]
    if isinstance(value, dict):
        return _normalize_info_dict(value)
    return value


def _normalize_info_dict(info: dict[Any, Any]) -> dict[str, Any]:
    """Normalize FT.INFO mapping keys and nested values to string-friendly shapes."""
    normalized: dict[str, Any] = {}
    for key, value in info.items():
        norm_key = key.decode() if isinstance(key, bytes) else str(key)
        normalized[norm_key] = _normalize_info_value(value)
    return normalized


def _index_type_from_info(info: dict[str, Any]) -> RedisIndexType | None:
    """Resolve RedisIndexType from an FT.INFO response."""
    definition = info.get("index_definition")
    if isinstance(definition, dict):
        key_type = definition.get("key_type") or definition.get("type")
        if key_type == "JSON":
            return RedisIndexType.JSON
        if key_type == "HASH":
            return RedisIndexType.HASH
    if isinstance(definition, (list, tuple)):
        decoded = [str(item) for item in definition]
        if "JSON" in decoded:
            return RedisIndexType.JSON
        if "HASH" in decoded:
            return RedisIndexType.HASH
    for attribute in info.get("attributes", []):
        identifier: str | None = None
        if isinstance(attribute, dict):
            raw_identifier = attribute.get("identifier")
            identifier = str(raw_identifier) if raw_identifier is not None else None
        elif isinstance(attribute, (list, tuple)):
            decoded = [str(item) for item in attribute]
            if "identifier" in decoded:
                identifier = decoded[decoded.index("identifier") + 1]
        if identifier and identifier.startswith("$."):
            return RedisIndexType.JSON
    return None


def _normalize_search_field_name(name: str) -> str:
    """Normalize a logical field name for RediSearch query construction."""
    return name.lstrip("@")


def _normalize_search_field_ref(name: str) -> str:
    """Normalize a field reference used in RediSearch aggregation/sort clauses."""
    field = _normalize_search_field_name(name)
    return field if field.startswith("@") else f"@{field}"


def _result_to_dto(result: Any) -> SearchResultDTO:
    """Convert a redis-py search Result into a SearchResultDTO."""
    hits: list[SearchHitDTO] = []
    if isinstance(result, dict):
        result = Result.from_resp3(result)
    for document in result.docs:
        score = getattr(document, "score", None)
        fields = _document_fields(document)
        hits.append(
            SearchHitDTO(
                doc_id=str(document.id),
                score=float(score) if score is not None else None,
                fields=fields,
            ),
        )
    return SearchResultDTO(
        total=int(result.total),
        hits=hits,
        duration_ms=float(result.duration) if getattr(result, "duration", None) is not None else None,
        warnings=list(getattr(result, "warnings", []) or []),
    )


def _hybrid_result_to_dto(result: Any) -> SearchResultDTO:
    """Convert a redis-py hybrid search result into a SearchResultDTO."""
    hits: list[SearchHitDTO] = []
    if isinstance(result, dict):
        result = Result.from_resp3(result)
    for document in result.docs:
        fields = _document_fields(document)
        score = fields.pop("score", None) or fields.pop("vector_score", None)
        hits.append(
            SearchHitDTO(
                doc_id=str(document.id),
                score=float(score) if score is not None else None,
                fields=fields,
            ),
        )
    return SearchResultDTO(total=len(hits), hits=hits)


def _build_search_query(
    query: SearchQueryDTO,
) -> tuple[Query, dict[str, str | int | float | bytes] | None]:
    """Build a redis-py Query and optional query params from a SearchQueryDTO."""
    if query.knn is not None:
        knn = query.knn
        filter_part = f"({knn.filter_expr})" if knn.filter_expr else "*"
        vector_field = _normalize_search_field_name(knn.vector_field)
        query_string = f"{filter_part}=>[KNN {knn.k} @{vector_field} $vec AS {knn.score_field}]"
        redis_query = Query(query_string).sort_by(knn.score_field).paging(0, knn.k).dialect(2)
        if knn.return_fields:
            redis_query = redis_query.return_fields(
                *[_normalize_search_field_name(field) for field in knn.return_fields],
            )
        return redis_query, {"vec": pack_vector(knn.vector)}

    redis_query = Query(query.query).paging(query.offset, query.limit).dialect(2)
    if query.return_fields:
        redis_query = redis_query.return_fields(
            *[_normalize_search_field_name(field) for field in query.return_fields],
        )
    return redis_query, None


def _build_aggregate_request(aggregation: AggregationDTO) -> AggregateRequest:
    """Build a redis-py AggregateRequest from an AggregationDTO."""
    request = AggregateRequest(aggregation.query)
    if aggregation.group_by:
        reducers = []
        if aggregation.reduce_function == "COUNT":
            alias = aggregation.reduce_field or "count"
            reducers.append(agg_count().alias(alias))
        group_by = [_normalize_search_field_ref(field) for field in aggregation.group_by]
        request.group_by(group_by, *reducers)
    if aggregation.sort_by:
        sort_field = _normalize_search_field_ref(aggregation.sort_by)
        sort_cls = Asc if aggregation.sort_direction.upper() == "ASC" else Desc
        request.sort_by(sort_cls(sort_field))  # ty: ignore[invalid-argument-type]
    if aggregation.limit is not None:
        request.limit(0, aggregation.limit)
    return request


def _build_hybrid_query(query: SearchQueryDTO) -> tuple[HybridQuery, dict[str, str | int | float | bytes]]:
    """Build a redis-py HybridQuery from a hybrid SearchQueryDTO."""
    if query.knn is None:
        raise ValueError("Hybrid search requires knn parameters")
    knn = query.knn
    text_query = HybridSearchQuery(query.query, scorer=query.text_scorer)
    vsim_params: dict[str, Any] = {"K": knn.k}
    vector_field = _normalize_search_field_ref(knn.vector_field)
    vector_query = HybridVsimQuery(
        vector_field,
        "$vec",
        vsim_search_method=VectorSearchMethods.KNN,
        vsim_search_method_params=vsim_params,
    )
    return HybridQuery(text_query, vector_query), {"vec": pack_vector(knn.vector)}


def _write_hash_document(
    client: Redis,
    doc_id: str,
    fields: dict[str, str | int | float],
    vector_field: str | None,
    vector: list[float] | None,
) -> None:
    """Write HASH fields and optional vector bytes to Redis."""
    for key, value in fields.items():
        client.hset(doc_id, key, value)
    if vector_field is not None and vector is not None:
        client.hset(doc_id, vector_field, pack_vector(vector))


class RedisSearchHandle(RedisSearchHandlePort):
    """Synchronous index-bound RediSearch handle."""

    def __init__(self, client: Redis, index_name: str) -> None:
        """Initialize the handle.

        Args:
            client: Binary-safe Redis client (`decode_responses=False`).
            index_name: RediSearch index name.
        """
        self._client = client
        self._index_name = index_name
        self._search = Search(client, index_name)
        self._index_type: RedisIndexType | None = None

    def _effective_index_type(self) -> RedisIndexType | None:
        """Return the cached index type or resolve it from FT.INFO."""
        if self._index_type is not None:
            return self._index_type
        resolved = _index_type_from_info(_normalize_info_dict(dict(self._search.info())))
        if resolved is not None:
            self._index_type = resolved
        return resolved

    @override
    def create_index(
        self,
        schema: IndexSchemaDTO,
        prefix: str,
        index_type: RedisIndexType | None = None,
        **kwargs: Any,
    ) -> bool:
        """Create a RediSearch index."""
        resolved_type = index_type or schema.index_type
        self._index_type = resolved_type
        definition = IndexDefinition(prefix=[prefix], index_type=_resolve_index_type(resolved_type))
        return bool(
            self._search.create_index(
                _build_redis_fields(schema.fields, index_type=resolved_type),
                definition=definition,
                **kwargs,
            ),
        )

    @override
    def drop_index(self, delete_documents: bool = False) -> bool:
        """Drop the RediSearch index."""
        return bool(self._search.dropindex(delete_documents=delete_documents))

    @override
    def info(self) -> dict[str, Any]:
        """Return index metadata."""
        return _normalize_info_dict(dict(self._search.info()))

    @override
    def alter_schema_add(
        self,
        fields: IndexFieldConfig | list[IndexFieldConfig],
        *,
        index_type: RedisIndexType | None = None,
    ) -> bool:
        """Add fields to an existing index schema."""
        field_list = fields if isinstance(fields, list) else [fields]
        resolved_type = index_type or self._index_type or self._effective_index_type()
        redis_fields = _build_redis_fields(field_list, index_type=resolved_type)
        if len(redis_fields) == 1:
            return bool(self._search.alter_schema_add(redis_fields[0]))
        return bool(self._search.alter_schema_add(redis_fields))

    @override
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
        _write_hash_document(self._client, doc_id, fields, vector_field, vector)
        return True

    @override
    def upsert_hash_dto(self, document: HashDocumentUpsertDTO, *, replace: bool = True) -> bool:
        """Upsert a HASH document from a DTO."""
        return self.upsert_hash(
            document.doc_id,
            document.fields,
            vector_field=document.vector_field,
            vector=document.vector,
            replace=replace,
        )

    @override
    def upsert_json(
        self,
        doc_id: str,
        payload: dict[str, str | int | float | list[float]],
        json_path: str = "$",
    ) -> bool:
        """Upsert a JSON document."""
        self._client.json().set(doc_id, json_path, payload)
        return True

    @override
    def upsert_json_dto(self, document: JsonDocumentUpsertDTO) -> bool:
        """Upsert a JSON document from a DTO."""
        return self.upsert_json(document.doc_id, document.payload, document.json_path)

    @override
    def get_document(self, doc_id: str) -> dict[str, Any]:
        """Load a document by ID."""
        key_type = _normalize_key_type(self._client.type(doc_id))
        if key_type == "ReJSON-RL":
            payload = _normalize_json_payload(self._client.json().get(doc_id, "$"))
            return {"id": doc_id, **payload}
        document = self._search.load_document(doc_id)
        return {"id": document.id, **_document_fields(document)}

    @override
    def delete_document(self, doc_id: str, *, delete_actual_document: bool = True) -> int:
        """Remove a document from the index."""
        return int(self._search.delete_document(doc_id, delete_actual_document=delete_actual_document))

    @override
    def search(self, query: SearchQueryDTO, **kwargs: Any) -> SearchResultDTO:
        """Execute a RediSearch query."""
        if query.is_hybrid:
            hybrid_query, hybrid_params = _build_hybrid_query(query)
            if kwargs.pop("raw", False):
                return cast(
                    "SearchResultDTO",
                    self._search.hybrid_search(hybrid_query, params_substitution=hybrid_params, **kwargs),
                )
            result = self._search.hybrid_search(hybrid_query, params_substitution=hybrid_params, **kwargs)
            return _hybrid_result_to_dto(result)

        redis_query, query_params = _build_search_query(query)
        if kwargs.pop("raw", False):
            return cast("SearchResultDTO", self._search.search(redis_query, query_params=query_params, **kwargs))
        result = self._search.search(redis_query, query_params=query_params, **kwargs)
        return _result_to_dto(result)

    @override
    def aggregate(self, aggregation: AggregationDTO, **kwargs: Any) -> dict[str, Any]:
        """Execute a RediSearch aggregation."""
        request = _build_aggregate_request(aggregation)
        if kwargs.pop("raw", False):
            return cast("dict[str, Any]", self._search.aggregate(request, **kwargs))
        result = self._search.aggregate(request, **kwargs)
        if isinstance(result, dict):
            norm = {k.decode() if isinstance(k, bytes) else k: v for k, v in result.items()}
            return {
                "total": norm.get("total_results", 0),
                "rows": [row.get("extra_attributes", row) for row in norm.get("results", [])],
            }
        return {"total": result.total, "rows": result.rows}

    @override
    def add_alias(self, alias: str) -> bool:
        """Add an alias for the index."""
        return bool(self._search.aliasadd(alias))

    @override
    def update_alias(self, alias: str) -> bool:
        """Update an alias to point to this index."""
        return bool(self._search.aliasupdate(alias))

    @override
    def delete_alias(self, alias: str) -> bool:
        """Delete an alias."""
        return bool(self._search.aliasdel(alias))


class AsyncRedisSearchHandle(AsyncRedisSearchHandlePort):
    """Asynchronous index-bound RediSearch handle."""

    def __init__(self, client: AsyncRedis, index_name: str) -> None:
        """Initialize the async handle.

        Args:
            client: Binary-safe async Redis client (`decode_responses=False`).
            index_name: RediSearch index name.
        """
        self._client = client
        self._index_name = index_name
        self._search = Search(client, index_name)
        self._index_type: RedisIndexType | None = None

    async def _effective_index_type(self) -> RedisIndexType | None:
        """Return the cached index type or resolve it from FT.INFO asynchronously."""
        if self._index_type is not None:
            return self._index_type
        info = await self._await_result(self._search.info())
        resolved = _index_type_from_info(_normalize_info_dict(dict(info)))
        if resolved is not None:
            self._index_type = resolved
        return resolved

    async def _await_result(self, value: Any) -> Any:
        """Await a result when the underlying client returns a coroutine."""
        if isinstance(value, Awaitable):
            return await value
        return value

    @override
    async def create_index(
        self,
        schema: IndexSchemaDTO,
        prefix: str,
        index_type: RedisIndexType | None = None,
        **kwargs: Any,
    ) -> bool:
        """Create a RediSearch index asynchronously."""
        resolved_type = index_type or schema.index_type
        self._index_type = resolved_type
        definition = IndexDefinition(prefix=[prefix], index_type=_resolve_index_type(resolved_type))
        result = await self._await_result(
            self._search.create_index(
                _build_redis_fields(schema.fields, index_type=resolved_type),
                definition=definition,
                **kwargs,
            ),
        )
        return bool(result)

    @override
    async def drop_index(self, delete_documents: bool = False) -> bool:
        """Drop the RediSearch index asynchronously."""
        result = await self._await_result(self._search.dropindex(delete_documents=delete_documents))
        return bool(result)

    @override
    async def info(self) -> dict[str, Any]:
        """Return index metadata asynchronously."""
        result = await self._await_result(self._search.info())
        return _normalize_info_dict(dict(result))

    @override
    async def alter_schema_add(
        self,
        fields: IndexFieldConfig | list[IndexFieldConfig],
        *,
        index_type: RedisIndexType | None = None,
    ) -> bool:
        """Add fields to an existing index schema asynchronously."""
        field_list = fields if isinstance(fields, list) else [fields]
        resolved_type = index_type or self._index_type or await self._effective_index_type()
        redis_fields = _build_redis_fields(field_list, index_type=resolved_type)
        if len(redis_fields) == 1:
            result = await self._await_result(self._search.alter_schema_add(redis_fields[0]))
        else:
            result = await self._await_result(self._search.alter_schema_add(redis_fields))
        return bool(result)

    @override
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
        for key, value in fields.items():
            await self._client.hset(doc_id, key, value)
        if vector_field is not None and vector is not None:
            await self._client.hset(doc_id, vector_field, pack_vector(vector))
        return True

    @override
    async def upsert_hash_dto(self, document: HashDocumentUpsertDTO, *, replace: bool = True) -> bool:
        """Upsert a HASH document from a DTO asynchronously."""
        return await self.upsert_hash(
            document.doc_id,
            document.fields,
            vector_field=document.vector_field,
            vector=document.vector,
            replace=replace,
        )

    @override
    async def upsert_json(
        self,
        doc_id: str,
        payload: dict[str, str | int | float | list[float]],
        json_path: str = "$",
    ) -> bool:
        """Upsert a JSON document asynchronously."""
        await self._client.json().set(doc_id, json_path, payload)
        return True

    @override
    async def upsert_json_dto(self, document: JsonDocumentUpsertDTO) -> bool:
        """Upsert a JSON document from a DTO asynchronously."""
        return await self.upsert_json(document.doc_id, document.payload, document.json_path)

    @override
    async def get_document(self, doc_id: str) -> dict[str, Any]:
        """Load a document by ID asynchronously."""
        key_type = _normalize_key_type(await self._client.type(doc_id))
        if key_type == "ReJSON-RL":
            payload = _normalize_json_payload(await self._await_result(self._client.json().get(doc_id, "$")))
            return {"id": doc_id, **payload}
        document = await self._await_result(self._search.load_document(doc_id))
        return {"id": document.id, **_document_fields(document)}

    @override
    async def delete_document(self, doc_id: str, *, delete_actual_document: bool = True) -> int:
        """Remove a document from the index asynchronously."""
        result = await self._await_result(
            self._search.delete_document(doc_id, delete_actual_document=delete_actual_document),
        )
        return int(result)

    @override
    async def search(self, query: SearchQueryDTO, **kwargs: Any) -> SearchResultDTO:
        """Execute a RediSearch query asynchronously."""
        if query.is_hybrid:
            hybrid_query, hybrid_params = _build_hybrid_query(query)
            if kwargs.pop("raw", False):
                return cast(
                    "SearchResultDTO",
                    await self._await_result(
                        self._search.hybrid_search(hybrid_query, params_substitution=hybrid_params, **kwargs),
                    ),
                )
            result = await self._await_result(
                self._search.hybrid_search(hybrid_query, params_substitution=hybrid_params, **kwargs),
            )
            return _hybrid_result_to_dto(result)

        redis_query, query_params = _build_search_query(query)
        if kwargs.pop("raw", False):
            return cast(
                "SearchResultDTO",
                await self._await_result(self._search.search(redis_query, query_params=query_params, **kwargs)),
            )
        result = await self._await_result(self._search.search(redis_query, query_params=query_params, **kwargs))
        return _result_to_dto(result)

    @override
    async def aggregate(self, aggregation: AggregationDTO, **kwargs: Any) -> dict[str, Any]:
        """Execute a RediSearch aggregation asynchronously."""
        request = _build_aggregate_request(aggregation)
        if kwargs.pop("raw", False):
            return cast("dict[str, Any]", await self._await_result(self._search.aggregate(request, **kwargs)))
        result = await self._await_result(self._search.aggregate(request, **kwargs))
        return {"total": result.total, "rows": result.rows}

    @override
    async def add_alias(self, alias: str) -> bool:
        """Add an alias for the index asynchronously."""
        result = await self._await_result(self._search.aliasadd(alias))
        return bool(result)

    @override
    async def update_alias(self, alias: str) -> bool:
        """Update an alias to point to this index asynchronously."""
        result = await self._await_result(self._search.aliasupdate(alias))
        return bool(result)

    @override
    async def delete_alias(self, alias: str) -> bool:
        """Delete an alias asynchronously."""
        result = await self._await_result(self._search.aliasdel(alias))
        return bool(result)
