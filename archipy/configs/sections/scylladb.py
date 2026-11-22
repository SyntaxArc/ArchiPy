"""ScyllaDB configuration."""

__lazy_modules__ = ["archipy.models.errors"]

import ssl
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.models.errors import InvalidArgumentError


class ScyllaTlsConfig(BaseModel):
    """TLS settings of the cluster connection."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=False,
        description=(
            "Encrypt the connection to the cluster with TLS. When disabled (default) credentials and data "
            "travel in plain text."
        ),
    )
    CA_FILE: str | None = Field(
        default=None,
        description="Path to the CA bundle used to verify the server certificate (system CAs when unset)",
    )
    CERT_FILE: str | None = Field(
        default=None,
        description="Path to the client certificate for mutual TLS (requires TLS_KEY_FILE)",
    )
    KEY_FILE: str | None = Field(
        default=None,
        description="Path to the client private key for mutual TLS (requires TLS_CERT_FILE)",
    )
    VERIFY_MODE: Literal["CERT_REQUIRED", "CERT_NONE"] = Field(
        default="CERT_REQUIRED",
        description=(
            "Server certificate verification. 'CERT_REQUIRED' validates the chain; "
            "'CERT_NONE' disables verification (and hostname checking) and is insecure"
        ),
    )
    CHECK_HOSTNAME: bool = Field(
        default=True,
        description="Check that the server certificate matches the contact point host name",
    )
    SERVER_NAME: str | None = Field(
        default=None,
        description="Host name to match the server certificate against, when it differs from the contact point address",
    )
    SESSION_CACHE_ENABLED: bool = Field(
        default=True,
        description=(
            "Resume TLS sessions. A resumed session skips the certificate check, so a revoked or expired certificate "
            "can be accepted until the cached session expires; disable to verify on every connection"
        ),
    )

    @model_validator(mode="after")
    def validate_tls(self) -> Self:
        """Validate TLS settings: files need IS_ENABLED, and the client cert and key come as a pair."""
        if (self.CERT_FILE is None) != (self.KEY_FILE is None):
            raise InvalidArgumentError(
                argument_name="tls",
                additional_data={"error": "TLS_CERT_FILE and TLS_KEY_FILE must be provided together"},
            )
        if not self.IS_ENABLED and (self.CA_FILE or self.CERT_FILE):
            raise InvalidArgumentError(
                argument_name="tls",
                additional_data={"error": "TLS_ENABLED must be true when TLS certificate files are set"},
            )
        return self

    def build_ssl_context(self) -> ssl.SSLContext | None:
        """Build the TLS context for the cluster connection.

        Returns:
            ssl.SSLContext | None: The context for ``Cluster(ssl_context=)``, or None when TLS is disabled.
        """
        if not self.IS_ENABLED:
            return None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if self.VERIFY_MODE == "CERT_NONE":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context.check_hostname = self.CHECK_HOSTNAME
            context.verify_mode = ssl.CERT_REQUIRED
            if self.CA_FILE:
                context.load_verify_locations(cafile=self.CA_FILE)
            else:
                context.load_default_certs()
        if self.CERT_FILE and self.KEY_FILE:
            context.load_cert_chain(certfile=self.CERT_FILE, keyfile=self.KEY_FILE)
        return context


class ScyllaRetryConfig(BaseModel):
    """Retry policy settings."""

    model_config = ConfigDict(extra="forbid")

    POLICY: Literal["EXPONENTIAL_BACKOFF", "FALLTHROUGH"] = Field(
        default="EXPONENTIAL_BACKOFF",
        description="Retry policy type (uses native driver RetryPolicy). "
        "Options: 'EXPONENTIAL_BACKOFF' (retries with exponential backoff), "
        "'FALLTHROUGH' (never retries, propagates failures to application)",
    )
    MAX_NUM_RETRIES: float = Field(
        default=3.0,
        ge=0.0,
        description="Maximum number of retries for ExponentialBackoffRetryPolicy",
    )
    MIN_INTERVAL: float = Field(
        default=0.1,
        ge=0.0,
        description="Minimum interval in seconds between retries for ExponentialBackoffRetryPolicy",
    )
    MAX_INTERVAL: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum interval in seconds between retries for ExponentialBackoffRetryPolicy",
    )


class ScyllaReconnectionConfig(BaseModel):
    """Reconnection policy settings."""

    model_config = ConfigDict(extra="forbid")

    POLICY: Literal["CONSTANT", "EXPONENTIAL"] | None = Field(
        default=None,
        description=(
            "How the driver retries a down host. 'CONSTANT' waits RECONNECTION_BASE_DELAY between attempts; "
            "'EXPONENTIAL' grows the wait from RECONNECTION_BASE_DELAY up to RECONNECTION_MAX_DELAY. "
            "Unset keeps the driver default (exponential, 1s to 600s)"
        ),
    )
    BASE_DELAY: float = Field(
        default=1.0,
        gt=0.0,
        description="Seconds between reconnection attempts (first delay for EXPONENTIAL)",
    )
    MAX_DELAY: float = Field(
        default=600.0,
        gt=0.0,
        description="Upper bound in seconds of the delay between attempts for EXPONENTIAL",
    )
    MAX_ATTEMPTS: int | None = Field(
        default=None,
        ge=1,
        description="Stop reconnecting to a host after this many attempts (unlimited when unset)",
    )

    @model_validator(mode="after")
    def validate_reconnection(self) -> Self:
        """Validate that the exponential reconnection delay does not shrink below its base."""
        if self.POLICY == "EXPONENTIAL" and self.BASE_DELAY > self.MAX_DELAY:
            raise InvalidArgumentError(
                argument_name="reconnection",
                additional_data={"error": "RECONNECTION_BASE_DELAY cannot exceed RECONNECTION_MAX_DELAY"},
            )
        return self


class ScyllaSpeculativeExecutionConfig(BaseModel):
    """Speculative execution settings."""

    model_config = ConfigDict(extra="forbid")

    DELAY: float | None = Field(
        default=None,
        gt=0.0,
        description=(
            "Seconds to wait for a response before the driver sends the query to the next host. "
            "Applies only to idempotent statements. Unset disables speculative execution"
        ),
    )
    MAX_ATTEMPTS: int = Field(
        default=2,
        ge=1,
        description="Extra executions allowed per query when SPECULATIVE_EXECUTION_DELAY is set",
    )


class ScyllaPreparedCacheConfig(BaseModel):
    """Prepared statement cache settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=True,
        description="Enable prepared statement caching",
    )
    SIZE: int = Field(
        default=100,
        ge=1,
        description="Maximum cached prepared statements",
    )
    TTL_SECONDS: int = Field(
        default=3600,
        ge=1,
        description="TTL for prepared statement cache in seconds (1 hour)",
    )


