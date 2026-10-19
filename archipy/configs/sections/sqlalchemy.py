"""SQLAlchemy database configurations."""

import contextlib
from typing import Self
from urllib.parse import urlparse

from pydantic import BaseModel, Field, PostgresDsn, field_validator, model_validator

from archipy.models.errors import ConfigurationError


class SQLAlchemyConfig(BaseModel):
    """Configuration settings for SQLAlchemy ORM.

    Controls database connection parameters, pooling behavior, and query execution settings.
    """

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
