from enum import StrEnum


class VectorDistanceMetric(StrEnum):
    """RediSearch vector distance metrics."""

    COSINE = "COSINE"
    L2 = "L2"
    IP = "IP"


class VectorAlgorithm(StrEnum):
    """RediSearch vector index algorithms."""

    FLAT = "FLAT"
    HNSW = "HNSW"
    SVS_VAMANA = "SVS-VAMANA"


class VectorType(StrEnum):
    """RediSearch vector storage type."""

    BFLOAT16 = "BFLOAT16"
    FLOAT16 = "FLOAT16"
    FLOAT32 = "FLOAT32"
    FLOAT64 = "FLOAT64"
    INT8 = "INT8"
    UINT8 = "UINT8"


class VectorCompression(StrEnum):
    """SVS-VAMANA vector compression algorithms."""

    LVQ8 = "LVQ8"
    LVQ4 = "LVQ4"
    LVQ4X4 = "LVQ4x4"
    LVQ4X8 = "LVQ4x8"
    LEAN_VEC4X8 = "LeanVec4x8"
    LEAN_VEC8X8 = "LeanVec8x8"


class VectorHybridPolicy(StrEnum):
    """Filter execution policy for vector search with metadata filters."""

    BATCHES = "BATCHES"
    ADHOC_BF = "ADHOC_BF"


class UseSearchHistory(StrEnum):
    """SVS-VAMANA search history mode."""

    OFF = "OFF"
    ON = "ON"
    AUTO = "AUTO"


class RedisIndexType(StrEnum):
    """RediSearch index document type."""

    HASH = "HASH"
    JSON = "JSON"
