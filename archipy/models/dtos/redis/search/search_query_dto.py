from archipy.models.dtos.base_dtos import BaseDTO


class KnnQueryDTO(BaseDTO):
    """Vector KNN search parameters."""

    vector: list[float]
    vector_field: str = "embedding"
    k: int = 10
    filter_expr: str | None = None
    return_fields: list[str] | None = None
    score_field: str = "score"


class SearchQueryDTO(BaseDTO):
    """Full-text, vector KNN, or hybrid RediSearch query."""

    query: str = "*"
    return_fields: list[str] | None = None
    offset: int = 0
    limit: int = 10
    text_scorer: str | None = None
    knn: KnnQueryDTO | None = None

    @property
    def is_hybrid(self) -> bool:
        """Return whether the query combines full-text and vector KNN."""
        return self.knn is not None and self.query != "*"

    @classmethod
    def from_knn(
        cls,
        vector: list[float],
        *,
        k: int = 10,
        vector_field: str = "embedding",
        filter_expr: str | None = None,
        return_fields: list[str] | None = None,
    ) -> SearchQueryDTO:
        """Build a KNN-only search query.

        Args:
            vector: Query embedding vector.
            k: Number of nearest neighbors to return.
            vector_field: Indexed vector field name.
            filter_expr: Optional RediSearch filter expression.
            return_fields: Optional document fields to return.

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
            ),
        )

    @classmethod
    def from_hybrid(
        cls,
        text_query: str,
        vector: list[float],
        *,
        k: int = 10,
        vector_field: str = "embedding",
        filter_expr: str | None = None,
        text_scorer: str | None = None,
        return_fields: list[str] | None = None,
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
            ),
        )
