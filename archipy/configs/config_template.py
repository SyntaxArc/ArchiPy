"""Configuration templates for various services and components.

This module provides Pydantic models for configuring different services and components
used in the application, including databases, message brokers, authentication services,
and more.
"""

import contextlib
import logging
from enum import StrEnum
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, PostgresDsn, SecretStr, field_validator, model_validator

from archipy.models.errors import FailedPreconditionError, InvalidArgumentError

logger = logging.getLogger(__name__)


class RedisMode(StrEnum):
    """Redis deployment mode."""

    STANDALONE = "STANDALONE"
    SENTINEL = "SENTINEL"
    CLUSTER = "CLUSTER"


class ElasticsearchConfig(BaseModel):
    """Configuration settings for Elasticsearch connections and operations.

    Contains settings related to Elasticsearch server connectivity, authentication,
    TLS/SSL, request handling, node status management, and batch operation parameters.

    Attributes:
        HOSTS (list[str]): List of Elasticsearch server hosts (e.g., ['https://localhost:9200']).
        HTTP_USER_NAME (str | None): Username for HTTP authentication.
        HTTP_PASSWORD (SecretStr | None): Password for HTTP authentication.
        CA_CERTS (str | None): Path to CA bundle for SSL verification.
        SSL_ASSERT_FINGERPRINT (str | None): SSL certificate fingerprint for verification.
        VERIFY_CERTS (bool): Whether to verify SSL certificates.
        CLIENT_CERT (str | None): Path to client certificate for TLS authentication.
        CLIENT_KEY (str | None): Path to client key for TLS authentication.
        HTTP_COMPRESS (bool): Whether to enable HTTP compression (gzip).
        REQUEST_TIMEOUT (float | None): Timeout for HTTP requests in seconds.
        MAX_RETRIES (int): Maximum number of retries per request.
        RETRY_ON_TIMEOUT (bool): Whether to retry on connection timeouts.
        RETRY_ON_STATUS (tuple[int, ...]): HTTP status codes to retry on.
        IGNORE_STATUS (tuple[int, ...]): HTTP status codes to ignore as errors.
        SNIFF_ON_START (bool): Whether to sniff nodes on client instantiation.
        SNIFF_BEFORE_REQUESTS (bool): Whether to sniff nodes before requests.
        SNIFF_ON_NODE_FAILURE (bool): Whether to sniff nodes on node failure.
        MIN_DELAY_BETWEEN_SNIFFING (float): Minimum delay between sniffing attempts in seconds.
        NODE_SELECTOR_CLASS (str): Node selector strategy ('round_robin' or 'random').
        CONNECTIONS_PER_NODE (int): Number of HTTP connections per node.
        DEAD_NODE_BACKOFF_FACTOR (float): Factor for calculating node timeout duration after failures.
        MAX_DEAD_NODE_BACKOFF (float): Maximum timeout duration for a dead node in seconds.
    """

    HOSTS: list[str] = Field(default=["https://localhost:9200"], description="List of Elasticsearch server hosts")
    HTTP_USER_NAME: str | None = None
    HTTP_PASSWORD: SecretStr | None = None
    API_KEY: str | None = None
    API_SECRET: SecretStr | None = None
    CA_CERTS: str | None = Field(default=None, description="Path to CA bundle for SSL verification")
    SSL_ASSERT_FINGERPRINT: str | None = Field(default=None, description="SSL certificate fingerprint for verification")
    VERIFY_CERTS: bool = Field(default=True, description="Whether to verify SSL certificates")
    CLIENT_CERT: str | None = Field(default=None, description="Path to client certificate for TLS authentication")
    CLIENT_KEY: str | None = Field(default=None, description="Path to client key for TLS authentication")
    HTTP_COMPRESS: bool = Field(default=True, description="Enable HTTP compression (gzip)")
    REQUEST_TIMEOUT: float | None = Field(default=1.0, description="Timeout for HTTP requests in seconds")
    MAX_RETRIES: int = Field(default=1, ge=0, description="Maximum number of retries per request")
    RETRY_ON_TIMEOUT: bool = Field(default=True, description="Retry on connection timeouts")
    RETRY_ON_STATUS: tuple[int, ...] = Field(default=(429, 502, 503, 504), description="HTTP status codes to retry on")
    IGNORE_STATUS: tuple[int, ...] = Field(default=(), description="HTTP status codes to ignore as errors")
    SNIFF_ON_START: bool = Field(default=False, description="Sniff nodes on client instantiation")
    SNIFF_BEFORE_REQUESTS: bool = Field(default=False, description="Sniff nodes before requests")
    SNIFF_ON_NODE_FAILURE: bool = Field(default=True, description="Sniff nodes on node failure")
    MIN_DELAY_BETWEEN_SNIFFING: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum delay between sniffing attempts in seconds",
    )
    NODE_SELECTOR_CLASS: str = Field(
        default="round_robin",
        description="Node selector strategy ('round_robin' or 'random')",
    )
    CONNECTIONS_PER_NODE: int = Field(default=10, ge=1, description="Number of HTTP connections per node")
    DEAD_NODE_BACKOFF_FACTOR: float = Field(
        default=1.0,
        ge=0.0,
        description="Factor for calculating node timeout duration after failures",
    )
    MAX_DEAD_NODE_BACKOFF: float = Field(
        default=300.0,
        ge=0.0,
        description="Maximum timeout duration for a dead node in seconds",
    )

    @model_validator(mode="after")
    def validate_tls_settings(self) -> Self:
        """Validate TLS-related settings to ensure compatibility."""
        if not self.VERIFY_CERTS and (self.CA_CERTS or self.SSL_ASSERT_FINGERPRINT):
            raise InvalidArgumentError()
        if self.CLIENT_CERT and not self.CLIENT_KEY:
            raise FailedPreconditionError()
        return self

    @model_validator(mode="after")
    def validate_sniffing_settings(self) -> Self:
        """Warn if sniffing is enabled with a load balancer."""
        if any([self.SNIFF_ON_START, self.SNIFF_BEFORE_REQUESTS, self.SNIFF_ON_NODE_FAILURE]):
            if len(self.HOSTS) == 1 and "localhost" not in self.HOSTS[0]:
                logger.warning("Warning: Sniffing may bypass load balancers or proxies, ensure this is intended.")
        return self


