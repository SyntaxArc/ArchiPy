from typing import Literal

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types.redis_search_types import (
    RedisIndexType,
    VectorAlgorithm,
    VectorDistanceMetric,
)


class TextFieldConfig(BaseDTO):
    """RediSearch text field definition."""

    field_type: Literal["text"] = "text"
    name: str


class TagFieldConfig(BaseDTO):
    """RediSearch tag field definition."""

    field_type: Literal["tag"] = "tag"
    name: str
    separator: str | None = None


class NumericFieldConfig(BaseDTO):
    """RediSearch numeric field definition."""

    field_type: Literal["numeric"] = "numeric"
    name: str


class VectorFieldConfig(BaseDTO):
    """RediSearch vector field definition."""

    field_type: Literal["vector"] = "vector"
    name: str
    dim: int
    distance_metric: VectorDistanceMetric = VectorDistanceMetric.COSINE
    algorithm: VectorAlgorithm = VectorAlgorithm.HNSW


IndexFieldConfig = TextFieldConfig | TagFieldConfig | NumericFieldConfig | VectorFieldConfig


class IndexSchemaDTO(BaseDTO):
    """Schema describing fields indexed by RediSearch."""

    fields: list[IndexFieldConfig]
    index_type: RedisIndexType = RedisIndexType.HASH
