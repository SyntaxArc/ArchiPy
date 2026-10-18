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

    # Common settings
    PORT: int = Field(default=6379, description="Default Redis server port")
    DATABASE: int = Field(default=0, description="Redis database number (not used in cluster)")
    PASSWORD: str | None = Field(default=None, description="Redis password")
    DECODE_RESPONSES: Literal[True] = Field(default=True, description="Whether to decode responses")
    PROTOCOL: Literal[2, 3] = Field(default=3, description="RESP protocol version (2 or 3)")
    HEALTH_CHECK_INTERVAL: int = Field(default=10, description="Health check interval in seconds")

    # Connection pooling
    MAX_CONNECTIONS: int = Field(default=50, description="Maximum connections per node")
    SOCKET_CONNECT_TIMEOUT: float = Field(default=5.0, description="Socket connection timeout")
    SOCKET_TIMEOUT: float = Field(default=5.0, description="Socket operation timeout")

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