class ElasticsearchAPMConfig(BaseModel):
    """Configuration settings for Elasticsearch APM (Application Performance Monitoring).

    Controls behavior of the Elastic APM agent for application monitoring, tracing,
    and error reporting.
    """

    API_REQUEST_SIZE: str = Field(default="768kb", description="Maximum size of API requests")
    API_REQUEST_TIME: str = Field(default="10s", description="Maximum time for API requests")
    AUTO_LOG_STACKS: bool = Field(default=True, description="Whether to automatically log stack traces")
    CAPTURE_BODY: str = Field(default="off", description="Level of request body capture")
    CAPTURE_HEADERS: bool = Field(default=False, description="Whether to capture HTTP headers")
    COLLECT_LOCAL_VARIABLES: str = Field(default="errors", description="Level of local variable collection")
    IS_ENABLED: bool = Field(default=False, description="Whether APM is enabled")
    ENVIRONMENT: str | None = Field(default=None, description="APM environment name")
    LOG_FILE: str = Field(default="", description="Path to APM log file")
    LOG_FILE_SIZE: str = Field(default="50mb", description="Maximum size of APM log file")
    RECORDING: bool = Field(default=True, description="Whether to record transactions")
    SECRET_TOKEN: str | None = Field(default=None, description="APM secret token")
    SERVER_TIMEOUT: str = Field(default="5s", description="Server timeout duration")
    SERVER_URL: str | None = Field(default=None, description="APM server URL")
    SERVICE_NAME: str = Field(default="unknown-python-service", description="Name of the service being monitored")
    SERVICE_VERSION: str | None = Field(default=None, description="Version of the service")
    TRANSACTION_SAMPLE_RATE: float = Field(default=0.001, description="Rate at which to sample transactions")
    API_KEY: str | None = Field(default=None, description="API key for authentication")


class FastAPIConfig(BaseModel):
    """Configuration settings for FastAPI applications.

    Controls FastAPI application behavior, including server settings, middleware,
    documentation, and performance parameters.
    """

    PROJECT_NAME: str = Field(default="project_name", description="Name of the FastAPI project")
    API_PREFIX: str = Field(default="/api", description="URL prefix for API endpoints")

    ACCESS_LOG: bool = Field(default=True, description="Whether to enable access logging")
    BACKLOG: int = Field(default=2048, description="Maximum number of queued connections")
    DATE_HEADER: bool = Field(default=True, description="Whether to include date header in responses")
    FORWARDED_ALLOW_IPS: list[str] | None = Field(default=None, description="List of allowed forwarded IPs")
    LIMIT_CONCURRENCY: int | None = Field(default=None, description="Maximum concurrent requests")
    LIMIT_MAX_REQUESTS: int | None = Field(default=None, description="Maximum number of requests")
    CORS_MIDDLEWARE_ALLOW_CREDENTIALS: bool = Field(default=True, description="Whether to allow credentials in CORS")
    CORS_MIDDLEWARE_ALLOW_HEADERS: list[str] = Field(default=["*"], description="Allowed CORS headers")
    CORS_MIDDLEWARE_ALLOW_METHODS: list[str] = Field(default=["*"], description="Allowed CORS methods")
    CORS_MIDDLEWARE_ALLOW_ORIGINS: list[str] = Field(default=["*"], description="Allowed CORS origins")
    PROXY_HEADERS: bool = Field(default=True, description="Whether to trust proxy headers")
    RELOAD: bool = Field(default=False, description="Whether to enable auto-reload")
    SERVER_HEADER: bool = Field(default=True, description="Whether to include server header")
    SERVE_HOST: str = Field(
        default="0.0.0.0",
        description="Host to serve the application on",
    )  # Deliberate binding to all interfaces for containerized deployments
    SERVE_PORT: int = Field(default=8100, description="Port to serve the application on")
    TIMEOUT_GRACEFUL_SHUTDOWN: int | None = Field(default=None, description="Graceful shutdown timeout")
    TIMEOUT_KEEP_ALIVE: int = Field(default=5, description="Keep-alive timeout")
    WORKERS_COUNT: int = Field(default=4, description="Number of worker processes")
    WS_MAX_SIZE: int = Field(default=16777216, description="Maximum WebSocket message size")
    WS_PER_MESSAGE_DEFLATE: bool = Field(default=True, description="Whether to enable WebSocket compression")
    WS_PING_INTERVAL: float = Field(default=20.0, description="WebSocket ping interval")
    WS_PING_TIMEOUT: float = Field(default=20.0, description="WebSocket ping timeout")
    OPENAPI_URL: str | None = Field(default=None, description="URL for OpenAPI schema")
    DOCS_URL: str | None = Field(default=None, description="URL for API documentation")
    RE_DOC_URL: str | None = Field(default=None, description="URL for ReDoc documentation")
    SWAGGER_UI_PARAMS: dict[str, str] | None = Field(
        default={"docExpansion": "none"},
        description="Swagger UI parameters",
    )