class ScyllaHeartbeatConfig(BaseModel):
    """Idle heartbeat settings."""

    model_config = ConfigDict(extra="forbid")

    IDLE_INTERVAL: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Seconds of connection idleness before the driver sends a heartbeat to detect dead connections. "
            "0 disables heartbeats; unset keeps the driver default (30)"
        ),
    )
    IDLE_TIMEOUT: float | None = Field(
        default=None,
        gt=0.0,
        description="Seconds to wait for a heartbeat response before the connection is dropped (driver default 30)",
    )


class ScyllaReplicationConfig(BaseModel):
    """Keyspace replication settings."""

    model_config = ConfigDict(extra="forbid")

    STRATEGY: Literal["SimpleStrategy", "NetworkTopologyStrategy"] = Field(
        default="NetworkTopologyStrategy",
        description="Replication strategy for keyspace creation",
    )
    CONFIG: dict[str, int] | None = Field(
        default={"datacenter1": 1},
        description="Replication configuration (e.g., {'dc1': 3, 'dc2': 2} for NetworkTopologyStrategy)",
    )

    @model_validator(mode="after")
    def validate_replication_config(self) -> Self:
        """Validate replication configuration."""
        if self.STRATEGY == "NetworkTopologyStrategy" and not self.CONFIG:
            raise InvalidArgumentError(
                argument_name="replication_config",
                additional_data={"error": "REPLICATION_CONFIG required for NetworkTopologyStrategy"},
            )
        return self


