"""Configuration templates for various services and components.

This module provides Pydantic models for configuring different services and components
used in the application, including databases, message brokers, authentication services,
and more.
"""

import logging
from typing import Any, Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, PostgresDsn, SecretStr, model_validator

from archipy.models.errors import FailedPreconditionError, InvalidArgumentError


class ElasticSearchConfig(BaseModel):
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
        SSL_VERSION (str | None): Minimum TLS version (e.g., 'TLSv1.2').
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
        KWARG (dict[str, Any]): Additional keyword arguments for Elasticsearch client.
        BATCH_INTERVAL_THRESHOLD_IN_SECONDS (int): Time threshold for batch operations.
        BATCH_DOC_COUNT_THRESHOLD (int): Document count threshold for batch operations.
    """

    HOSTS: list[str] = Field(default=["https://localhost:9200"], description="List of Elasticsearch server hosts")
    HTTP_USER_NAME: str | None = None
    HTTP_PASSWORD: SecretStr | None = None
    CA_CERTS: str | None = Field(default=None, description="Path to CA bundle for SSL verification")
    SSL_ASSERT_FINGERPRINT: str | None = Field(default=None, description="SSL certificate fingerprint for verification")
    VERIFY_CERTS: bool = Field(default=True, description="Whether to verify SSL certificates")
    SSL_VERSION: str | None = Field(default="TLSv1.2", description="Minimum TLS version (e.g., 'TLSv1.2')")
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
    KWARG: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional keyword arguments for Elasticsearch client",
    )
    BATCH_INTERVAL_THRESHOLD_IN_SECONDS: int = Field(default=1, ge=1, description="Time threshold for batch operations")
    BATCH_DOC_COUNT_THRESHOLD: int = Field(
        default=500,
        ge=1,
        description="Document count threshold for batch operations",
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
                logging.warning("Warning: Sniffing may bypass load balancers or proxies, ensure this is intended.")
        return self


class ElasticSearchAPMConfig(BaseModel):
    """Configuration settings for Elasticsearch APM (Application Performance Monitoring).

    Controls behavior of the Elastic APM agent for application monitoring, tracing,
    and error reporting.

    Attributes:
        API_REQUEST_SIZE (str): Maximum size of API requests.
        API_REQUEST_TIME (str): Maximum time for API requests.
        AUTO_LOG_STACKS (bool): Whether to automatically log stack traces.
        CAPTURE_BODY (str): Level of request body capture.
        CAPTURE_HEADERS (bool): Whether to capture HTTP headers.
        COLLECT_LOCAL_VARIABLES (str): Level of local variable collection.
        IS_ENABLED (bool): Whether APM is enabled.
        ENVIRONMENT (str | None): APM environment name.
        LOG_FILE (str): Path to APM log file.
        LOG_FILE_SIZE (str): Maximum size of APM log file.
        RECORDING (bool): Whether to record transactions.
        SECRET_TOKEN (str | None): APM secret token.
        SERVER_TIMEOUT (str): Server timeout duration.
        SERVER_URL (str | None): APM server URL.
        SERVICE_NAME (str): Name of the service being monitored.
        SERVICE_VERSION (str | None): Version of the service.
        TRANSACTION_SAMPLE_RATE (str): Rate at which to sample transactions.
        API_KEY (str | None): API key for authentication.
    """

    API_REQUEST_SIZE: str = "768kb"
    API_REQUEST_TIME: str = "10s"
    AUTO_LOG_STACKS: bool = True
    CAPTURE_BODY: str = "off"
    CAPTURE_HEADERS: bool = False
    COLLECT_LOCAL_VARIABLES: str = "errors"
    IS_ENABLED: bool = False
    ENVIRONMENT: str | None = None
    LOG_FILE: str = ""
    LOG_FILE_SIZE: str = "1mb"
    RECORDING: bool = True
    SECRET_TOKEN: str | None = None
    SERVER_TIMEOUT: str = "5s"
    SERVER_URL: str | None = None
    SERVICE_NAME: str = "unknown-python-service"
    SERVICE_VERSION: str | None = None
    TRANSACTION_SAMPLE_RATE: str = "0.001"
    API_KEY: str | None = None


class FastAPIConfig(BaseModel):
    """Configuration settings for FastAPI applications.

    Controls FastAPI application behavior, including server settings, middleware,
    documentation, and performance parameters.

    Attributes:
        PROJECT_NAME (str): Name of the FastAPI project.
        API_PREFIX (str): URL prefix for API endpoints.
        ACCESS_LOG (bool): Whether to enable access logging.
        BACKLOG (int): Maximum number of queued connections.
        DATE_HEADER (bool): Whether to include date header in responses.
        FORWARDED_ALLOW_IPS (list[str] | None): List of allowed forwarded IPs.
        LIMIT_CONCURRENCY (int | None): Maximum concurrent requests.
        LIMIT_MAX_REQUESTS (int | None): Maximum number of requests.
        CORS_MIDDLEWARE_ALLOW_CREDENTIALS (bool): Whether to allow credentials in CORS.
        CORS_MIDDLEWARE_ALLOW_HEADERS (list[str]): Allowed CORS headers.
        CORS_MIDDLEWARE_ALLOW_METHODS (list[str]): Allowed CORS methods.
        CORS_MIDDLEWARE_ALLOW_ORIGINS (list[str]): Allowed CORS origins.
        PROXY_HEADERS (bool): Whether to trust proxy headers.
        RELOAD (bool): Whether to enable auto-reload.
        SERVER_HEADER (bool): Whether to include server header.
        SERVE_HOST (str): Host to serve the application on.
        SERVE_PORT (int): Port to serve the application on.
        TIMEOUT_GRACEFUL_SHUTDOWN (int | None): Graceful shutdown timeout.
        TIMEOUT_KEEP_ALIVE (int): Keep-alive timeout.
        WORKERS_COUNT (int): Number of worker processes.
        WS_MAX_SIZE (int): Maximum WebSocket message size.
        WS_PER_MESSAGE_DEFLATE (bool): Whether to enable WebSocket compression.
        WS_PING_INTERVAL (float): WebSocket ping interval.
        WS_PING_TIMEOUT (float): WebSocket ping timeout.
        OPENAPI_URL (str | None): URL for OpenAPI schema.
        DOCS_URL (str | None): URL for API documentation.
        RE_DOCS_URL (str | None): URL for ReDoc documentation.
        SWAGGER_UI_PARAMS (dict[str, str] | None): Swagger UI parameters.
    """

    PROJECT_NAME: str = "project_name"
    API_PREFIX: str = "/api"

    ACCESS_LOG: bool = True
    BACKLOG: int = 2048
    DATE_HEADER: bool = True
    FORWARDED_ALLOW_IPS: list[str] | None = None
    LIMIT_CONCURRENCY: int | None = None
    LIMIT_MAX_REQUESTS: int | None = None
    CORS_MIDDLEWARE_ALLOW_CREDENTIALS: bool = True
    CORS_MIDDLEWARE_ALLOW_HEADERS: list[str] = ["*"]
    CORS_MIDDLEWARE_ALLOW_METHODS: list[str] = ["*"]
    CORS_MIDDLEWARE_ALLOW_ORIGINS: list[str] = ["*"]
    PROXY_HEADERS: bool = True
    RELOAD: bool = False
    SERVER_HEADER: bool = True
    SERVE_HOST: str = "0.0.0.0"  # noqa: S104 # Deliberate binding to all interfaces for containerized deployments
    SERVE_PORT: int = 8100
    TIMEOUT_GRACEFUL_SHUTDOWN: int | None = None
    TIMEOUT_KEEP_ALIVE: int = 5
    WORKERS_COUNT: int = 4
    WS_MAX_SIZE: int = 16777216
    WS_PER_MESSAGE_DEFLATE: bool = True
    WS_PING_INTERVAL: float = 20.0
    WS_PING_TIMEOUT: float = 20.0
    OPENAPI_URL: str | None = "/openapi.json"
    DOCS_URL: str | None = None
    RE_DOCS_URL: str | None = None
    SWAGGER_UI_PARAMS: dict[str, str] | None = {"docExpansion": "none"}


class GrpcConfig(BaseModel):
    """Configuration settings for gRPC services.

    Controls gRPC server behavior, including connection parameters,
    performance tuning, and timeout settings.

    Attributes:
        SERVE_PORT (int): Port to serve gRPC on.
        SERVE_HOST (str): Host to serve gRPC on.
        THREAD_WORKER_COUNT (int | None): Number of worker threads.
        THREAD_PER_CPU_CORE (int): Threads per CPU core.
        SERVER_OPTIONS_CONFIG_LIST (list[tuple[str, int]]): Server configuration options.
        STUB_OPTIONS_CONFIG_LIST (list[tuple[str, int | str]]): Client stub configuration options.
    """

    SERVE_PORT: int = 8100
    SERVE_HOST: str = "[::]"  # IPv6 equivalent of 0.0.0.0
    THREAD_WORKER_COUNT: int | None = None
    THREAD_PER_CPU_CORE: int = 40  # Adjust based on thread block to cpu time ratio
    SERVER_OPTIONS_CONFIG_LIST: list[tuple[str, int]] = [
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
    ]

    STUB_OPTIONS_CONFIG_LIST: list[tuple[str, int | str]] = [
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
    ]


class KafkaConfig(BaseModel):
    """Configuration settings for Apache Kafka integration.

    Controls Kafka producer and consumer behavior, including broker connections,
    message delivery guarantees, and performance settings.

    Attributes:
        ACKNOWLEDGE_COUNT (int): Number of acknowledgments required.
        AUTO_OFFSET_RESET (str): Action to take when there is no initial offset.
        BROKERS_LIST (list[str] | None): List of Kafka broker addresses.
        CERT_PEM (str | None): Path to SSL certificate.
        ENABLE_AUTO_COMMIT (bool): Whether to enable auto-commit.
        MAX_BUFFER_MS (int): Maximum time to buffer messages.
        MAX_BUFFER_SIZE (int): Maximum number of messages to buffer.
        PASSWORD (str | None): Password for authentication.
        SASL_MECHANISMS (str): SASL mechanism for authentication.
        SECURITY_PROTOCOL (str): Security protocol to use.
        SESSION_TIMEOUT_MS (int): Session timeout in milliseconds.
        REQUEST_ACK_TIMEOUT_MS (int): Request acknowledgment timeout.
        DELIVERY_MESSAGE_TIMEOUT_MS (int): Message delivery timeout.
        USER_NAME (str | None): Username for authentication.
        LIST_TOPICS_TIMEOUT (int): Timeout for listing topics.
    """

    ACKNOWLEDGE_COUNT: int = 1
    AUTO_OFFSET_RESET: str = "earliest"
    BROKERS_LIST: list[str] | None = None
    CERT_PEM: str | None = None
    ENABLE_AUTO_COMMIT: bool = False
    MAX_BUFFER_MS: int = 1
    MAX_BUFFER_SIZE: int = 1000
    PASSWORD: str | None = None
    SASL_MECHANISMS: str = "SCRAM-SHA-512"
    SECURITY_PROTOCOL: str = "SASL_SSL"
    SESSION_TIMEOUT_MS: int = 6000
    REQUEST_ACK_TIMEOUT_MS: int = 2000
    DELIVERY_MESSAGE_TIMEOUT_MS: int = 2300
    USER_NAME: str | None = None
    LIST_TOPICS_TIMEOUT: int = 1


class KeycloakConfig(BaseModel):
    """Configuration settings for Keycloak integration.

    Controls connection parameters and authentication settings for the Keycloak
    identity and access management service.

    Attributes:
        SERVER_URL (str | None): URL of the Keycloak server.
        CLIENT_ID (str | None): Client ID for authentication.
        REALM_NAME (str): Name of the Keycloak realm.
        CLIENT_SECRET_KEY (str | None): Client secret key.
        VERIFY_SSL (bool): Whether to verify SSL certificates.
        TIMEOUT (int): Request timeout in seconds.
    """

    SERVER_URL: str | None = None
    CLIENT_ID: str | None = None
    REALM_NAME: str = "master"
    CLIENT_SECRET_KEY: str | None = None
    VERIFY_SSL: bool = True
    TIMEOUT: int = 10


class MinioConfig(BaseModel):
    """Configuration settings for MinIO object storage integration.

    Controls connection parameters and authentication for the MinIO S3-compatible
    object storage service.

    Attributes:
        ENDPOINT (str | None): MinIO server endpoint.
        ACCESS_KEY (str | None): Access key for authentication.
        SECRET_KEY (str | None): Secret key for authentication.
        SECURE (bool): Whether to use secure (HTTPS) connection.
        SESSION_TOKEN (str | None): Session token for temporary credentials.
        REGION (str | None): AWS region for S3 compatibility.
    """

    ENDPOINT: str | None = None
    ACCESS_KEY: str | None = None
    SECRET_KEY: str | None = None
    SECURE: bool = False
    SESSION_TOKEN: str | None = None
    REGION: str | None = None


class SQLAlchemyConfig(BaseModel):
    """Configuration settings for SQLAlchemy ORM.

    Controls database connection parameters, pooling behavior, and query execution settings.

    Attributes:
        DATABASE (str | None): Database name.
        DRIVER_NAME (str): Database driver name.
        ECHO (bool): Whether to log SQL statements.
        ECHO_POOL (bool): Whether to log connection pool events.
        ENABLE_FROM_LINTING (bool): Whether to enable SQL linting.
        HIDE_PARAMETERS (bool): Whether to hide SQL parameters in logs.
        HOST (str | None): Database host.
        ISOLATION_LEVEL (str | None): Transaction isolation level.
        PASSWORD (str | None): Database password.
        POOL_MAX_OVERFLOW (int): Maximum number of connections to allow in pool overflow.
        POOL_PRE_PING (bool): Whether to ping connections before use.
        POOL_RECYCLE_SECONDS (int): Number of seconds between connection recycling.
        POOL_RESET_ON_RETURN (str): Action to take when returning connections to pool.
        POOL_SIZE (int): Number of connections to keep open in the pool.
        POOL_TIMEOUT (int): Seconds to wait before giving up on getting a connection.
        POOL_USE_LIFO (bool): Whether to use LIFO for connection pool.
        PORT (int | None): Database port.
        QUERY_CACHE_SIZE (int): Size of the query cache.
        USERNAME (str | None): Database username.
    """

    DATABASE: str | None = None
    DRIVER_NAME: str = "postgresql+psycopg"
    ECHO: bool = False
    ECHO_POOL: bool = False
    ENABLE_FROM_LINTING: bool = True
    HIDE_PARAMETERS: bool = False
    HOST: str | None = None
    ISOLATION_LEVEL: str | None = "REPEATABLE READ"
    PASSWORD: str | None = None
    POOL_MAX_OVERFLOW: int = 1
    POOL_PRE_PING: bool = True
    POOL_RECYCLE_SECONDS: int = 10 * 60
    POOL_RESET_ON_RETURN: str = "rollback"
    POOL_SIZE: int = 20
    POOL_TIMEOUT: int = 30
    POOL_USE_LIFO: bool = True
    PORT: int | None = 5432
    QUERY_CACHE_SIZE: int = 500
    USERNAME: str | None = None


class SqliteSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for SQLite SQLAlchemy ORM.

    Extends SQLAlchemyConfig with SQLite-specific settings.

    Attributes:
        DRIVER_NAME (str): SQLite driver name.
        DATABASE (str): SQLite database path.
        ISOLATION_LEVEL (str | None): SQLite isolation level.
        PORT (str | None): Not used for SQLite.
    """

    DRIVER_NAME: str = "sqlite+aiosqlite"
    DATABASE: str = ":memory:"
    ISOLATION_LEVEL: str | None = None
    PORT: str | None = None


class PostgresSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for PostgreSQL SQLAlchemy ORM.

    Extends SQLAlchemyConfig with PostgreSQL-specific settings and URL building.

    Attributes:
        POSTGRES_DSN (PostgresDsn | None): PostgreSQL connection URL.
    """

    POSTGRES_DSN: PostgresDsn | None = None

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
            self.POSTGRES_DSN = (
                f"{self.DRIVER_NAME}://{self.USERNAME}{password_part}@{self.HOST}:{self.PORT}/{self.DATABASE}"
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

            # Extract scheme/driver
            if self.DRIVER_NAME is None and parsed.scheme:
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
                    try:
                        self.PORT = int(port_str)
                    except ValueError:
                        pass
            elif host_part and self.HOST is None:
                self.HOST = host_part

            # Extract database name
            if self.DATABASE is None and parsed.path and parsed.path.startswith("/"):
                self.DATABASE = parsed.path[1:]

        return self


class StarrocksSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for Starrocks SQLAlchemy ORM.

    Extends SQLAlchemyConfig with Starrocks-specific settings.

    Attributes:
        CATALOG (str | None): Starrocks catalog name.
    """

    CATALOG: str | None = None


class PrometheusConfig(BaseModel):
    """Configuration settings for Prometheus metrics integration.

    Controls whether Prometheus metrics collection is enabled and the port
    for the metrics endpoint.

    Attributes:
        IS_ENABLED (bool): Whether Prometheus metrics are enabled.
        SERVER_PORT (int): Port for the Prometheus metrics endpoint.
    """

    IS_ENABLED: bool = False
    SERVER_PORT: int = 8200