class GrpcConfig(BaseModel):
    """Configuration settings for gRPC services.

    Controls gRPC server behavior, including connection parameters,
    performance tuning, and timeout settings.
    """

    SERVE_PORT: int = Field(default=8100, description="Port to serve gRPC on")
    SERVE_HOST: str = Field(default="[::]", description="Host to serve gRPC on")  # IPv6 equivalent of 0.0.0.0
    THREAD_WORKER_COUNT: int | None = Field(default=None, description="Number of worker threads")
    MAX_CONCURRENT_RPCS: int | None = Field(default=None, description="Maximum number of concurrent requests")
    THREAD_PER_CPU_CORE: int = Field(
        default=40,
        description="Threads per CPU core",
    )  # Adjust based on thread block to cpu time ratio
    SERVER_OPTIONS_CONFIG_LIST: list[tuple[str, int]] = Field(
        default=[
            ("grpc.max_metadata_size", 1 * 1024 * 1024),
            ("grpc.max_message_length", 128 * 1024 * 1024),
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 5000),
            ("grpc.keepalive_timeout_ms", 1000),
            ("grpc.http2.min_ping_interval_without_data_ms", 5000),
            ("grpc.max_connection_idle_ms", 10000),
            ("grpc.max_connection_age_ms", 30000),
            ("grpc.max_connection_age_grace_ms", 5000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_ping_strikes", 0),
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 4000),
        ],
        description="Server configuration options",
    )

    STUB_OPTIONS_CONFIG_LIST: list[tuple[str, int | str]] = Field(
        default=[
            ("grpc.max_metadata_size", 1 * 1024 * 1024),
            ("grpc.max_message_length", 128 * 1024 * 1024),
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 5000),
            ("grpc.keepalive_timeout_ms", 1000),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.keepalive_permit_without_calls", 1),
            (
                "grpc.service_config",
                '{"methodConfig": [{"name": [],'
                ' "timeout": "1s", "waitForReady": true,'
                ' "retryPolicy": {"maxAttempts": 5,'
                ' "initialBackoff": "0.1s",'
                ' "maxBackoff": "1s",'
                ' "backoffMultiplier": 2,'
                ' "retryableStatusCodes": ["UNAVAILABLE", "ABORTED",'
                ' "RESOURCE_EXHAUSTED"]}}]}',
            ),
        ],
        description="Client stub configuration options",
    )


