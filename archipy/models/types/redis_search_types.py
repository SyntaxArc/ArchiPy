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


class RedisIndexType(StrEnum):
    """RediSearch index document type."""

    HASH = "HASH"
    JSON = "JSON"
