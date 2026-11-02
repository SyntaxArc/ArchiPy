"""Elasticsearch configuration."""

import logging
import ssl
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.models.errors import FailedPreconditionError, InvalidArgumentError

logger = logging.getLogger(__name__)

# Backoff cap applied when only RETRY_BACKOFF_BASE is set (the client needs both to back off)
DEFAULT_RETRY_BACKOFF_CAP = 30.0


class ElasticsearchConfig(BaseModel):
    """Configuration settings for Elasticsearch connections and operations.

    Contains settings related to Elasticsearch server connectivity, authentication,
    TLS/SSL, request handling, node status management, and batch operation parameters.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    HOSTS: list[str] = Field(default=["https://localhost:9200"], description="List of Elasticsearch server hosts")
    HTTP_USER_NAME: str | None = None
    HTTP_PASSWORD: SecretStr | None = None
    API_KEY: str | None = None
    API_SECRET: SecretStr | None = None
    BEARER_AUTH: SecretStr | None = Field(
        default=None,
        description="Bearer token for token or OIDC auth (exclusive with API key and basic auth)",
    )
    CLOUD_ID: str | None = Field(
        default=None,
        description="Elastic Cloud ID; when set it replaces HOSTS",
    )
    CA_CERTS: str | None = Field(default=None, description="Path to CA bundle for SSL verification")
    SSL_ASSERT_FINGERPRINT: str | None = Field(default=None, description="SSL certificate fingerprint for verification")
    VERIFY_CERTS: bool = Field(default=True, description="Whether to verify SSL certificates")
    CLIENT_CERT: str | None = Field(default=None, description="Path to client certificate for TLS authentication")
    CLIENT_KEY: str | None = Field(default=None, description="Path to client key for TLS authentication")
    SSL_VERSION: ssl.TLSVersion | None = Field(
        default=None,
        description="TLS protocol version (client default if unset)",
    )
    SSL_CONTEXT: ssl.SSLContext | None = Field(
        default=None,
        description="Custom SSL context; takes precedence over the other TLS file settings in the client",
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
    MAX_RETRIES: int = Field(default=1, ge=0, description="Maximum number of retries per request")
    RETRY_ON_TIMEOUT: bool = Field(default=True, description="Retry on connection timeouts")
    RETRY_ON_STATUS: tuple[int, ...] = Field(default=(429, 502, 503, 504), description="HTTP status codes to retry on")
    RETRY_BACKOFF_BASE: float | None = Field(
        default=None,
        gt=0,
        description="Base delay in seconds for exponential retry backoff (None: retry immediately)",
    )
    RETRY_BACKOFF_CAP: float | None = Field(
        default=None,
        gt=0,
        description="Maximum delay in seconds between retries (None: client default)",
    )
    IGNORE_STATUS: tuple[int, ...] = Field(default=(), description="HTTP status codes to ignore as errors")
    SNIFF_ON_START: bool = Field(default=False, description="Sniff nodes on client instantiation")
    SNIFF_BEFORE_REQUESTS: bool = Field(default=False, description="Sniff nodes before requests")
    SNIFF_ON_NODE_FAILURE: bool = Field(default=True, description="Sniff nodes on node failure")
    MIN_DELAY_BETWEEN_SNIFFING: float = Field(
        default=60.0,
        ge=0.0,
        description="Minimum delay between sniffing attempts in seconds (needs SNIFF_BEFORE_REQUESTS)",
    )
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

    @model_validator(mode="after")
    def validate_auth_settings(self) -> Self:
        """Validate auth settings: no partial credential pairs, no bearer auth mixed with another method."""
        if bool(self.API_KEY) != bool(self.API_SECRET):
            raise InvalidArgumentError(argument_name="API_KEY and API_SECRET")
        if bool(self.HTTP_USER_NAME) != bool(self.HTTP_PASSWORD):
            raise InvalidArgumentError(argument_name="HTTP_USER_NAME and HTTP_PASSWORD")
        has_api_key = bool(self.API_KEY and self.API_SECRET)
        has_basic = bool(self.HTTP_USER_NAME and self.HTTP_PASSWORD)
        if self.BEARER_AUTH and (has_api_key or has_basic):
            raise InvalidArgumentError()
        return self

    @model_validator(mode="after")
    def warn_insecure_transport(self) -> Self:
        """Warn when credentials travel over plaintext HTTP or without certificate verification."""
        if not (self.API_KEY or self.HTTP_USER_NAME or self.BEARER_AUTH):
            return self
        if not self.CLOUD_ID and any(host.lower().startswith("http://") for host in self.HOSTS):
            logger.warning("Elasticsearch credentials are sent over plaintext http://; use https:// hosts.")
        if not self.VERIFY_CERTS:
            logger.warning("Elasticsearch credentials are sent with VERIFY_CERTS disabled; enable certificate checks.")
        return self

    @model_validator(mode="after")
    def default_retry_backoff_cap(self) -> Self:
        """Set a backoff cap when only the base is given, since the client ignores a lone base."""
        if self.RETRY_BACKOFF_BASE is not None and self.RETRY_BACKOFF_CAP is None:
            self.RETRY_BACKOFF_CAP = max(self.RETRY_BACKOFF_BASE, DEFAULT_RETRY_BACKOFF_CAP)
        return self

    @model_validator(mode="after")
    def validate_tls_settings(self) -> Self:
        """Validate TLS-related settings to ensure compatibility."""
        if not self.VERIFY_CERTS and (self.CA_CERTS or self.SSL_ASSERT_FINGERPRINT):
            raise InvalidArgumentError()
        if self.CLIENT_CERT and not self.CLIENT_KEY:
            raise FailedPreconditionError()
        if self.CLIENT_KEY and not self.CLIENT_CERT:
            raise InvalidArgumentError(argument_name="CLIENT_KEY")
        return self

    @model_validator(mode="after")
    def validate_sniffing_settings(self) -> Self:
        """Warn if sniffing is enabled with a load balancer."""
        if (
            any([self.SNIFF_ON_START, self.SNIFF_BEFORE_REQUESTS, self.SNIFF_ON_NODE_FAILURE])
            and len(self.HOSTS) == 1
            and "localhost" not in self.HOSTS[0]
        ):
            logger.warning("Warning: Sniffing may bypass load balancers or proxies, ensure this is intended.")
        return self