class KafkaConfig(BaseModel):
    """Configuration settings for Apache Kafka integration.

    Controls Kafka producer and consumer behavior, including broker connections,
    message delivery guarantees, and performance settings.
    """

    BROKERS_LIST: list[str] = Field(default=["localhost:9092"], description="List of Kafka broker addresses")
    SECURITY_PROTOCOL: str = Field(default="PLAINTEXT", description="Security protocol for Kafka connections")
    SASL_MECHANISM: str | None = Field(default=None, description="SASL mechanism for authentication")
    USERNAME: str | None = Field(default=None, description="Username for SASL authentication")
    PASSWORD: SecretStr | None = Field(default=None, description="Password for SASL authentication")
    SSL_CA_FILE: str | None = Field(default=None, description="Path to SSL CA certificate file")
    SSL_CERT_FILE: str | None = Field(default=None, description="Path to SSL certificate file")
    SSL_KEY_FILE: str | None = Field(default=None, description="Path to SSL key file")
    ACKS: Literal["0", "1", "all"] = Field(default="all", description="Acknowledgment mode for producers")
    AUTO_OFFSET_RESET: Literal["earliest", "latest", "none"] = Field(
        default="earliest",
        description="Offset reset policy for consumers",
    )
    ENABLE_AUTO_COMMIT: bool = Field(default=False, description="Enable auto-commit for consumer offsets")
    FETCH_MIN_BYTES: int = Field(default=1, ge=1, description="Minimum bytes to fetch per poll")
    SESSION_TIMEOUT_MS: int = Field(default=10000, ge=1000, description="Consumer session timeout (ms)")
    HEARTBEAT_INTERVAL_MS: int = Field(default=3000, ge=100, description="Consumer heartbeat interval (ms)")
    REQUEST_TIMEOUT_MS: int = Field(default=30000, ge=1000, description="Request timeout (ms)")
    DELIVERY_TIMEOUT_MS: int = Field(default=120000, ge=1000, description="Message delivery timeout (ms)")
    COMPRESSION_TYPE: Literal["none", "gzip", "snappy", "lz4", "zstd"] | None = Field(
        default=None,
        description="Compression type for messages",
    )
    LINGER_MS: int = Field(default=0, ge=0, description="Time to buffer messages before sending (ms)")
    BATCH_SIZE: int = Field(default=16384, ge=0, description="Maximum batch size in bytes")
    MAX_IN_FLIGHT_REQUESTS: int = Field(default=5, ge=1, description="Maximum unacknowledged requests per connection")
    RETRIES: int = Field(default=5, ge=0, description="Number of retries for failed producer requests")
    LIST_TOPICS_TIMEOUT_MS: int = Field(default=5000, ge=1000, description="Timeout for listing topics (ms)")
    CLIENT_ID: str = Field(default="kafka-client", description="Client identifier")
    CONNECTIONS_MAX_IDLE_MS: int = Field(
        default=540000,
        description="Close idle connections after this number of milliseconds",
    )
    ENABLE_IDEMPOTENCE: bool = Field(default=False, description="Enable idempotent producer for exactly-once delivery")
    TRANSACTIONAL_ID: str | None = Field(default=None, description="Transactional ID for the producer")
    ISOLATION_LEVEL: Literal["read_uncommitted", "read_committed"] = Field(
        default="read_uncommitted",
        description="Isolation level for consumer",
    )
    MAX_POLL_INTERVAL_MS: int = Field(default=300000, ge=1000, description="Maximum time between poll invocations")
    PARTITION_ASSIGNMENT_STRATEGY: str = Field(
        default="range",
        description="Partition assignment strategy for consumer",
    )
    FETCH_MAX_BYTES: int = Field(
        default=52428800,
        ge=0,
        description="Maximum amount of data the server returns for a fetch request",
    )
    MAX_PARTITION_FETCH_BYTES: int = Field(
        default=1048576,
        ge=0,
        description="Maximum amount of data per partition the server returns",
    )
    QUEUE_BUFFERING_MAX_MESSAGES: int = Field(
        default=100000,
        ge=0,
        description="Maximum number of messages allowed on the producer queue",
    )
    STATISTICS_INTERVAL_MS: int = Field(
        default=0,
        ge=0,
        description="Frequency in milliseconds to send statistics data",
    )

    @model_validator(mode="after")
    def validate_security_settings(self) -> KafkaConfig:
        """Validate security-related settings for Kafka configuration.

        Ensures that SASL authentication settings are properly configured when
        using SASL security protocols, and warns about missing SSL certificates
        when SSL is enabled.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If SASL authentication is incomplete.
        """
        if self.SECURITY_PROTOCOL in ["SASL_PLAINTEXT", "SASL_SSL"]:
            if not (self.SASL_MECHANISM and self.USERNAME and self.PASSWORD):
                raise ValueError("SASL authentication requires SASL_MECHANISM, USERNAME, and PASSWORD to be set.")
        if self.SECURITY_PROTOCOL == "SSL":
            if not (self.SSL_CA_FILE or self.SSL_CERT_FILE or self.SSL_KEY_FILE):
                logger.warning("SSL enabled but no SSL certificates provided; this may cause connection issues.")
        return self

    @model_validator(mode="after")
    def validate_consumer_settings(self) -> KafkaConfig:
        """Validate consumer-specific settings for Kafka configuration.

        Ensures that auto-commit and offset reset settings are compatible,
        and that heartbeat interval is less than session timeout.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If consumer settings are incompatible.
        """
        if self.ENABLE_AUTO_COMMIT and self.AUTO_OFFSET_RESET == "none":
            raise ValueError("ENABLE_AUTO_COMMIT cannot be True when AUTO_OFFSET_RESET is 'none'.")
        if self.HEARTBEAT_INTERVAL_MS >= self.SESSION_TIMEOUT_MS:
            raise ValueError("HEARTBEAT_INTERVAL_MS must be less than SESSION_TIMEOUT_MS.")
        return self

    @model_validator(mode="after")
    def validate_idempotence_and_transactions(self) -> KafkaConfig:
        """Validate idempotence and transaction settings for Kafka configuration.

        Ensures that idempotence is properly configured with 'all' acknowledgments,
        and that transactional producers have idempotence enabled.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If idempotence or transaction settings are invalid.
        """
        if self.ENABLE_IDEMPOTENCE and self.ACKS != "all":
            raise ValueError("ENABLE_IDEMPOTENCE requires ACKS to be 'all'.")
        if self.TRANSACTIONAL_ID is not None and not self.ENABLE_IDEMPOTENCE:
            raise ValueError("TRANSACTIONAL_ID requires ENABLE_IDEMPOTENCE to be True.")
        return self


class KeycloakConfig(BaseModel):
    """Configuration settings for Keycloak integration.

    Controls connection parameters and authentication settings for the Keycloak
    identity and access management service.
    """

    SERVER_URL: str | None = None
    CLIENT_ID: str | None = None
    REALM_NAME: str = "master"
    CLIENT_SECRET_KEY: str | None = None
    VERIFY_SSL: bool = True
    TIMEOUT: int = 10
    IS_ADMIN_MODE_ENABLED: bool = False
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_REALM_NAME: str = "master"


class MinioConfig(BaseModel):
    """Configuration settings for MinIO object storage integration.

    Controls connection parameters and authentication for the MinIO S3-compatible
    object storage service.
    """

    ENDPOINT: str | None = Field(default=None, description="MinIO server endpoint")
    ACCESS_KEY: str | None = Field(default=None, description="Access key for authentication")
    SECRET_KEY: str | None = Field(default=None, description="Secret key for authentication")
    SECURE: bool = Field(default=False, description="Whether to use secure (HTTPS) connection")
    SESSION_TOKEN: str | None = Field(default=None, description="Session token for temporary credentials")
    REGION: str | None = Field(default=None, description="AWS region for S3 compatibility")


