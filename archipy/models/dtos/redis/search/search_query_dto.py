"""DTOs for Redis Search queries."""

from typing import Literal

from pydantic import NonNegativeInt, PositiveInt

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.dtos.redis.search.escaping import SearchIdentifier, escape_text
from archipy.models.types.redis_search_types import (
    UseSearchHistory,
    VectorHybridPolicy,
)


class VectorQueryRuntimeDTO(BaseDTO):
    """Runtime tuning parameters for vector KNN and range queries."""

    ef_runtime: int | None = None
    epsilon: float | None = None
    hybrid_policy: VectorHybridPolicy | None = None
    batch_size: int | None = None
    shard_k_ratio: float | None = None
    search_window_size: int | None = None
    use_search_history: UseSearchHistory | None = None
    search_buffer_capacity: int | None = None


class KnnQueryDTO(BaseDTO):
    """Vector KNN search parameters.

    ``filter_expr`` is raw RediSearch syntax and is not escaped; build it from untrusted input with
    ``escape_text``, ``escape_tag`` or ``quote_phrase``. Identifier-like fields are validated.
    """

    vector: list[float]
    vector_field: SearchIdentifier = "embedding"
    k: PositiveInt = 10
    filter_expr: str | None = None
    return_fields: list[SearchIdentifier] | None = None
    score_field: SearchIdentifier = "score"
    runtime: VectorQueryRuntimeDTO | None = None


class RangeQueryDTO(BaseDTO):
    """Vector range search parameters."""

    vector: list[float]
    vector_field: SearchIdentifier = "embedding"
    radius: float
    filter_expr: str | None = None
    filter_mode: Literal["and", "or"] = "and"
    return_fields: list[SearchIdentifier] | None = None
    score_field: SearchIdentifier | None = None
    runtime: VectorQueryRuntimeDTO | None = None


class SearchQueryDTO(BaseDTO):
    """Full-text, vector KNN, vector range, or hybrid RediSearch query.

    ``query`` is raw RediSearch syntax and is not escaped. For untrusted user text use ``from_text`` or escape
    with ``escape_text`` / ``escape_tag`` / ``quote_phrase`` first. Identifier-like fields are validated.
    """

    query: str = "*"
    return_fields: list[SearchIdentifier] | None = None
    offset: NonNegativeInt = 0
    limit: NonNegativeInt = 10
    text_scorer: str | None = None
    knn: KnnQueryDTO | None = None
    range: RangeQueryDTO | None = None

    @property
    def is_hybrid(self) -> bool:
        """Return whether the query combines full-text and vector KNN."""
        return self.knn is not None and self.query != "*"

    @property
    def is_range(self) -> bool:
        """Return whether the query is a vector range search."""
        return self.range is not None

    @classmethod
    def from_text(
        cls,
        text: str,
        *,
        return_fields: list[str] | None = None,
        offset: int = 0,
        limit: int = 10,
        text_scorer: str | None = None,
    ) -> SearchQueryDTO:
        """Build a full-text query from untrusted text, escaping every term.

        Args:
            text: User text; whitespace-separated terms are escaped and combined with AND.
            return_fields: Optional document fields to return.
            offset: Number of hits to skip.
            limit: Maximum number of hits.
            text_scorer: Optional full-text scorer name.

        Returns:
            SearchQueryDTO whose query matches the terms literally.
        """
        terms = [escape_text(term) for term in text.split()]
        return cls(
            query=" ".join(terms) if terms else "*",
            return_fields=return_fields,
            offset=offset,
            limit=limit,
            text_scorer=text_scorer,
        )

    @classmethod
    def from_knn(
        cls,
        vector: list[float],
        *,
        k: int = 10,
        vector_field: SearchIdentifier = "embedding",
        filter_expr: str | None = None,
        return_fields: list[str] | None = None,
        runtime: VectorQueryRuntimeDTO | None = None,
    ) -> SearchQueryDTO:
        """Build a KNN-only search query.

        Args:
            vector: Query embedding vector.
            k: Number of nearest neighbors to return.
            vector_field: Indexed vector field name.
            filter_expr: Optional RediSearch filter expression.
            return_fields: Optional document fields to return.
            runtime: Optional vector query runtime parameters.

        Returns:
            SearchQueryDTO configured for vector KNN search.
        """
        return cls(
            knn=KnnQueryDTO(
                vector=vector,
                k=k,
                vector_field=vector_field,
                filter_expr=filter_expr,
                return_fields=return_fields,
                runtime=runtime,
            ),
        )

    @classmethod
    def from_range(
        cls,
        vector: list[float],
        *,
        radius: float,
        vector_field: SearchIdentifier = "embedding",
        filter_expr: str | None = None,
        filter_mode: Literal["and", "or"] = "and",
        return_fields: list[str] | None = None,
        score_field: str | None = None,
        limit: int = 10,
        runtime: VectorQueryRuntimeDTO | None = None,
    ) -> SearchQueryDTO:
        """Build a vector range search query.

        Args:
            vector: Query embedding vector.
            radius: Maximum semantic distance from the query vector.
            vector_field: Indexed vector field name.
            filter_expr: Optional RediSearch filter expression combined with the range clause.
            filter_mode: How the filter combines with the range: ``"and"`` (default) keeps only documents
                matching both, ``"or"`` also returns documents matching only the filter.
            return_fields: Optional document fields to return.
            score_field: Optional distance field name in the response.
            limit: Maximum number of documents to return.
            runtime: Optional vector query runtime parameters.

        Returns:
            SearchQueryDTO configured for vector range search.
        """
        return cls(
            limit=limit,
            range=RangeQueryDTO(
                vector=vector,
                radius=radius,
                vector_field=vector_field,
                filter_expr=filter_expr,
                filter_mode=filter_mode,
                return_fields=return_fields,
                score_field=score_field,
                runtime=runtime,
            ),
        )

    @classmethod
    def from_hybrid(
        cls,
        text_query: str,
        vector: list[float],
        *,
        k: int = 10,
        vector_field: SearchIdentifier = "embedding",
        filter_expr: str | None = None,
        text_scorer: str | None = None,
        return_fields: list[str] | None = None,
        runtime: VectorQueryRuntimeDTO | None = None,
    ) -> SearchQueryDTO:
        """Build a hybrid full-text and vector search query.

        Args:
            text_query: Full-text query string.
            vector: Query embedding vector.
            k: Number of nearest neighbors to return.
            vector_field: Indexed vector field name.
            filter_expr: Optional RediSearch filter expression.
            text_scorer: Optional full-text scorer name.
            return_fields: Optional document fields to return.
            runtime: Optional vector query runtime parameters.

        Returns:
            SearchQueryDTO configured for hybrid search.
        """
        return cls(
            query=text_query,
            text_scorer=text_scorer,
            knn=KnnQueryDTO(
                vector=vector,
                k=k,
                vector_field=vector_field,
                filter_expr=filter_expr,
                return_fields=return_fields,
                runtime=runtime,
            ),
        )
