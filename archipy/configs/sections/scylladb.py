"""ScyllaDB configuration."""

import ssl
from typing import Literal, Self

from pydantic import BaseModel, Field, SecretStr, model_validator

from archipy.models.errors import InvalidArgumentError


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
    RETRY_POLICY: Literal["EXPONENTIAL_BACKOFF", "FALLTHROUGH"] = Field(
        default="EXPONENTIAL_BACKOFF",
        description="Retry policy type (uses native driver RetryPolicy). "
        "Options: 'EXPONENTIAL_BACKOFF' (retries with exponential backoff), "
        "'FALLTHROUGH' (never retries, propagates failures to application)",
    )
    RETRY_MAX_NUM_RETRIES: float = Field(
        default=3.0,
        ge=0.0,
        description="Maximum number of retries for ExponentialBackoffRetryPolicy",
    )
    RETRY_MIN_INTERVAL: float = Field(
        default=0.1,
        ge=0.0,
        description="Minimum interval in seconds between retries for ExponentialBackoffRetryPolicy",
    )
    RETRY_MAX_INTERVAL: float = Field(
        default=10.0,
        ge=0.0,
        description="Maximum interval in seconds between retries for ExponentialBackoffRetryPolicy",
    )
    ENABLE_PREPARED_STATEMENT_CACHE: bool = Field(
        default=True,
        description="Enable prepared statement caching",
    )
    PREPARED_STATEMENT_CACHE_SIZE: int = Field(
        default=100,
        ge=1,
        description="Maximum cached prepared statements",
    )
    PREPARED_STATEMENT_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        ge=1,
        description="TTL for prepared statement cache in seconds (1 hour)",
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

    # TLS Configuration
    TLS_ENABLED: bool = Field(
        default=False,
        description=(
            "Encrypt the connection to the cluster with TLS. When disabled (default) credentials and data "
            "travel in plain text."
        ),
    )
    TLS_CA_FILE: str | None = Field(
        default=None,
        description="Path to the CA bundle used to verify the server certificate (system CAs when unset)",
    )
    TLS_CERT_FILE: str | None = Field(
        default=None,
        description="Path to the client certificate for mutual TLS (requires TLS_KEY_FILE)",
    )
    TLS_KEY_FILE: str | None = Field(
        default=None,
        description="Path to the client private key for mutual TLS (requires TLS_CERT_FILE)",
    )
    TLS_VERIFY_MODE: Literal["CERT_REQUIRED", "CERT_NONE"] = Field(
        default="CERT_REQUIRED",
        description=(
            "Server certificate verification. 'CERT_REQUIRED' validates the chain; "
            "'CERT_NONE' disables verification (and hostname checking) and is insecure"
        ),
    )
    TLS_CHECK_HOSTNAME: bool = Field(
        default=True,
        description="Check that the server certificate matches the contact point host name",
    )

    # Connection Pool Configuration
    MAX_CONNECTIONS_PER_HOST: int = Field(
        default=2,
        ge=1,
        description="Maximum connections per host (recommended: 1-3 per CPU core)",
    )
    MIN_CONNECTIONS_PER_HOST: int = Field(
        default=1,
        ge=1,
        description="Minimum connections per host",
    )
    CORE_CONNECTIONS_PER_HOST: int = Field(
        default=1,
        ge=1,
        description="Core connections per host to maintain",
    )
    MAX_REQUESTS_PER_CONNECTION: int = Field(
        default=100,
        ge=1,
        description="Maximum concurrent requests per connection",
    )

    # Datacenter Configuration
    LOCAL_DC: str | None = Field(
        default=None,
        description="Local datacenter name for datacenter-aware routing",
    )
    REPLICATION_STRATEGY: Literal["SimpleStrategy", "NetworkTopologyStrategy"] = Field(
        default="NetworkTopologyStrategy",
        description="Replication strategy for keyspace creation",
    )
    REPLICATION_CONFIG: dict[str, int] | None = Field(
        default={"datacenter1": 1},
        description="Replication configuration (e.g., {'dc1': 3, 'dc2': 2} for NetworkTopologyStrategy)",
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

    @model_validator(mode="after")
    def validate_connection_pool(self) -> Self:
        """Validate connection pool configuration."""
        if self.MIN_CONNECTIONS_PER_HOST > self.MAX_CONNECTIONS_PER_HOST:
            raise InvalidArgumentError(
                argument_name="connection_pool",
                additional_data={"error": "MIN_CONNECTIONS_PER_HOST cannot exceed MAX_CONNECTIONS_PER_HOST"},
            )
        if self.CORE_CONNECTIONS_PER_HOST > self.MAX_CONNECTIONS_PER_HOST:
            raise InvalidArgumentError(
                argument_name="connection_pool",
                additional_data={"error": "CORE_CONNECTIONS_PER_HOST cannot exceed MAX_CONNECTIONS_PER_HOST"},
            )
        return self

    @model_validator(mode="after")
    def validate_replication_config(self) -> Self:
        """Validate replication configuration."""
        if self.REPLICATION_STRATEGY == "NetworkTopologyStrategy" and not self.REPLICATION_CONFIG:
            raise InvalidArgumentError(
                argument_name="replication_config",
                additional_data={"error": "REPLICATION_CONFIG required for NetworkTopologyStrategy"},
            )
        return self

    @model_validator(mode="after")
    def validate_tls(self) -> Self:
        """Validate TLS settings: files need TLS_ENABLED, and the client cert and key come as a pair."""
        if (self.TLS_CERT_FILE is None) != (self.TLS_KEY_FILE is None):
            raise InvalidArgumentError(
                argument_name="tls",
                additional_data={"error": "TLS_CERT_FILE and TLS_KEY_FILE must be provided together"},
            )
        if not self.TLS_ENABLED and (self.TLS_CA_FILE or self.TLS_CERT_FILE):
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
        if not self.TLS_ENABLED:
            return None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        if self.TLS_VERIFY_MODE == "CERT_NONE":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context.check_hostname = self.TLS_CHECK_HOSTNAME
            context.verify_mode = ssl.CERT_REQUIRED
            if self.TLS_CA_FILE:
                context.load_verify_locations(cafile=self.TLS_CA_FILE)
            else:
                context.load_default_certs()
        if self.TLS_CERT_FILE and self.TLS_KEY_FILE:
            context.load_cert_chain(certfile=self.TLS_CERT_FILE, keyfile=self.TLS_KEY_FILE)
        return context
