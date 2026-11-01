"""Redis configuration."""

import logging
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)


class RedisMode(StrEnum):
    """Redis deployment mode."""

    STANDALONE = "STANDALONE"
    SENTINEL = "SENTINEL"
    CLUSTER = "CLUSTER"


class RedisConfig(BaseModel):
    """Configuration settings for Redis cache integration.

    Supports standalone, sentinel, and cluster deployments.
    """

    # Deployment mode
    MODE: RedisMode = Field(default=RedisMode.STANDALONE, description="Redis deployment mode")

    # Standalone mode settings (existing)
    MASTER_HOST: str | None = Field(default="localhost", description="Redis master host (standalone/sentinel)")
    SLAVE_HOST: str | None = Field(default=None, description="Redis slave host (standalone)")

    # Cluster mode settings
    CLUSTER_NODES: list[str] = Field(default=[], description="List of cluster node addresses (host:port)")
    CLUSTER_REQUIRE_FULL_COVERAGE: bool = Field(default=True, description="Require full cluster coverage")
    CLUSTER_READ_FROM_REPLICAS: bool = Field(default=True, description="Allow reading from replica nodes")

    # Sentinel mode settings
    SENTINEL_NODES: list[str] = Field(default=[], description="List of sentinel addresses (host:port)")
    SENTINEL_SERVICE_NAME: str | None = Field(default=None, description="Master service name for sentinel")
    SENTINEL_SOCKET_TIMEOUT: float = Field(default=0.1, description="Sentinel socket timeout")
    SENTINEL_PASSWORD: str | None = Field(default=None, description="Password for sentinel nodes (if distinct)")
    SENTINEL_USERNAME: str | None = Field(default=None, description="ACL username for sentinel nodes (if distinct)")

    # Common settings
    PORT: int = Field(default=6379, description="Default Redis server port")
    DATABASE: int = Field(default=0, description="Redis database number (not used in cluster)")
    USERNAME: str | None = Field(default=None, description="Redis ACL username (Redis 6+); None uses the default user")
    PASSWORD: str | None = Field(default=None, description="Redis password")
    DECODE_RESPONSES: Literal[True] = Field(default=True, description="Whether to decode responses")
    PROTOCOL: Literal[2, 3] = Field(default=3, description="RESP protocol version (2 or 3)")
    HEALTH_CHECK_INTERVAL: int = Field(default=10, description="Health check interval in seconds")

    # TLS settings
    SSL: bool = Field(default=False, description="Connect to Redis over TLS")
    SSL_CA_CERTS: str | None = Field(default=None, description="Path to the CA bundle used to verify the server")
    SSL_CERTFILE: str | None = Field(default=None, description="Path to the client certificate (mTLS)")
    SSL_KEYFILE: str | None = Field(default=None, description="Path to the client private key (mTLS)")
    SSL_CHECK_HOSTNAME: bool = Field(default=True, description="Verify the server hostname against its certificate")

    # Resilience and observability (unset keeps the redis-py defaults)
    RETRY_ATTEMPTS: int | None = Field(
        default=None,
        ge=0,
        description="Retries per command with exponential backoff on connection errors; None keeps redis-py defaults",
    )
    RETRY_BACKOFF_BASE: float = Field(default=0.008, gt=0, description="Exponential backoff base delay in seconds")
    RETRY_BACKOFF_CAP: float = Field(default=0.512, gt=0, description="Exponential backoff maximum delay in seconds")
    RETRY_ON_TIMEOUT: bool = Field(default=False, description="Also retry commands that hit a socket timeout")
    SOCKET_KEEPALIVE: bool | None = Field(
        default=None,
        description="TCP keepalive to detect dead peers behind NAT; None keeps the redis-py default",
    )
    CLIENT_NAME: str | None = Field(default=None, description="Connection name shown in CLIENT LIST")

    # Connection pooling
    MAX_CONNECTIONS: int = Field(default=50, description="Maximum connections per node")
    SOCKET_CONNECT_TIMEOUT: float = Field(default=5.0, description="Socket connection timeout")
    SOCKET_TIMEOUT: float = Field(default=5.0, description="Socket operation timeout")

    @model_validator(mode="after")
    def validate_tls_configuration(self) -> Self:
        """Validate TLS settings."""
        if bool(self.SSL_CERTFILE) != bool(self.SSL_KEYFILE):
            raise ConfigurationError(operation="redis", reason="ssl_certfile_and_keyfile_must_be_set_together")
        if not self.SSL and (self.SSL_CA_CERTS or self.SSL_CERTFILE):
            raise ConfigurationError(operation="redis", reason="ssl_options_require_ssl_enabled")
        return self

    @model_validator(mode="after")
    def validate_mode_configuration(self) -> Self:
        """Validate mode-specific configuration."""
        if self.MODE == RedisMode.CLUSTER:
            if not self.CLUSTER_NODES:
                raise ConfigurationError(operation="redis", reason="cluster_nodes_required")
            if self.DATABASE != 0:
                logger.warning("DATABASE setting ignored in cluster mode")

        elif self.MODE == RedisMode.SENTINEL:
            if not self.SENTINEL_NODES or not self.SENTINEL_SERVICE_NAME:
                raise ConfigurationError(operation="redis", reason="sentinel_config_incomplete")

        elif self.MODE == RedisMode.STANDALONE:
            if not self.MASTER_HOST:
                raise ConfigurationError(operation="redis", reason="master_host_required")

        return self