class RedisConfig(BaseModel):
    """Configuration settings for Redis cache integration.

    Controls Redis server connection parameters and client behavior settings.

    Attributes:
        MASTER_HOST (str | None): Redis master host.
        SLAVE_HOST (str | None): Redis slave host.
        PORT (int): Redis server port.
        DATABASE (int): Redis database number.
        PASSWORD (str | None): Redis password.
        DECODE_RESPONSES (Literal[True]): Whether to decode responses.
        VERSION (int): Redis protocol version.
        HEALTH_CHECK_INTERVAL (int): Health check interval in seconds.
    """

    MASTER_HOST: str | None = None
    SLAVE_HOST: str | None = None
    PORT: int = 6379
    DATABASE: int = 0
    PASSWORD: str | None = None
    DECODE_RESPONSES: Literal[True] = True
    VERSION: int = 7
    HEALTH_CHECK_INTERVAL: int = 10


class SentryConfig(BaseModel):
    """Configuration settings for Sentry error tracking integration.

    Controls Sentry client behavior, including DSN, sampling rates, and debug settings.

    Attributes:
        IS_ENABLED (bool): Whether Sentry is enabled.
        DSN (str | None): Sentry DSN for error reporting.
        DEBUG (bool): Whether to enable debug mode.
        RELEASE (str): Application release version.
        SAMPLE_RATE (float): Error sampling rate (0.0 to 1.0).
        TRACES_SAMPLE_RATE (float): Performance monitoring sampling rate (0.0 to 1.0).
    """

    IS_ENABLED: bool = False
    DSN: str | None = None
    DEBUG: bool = False
    RELEASE: str = ""
    SAMPLE_RATE: float = 1.0  # between zero and one
    TRACES_SAMPLE_RATE: float = 0.0  # between zero and one


