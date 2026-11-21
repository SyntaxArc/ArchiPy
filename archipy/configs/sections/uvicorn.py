"""Uvicorn server configuration."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields
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


class UvicornTlsConfig(BaseModel):
    """TLS settings of the server."""

    model_config = ConfigDict(extra="forbid")

    KEYFILE: str | None = Field(default=None, description="Path to the PEM TLS private key (with SSL_CERTFILE)")
    CERTFILE: str | None = Field(default=None, description="Path to the PEM TLS certificate (with SSL_KEYFILE)")
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
                additional_data={"hint": "Set both SSL_KEYFILE and SSL_CERTFILE"},
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


# Settings of ``UvicornConfig`` that moved into a group: flat name -> (group, field inside the group).
UVICORN_GROUPED_FIELDS = {
    "SSL_KEYFILE": ("TLS", "KEYFILE"),
    "SSL_CERTFILE": ("TLS", "CERTFILE"),
    "SSL_CA_CERTS": ("TLS", "CA_CERTS"),
    "WS_MAX_SIZE": ("WEBSOCKET", "MAX_SIZE"),
    "WS_PER_MESSAGE_DEFLATE": ("WEBSOCKET", "PER_MESSAGE_DEFLATE"),
    "WS_PING_INTERVAL": ("WEBSOCKET", "PING_INTERVAL"),
    "WS_PING_TIMEOUT": ("WEBSOCKET", "PING_TIMEOUT"),
    "BACKLOG": ("LIMITS", "BACKLOG"),
    "LIMIT_CONCURRENCY": ("LIMITS", "CONCURRENCY"),
    "LIMIT_MAX_REQUESTS": ("LIMITS", "MAX_REQUESTS"),
}


class UvicornConfig(BaseModel):
    """Settings of the Uvicorn server that runs a FastAPI application.

    ``AppUtils.uvicorn_config()`` turns them into keyword arguments for ``uvicorn.run`` or ``uvicorn.Config``. The
    same names on ``FASTAPI`` are deprecated; they apply when the matching field here is not set.
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

    SSL_KEYFILE: str | None = Field(
        default=None,
        description="Path to the PEM TLS private key (with SSL_CERTFILE)",
        deprecated=deprecated_flat_message("UVICORN", "SSL_KEYFILE", "TLS", "KEYFILE"),
    )
    SSL_CERTFILE: str | None = Field(
        default=None,
        description="Path to the PEM TLS certificate (with SSL_KEYFILE)",
        deprecated=deprecated_flat_message("UVICORN", "SSL_CERTFILE", "TLS", "CERTFILE"),
    )
    SSL_CA_CERTS: str | None = Field(
        default=None,
        description="Path to the CA bundle that verifies client certificates",
        deprecated=deprecated_flat_message("UVICORN", "SSL_CA_CERTS", "TLS", "CA_CERTS"),
    )
    WS_MAX_SIZE: int = Field(
        default=16777216,
        description="Maximum WebSocket message size in bytes",
        deprecated=deprecated_flat_message("UVICORN", "WS_MAX_SIZE", "WEBSOCKET", "MAX_SIZE"),
    )
    WS_PER_MESSAGE_DEFLATE: bool = Field(
        default=True,
        description="Whether to enable WebSocket compression",
        deprecated=deprecated_flat_message("UVICORN", "WS_PER_MESSAGE_DEFLATE", "WEBSOCKET", "PER_MESSAGE_DEFLATE"),
    )
    WS_PING_INTERVAL: float = Field(
        default=20.0,
        description="WebSocket ping interval in seconds",
        deprecated=deprecated_flat_message("UVICORN", "WS_PING_INTERVAL", "WEBSOCKET", "PING_INTERVAL"),
    )
    WS_PING_TIMEOUT: float = Field(
        default=20.0,
        description="WebSocket ping timeout in seconds",
        deprecated=deprecated_flat_message("UVICORN", "WS_PING_TIMEOUT", "WEBSOCKET", "PING_TIMEOUT"),
    )
    BACKLOG: int = Field(
        default=2048,
        description="Maximum number of queued connections",
        deprecated=deprecated_flat_message("UVICORN", "BACKLOG", "LIMITS", "BACKLOG"),
    )
    LIMIT_CONCURRENCY: int | None = Field(
        default=None,
        description="Maximum concurrent connections or tasks",
        deprecated=deprecated_flat_message("UVICORN", "LIMIT_CONCURRENCY", "LIMITS", "CONCURRENCY"),
    )
    LIMIT_MAX_REQUESTS: int | None = Field(
        default=None,
        description="Requests served before the worker restarts",
        deprecated=deprecated_flat_message("UVICORN", "LIMIT_MAX_REQUESTS", "LIMITS", "MAX_REQUESTS"),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "TLS",
            UvicornTlsConfig,
            {"SSL_KEYFILE": "KEYFILE", "SSL_CERTFILE": "CERTFILE", "SSL_CA_CERTS": "CA_CERTS"},
        )
        fold_flat_fields(
            self,
            "WEBSOCKET",
            UvicornWebSocketConfig,
            {
                "WS_MAX_SIZE": "MAX_SIZE",
                "WS_PER_MESSAGE_DEFLATE": "PER_MESSAGE_DEFLATE",
                "WS_PING_INTERVAL": "PING_INTERVAL",
                "WS_PING_TIMEOUT": "PING_TIMEOUT",
            },
        )
        fold_flat_fields(
            self,
            "LIMITS",
            UvicornLimitsConfig,
            {"BACKLOG": "BACKLOG", "LIMIT_CONCURRENCY": "CONCURRENCY", "LIMIT_MAX_REQUESTS": "MAX_REQUESTS"},
        )
        return self
