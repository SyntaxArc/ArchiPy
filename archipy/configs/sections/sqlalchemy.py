"""SQLAlchemy database configurations."""

import contextlib
from typing import Literal, Self
from urllib.parse import quote, urlparse

from pydantic import BaseModel, ConfigDict, Field, PostgresDsn, field_validator, model_validator

from archipy.models.errors import ConfigurationError


class SQLAlchemyConfig(BaseModel):
    """Configuration settings for SQLAlchemy ORM.

    Controls database connection parameters, pooling behavior, and query execution settings.
    """

    # Validation errors must not echo input values: they can contain the DSN and the password
    model_config = ConfigDict(hide_input_in_errors=True)

    DATABASE: str | None = Field(default=None, description="Database name")
    DRIVER_NAME: str = Field(default="postgresql+psycopg", description="Database driver name")
    COUNT_CACHE_ENABLED: bool = Field(
        default=False,
        description="Whether to cache the total count of search queries, so only the first page runs a COUNT",
    )
    COUNT_CACHE_MAX_SIZE: int = Field(default=1000, ge=1, description="Maximum number of cached search query totals")
    COUNT_CACHE_TTL_SECONDS: int = Field(
        default=60,
        ge=1,
        description="Seconds a cached search query total stays valid",
    )
    COUNT_THRESHOLD: int | None = Field(
        default=None,
        ge=0,
        description="Count threshold of search queries: exact totals up to it, a PostgreSQL estimate above it. "
        "When unset, BaseConfig.set_global() fills it with PAGINATION.MAX_ITEMS",
    )
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
    DATABASE: str = Field(default=":memory:", description="SQLite database path")  # ty: ignore[invalid-mutable-override]  # SQLite always has a path; narrows the base str | None
    ISOLATION_LEVEL: str | None = Field(default=None, description="SQLite isolation level")
    PORT: int | None = Field(default=None, description="Not used for SQLite")
    TIMEOUT: float | None = Field(
        default=None,
        ge=0,
        description="Seconds a connection waits for a lock before 'database is locked' (the sqlite3 'timeout', "
        "i.e. the busy timeout). None: the sqlite3 default of 5 seconds",
    )
    CHECK_SAME_THREAD: bool | None = Field(
        default=None,
        description="The sqlite3 'check_same_thread' option of the sync driver. False lets a connection be used "
        "from several threads (the caller must serialize access). None: the driver default. "
        "The async driver ignores it",
    )


class PostgresSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for PostgreSQL SQLAlchemy ORM.

    Extends SQLAlchemyConfig with PostgreSQL-specific settings and URL building.
    """

    POSTGRES_DSN: PostgresDsn | None = Field(default=None, description="PostgreSQL connection URL")
    CONNECT_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Seconds to wait for the connection to be established (None: libpq waits indefinitely)",
    )
    SSL_MODE: Literal["disable", "allow", "prefer", "require", "verify-ca", "verify-full"] | None = Field(
        default=None,
        description="libpq sslmode. 'require' enforces TLS; 'verify-ca' and 'verify-full' also verify the server "
        "certificate (and host name). None: the libpq default ('prefer')",
    )
    SSL_ROOT_CERT: str | None = Field(
        default=None,
        description="Path to the CA certificate file (libpq sslrootcert) used by 'verify-ca' and 'verify-full'",
    )
    SSL_CERT: str | None = Field(default=None, description="Path to the client certificate file (libpq sslcert)")
    SSL_KEY: str | None = Field(default=None, description="Path to the client private key file (libpq sslkey)")
    APPLICATION_NAME: str | None = Field(
        default=None,
        description="Name shown in pg_stat_activity (libpq application_name). None: no name is sent",
    )
    STATEMENT_TIMEOUT_MS: int | None = Field(
        default=None,
        ge=0,
        description="Milliseconds after which the server aborts a statement (session statement_timeout; 0 "
        "disables it). None: the server default",
    )
    LOCK_TIMEOUT_MS: int | None = Field(
        default=None,
        ge=0,
        description="Milliseconds a statement waits for a lock before it is aborted (session lock_timeout; 0 "
        "disables it). None: the server default",
    )
    PREPARE_THRESHOLD: int | None = Field(
        default=None,
        ge=0,
        description="Number of executions of a query after which psycopg prepares it (0 prepares immediately). "
        "None: the psycopg default (5)",
    )
    DISABLE_PREPARED_STATEMENTS: bool = Field(
        default=False,
        description="Never use server-side prepared statements (psycopg prepare_threshold=None). Needed behind "
        "pgbouncer in transaction pooling mode. Takes precedence over PREPARE_THRESHOLD",
    )

    @model_validator(mode="after")
    def validate_ssl_client_pair(self) -> Self:
        """Require the client certificate and key together.

        Returns:
            Self: The validated configuration instance.

        Raises:
            ConfigurationError: If only one of SSL_CERT and SSL_KEY is set.
        """
        if (self.SSL_CERT is None) != (self.SSL_KEY is None):
            raise ConfigurationError(operation="postgres", reason="ssl_cert_and_key_must_be_set_together")
        return self

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
            user_part = quote(str(self.USERNAME), safe="")
            password_part = f":{quote(self.PASSWORD, safe='')}" if self.PASSWORD else ""
            self.POSTGRES_DSN = PostgresDsn(
                url=f"{self.DRIVER_NAME}://{user_part}{password_part}@{self.HOST}:{self.PORT}/{self.DATABASE}",
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

            if parsed.scheme and parsed.scheme != self.DRIVER_NAME:
                self.DRIVER_NAME = parsed.scheme

            _extract_postgres_auth_from_url(parsed, self)
            _extract_postgres_host_port_from_url(parsed, self)

            if self.DATABASE is None and parsed.path and parsed.path.startswith("/"):
                self.DATABASE = parsed.path[1:]

        return self


def _extract_postgres_auth_from_url(parsed: object, config: PostgresSQLAlchemyConfig) -> None:
    """Populate username and password on config from a parsed Postgres DSN."""
    netloc = getattr(parsed, "netloc", "")
    if not netloc:
        return
    auth_part = netloc.split("@")[0] if "@" in netloc else ""
    if ":" in auth_part:
        username, password = auth_part.split(":", 1)
        if config.USERNAME is None:
            config.USERNAME = username
        if config.PASSWORD is None:
            config.PASSWORD = password
    elif auth_part and config.USERNAME is None:
        config.USERNAME = auth_part


def _extract_postgres_host_port_from_url(parsed: object, config: PostgresSQLAlchemyConfig) -> None:
    """Populate host and port on config from a parsed Postgres DSN."""
    netloc = getattr(parsed, "netloc", "")
    host_part = netloc.split("@")[-1] if "@" in netloc else netloc
    if ":" in host_part:
        host, port_str = host_part.split(":", 1)
        if config.HOST is None:
            config.HOST = host
        if config.PORT is None or "PORT" not in config.model_fields_set:
            with contextlib.suppress(ValueError):
                config.PORT = int(port_str)
    elif host_part and config.HOST is None:
        config.HOST = host_part


class MySQLSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for MySQL SQLAlchemy ORM.

    Extends SQLAlchemyConfig with MySQL-specific defaults.
    """

    DRIVER_NAME: str = Field(default="mysql+pymysql", description="MySQL driver name")
    PORT: int | None = Field(default=3306, description="MySQL port")
    SSL_MODE: Literal["required", "verify_ca", "verify_identity"] | None = Field(
        default=None,
        description="TLS mode. 'required' enforces an encrypted connection without verifying the server; "
        "'verify_ca' also verifies the server certificate; 'verify_identity' also verifies the host name. "
        "None: the driver default (no TLS options are passed)",
    )
    SSL_CA: str | None = Field(
        default=None,
        description="Path to the CA certificate file used by 'verify_ca' and 'verify_identity' "
        "(None: the system trust store)",
    )
    SSL_CERT: str | None = Field(default=None, description="Path to the client certificate file")
    SSL_KEY: str | None = Field(default=None, description="Path to the client private key file")
    CONNECT_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Seconds to wait for the connection to be established (None: the driver default of 10)",
    )
    READ_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Seconds to wait for a read from the server (None: wait indefinitely)",
    )
    WRITE_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Seconds to wait for a write to the server (None: wait indefinitely). "
        "The async driver (asyncmy) has no write timeout and ignores it",
    )
    STATEMENT_TIMEOUT_MS: int | None = Field(
        default=None,
        ge=0,
        description="Milliseconds after which the server aborts a read-only SELECT (session max_execution_time; "
        "0 disables it; MySQL 5.7.8+, not MariaDB). None: the server default",
    )
    LOCK_WAIT_TIMEOUT_SECONDS: int | None = Field(
        default=None,
        ge=1,
        description="Seconds an InnoDB statement waits for a row lock (session innodb_lock_wait_timeout). "
        "None: the server default",
    )

    @model_validator(mode="after")
    def validate_ssl_options(self) -> Self:
        """Require SSL_MODE for any TLS file, and the client certificate and key together.

        Returns:
            Self: The validated configuration instance.

        Raises:
            ConfigurationError: If the TLS options are inconsistent.
        """
        if self.SSL_MODE is None and any((self.SSL_CA, self.SSL_CERT, self.SSL_KEY)):
            raise ConfigurationError(operation="mysql", reason="ssl_files_require_ssl_mode")
        if (self.SSL_CERT is None) != (self.SSL_KEY is None):
            raise ConfigurationError(operation="mysql", reason="ssl_cert_and_key_must_be_set_together")
        return self


class StarRocksSQLAlchemyConfig(SQLAlchemyConfig):
    """Configuration settings for Starrocks SQLAlchemy ORM.

    Extends SQLAlchemyConfig with Starrocks-specific settings.

    Note: StarRocks only supports READ COMMITTED isolation level.
    StarRocks uses MySQL protocol which requires explicit connection timeouts
    to prevent indefinite hangs on network issues.
    """

    DRIVER_NAME: str = Field(default="starrocks", description="StarRocks driver name")
    CATALOG: str | None = Field(default=None, description="Starrocks catalog name")
    ISOLATION_LEVEL: str = Field(  # ty: ignore[invalid-mutable-override]  # StarRocks always sets a level; narrows the base str | None
        default="READ COMMITTED",
        description="Transaction isolation level (StarRocks only supports READ COMMITTED)",
    )

    # Override timeout default for StarRocks (MySQL protocol requirement)
    CONNECT_TIMEOUT: int | None = Field(
        default=10,
        description="Timeout in seconds for establishing connection (MySQL protocol default: 10s)",
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
            raise ConfigurationError(
                operation="starrocks",
                reason="isolation_level_not_read_committed",
                additional_data={"got": v},
            )
        return "READ COMMITTED"