class KavenegarConfig(BaseModel):
    """Configuration settings for Kavenegar SMS service integration.

    Controls connection parameters and authentication for sending SMS messages
    through the Kavenegar service.

    Attributes:
        SERVER_URL (str | None): Kavenegar API server URL.
        API_KEY (str | None): Kavenegar API key.
        PHONE_NUMBER (str | None): Default sender phone number.
    """

    SERVER_URL: str | None = None
    API_KEY: str | None = None
    PHONE_NUMBER: str | None = None


class AuthConfig(BaseModel):
    """Configuration settings for authentication and security.

    Controls JWT token settings, TOTP configuration, rate limiting,
    password policies, and token security features.

    Attributes:
        SECRET_KEY (SecretStr | None): JWT signing key.
        ACCESS_TOKEN_EXPIRES_IN (int): Access token expiration in seconds.
        REFRESH_TOKEN_EXPIRES_IN (int): Refresh token expiration in seconds.
        HASH_ALGORITHM (str): JWT signing algorithm.
        JWT_ISSUER (str): JWT issuer claim.
        JWT_AUDIENCE (str): JWT audience claim.
        TOKEN_VERSION (int): JWT token version.
        TOTP_SECRET_KEY (SecretStr | None): TOTP master key.
        TOTP_HASH_ALGORITHM (str): TOTP hash algorithm.
        TOTP_LENGTH (int): TOTP code length.
        TOTP_EXPIRES_IN (int): TOTP expiration in seconds.
        TOTP_TIME_STEP (int): TOTP time step in seconds.
        TOTP_VERIFICATION_WINDOW (int): TOTP verification window size.
        TOTP_MAX_ATTEMPTS (int): Maximum TOTP verification attempts.
        TOTP_LOCKOUT_TIME (int): TOTP lockout duration in seconds.
        LOGIN_RATE_LIMIT (int): Login attempts per minute.
        TOTP_RATE_LIMIT (int): TOTP requests per minute.
        PASSWORD_RESET_RATE_LIMIT (int): Password reset requests per hour.
        HASH_ITERATIONS (int): Password hash iterations.
        MIN_LENGTH (int): Minimum password length.
        REQUIRE_DIGIT (bool): Whether password requires digits.
        REQUIRE_LOWERCASE (bool): Whether password requires lowercase.
        REQUIRE_SPECIAL (bool): Whether password requires special chars.
        REQUIRE_UPPERCASE (bool): Whether password requires uppercase.
        SALT_LENGTH (int): Password salt length.
        SPECIAL_CHARACTERS (set[str]): Allowed special characters.
        PASSWORD_HISTORY_SIZE (int): Number of previous passwords to remember.
        ENABLE_JTI_CLAIM (bool): Whether to enable JWT ID claim.
        ENABLE_TOKEN_ROTATION (bool): Whether to enable refresh token rotation.
        REFRESH_TOKEN_REUSE_INTERVAL (int): Refresh token reuse grace period.
    """

    # JWT Settings
    SECRET_KEY: SecretStr | None = None
    ACCESS_TOKEN_EXPIRES_IN: int = 1 * 60 * 60  # 1 hour in seconds
    REFRESH_TOKEN_EXPIRES_IN: int = 24 * 60 * 60  # 24 hours in seconds
    HASH_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "your-app-name"
    JWT_AUDIENCE: str = "your-app-audience"
    TOKEN_VERSION: int = 1

    # TOTP Settings
    TOTP_SECRET_KEY: SecretStr | None = None
    TOTP_HASH_ALGORITHM: str = Field(
        default="SHA1",
        description="Hash algorithm for TOTP generation (SHA1, SHA256, SHA512)",
    )
    TOTP_LENGTH: int = Field(default=6, ge=6, le=8)
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
    HASH_ITERATIONS: int = 100000
    MIN_LENGTH: int = Field(default=12, ge=8)
    REQUIRE_DIGIT: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_SPECIAL: bool = True
    REQUIRE_UPPERCASE: bool = True
    SALT_LENGTH: int = 16
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

    Attributes:
        SMTP_SERVER (str | None): SMTP server host.
        SMTP_PORT (int): SMTP server port.
        USERNAME (str | None): SMTP username.
        PASSWORD (str | None): SMTP password.
        POOL_SIZE (int): Connection pool size.
        CONNECTION_TIMEOUT (int): Connection timeout in seconds.
        MAX_RETRIES (int): Maximum retry attempts.
        ATTACHMENT_MAX_SIZE (int): Maximum attachment size in bytes.
    """

    SMTP_SERVER: str | None = None
    SMTP_PORT: int = 587
    USERNAME: str | None = None
    PASSWORD: str | None = None
    POOL_SIZE: int = 5
    CONNECTION_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    ATTACHMENT_MAX_SIZE: int = 5 * 1024 * 1024


class FileConfig(BaseModel):
    """Configuration settings for file handling capabilities.

    Controls file link security, expiration policies, and file type restrictions.

    Attributes:
        SECRET_KEY (str | None): Secret key for generating secure file links.
        DEFAULT_EXPIRY_MINUTES (int): Default link expiration time in minutes.
        ALLOWED_EXTENSIONS (list[str]): List of allowed file extensions.
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

    Attributes:
        TIME_IR_API_KEY (str | None): API key for time.ir service.
        TIME_IR_API_ENDPOINT (str | None): Endpoint for time.ir service.
        REQUEST_TIMEOUT (int): Request timeout in seconds.
        MAX_RETRIES (int): Maximum retry attempts.
        CACHE_TTL (int): Cache time-to-live in seconds.
    """

    TIME_IR_API_KEY: str | None = "ZAVdqwuySASubByCed5KYuYMzb9uB2f7"
    TIME_IR_API_ENDPOINT: str | None = "https://api.time.ir/v1/event/fa/events/calendar"
    REQUEST_TIMEOUT: int = 5
    MAX_RETRIES: int = 3
    CACHE_TTL: int = 86400  # TTL for cache in seconds (24 hours)


class ElasticsearchConfig(BaseModel):
    """Configuration settings for Elasticsearch integration.

    Controls Elasticsearch server connection parameters, authentication, and client behavior settings.
    This configuration supports both basic authentication and API key authentication methods.

    Attributes:
        HOSTS (list[str]): List of Elasticsearch host URLs (e.g., ['http://localhost:9200']).
        API_KEY (str | None): API key for authentication. If provided, takes precedence over username/password.
        USERNAME (str | None): Username for basic authentication.
        PASSWORD (str | None): Password for basic authentication.
        CLIENT_CERT (str | None): Path to client certificate file for SSL/TLS authentication.
        CLIENT_KEY (str | None): Path to client private key file for SSL/TLS authentication.
        CA_CERTS (str | None): Path to CA certificates file for SSL/TLS verification.
        REQUEST_TIMEOUT (float | None): Timeout in seconds for requests. Defaults to 10.0.
        MAX_RETRIES (int): Maximum number of retries for failed requests. Defaults to 0 (no retries).
        RETRY_ON_STATUS (tuple[int, ...]): HTTP status codes that should trigger a retry.
            Defaults to (429, 502, 503, 504) for rate limiting and server errors.
        RETRY_ON_TIMEOUT (bool): Whether to retry on timeout. Defaults to False.
        HTTP_COMPRESS (bool): Whether to enable HTTP compression. Defaults to False.
        CONNECTIONS_PER_NODE (int): Maximum number of connections per node. Defaults to 10.
        VERIFY_CERTS (bool): Whether to verify SSL certificates. Defaults to True.
    """

    HOSTS: list[str] = []
    API_KEY: str | None = None
    USERNAME: str | None = None
    PASSWORD: str | None = None
    CLIENT_CERT: str | None = None
    CLIENT_KEY: str | None = None
    CA_CERTS: str | None = None
    REQUEST_TIMEOUT: float | None = 10.0
    MAX_RETRIES: int = 0
    RETRY_ON_STATUS: tuple[int, ...] = (429, 502, 503, 504)
    RETRY_ON_TIMEOUT: bool = False
    HTTP_COMPRESS: bool = False
    CONNECTIONS_PER_NODE: int = 10
    VERIFY_CERTS: bool = True
