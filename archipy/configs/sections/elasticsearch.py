"""Elasticsearch configuration."""

__lazy_modules__ = ["archipy.models.errors"]

import logging
import ssl
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.models.errors import FailedPreconditionError, InvalidArgumentError

logger = logging.getLogger(__name__)

# Backoff cap applied when only RETRY_BACKOFF_BASE is set (the client needs both to back off)
DEFAULT_RETRY_BACKOFF_CAP = 30.0


class ElasticsearchAuthConfig(BaseModel):
    """Authentication settings."""

    model_config = ConfigDict(extra="forbid")

    USER_NAME: str | None = None
    PASSWORD: SecretStr | None = None
    API_KEY: str | None = None
    API_SECRET: SecretStr | None = None
    BEARER: SecretStr | None = Field(
        default=None,
        description="Bearer token for token or OIDC auth (exclusive with API key and basic auth)",
    )

    @model_validator(mode="after")
    def validate_auth_settings(self) -> Self:
        """Validate auth settings: no partial credential pairs, no bearer auth mixed with another method."""
        if bool(self.API_KEY) != bool(self.API_SECRET):
            raise InvalidArgumentError(argument_name="API_KEY and API_SECRET")
        if bool(self.USER_NAME) != bool(self.PASSWORD):
            raise InvalidArgumentError(argument_name="HTTP_USER_NAME and HTTP_PASSWORD")
        has_api_key = bool(self.API_KEY and self.API_SECRET)
        has_basic = bool(self.USER_NAME and self.PASSWORD)
        if self.BEARER and (has_api_key or has_basic):
            raise InvalidArgumentError()
        return self