class SQLAlchemyConfig(BaseModel):
    """Configuration settings for SQLAlchemy ORM.

    Controls database connection parameters, pooling behavior, and query execution settings.
    """

    DATABASE: str | None = Field(default=None, description="Database name")
    DRIVER_NAME: str = Field(default="postgresql+psycopg", description="Database driver name")
    ECHO: bool = Field(default=False, description="Whether to log SQL statements")
    ECHO_POOL: bool = Field(default=False, description="Whether to log connection pool events")
    ENABLE_FROM_LINTING: bool = Field(default=True, description="Whether to enable SQL linting")
    HIDE_PARAMETERS: bool = Field(default=False, description="Whether to hide SQL parameters in logs")
    HOST: str | None = Field(default=None, description="Database host")
    ISOLATION_LEVEL: str | None = Field(default="REPEATABLE READ", description="Transaction isolation level")
    PASSWORD: str | None = Field(default=None, description="Database password")
    POOL_MAX_OVERFLOW: int = Field(default=1, description="Maximum number of connections to allow in pool overflow")
    POOL_PRE_PING: bool = Field(default=True, description="Whether to ping connections before use")
    POOL_RECYCLE_SECONDS: int = Field(default=10 * 60, description="Number of seconds between connection recycling")
    POOL_RESET_ON_RETURN: str = Field(
        default="rollback",
        description="Action to take when returning connections to pool",
    )
    POOL_SIZE: int = Field(default=20, description="Number of connections to keep open in the pool")
    POOL_TIMEOUT: int = Field(default=30, description="Seconds to wait before giving up on getting a connection")
    POOL_USE_LIFO: bool = Field(default=True, description="Whether to use LIFO for connection pool")
    PORT: int | None = Field(default=5432, description="Database port")
    QUERY_CACHE_SIZE: int = Field(default=500, description="Size of the query cache")
    USERNAME: str | None = Field(default=None, description="Database username")


class SQLiteSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for SQLite SQLAlchemy ORM.

    Extends SQLAlchemyConfig with SQLite-specific settings.
    """

    DRIVER_NAME: str = Field(default="sqlite+aiosqlite", description="SQLite driver name")
    DATABASE: str = Field(default=":memory:", description="SQLite database path")
    ISOLATION_LEVEL: str | None = Field(default=None, description="SQLite isolation level")
    PORT: int | None = Field(default=None, description="Not used for SQLite")


class PostgresSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for PostgreSQL SQLAlchemy ORM.

    Extends SQLAlchemyConfig with PostgreSQL-specific settings and URL building.
    """

    POSTGRES_DSN: PostgresDsn | None = Field(default=None, description="PostgreSQL connection URL")

    @model_validator(mode="after")
    def build_connection_url(self) -> Self:
        """Build and populate DB_URL if not provided but all component parts are present.

        Returns:
            Self: The updated configuration instance.

        Raises:
            ValueError: If required connection parameters are missing.
        """
        if self.POSTGRES_DSN is not None:
            return self

        if all([self.USERNAME, self.HOST, self.PORT, self.DATABASE]):
            password_part = f":{self.PASSWORD}" if self.PASSWORD else ""
            self.POSTGRES_DSN = PostgresDsn(
                url=f"{self.DRIVER_NAME}://{self.USERNAME}{password_part}@{self.HOST}:{self.PORT}/{self.DATABASE}",
            )
        return self

    @model_validator(mode="after")
    def extract_connection_parts(self) -> Self:
        """Extract connection parts from DB_URL if provided but component parts are missing.

        Returns:
            Self: The updated configuration instance.

        Raises:
            ValueError: If the connection URL is invalid.
        """
        if self.POSTGRES_DSN is None:
            return self

        # Check if we need to extract components (if any are None)
        if any(x is None for x in [self.DRIVER_NAME, self.USERNAME, self.HOST, self.PORT, self.DATABASE]):
            url = str(self.POSTGRES_DSN)
            parsed = urlparse(url)

            # Extract scheme/driver (override default if URL scheme is different)
            if parsed.scheme and parsed.scheme != self.DRIVER_NAME:
                self.DRIVER_NAME = parsed.scheme

            # Extract username and password
            if parsed.netloc:
                auth_part = parsed.netloc.split("@")[0] if "@" in parsed.netloc else ""
                if ":" in auth_part:
                    username, password = auth_part.split(":", 1)
                    if self.USERNAME is None:
                        self.USERNAME = username
                    if self.PASSWORD is None:
                        self.PASSWORD = password
                elif auth_part and self.USERNAME is None:
                    self.USERNAME = auth_part

            # Extract host and port
            host_part = parsed.netloc.split("@")[-1] if "@" in parsed.netloc else parsed.netloc
            if ":" in host_part:
                host, port_str = host_part.split(":", 1)
                if self.HOST is None:
                    self.HOST = host
                if self.PORT is None:
                    with contextlib.suppress(ValueError):
                        self.PORT = int(port_str)
            elif host_part and self.HOST is None:
                self.HOST = host_part

            # Extract database name
            if self.DATABASE is None and parsed.path and parsed.path.startswith("/"):
                self.DATABASE = parsed.path[1:]

        return self


class StarRocksSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for Starrocks SQLAlchemy ORM.

    Extends SQLAlchemyConfig with Starrocks-specific settings.

    Note: StarRocks only supports READ COMMITTED isolation level.
    """

    DRIVER_NAME: str = Field(default="starrocks", description="StarRocks driver name")
    CATALOG: str | None = Field(default=None, description="Starrocks catalog name")
    ISOLATION_LEVEL: str = Field(
        default="READ COMMITTED",
        description="Transaction isolation level (StarRocks only supports READ COMMITTED)",
    )

    @field_validator("ISOLATION_LEVEL")
    @classmethod
    def validate_isolation_level(cls, v: str) -> str:
        """Validate that isolation level is READ COMMITTED for StarRocks.

        Args:
            v: The isolation level value to validate.

        Returns:
            The validated isolation level.

        Raises:
            ValueError: If the isolation level is not READ COMMITTED.
        """
        # Normalize the value (handle case variations and underscores)
        normalized = v.upper().replace("_", " ").strip()
        if normalized != "READ COMMITTED":
            raise ValueError(
                f"StarRocks only supports READ COMMITTED isolation level. Got: {v}. "
                "StarRocks does not support other isolation levels like REPEATABLE READ or SERIALIZABLE.",
            )
        return "READ COMMITTED"


class PrometheusConfig(BaseModel):
    """Configuration settings for Prometheus metrics integration.

    Controls whether Prometheus metrics collection is enabled and the port
    for the metrics endpoint.
    """

    IS_ENABLED: bool = Field(default=False, description="Whether Prometheus metrics are enabled")
    SERVER_PORT: int = Field(default=8200, description="Port for the Prometheus metrics endpoint")


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

    # Common settings
    PORT: int = Field(default=6379, description="Default Redis server port")
    DATABASE: int = Field(default=0, description="Redis database number (not used in cluster)")
    PASSWORD: str | None = Field(default=None, description="Redis password")
    DECODE_RESPONSES: Literal[True] = Field(default=True, description="Whether to decode responses")
    VERSION: int = Field(default=7, description="Redis protocol version")
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
                raise ValueError("CLUSTER_NODES must be provided when MODE is 'cluster'")
            if self.DATABASE != 0:
                logger.warning("DATABASE setting ignored in cluster mode")

        elif self.MODE == RedisMode.SENTINEL:
            if not self.SENTINEL_NODES or not self.SENTINEL_SERVICE_NAME:
                raise ValueError("SENTINEL_NODES and SENTINEL_SERVICE_NAME required for sentinel mode")

        elif self.MODE == RedisMode.STANDALONE:
            if not self.MASTER_HOST:
                raise ValueError("MASTER_HOST required for standalone mode")

        return self


class SentryConfig(BaseModel):
    """Configuration settings for Sentry error tracking integration.

    Controls Sentry client behavior, including DSN, sampling rates, and debug settings.
    """

    IS_ENABLED: bool = Field(default=False, description="Whether Sentry is enabled")
    DSN: str | None = Field(default=None, description="Sentry DSN for error reporting")
    DEBUG: bool = Field(default=False, description="Whether to enable debug mode")
    RELEASE: str = Field(default="", description="Application release version")
    SAMPLE_RATE: float = Field(default=1.0, description="Error sampling rate (0.0 to 1.0)")
    TRACES_SAMPLE_RATE: float = Field(default=0.0, description="Performance monitoring sampling rate (0.0 to 1.0)")


class KavenegarConfig(BaseModel):
    """Configuration settings for Kavenegar SMS service integration.

    Controls connection parameters and authentication for sending SMS messages
    through the Kavenegar service.
    """

    SERVER_URL: str | None = Field(default=None, description="Kavenegar API server URL")
    API_KEY: str | None = Field(default=None, description="Kavenegar API key")
    PHONE_NUMBER: str | None = Field(default=None, description="Default sender phone number")


class AuthConfig(BaseModel):
    """Configuration settings for authentication and security.

    Controls JWT token settings, TOTP configuration, rate limiting,
    password policies, and token security features.
    """

    # JWT Settings
    SECRET_KEY: SecretStr | None = Field(default=None, description="JWT signing key")
    ACCESS_TOKEN_EXPIRES_IN: int = Field(
        default=1 * 60 * 60,
        description="Access token expiration in seconds",
    )  # 1 hour
    REFRESH_TOKEN_EXPIRES_IN: int = Field(
        default=24 * 60 * 60,
        description="Refresh token expiration in seconds",
    )  # 24 hours
    HASH_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ISSUER: str = Field(default="your-app-name", description="JWT issuer claim")
    JWT_AUDIENCE: str = Field(default="your-app-audience", description="JWT audience claim")
    TOKEN_VERSION: int = Field(default=1, description="JWT token version")

    # TOTP Settings
    TOTP_SECRET_KEY: SecretStr | None = Field(default=None, description="TOTP master key")
    TOTP_HASH_ALGORITHM: str = Field(
        default="SHA1",
        description="Hash algorithm for TOTP generation (SHA1, SHA256, SHA512)",
    )
    TOTP_LENGTH: int = Field(default=6, ge=6, le=8, description="TOTP code length")
    TOTP_EXPIRES_IN: int = Field(default=300, description="TOTP expiration time in seconds (5 minutes)")
    TOTP_TIME_STEP: int = Field(default=30, description="TOTP time step in seconds")
    TOTP_VERIFICATION_WINDOW: int = Field(default=1, description="Number of time steps to check before/after")
    TOTP_MAX_ATTEMPTS: int = Field(default=3, description="Maximum failed TOTP attempts before lockout")
    TOTP_LOCKOUT_TIME: int = Field(default=300, description="Lockout time in seconds after max attempts")

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT: int = Field(default=5, description="Maximum login attempts per minute")
    TOTP_RATE_LIMIT: int = Field(default=3, description="Maximum TOTP requests per minute")
    PASSWORD_RESET_RATE_LIMIT: int = Field(default=3, description="Maximum password reset requests per hour")

    # Password Policy
    HASH_ITERATIONS: int = Field(default=100000, description="Password hash iterations")
    MIN_LENGTH: int = Field(default=12, ge=8, description="Minimum password length")
    REQUIRE_DIGIT: bool = Field(default=True, description="Whether password requires digits")
    REQUIRE_LOWERCASE: bool = Field(default=True, description="Whether password requires lowercase")
    REQUIRE_SPECIAL: bool = Field(default=True, description="Whether password requires special chars")
    REQUIRE_UPPERCASE: bool = Field(default=True, description="Whether password requires uppercase")
    SALT_LENGTH: int = Field(default=16, description="Password salt length")
    SPECIAL_CHARACTERS: set[str] = Field(default=set("!@#$%^&*()-_+="), description="Set of allowed special characters")
    PASSWORD_HISTORY_SIZE: int = Field(default=3, description="Number of previous passwords to remember")

    # Token Security
    ENABLE_JTI_CLAIM: bool = Field(default=True, description="Enable JWT ID claim for token tracking")
    ENABLE_TOKEN_ROTATION: bool = Field(default=True, description="Enable refresh token rotation")
    REFRESH_TOKEN_REUSE_INTERVAL: int = Field(default=60, description="Grace period for refresh token reuse in seconds")


class EmailConfig(BaseModel):
    """Configuration settings for email service integration.

    Controls SMTP server connection parameters, authentication,
    and email sending behavior.
    """

    SMTP_SERVER: str | None = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    USERNAME: str | None = Field(default=None, description="SMTP username")
    PASSWORD: str | None = Field(default=None, description="SMTP password")
    POOL_SIZE: int = Field(default=5, description="Connection pool size")
    CONNECTION_TIMEOUT: int = Field(default=30, description="Connection timeout in seconds")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    ATTACHMENT_MAX_SIZE: int = Field(default=5 * 1024 * 1024, description="Maximum attachment size in bytes")


class FileConfig(BaseModel):
    """Configuration settings for file handling capabilities.

    Controls file link security, expiration policies, and file type restrictions.
    """

    SECRET_KEY: str | None = Field(default=None, description="Secret key used for generating secure file links")
    DEFAULT_EXPIRY_MINUTES: int = Field(
        default=60,
        ge=1,
        description="Default number of minutes until link expiration",  # Default 60 minutes (1 hour)
    )
    ALLOWED_EXTENSIONS: list[str] = Field(default=["jpg", "jpeg", "png"], description="List of allowed file extensions")


class DatetimeConfig(BaseModel):
    """Configuration settings for date and time handling.

    Controls API connections for specialized date/time services
    and date caching behavior.
    """

    TIME_IR_API_KEY: str | None = Field(
        default="ZAVdqwuySASubByCed5KYuYMzb9uB2f7",
        description="API key for time.ir service",
    )
    TIME_IR_API_ENDPOINT: str | None = Field(
        default="https://api.time.ir/v1/event/fa/events/calendar",
        description="Endpoint for time.ir service",
    )
    REQUEST_TIMEOUT: int = Field(default=5, description="Request timeout in seconds")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    CACHE_TTL: int = Field(default=86400, description="Cache time-to-live in seconds (24 hours)")
    HISTORICAL_CACHE_TTL: int = Field(
        default=604800,
        description="Cache time-to-live for historical dates in seconds (7 days)",
    )


class ParsianShaparakConfig(BaseModel):
    """Configuration settings for Parsian Shaparak payment gateway integration.

    Controls connection parameters and authentication for the Parsian Shaparak
    payment gateway services.
    """

    LOGIN_ACCOUNT: str | None = Field(default=None, description="Merchant login account for authentication")
    PAYMENT_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?WSDL",
        description="WSDL URL for the payment service",
    )
    CONFIRM_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?WSDL",
        description="WSDL URL for the confirm service",
    )
    REVERSAL_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Reverse/ReversalService.asmx?WSDL",
        description="WSDL URL for the reversal service",
    )
    PROXIES: dict[str, str] | None = Field(
        default=None,
        description="Optional HTTP/HTTPS proxy configuration dictionary",
    )


class TemporalConfig(BaseModel):
    """Configuration settings for Temporal workflow engine integration.

    Controls connection parameters, security settings, and timeout configurations
    for Temporal workflow orchestration services.

    Attributes:
        HOST (str): Temporal server host address.
        PORT (int): Temporal server port number.
        NAMESPACE (str): Temporal namespace for workflow isolation.
        TASK_QUEUE (str): Default task queue for workflow and activity execution.
        TLS_CA_CERT (str | None): Path to TLS CA certificate for secure connections.
        TLS_CLIENT_CERT (str | None): Path to TLS client certificate for mutual authentication.
        TLS_CLIENT_KEY (str | None): Path to TLS client private key.
        WORKFLOW_EXECUTION_TIMEOUT (int): Maximum workflow execution time in seconds.
        WORKFLOW_RUN_TIMEOUT (int): Maximum single workflow run time in seconds.
        WORKFLOW_TASK_TIMEOUT (int): Maximum workflow task processing time in seconds.
        ACTIVITY_START_TO_CLOSE_TIMEOUT (int): Maximum activity execution time in seconds.
        ACTIVITY_HEARTBEAT_TIMEOUT (int): Activity heartbeat timeout in seconds.
        RETRY_MAXIMUM_ATTEMPTS (int): Maximum retry attempts for failed activities.
        RETRY_BACKOFF_COEFFICIENT (float): Backoff multiplier for retry delays.
        RETRY_MAXIMUM_INTERVAL (int): Maximum retry interval in seconds.
    """

    HOST: str = Field(default="localhost", description="Temporal server host address")
    PORT: int = Field(default=7233, ge=1, le=65535, description="Temporal server port number")
    NAMESPACE: str = Field(default="default", description="Temporal namespace for workflow isolation")
    TASK_QUEUE: str = Field(default="task-queue", description="Default task queue name")

    # TLS Configuration
    TLS_CA_CERT: str | None = Field(default=None, description="Path to TLS CA certificate")
    TLS_CLIENT_CERT: str | None = Field(default=None, description="Path to TLS client certificate")
    TLS_CLIENT_KEY: str | None = Field(default=None, description="Path to TLS client private key")

    # Workflow Timeout Settings
    WORKFLOW_EXECUTION_TIMEOUT: int = Field(
        default=300,
        ge=1,
        description="Maximum workflow execution time in seconds",
    )
    WORKFLOW_RUN_TIMEOUT: int = Field(
        default=60,
        ge=1,
        description="Maximum single workflow run time in seconds",
    )
    WORKFLOW_TASK_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum workflow task processing time in seconds",
    )

    # Activity Timeout Settings
    ACTIVITY_START_TO_CLOSE_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum activity execution time in seconds",
    )
    ACTIVITY_HEARTBEAT_TIMEOUT: int = Field(
        default=10,
        ge=1,
        description="Activity heartbeat timeout in seconds",
    )

    # Retry Configuration
    RETRY_MAXIMUM_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for failed activities",
    )
    RETRY_BACKOFF_COEFFICIENT: float = Field(
        default=2.0,
        ge=1.0,
        description="Backoff multiplier for retry delays",
    )
    RETRY_MAXIMUM_INTERVAL: int = Field(
        default=60,
        ge=1,
        description="Maximum retry interval in seconds",
    )

    @model_validator(mode="after")
    def validate_tls_configuration(self) -> Self:
        """Validate TLS configuration consistency."""
        tls_fields = [self.TLS_CA_CERT, self.TLS_CLIENT_CERT, self.TLS_CLIENT_KEY]
        tls_provided = [field for field in tls_fields if field is not None]

        if len(tls_provided) > 0 and len(tls_provided) != 3:
            raise InvalidArgumentError()

        return self

    @model_validator(mode="after")
    def validate_timeout_hierarchy(self) -> Self:
        """Validate timeout configuration hierarchy."""
        if self.WORKFLOW_RUN_TIMEOUT >= self.WORKFLOW_EXECUTION_TIMEOUT:
            raise InvalidArgumentError()

        if self.WORKFLOW_TASK_TIMEOUT >= self.WORKFLOW_RUN_TIMEOUT:
            raise InvalidArgumentError()

        return self


class ScyllaDBConfig(BaseModel):
    """Configuration settings for ScyllaDB/Cassandra connections and operations.

    Contains settings related to ScyllaDB cluster connectivity, authentication,
    compression, consistency levels, connection management, retry policies,
    prepared statement caching, and health checks.

    Attributes:
        CONTACT_POINTS (list[str]): List of ScyllaDB node addresses.
        PORT (int): CQL native transport port number.
        KEYSPACE (str | None): Default keyspace name.
        USERNAME (str | None): Username for authentication.
        PASSWORD (SecretStr | None): Password for authentication.
        PROTOCOL_VERSION (int): Protocol version to use.
        COMPRESSION (bool): Enable LZ4 compression.
        CONNECT_TIMEOUT (int): Connection timeout in seconds.
        REQUEST_TIMEOUT (int): Request timeout in seconds.
        CONSISTENCY_LEVEL (Literal): Default consistency level.
        DISABLE_SHARD_AWARENESS (bool): Disable shard awareness (default: False).
        RETRY_POLICY (Literal): Retry policy type (default: "EXPONENTIAL_BACKOFF").
            Options: "EXPONENTIAL_BACKOFF", "FALLTHROUGH", "DOWNGRADING_CONSISTENCY".
        RETRY_MAX_NUM_RETRIES (float): Maximum number of retries for ExponentialBackoffRetryPolicy (default: 3.0).
        RETRY_MIN_INTERVAL (float): Minimum interval in seconds between retries (default: 0.1).
        RETRY_MAX_INTERVAL (float): Maximum interval in seconds between retries (default: 10.0).
        ENABLE_PREPARED_STATEMENT_CACHE (bool): Enable prepared statement caching (default: True).
        PREPARED_STATEMENT_CACHE_SIZE (int): Maximum cached prepared statements (default: 100).
        PREPARED_STATEMENT_CACHE_TTL_SECONDS (int): TTL for cache in seconds (default: 3600).
        HEALTH_CHECK_TIMEOUT (int): Timeout for health check queries in seconds (default: 5).
        ENABLE_CONNECTION_POOL_MONITORING (bool): Enable pool monitoring (default: False).
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
        default="SimpleStrategy",
        description="Replication strategy for keyspace creation",
    )
    REPLICATION_CONFIG: dict[str, int] | None = Field(
        default=None,
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
