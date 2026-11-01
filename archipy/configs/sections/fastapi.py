"""FastAPI configuration."""

import warnings
from typing import Self

from pydantic import BaseModel, Field, model_validator

from archipy.configs.sections.uvicorn import UVICORN_FIELDS_ON_FASTAPI


class FastAPIConfig(BaseModel):
    """Configuration settings for FastAPI applications.

    Controls FastAPI application behavior, including server settings, middleware,
    documentation, and performance parameters.
    """

    PROJECT_NAME: str = Field(default="project_name", description="Name of the FastAPI project")
    API_PREFIX: str = Field(default="/api", description="URL prefix for API endpoints")

    ACCESS_LOG: bool = Field(default=True, description="Whether to enable access logging")
    BACKLOG: int = Field(default=2048, description="Maximum number of queued connections")
    DATE_HEADER: bool = Field(default=True, description="Whether to include date header in responses")
    FORWARDED_ALLOW_IPS: list[str] | None = Field(default=None, description="List of allowed forwarded IPs")
    LIMIT_CONCURRENCY: int | None = Field(default=None, description="Maximum concurrent requests")
    LIMIT_MAX_REQUESTS: int | None = Field(default=None, description="Maximum number of requests")
    CORS_MIDDLEWARE_ALLOW_CREDENTIALS: bool = Field(default=True, description="Whether to allow credentials in CORS")
    CORS_MIDDLEWARE_ALLOW_HEADERS: list[str] = Field(default=["*"], description="Allowed CORS headers")
    CORS_MIDDLEWARE_ALLOW_METHODS: list[str] = Field(default=["*"], description="Allowed CORS methods")
    CORS_MIDDLEWARE_ALLOW_ORIGIN_REGEX: str | None = Field(
        default=None,
        description="Regex pattern for allowed origins",
    )
    CORS_MIDDLEWARE_ALLOW_ORIGINS: list[str] = Field(default=["*"], description="Allowed CORS origins")
    CORS_MIDDLEWARE_EXPOSE_HEADERS: list[str] = Field(default=[], description="Exposed CORS headers")
    CORS_MIDDLEWARE_MAX_AGE: int = Field(default=600, description="Preflight cache duration in seconds")
    GZIP_MIDDLEWARE_IS_ENABLED: bool = Field(default=False, description="Whether GZip response compression is enabled")
    GZIP_MIDDLEWARE_MINIMUM_SIZE: int = Field(
        default=500,
        ge=0,
        description="Minimum response body size in bytes before compression is applied",
    )
    GZIP_MIDDLEWARE_COMPRESSLEVEL: int = Field(
        default=6,
        ge=1,
        le=9,
        description="GZip compression level (1=fastest, 9=best compression)",
    )
    TRUSTED_HOST_MIDDLEWARE_IS_ENABLED: bool = Field(
        default=False,
        description="Whether TrustedHost middleware validates the Host header",
    )
    TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS: list[str] = Field(
        default=[],
        description="Allowed hostnames (e.g. example.com, *.example.com)",
    )
    TRUSTED_HOST_MIDDLEWARE_WWW_REDIRECT: bool = Field(
        default=True,
        description="Redirect www hosts to bare domain when allowed",
    )
    HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED: bool = Field(
        default=False,
        description="Whether HTTP requests are redirected to HTTPS",
    )
    PROXY_HEADERS: bool = Field(default=True, description="Whether to trust proxy headers")
    RELOAD: bool = Field(default=False, description="Whether to enable auto-reload")
    SERVER_HEADER: bool = Field(default=True, description="Whether to include server header")
    SERVE_HOST: str = Field(
        default="127.0.0.1",
        description="Host to serve the application on (set to 0.0.0.0 for container/public binding)",
    )
    SERVE_PORT: int = Field(default=8100, description="Port to serve the application on")
    TIMEOUT_GRACEFUL_SHUTDOWN: int | None = Field(default=None, description="Graceful shutdown timeout")
    TIMEOUT_KEEP_ALIVE: int = Field(default=5, description="Keep-alive timeout")
    WORKERS_COUNT: int = Field(default=4, description="Number of worker processes")
    WS_MAX_SIZE: int = Field(default=16777216, description="Maximum WebSocket message size")
    WS_PER_MESSAGE_DEFLATE: bool = Field(default=True, description="Whether to enable WebSocket compression")
    WS_PING_INTERVAL: float = Field(default=20.0, description="WebSocket ping interval")
    WS_PING_TIMEOUT: float = Field(default=20.0, description="WebSocket ping timeout")
    OPENAPI_URL: str | None = Field(default=None, description="URL for OpenAPI schema")
    DOCS_URL: str | None = Field(default=None, description="URL for API documentation")
    RE_DOC_URL: str | None = Field(default=None, description="URL for ReDoc documentation")
    SWAGGER_UI_PARAMS: dict[str, str] | None = Field(
        default={"docExpansion": "none"},
        description="Swagger UI parameters",
    )

    @model_validator(mode="after")
    def warn_deprecated_uvicorn_fields(self) -> Self:
        """Warn when a deprecated uvicorn setting is set here; ``UVICORN`` holds it now."""
        used = sorted(name for name in UVICORN_FIELDS_ON_FASTAPI if name in self.model_fields_set)
        if used:
            warnings.warn(
                f"FASTAPI.{', FASTAPI.'.join(used)} are deprecated and will be removed in 6.0.0; "
                "set the same names on UVICORN instead",
                DeprecationWarning,
                stacklevel=2,
            )
        return self
