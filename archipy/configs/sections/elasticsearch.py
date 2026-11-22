"""Elasticsearch configuration."""

# Error classes are used only by validators, which run when a config is built, not when it is imported.
__lazy_modules__ = ["archipy.models.errors"]

import logging
import ssl
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields
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
    MAP_ERRORS: bool = Field(
        default=False,
        description=(
            "Raise ArchiPy errors instead of raw elasticsearch-py exceptions. "
            "Deprecated default: this will become True in a future release."
        ),
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

    HTTP_USER_NAME: str | None = Field(
        default=None,
        deprecated=deprecated_flat_message("ELASTIC", "HTTP_USER_NAME", "AUTH", "USER_NAME"),
    )
    HTTP_PASSWORD: SecretStr | None = Field(
        default=None,
        deprecated=deprecated_flat_message("ELASTIC", "HTTP_PASSWORD", "AUTH", "PASSWORD"),
    )
    API_KEY: str | None = Field(
        default=None,
        deprecated=deprecated_flat_message("ELASTIC", "API_KEY", "AUTH", "API_KEY"),
    )
    API_SECRET: SecretStr | None = Field(
        default=None,
        deprecated=deprecated_flat_message("ELASTIC", "API_SECRET", "AUTH", "API_SECRET"),
    )
    BEARER_AUTH: SecretStr | None = Field(
        default=None,
        description="Bearer token for token or OIDC auth (exclusive with API key and basic auth)",
        deprecated=deprecated_flat_message("ELASTIC", "BEARER_AUTH", "AUTH", "BEARER"),
    )
    CA_CERTS: str | None = Field(
        default=None,
        description="Path to CA bundle for SSL verification",
        deprecated=deprecated_flat_message("ELASTIC", "CA_CERTS", "TLS", "CA_CERTS"),
    )
    SSL_ASSERT_FINGERPRINT: str | None = Field(
        default=None,
        description="SSL certificate fingerprint for verification",
        deprecated=deprecated_flat_message("ELASTIC", "SSL_ASSERT_FINGERPRINT", "TLS", "ASSERT_FINGERPRINT"),
    )
    VERIFY_CERTS: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
        deprecated=deprecated_flat_message("ELASTIC", "VERIFY_CERTS", "TLS", "VERIFY_CERTS"),
    )
    CLIENT_CERT: str | None = Field(
        default=None,
        description="Path to client certificate for TLS authentication",
        deprecated=deprecated_flat_message("ELASTIC", "CLIENT_CERT", "TLS", "CLIENT_CERT"),
    )
    CLIENT_KEY: str | None = Field(
        default=None,
        description="Path to client key for TLS authentication",
        deprecated=deprecated_flat_message("ELASTIC", "CLIENT_KEY", "TLS", "CLIENT_KEY"),
    )
    SSL_VERSION: ssl.TLSVersion | None = Field(
        default=None,
        description="TLS protocol version (client default if unset)",
        deprecated=deprecated_flat_message("ELASTIC", "SSL_VERSION", "TLS", "VERSION"),
    )
    SSL_CONTEXT: ssl.SSLContext | None = Field(
        default=None,
        description="Custom SSL context; takes precedence over the other TLS file settings in the client",
        deprecated=deprecated_flat_message("ELASTIC", "SSL_CONTEXT", "TLS", "CONTEXT"),
    )
    MAX_RETRIES: int = Field(
        default=1,
        ge=0,
        description="Maximum number of retries per request",
        deprecated=deprecated_flat_message("ELASTIC", "MAX_RETRIES", "RETRY", "MAX_RETRIES"),
    )
    RETRY_ON_TIMEOUT: bool = Field(
        default=True,
        description="Retry on connection timeouts",
        deprecated=deprecated_flat_message("ELASTIC", "RETRY_ON_TIMEOUT", "RETRY", "ON_TIMEOUT"),
    )
    RETRY_ON_STATUS: tuple[int, ...] = Field(
        default=(429, 502, 503, 504),
        description="HTTP status codes to retry on",
        deprecated=deprecated_flat_message("ELASTIC", "RETRY_ON_STATUS", "RETRY", "ON_STATUS"),
    )
    RETRY_BACKOFF_BASE: float | None = Field(
        default=None,
        gt=0,
        description="Base delay in seconds for exponential retry backoff (None: retry immediately)",
        deprecated=deprecated_flat_message("ELASTIC", "RETRY_BACKOFF_BASE", "RETRY", "BACKOFF_BASE"),
    )
    RETRY_BACKOFF_CAP: float | None = Field(
        default=None,
        gt=0,
        description="Maximum delay in seconds between retries (None: client default)",
        deprecated=deprecated_flat_message("ELASTIC", "RETRY_BACKOFF_CAP", "RETRY", "BACKOFF_CAP"),
    )
    SNIFF_ON_START: bool = Field(
        default=False,
        description="Sniff nodes on client instantiation",
        deprecated=deprecated_flat_message("ELASTIC", "SNIFF_ON_START", "SNIFFING", "ON_START"),
    )
    SNIFF_BEFORE_REQUESTS: bool = Field(
        default=False,
        description="Sniff nodes before requests",
        deprecated=deprecated_flat_message("ELASTIC", "SNIFF_BEFORE_REQUESTS", "SNIFFING", "BEFORE_REQUESTS"),
    )
    SNIFF_ON_NODE_FAILURE: bool = Field(
        default=True,
        description="Sniff nodes on node failure",
        deprecated=deprecated_flat_message("ELASTIC", "SNIFF_ON_NODE_FAILURE", "SNIFFING", "ON_NODE_FAILURE"),
    )
    MIN_DELAY_BETWEEN_SNIFFING: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum delay between sniffing attempts in seconds (needs SNIFF_BEFORE_REQUESTS)",
        deprecated=deprecated_flat_message("ELASTIC", "MIN_DELAY_BETWEEN_SNIFFING", "SNIFFING", "MIN_DELAY"),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "AUTH",
            ElasticsearchAuthConfig,
            {
                "HTTP_USER_NAME": "USER_NAME",
                "HTTP_PASSWORD": "PASSWORD",
                "API_KEY": "API_KEY",
                "API_SECRET": "API_SECRET",
                "BEARER_AUTH": "BEARER",
            },
        )
        fold_flat_fields(
            self,
            "TLS",
            ElasticsearchTlsConfig,
            {
                "CA_CERTS": "CA_CERTS",
                "SSL_ASSERT_FINGERPRINT": "ASSERT_FINGERPRINT",
                "VERIFY_CERTS": "VERIFY_CERTS",
                "CLIENT_CERT": "CLIENT_CERT",
                "CLIENT_KEY": "CLIENT_KEY",
                "SSL_VERSION": "VERSION",
                "SSL_CONTEXT": "CONTEXT",
            },
        )
        fold_flat_fields(
            self,
            "RETRY",
            ElasticsearchRetryConfig,
            {
                "MAX_RETRIES": "MAX_RETRIES",
                "RETRY_ON_TIMEOUT": "ON_TIMEOUT",
                "RETRY_ON_STATUS": "ON_STATUS",
                "RETRY_BACKOFF_BASE": "BACKOFF_BASE",
                "RETRY_BACKOFF_CAP": "BACKOFF_CAP",
            },
        )
        fold_flat_fields(
            self,
            "SNIFFING",
            ElasticsearchSniffingConfig,
            {
                "SNIFF_ON_START": "ON_START",
                "SNIFF_BEFORE_REQUESTS": "BEFORE_REQUESTS",
                "SNIFF_ON_NODE_FAILURE": "ON_NODE_FAILURE",
                "MIN_DELAY_BETWEEN_SNIFFING": "MIN_DELAY",
            },
        )
        return self

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
