"""Redis configuration."""

__lazy_modules__ = ["archipy.models.errors"]

import logging
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)


class RedisMode(StrEnum):
    """Redis deployment mode."""

    STANDALONE = "STANDALONE"
    SENTINEL = "SENTINEL"
    CLUSTER = "CLUSTER"


class RedisClusterConfig(BaseModel):
    """Cluster mode settings."""

    model_config = ConfigDict(extra="forbid")

    NODES: list[str] = Field(default=[], description="List of cluster node addresses (host:port)")
    REQUIRE_FULL_COVERAGE: bool = Field(default=True, description="Require full cluster coverage")
    TOPOLOGY_REFRESH_MIN_INTERVAL: float | None = Field(
        default=None,
        ge=0,
        description="Minimum seconds between error-triggered topology refreshes; None uses the client default",
    )
    READ_FROM_REPLICAS: bool = Field(default=True, description="Allow reading from replica nodes")


class RedisSentinelConfig(BaseModel):
    """Sentinel mode settings."""

    model_config = ConfigDict(extra="forbid")

    NODES: list[str] = Field(default=[], description="List of sentinel addresses (host:port)")
    SERVICE_NAME: str | None = Field(default=None, description="Master service name for sentinel")
    SOCKET_TIMEOUT: float = Field(default=0.1, description="Sentinel socket timeout")
    PASSWORD: SecretStr | None = Field(
        default=None,
        description="Password for sentinel nodes (if distinct)",
    )
    USERNAME: str | None = Field(default=None, description="ACL username for sentinel nodes (if distinct)")