class ScyllaDBConfig(BaseModel):
    """Configuration settings for ScyllaDB/Cassandra connections and operations.

    Contains settings related to ScyllaDB cluster connectivity, authentication,
    compression, consistency levels, connection management, retry policies,
    prepared statement caching, and health checks.
    """

    CONTACT_POINTS: list[str] = Field(
        default=["127.0.0.1"],
        description="List of ScyllaDB node addresses for initial connection",
    )
    PORT: int = Field(
        default=9042,
        ge=1,
        le=65535,
        description="CQL native transport port number",
    )
    KEYSPACE: str | None = Field(
        default=None,
        description="Default keyspace name to use",
    )
    USERNAME: str | None = Field(
        default=None,
        description="Username for authentication",
    )
    PASSWORD: SecretStr | None = Field(
        default=None,
        description="Password for authentication",
    )
    PROTOCOL_VERSION: int = Field(
        default=4,
        ge=3,
        le=5,
        description="CQL protocol version (3-5)",
    )
    COMPRESSION: bool = Field(
        default=True,
        description="Enable LZ4 compression for network traffic",
    )
    CONNECT_TIMEOUT: int = Field(
        default=10,
        ge=1,
        description="Connection timeout in seconds",
    )
    REQUEST_TIMEOUT: int = Field(
        default=10,
        ge=1,
        description="Request timeout in seconds",
    )
    CONSISTENCY_LEVEL: Literal[
        "ONE",
        "TWO",
        "THREE",
        "QUORUM",
        "ALL",
        "LOCAL_QUORUM",
        "EACH_QUORUM",
        "LOCAL_ONE",
        "ANY",
    ] = Field(
        default="ONE",
        description="Default consistency level",
    )
    DISABLE_SHARD_AWARENESS: bool = Field(
        default=False,
        description="Disable shard awareness (useful for Docker/Testcontainer/NAT environments)",
    )
    ADDRESS_TRANSLATION_ENABLED: bool = Field(
        default=False,
        description=(
            "Enable address translation to redirect all discovered node connections "
            "to the first contact point. In Docker/Testcontainer/NAT environments, "
            "ScyllaDB nodes advertise their internal container IPs via gossip, which "
            "are unreachable from the host. When enabled, the driver translates all "
            "discovered addresses to the first configured contact point, allowing "
            "connections through Docker's port mapping."
        ),
    )
    HEALTH_CHECK_TIMEOUT: int = Field(
        default=5,
        ge=1,
        description="Timeout for health check queries in seconds",
    )
    ENABLE_CONNECTION_POOL_MONITORING: bool = Field(
        default=False,
        description="Enable connection pool monitoring and metrics",
    )
    CONTROL_CONNECTION_TIMEOUT: float | None = Field(
        default=None,
        gt=0.0,
        description="Seconds the control connection waits for topology and schema queries (driver default 2)",
    )
    SERIAL_CONSISTENCY_LEVEL: Literal["SERIAL", "LOCAL_SERIAL"] | None = Field(
        default=None,
        description="Consistency level of the Paxos phase of lightweight transactions (IF clauses); unset keeps SERIAL",
    )
    LOCAL_DC: str | None = Field(
        default=None,
        description="Local datacenter name for datacenter-aware routing",
    )

    TLS: ScyllaTlsConfig = Field(default_factory=ScyllaTlsConfig, description="TLS settings of the cluster connection")
    RETRY: ScyllaRetryConfig = Field(default_factory=ScyllaRetryConfig, description="Retry policy settings")
    RECONNECTION: ScyllaReconnectionConfig = Field(
        default_factory=ScyllaReconnectionConfig,
        description="Reconnection policy settings",
    )
    SPECULATIVE_EXECUTION: ScyllaSpeculativeExecutionConfig = Field(
        default_factory=ScyllaSpeculativeExecutionConfig,
        description="Speculative execution settings",
    )
    PREPARED_CACHE: ScyllaPreparedCacheConfig = Field(
        default_factory=ScyllaPreparedCacheConfig,
        description="Prepared statement cache settings",
    )
    HEARTBEAT: ScyllaHeartbeatConfig = Field(
        default_factory=ScyllaHeartbeatConfig,
        description="Idle heartbeat settings",
    )
    REPLICATION: ScyllaReplicationConfig = Field(
        default_factory=ScyllaReplicationConfig,
        description="Keyspace replication settings",
    )

    @model_validator(mode="after")
    def validate_contact_points(self) -> Self:
        """Validate that at least one contact point is provided."""
        if not self.CONTACT_POINTS or len(self.CONTACT_POINTS) == 0:
            raise InvalidArgumentError(
                argument_name="CONTACT_POINTS",
                additional_data={"error": "Empty contact points list"},
            )
        return self

    @model_validator(mode="after")
    def validate_authentication(self) -> Self:
        """Validate that both username and password are provided together."""
        if (self.USERNAME is None) != (self.PASSWORD is None):
            raise InvalidArgumentError(
                argument_name="authentication",
                additional_data={"error": "Both username and password must be provided together"},
            )
        return self

    def build_ssl_context(self) -> ssl.SSLContext | None:
        """Build the TLS context for the cluster connection (see ``TLS``)."""
        return self.TLS.build_ssl_context()
