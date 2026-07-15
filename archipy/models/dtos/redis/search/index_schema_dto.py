from typing import Literal

from pydantic import model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types.redis_search_types import (
    RedisIndexType,
    VectorAlgorithm,
    VectorCompression,
    VectorDistanceMetric,
    VectorType,
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
    vector_type: VectorType = VectorType.FLOAT32
    m: int | None = None
    ef_construction: int | None = None
    ef_runtime: int | None = None
    epsilon: float | None = None
    compression: VectorCompression | None = None
    construction_window_size: int | None = None
    graph_max_degree: int | None = None
    search_window_size: int | None = None
    training_threshold: int | None = None
    reduce: int | None = None

    @model_validator(mode="after")
    def validate_algorithm_attributes(self) -> VectorFieldConfig:
        """Reject tuning attributes that do not apply to the selected algorithm."""
        hnsw_only = {
            "m": self.m,
            "ef_construction": self.ef_construction,
            "ef_runtime": self.ef_runtime,
        }
        svs_only = {
            "compression": self.compression,
            "construction_window_size": self.construction_window_size,
            "graph_max_degree": self.graph_max_degree,
            "search_window_size": self.search_window_size,
            "training_threshold": self.training_threshold,
            "reduce": self.reduce,
        }
        if self.algorithm == VectorAlgorithm.FLAT:
            invalid = [name for name, value in {**hnsw_only, **svs_only}.items() if value is not None]
            if invalid:
                msg = f"FLAT indexes do not support tuning attributes: {', '.join(invalid)}"
                raise ValueError(msg)
        if self.algorithm == VectorAlgorithm.HNSW:
            invalid = [name for name, value in svs_only.items() if value is not None]
            if invalid:
                msg = f"HNSW indexes do not support SVS-VAMANA attributes: {', '.join(invalid)}"
                raise ValueError(msg)
        if self.algorithm == VectorAlgorithm.SVS_VAMANA:
            invalid = [name for name, value in hnsw_only.items() if value is not None]
            if invalid:
                msg = f"SVS-VAMANA indexes do not support HNSW attributes: {', '.join(invalid)}"
                raise ValueError(msg)
            if self.vector_type not in {VectorType.FLOAT16, VectorType.FLOAT32}:
                msg = "SVS-VAMANA indexes support FLOAT16 and FLOAT32 vector types only"
                raise ValueError(msg)
        return self


IndexFieldConfig = TextFieldConfig | TagFieldConfig | NumericFieldConfig | VectorFieldConfig


class IndexSchemaDTO(BaseDTO):
    """Schema describing fields indexed by RediSearch."""

    fields: list[IndexFieldConfig]
    index_type: RedisIndexType = RedisIndexType.HASH