class RedisTlsConfig(BaseModel):
    """TLS settings of the Redis connection."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(default=False, description="Connect to Redis over TLS")
    CA_CERTS: str | None = Field(default=None, description="Path to the CA bundle used to verify the server")
    CERTFILE: str | None = Field(default=None, description="Path to the client certificate (mTLS)")
    KEYFILE: str | None = Field(default=None, description="Path to the client private key (mTLS)")
    CHECK_HOSTNAME: bool = Field(default=True, description="Verify the server hostname against its certificate")

    @model_validator(mode="after")
    def validate_tls_files(self) -> Self:
        """Validate that the client certificate and key come together and need ``IS_ENABLED``."""
        if bool(self.CERTFILE) != bool(self.KEYFILE):
            raise ConfigurationError(operation="redis", reason="ssl_certfile_and_keyfile_must_be_set_together")
        if not self.IS_ENABLED and (self.CA_CERTS or self.CERTFILE):
            raise ConfigurationError(operation="redis", reason="ssl_options_require_ssl_enabled")
        return self


class RedisRetryConfig(BaseModel):
    """Retry and backoff settings."""

    model_config = ConfigDict(extra="forbid")

    ATTEMPTS: int | None = Field(
        default=None,
        ge=0,
        description="Retries per command with exponential backoff on connection errors; None keeps redis-py defaults",
    )
    BACKOFF_BASE: float = Field(default=0.008, gt=0, description="Exponential backoff base delay in seconds")
    BACKOFF_CAP: float = Field(default=0.512, gt=0, description="Exponential backoff maximum delay in seconds")
    FAIL_FAST_MISSING_SOCKET: bool = Field(default=False, description="Skip retries when the Unix socket is missing")
    ON_TIMEOUT: bool = Field(default=False, description="Also retry commands that hit a socket timeout")


class RedisConfig(BaseModel):
    """Configuration settings for Redis cache integration.

    Supports standalone, sentinel, and cluster deployments.
    """

    MODE: RedisMode = Field(default=RedisMode.STANDALONE, description="Redis deployment mode")
    MASTER_HOST: str | None = Field(default="localhost", description="Redis master host (standalone/sentinel)")
    SLAVE_HOST: str | None = Field(default=None, description="Redis slave host (standalone)")
    UNIX_SOCKET_PATH: str | None = Field(default=None, min_length=1, description="Standalone Redis Unix socket path")
    PORT: int = Field(default=6379, description="Default Redis server port")
    DATABASE: int = Field(default=0, description="Redis database number (standalone and sentinel; ignored in cluster)")
    USERNAME: str | None = Field(default=None, description="Redis ACL username (Redis 6+); None uses the default user")
    PASSWORD: SecretStr | None = Field(default=None, description="Redis password")
    DECODE_RESPONSES: Literal[True] = Field(default=True, description="Whether to decode responses")
    PROTOCOL: Literal[2, 3] | None = Field(default=3, description="RESP protocol version; None enables negotiation")
    HEALTH_CHECK_INTERVAL: int = Field(default=10, description="Health check interval in seconds")
    SOCKET_KEEPALIVE: bool | None = Field(
        default=None,
        description="TCP keepalive to detect dead peers behind NAT; None keeps the redis-py default",
    )
    CLIENT_NAME: str | None = Field(default=None, description="Connection name shown in CLIENT LIST")
    MAX_CONNECTIONS: int = Field(default=50, description="Maximum connections per node")
    SOCKET_CONNECT_TIMEOUT: float = Field(default=5.0, description="Socket connection timeout")
    SOCKET_TIMEOUT: float = Field(default=5.0, description="Socket operation timeout")

    CLUSTER: RedisClusterConfig = Field(default_factory=RedisClusterConfig, description="Cluster mode settings")
    SENTINEL: RedisSentinelConfig = Field(default_factory=RedisSentinelConfig, description="Sentinel mode settings")
    TLS: RedisTlsConfig = Field(default_factory=RedisTlsConfig, description="TLS settings of the Redis connection")
    RETRY: RedisRetryConfig = Field(default_factory=RedisRetryConfig, description="Retry and backoff settings")

    @staticmethod
    def _validate_node_address(node: str, *, port_required: bool) -> None:
        """Validate a ``host[:port]`` node address."""
        host, separator, port = node.partition(":")
        if not host or (separator and not port.isdecimal()) or (port_required and not separator):
            raise ConfigurationError(operation="redis", reason="invalid_node_address", additional_data={"node": node})

    @model_validator(mode="after")
    def validate_mode_configuration(self) -> Self:
        """Validate mode-specific configuration."""
        if self.MODE == RedisMode.CLUSTER:
            if not self.CLUSTER.NODES:
                raise ConfigurationError(operation="redis", reason="cluster_nodes_required")
            for node in self.CLUSTER.NODES:
                self._validate_node_address(node, port_required=False)
            if self.DATABASE != 0:
                logger.warning("DATABASE setting ignored in cluster mode")

        elif self.MODE == RedisMode.SENTINEL:
            if not self.SENTINEL.NODES or not self.SENTINEL.SERVICE_NAME:
                raise ConfigurationError(operation="redis", reason="sentinel_config_incomplete")
            for node in self.SENTINEL.NODES:
                self._validate_node_address(node, port_required=True)

        elif not (self.MASTER_HOST or self.UNIX_SOCKET_PATH):
            raise ConfigurationError(operation="redis", reason="master_host_required")

        return self

    @model_validator(mode="after")
    def validate_unix_socket(self) -> Self:
        """Validate options for a standalone Unix socket connection."""
        if self.UNIX_SOCKET_PATH and (self.MODE != RedisMode.STANDALONE or self.TLS.IS_ENABLED or self.SLAVE_HOST):
            raise ConfigurationError(operation="redis", reason="unix_socket_requires_standalone_without_tls_or_replica")
        if self.RETRY.FAIL_FAST_MISSING_SOCKET and self.UNIX_SOCKET_PATH is None:
            raise ConfigurationError(operation="redis", reason="missing_socket_fast_fail_requires_unix_socket")

        return self

    @model_validator(mode="after")
    def warn_insecure_tls(self) -> Self:
        """Warn when credentials travel without TLS or the server identity is not verified."""
        if not self.TLS.IS_ENABLED and (self.PASSWORD or self.SENTINEL.PASSWORD):
            logger.warning("Redis credentials are configured without SSL; they are sent in clear text")
        if self.TLS.IS_ENABLED and not self.TLS.CHECK_HOSTNAME:
            logger.warning("Redis TLS.CHECK_HOSTNAME is disabled; the server identity is not verified")
        return self
