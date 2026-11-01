"""Elasticsearch configuration."""

import logging
from typing import Self

from pydantic import BaseModel, Field, SecretStr, model_validator

from archipy.models.errors import FailedPreconditionError, InvalidArgumentError

logger = logging.getLogger(__name__)


class ElasticsearchConfig(BaseModel):
    """Configuration settings for Elasticsearch connections and operations.

    Contains settings related to Elasticsearch server connectivity, authentication,
    TLS/SSL, request handling, node status management, and batch operation parameters.
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
        if (
            any([self.SNIFF_ON_START, self.SNIFF_BEFORE_REQUESTS, self.SNIFF_ON_NODE_FAILURE])
            and len(self.HOSTS) == 1
            and "localhost" not in self.HOSTS[0]
        ):
            logger.warning("Warning: Sniffing may bypass load balancers or proxies, ensure this is intended.")
        return self