class ElasticsearchTlsConfig(BaseModel):
    """TLS and certificate settings."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    CA_CERTS: str | None = Field(default=None, description="Path to CA bundle for SSL verification")
    ASSERT_FINGERPRINT: str | None = Field(default=None, description="SSL certificate fingerprint for verification")
    VERIFY_CERTS: bool = Field(default=True, description="Whether to verify SSL certificates")
    CLIENT_CERT: str | None = Field(default=None, description="Path to client certificate for TLS authentication")
    CLIENT_KEY: str | None = Field(default=None, description="Path to client key for TLS authentication")
    VERSION: ssl.TLSVersion | None = Field(
        default=None,
        description="TLS protocol version (client default if unset)",
    )
    CONTEXT: ssl.SSLContext | None = Field(
        default=None,
        description="Custom SSL context; takes precedence over the other TLS file settings in the client",
    )

    @model_validator(mode="after")
    def validate_tls_settings(self) -> Self:
        """Validate TLS-related settings to ensure compatibility."""
        if not self.VERIFY_CERTS and (self.CA_CERTS or self.ASSERT_FINGERPRINT):
            raise InvalidArgumentError()
        if self.CLIENT_CERT and not self.CLIENT_KEY:
            raise FailedPreconditionError()
        if self.CLIENT_KEY and not self.CLIENT_CERT:
            raise InvalidArgumentError(argument_name="CLIENT_KEY")
        return self


class ElasticsearchRetryConfig(BaseModel):
    """Retry and backoff settings."""

    model_config = ConfigDict(extra="forbid")

    MAX_RETRIES: int = Field(default=1, ge=0, description="Maximum number of retries per request")
    ON_TIMEOUT: bool = Field(default=True, description="Retry on connection timeouts")
    ON_STATUS: tuple[int, ...] = Field(default=(429, 502, 503, 504), description="HTTP status codes to retry on")
    BACKOFF_BASE: float | None = Field(
        default=None,
        gt=0,
        description="Base delay in seconds for exponential retry backoff (None: retry immediately)",
    )
    BACKOFF_CAP: float | None = Field(
        default=None,
        gt=0,
        description="Maximum delay in seconds between retries (None: client default)",
    )

    @model_validator(mode="after")
    def default_retry_backoff_cap(self) -> Self:
        """Set a backoff cap when only the base is given, since the client ignores a lone base."""
        if self.BACKOFF_BASE is not None and self.BACKOFF_CAP is None:
            self.BACKOFF_CAP = max(self.BACKOFF_BASE, DEFAULT_RETRY_BACKOFF_CAP)
        return self


class ElasticsearchSniffingConfig(BaseModel):
    """Node sniffing settings."""

    model_config = ConfigDict(extra="forbid")

    ON_START: bool = Field(default=False, description="Sniff nodes on client instantiation")
    BEFORE_REQUESTS: bool = Field(default=False, description="Sniff nodes before requests")
    ON_NODE_FAILURE: bool = Field(default=True, description="Sniff nodes on node failure")
    MIN_DELAY: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum delay between sniffing attempts in seconds (needs SNIFF_BEFORE_REQUESTS)",
    )


class ElasticsearchConfig(BaseModel):
    """Configuration settings for Elasticsearch connections and operations.

    Contains settings related to Elasticsearch server connectivity, authentication,
    TLS/SSL, request handling, node status management, and batch operation parameters.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    HOSTS: list[str] = Field(default=["https://localhost:9200"], description="List of Elasticsearch server hosts")
    CLOUD_ID: str | None = Field(
        default=None,
        description="Elastic Cloud ID; when set it replaces HOSTS",
    )
    OPAQUE_ID: str | None = Field(default=None, description="Opaque ID sent as X-Opaque-Id to trace requests")
    HEADERS: dict[str, str] | None = Field(default=None, description="Extra HTTP headers sent with every request")
    HTTP_COMPRESS: bool = Field(default=True, description="Enable HTTP compression (gzip)")
    REQUEST_TIMEOUT: float | None = Field(
        default=1.0,
        description="Timeout for HTTP requests in seconds (1.0 is short for bulk and heavy searches; raise it)",
    )
    IGNORE_STATUS: tuple[int, ...] = Field(default=(), description="HTTP status codes to ignore as errors")
    NODE_SELECTOR_CLASS: Literal["round_robin", "random"] = Field(
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

    AUTH: ElasticsearchAuthConfig = Field(
        default_factory=ElasticsearchAuthConfig,
        description="Authentication settings",
    )
    TLS: ElasticsearchTlsConfig = Field(
        default_factory=ElasticsearchTlsConfig,
        description="TLS and certificate settings",
    )
    RETRY: ElasticsearchRetryConfig = Field(
        default_factory=ElasticsearchRetryConfig,
        description="Retry and backoff settings",
    )
    SNIFFING: ElasticsearchSniffingConfig = Field(
        default_factory=ElasticsearchSniffingConfig,
        description="Node sniffing settings",
    )

    @model_validator(mode="after")
    def warn_insecure_transport(self) -> Self:
        """Warn when credentials travel over plaintext HTTP or without certificate verification."""
        if not (self.AUTH.API_KEY or self.AUTH.USER_NAME or self.AUTH.BEARER):
            return self
        if not self.CLOUD_ID and any(host.lower().startswith("http://") for host in self.HOSTS):
            logger.warning("Elasticsearch credentials are sent over plaintext http://; use https:// hosts.")
        if not self.TLS.VERIFY_CERTS:
            logger.warning(
                "Elasticsearch credentials are sent with TLS.VERIFY_CERTS disabled; enable certificate checks.",
            )
        return self

    @model_validator(mode="after")
    def validate_sniffing_settings(self) -> Self:
        """Warn if sniffing is enabled with a load balancer."""
        if (
            any([self.SNIFFING.ON_START, self.SNIFFING.BEFORE_REQUESTS, self.SNIFFING.ON_NODE_FAILURE])
            and len(self.HOSTS) == 1
            and "localhost" not in self.HOSTS[0]
        ):
            logger.warning("Warning: Sniffing may bypass load balancers or proxies, ensure this is intended.")
        return self
