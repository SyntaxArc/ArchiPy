"""Uvicorn server configuration."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archipy.models.errors import ConfigurationError


class UvicornTlsConfig(BaseModel):
    """TLS settings of the server."""

    model_config = ConfigDict(extra="forbid")

    KEYFILE: str | None = Field(default=None, description="Path to the PEM TLS private key (with CERTFILE)")
    CERTFILE: str | None = Field(default=None, description="Path to the PEM TLS certificate (with KEYFILE)")
    CA_CERTS: str | None = Field(
        default=None,
        description="Path to the CA bundle that verifies client certificates",
    )

    @model_validator(mode="after")
    def validate_tls_pair(self) -> Self:
        """Require the TLS key and certificate together.

        Raises:
            ConfigurationError: If only one of KEYFILE and CERTFILE is set.
        """
        if (self.KEYFILE is None) != (self.CERTFILE is None):
            raise ConfigurationError(
                operation="uvicorn",
                reason="ssl_keyfile_and_certfile_required_together",
                additional_data={"hint": "Set both UVICORN.TLS.KEYFILE and UVICORN.TLS.CERTFILE"},
            )
        return self


class UvicornWebSocketConfig(BaseModel):
    """WebSocket settings."""

    model_config = ConfigDict(extra="forbid")

    MAX_SIZE: int = Field(default=16777216, description="Maximum WebSocket message size in bytes")
    PER_MESSAGE_DEFLATE: bool = Field(default=True, description="Whether to enable WebSocket compression")
    PING_INTERVAL: float = Field(default=20.0, description="WebSocket ping interval in seconds")
    PING_TIMEOUT: float = Field(default=20.0, description="WebSocket ping timeout in seconds")


class UvicornLimitsConfig(BaseModel):
    """Connection and request limits."""

    model_config = ConfigDict(extra="forbid")

    BACKLOG: int = Field(default=2048, description="Maximum number of queued connections")
    CONCURRENCY: int | None = Field(default=None, description="Maximum concurrent connections or tasks")
    MAX_REQUESTS: int | None = Field(default=None, description="Requests served before the worker restarts")


class UvicornConfig(BaseModel):
    """Settings of the Uvicorn server that runs a FastAPI application.

    ``AppUtils.uvicorn_config()`` turns them into keyword arguments for ``uvicorn.run`` or ``uvicorn.Config``.
    """

    ACCESS_LOG: bool = Field(default=True, description="Whether to enable access logging")
    DATE_HEADER: bool = Field(default=True, description="Whether to include the Date header in responses")
    FORWARDED_ALLOW_IPS: list[str] | None = Field(
        default=None,
        description="Proxy IPs whose X-Forwarded-* headers are trusted (None: uvicorn's default, 127.0.0.1)",
    )
    PROXY_HEADERS: bool = Field(default=True, description="Whether to trust X-Forwarded-* proxy headers")
    RELOAD: bool = Field(default=False, description="Whether to enable auto-reload")
    SERVER_HEADER: bool = Field(default=True, description="Whether to include the Server header in responses")
    TIMEOUT_GRACEFUL_SHUTDOWN: int | None = Field(default=None, description="Graceful shutdown timeout in seconds")
    TIMEOUT_KEEP_ALIVE: int = Field(default=5, description="Keep-alive timeout in seconds")
    WORKERS_COUNT: int = Field(default=4, description="Number of worker processes (ignored with RELOAD)")

    TLS: UvicornTlsConfig = Field(default_factory=UvicornTlsConfig, description="TLS settings of the server")
    WEBSOCKET: UvicornWebSocketConfig = Field(default_factory=UvicornWebSocketConfig, description="WebSocket settings")
    LIMITS: UvicornLimitsConfig = Field(
        default_factory=UvicornLimitsConfig,
        description="Connection and request limits",
    )
