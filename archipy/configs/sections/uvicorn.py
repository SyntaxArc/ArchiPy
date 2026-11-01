"""Uvicorn server configuration."""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from archipy.models.errors import ConfigurationError

# Uvicorn settings that ``FastAPIConfig`` used to hold; they still work there as a fallback and are deprecated.
UVICORN_FIELDS_ON_FASTAPI = (
    "ACCESS_LOG",
    "BACKLOG",
    "DATE_HEADER",
    "FORWARDED_ALLOW_IPS",
    "LIMIT_CONCURRENCY",
    "LIMIT_MAX_REQUESTS",
    "PROXY_HEADERS",
    "RELOAD",
    "SERVER_HEADER",
    "TIMEOUT_GRACEFUL_SHUTDOWN",
    "TIMEOUT_KEEP_ALIVE",
    "WORKERS_COUNT",
    "WS_MAX_SIZE",
    "WS_PER_MESSAGE_DEFLATE",
    "WS_PING_INTERVAL",
    "WS_PING_TIMEOUT",
)


class UvicornConfig(BaseModel):
    """Settings of the Uvicorn server that runs a FastAPI application.

    ``AppUtils.uvicorn_config()`` turns them into keyword arguments for ``uvicorn.run`` or ``uvicorn.Config``. The
    same names on ``FASTAPI`` are deprecated; they apply when the matching field here is not set.
    """

    ACCESS_LOG: bool = Field(default=True, description="Whether to enable access logging")
    BACKLOG: int = Field(default=2048, description="Maximum number of queued connections")
    DATE_HEADER: bool = Field(default=True, description="Whether to include the Date header in responses")
    FORWARDED_ALLOW_IPS: list[str] | None = Field(
        default=None,
        description="Proxy IPs whose X-Forwarded-* headers are trusted (None: uvicorn's default, 127.0.0.1)",
    )
    LIMIT_CONCURRENCY: int | None = Field(default=None, description="Maximum concurrent connections or tasks")
    LIMIT_MAX_REQUESTS: int | None = Field(default=None, description="Requests served before the worker restarts")
    PROXY_HEADERS: bool = Field(default=True, description="Whether to trust X-Forwarded-* proxy headers")
    RELOAD: bool = Field(default=False, description="Whether to enable auto-reload")
    SERVER_HEADER: bool = Field(default=True, description="Whether to include the Server header in responses")
    TIMEOUT_GRACEFUL_SHUTDOWN: int | None = Field(default=None, description="Graceful shutdown timeout in seconds")
    TIMEOUT_KEEP_ALIVE: int = Field(default=5, description="Keep-alive timeout in seconds")
    WORKERS_COUNT: int = Field(default=4, description="Number of worker processes (ignored with RELOAD)")
    WS_MAX_SIZE: int = Field(default=16777216, description="Maximum WebSocket message size in bytes")
    WS_PER_MESSAGE_DEFLATE: bool = Field(default=True, description="Whether to enable WebSocket compression")
    WS_PING_INTERVAL: float = Field(default=20.0, description="WebSocket ping interval in seconds")
    WS_PING_TIMEOUT: float = Field(default=20.0, description="WebSocket ping timeout in seconds")
    SSL_KEYFILE: str | None = Field(default=None, description="Path to the PEM TLS private key (with SSL_CERTFILE)")
    SSL_CERTFILE: str | None = Field(default=None, description="Path to the PEM TLS certificate (with SSL_KEYFILE)")
    SSL_CA_CERTS: str | None = Field(
        default=None,
        description="Path to the CA bundle that verifies client certificates",
    )

    @model_validator(mode="after")
    def validate_tls_pair(self) -> Self:
        """Require the TLS key and certificate together.

        Raises:
            ConfigurationError: If only one of SSL_KEYFILE and SSL_CERTFILE is set.
        """
        if (self.SSL_KEYFILE is None) != (self.SSL_CERTFILE is None):
            raise ConfigurationError(
                operation="uvicorn",
                reason="ssl_keyfile_and_certfile_required_together",
                additional_data={"hint": "Set both SSL_KEYFILE and SSL_CERTFILE"},
            )
        return self
