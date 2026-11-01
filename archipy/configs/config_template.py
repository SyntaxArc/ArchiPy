"""Configuration templates for various services and components.

This module provides Pydantic models for configuring different services and components
used in the application, including databases, message brokers, authentication services,
and more.
"""

from archipy.configs.sections.auth import (
    AuthConfig,
)
from archipy.configs.sections.elasticsearch import (
    ElasticsearchConfig,
)
from archipy.configs.sections.email import (
    EmailConfig,
)
from archipy.configs.sections.fastapi import (
    FastAPIConfig,
)
from archipy.configs.sections.general import (
    DatetimeConfig,
    FileConfig,
    PaginationConfig,
)
from archipy.configs.sections.grpc import (
    GrpcConfig,
    GrpcRateLimitConfig,
)
from archipy.configs.sections.kafka import (
    KafkaConfig,
)
from archipy.configs.sections.keycloak import (
    KeycloakConfig,
)
from archipy.configs.sections.minio import (
    MinioConfig,
)
from archipy.configs.sections.otel import (
    OpentelemetryConfig,
    OtelLogsExporter,
    OtelMetricsExporter,
    OtelSampler,
)
from archipy.configs.sections.payment import (
    ParsianShaparakConfig,
    SamanShaparakConfig,
)
from archipy.configs.sections.pydantic_ai import (
    PydanticAIConfig,
)
from archipy.configs.sections.redis import (
    RedisConfig,
    RedisMode,
)
from archipy.configs.sections.scylladb import (
    ScyllaDBConfig,
)
from archipy.configs.sections.sqlalchemy import (
    MySQLSQLAlchemyConfig,
    PostgresSQLAlchemyConfig,
    SQLAlchemyConfig,
    SQLiteSQLAlchemyConfig,
    StarRocksSQLAlchemyConfig,
    _extract_postgres_auth_from_url,  # noqa: F401
    _extract_postgres_host_port_from_url,  # noqa: F401
)
from archipy.configs.sections.temporal import (
    TLS_CERT_PARTS_REQUIRED,
    TemporalConfig,
)
from archipy.configs.sections.uvicorn import UvicornConfig
from archipy.configs.sections.vault import (
    VaultConfig,
)

__all__ = [
    "TLS_CERT_PARTS_REQUIRED",
    "AuthConfig",
    "DatetimeConfig",
    "ElasticsearchConfig",
    "EmailConfig",
    "FastAPIConfig",
    "FileConfig",
    "GrpcConfig",
    "GrpcRateLimitConfig",
    "KafkaConfig",
    "KeycloakConfig",
    "MinioConfig",
    "MySQLSQLAlchemyConfig",
    "OpentelemetryConfig",
    "OtelLogsExporter",
    "OtelMetricsExporter",
    "OtelSampler",
    "PaginationConfig",
    "ParsianShaparakConfig",
    "PostgresSQLAlchemyConfig",
    "PydanticAIConfig",
    "RedisConfig",
    "RedisMode",
    "SQLAlchemyConfig",
    "SQLiteSQLAlchemyConfig",
    "SamanShaparakConfig",
    "ScyllaDBConfig",
    "StarRocksSQLAlchemyConfig",
    "TemporalConfig",
    "UvicornConfig",
    "VaultConfig",
]
