"""FastAPI configuration."""

from pydantic import BaseModel, ConfigDict, Field, NonNegativeInt


class FastAPIFormLimits(BaseModel):
    """Overrides for the number of fields and files and the size of each text field in bytes."""

    model_config = ConfigDict(extra="forbid")

    MAX_FIELDS: NonNegativeInt | None = Field(default=None, serialization_alias="max_fields")
    MAX_FILES: NonNegativeInt | None = Field(default=None, serialization_alias="max_files")
    MAX_PART_SIZE: NonNegativeInt | None = Field(default=None, serialization_alias="max_part_size")


class FastAPICorsConfig(BaseModel):
    """CORS middleware settings."""

    model_config = ConfigDict(extra="forbid")

    ALLOW_CREDENTIALS: bool = Field(default=True, description="Whether to allow credentials in CORS")
    ALLOW_HEADERS: list[str] = Field(default=["*"], description="Allowed CORS headers")
    ALLOW_METHODS: list[str] = Field(default=["*"], description="Allowed CORS methods")
    ALLOW_ORIGIN_REGEX: str | None = Field(
        default=None,
        description="Regex pattern for allowed origins",
    )
    ALLOW_ORIGINS: list[str] = Field(default=["*"], description="Allowed CORS origins")
    EXPOSE_HEADERS: list[str] = Field(default=[], description="Exposed CORS headers")
    MAX_AGE: int = Field(default=600, description="Preflight cache duration in seconds")


class FastAPIGzipConfig(BaseModel):
    """GZip response compression settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(default=False, description="Whether GZip response compression is enabled")
    MINIMUM_SIZE: int = Field(
        default=500,
        ge=0,
        description="Minimum response body size in bytes before compression is applied",
    )
    COMPRESSLEVEL: int = Field(
        default=6,
        ge=1,
        le=9,
        description="GZip compression level (1=fastest, 9=best compression)",
    )


class FastAPITrustedHostConfig(BaseModel):
    """TrustedHost middleware settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=False,
        description="Whether TrustedHost middleware validates the Host header",
    )
    ALLOWED_HOSTS: list[str] = Field(
        default=[],
        description="Allowed hostnames (e.g. example.com, *.example.com)",
    )
    WWW_REDIRECT: bool = Field(
        default=True,
        description="Redirect www hosts to bare domain when allowed",
    )


class FastAPIHttpsRedirectConfig(BaseModel):
    """HTTPS redirect middleware settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=False,
        description="Whether HTTP requests are redirected to HTTPS",
    )


class FastAPIConfig(BaseModel):
    """Configuration settings for FastAPI applications.

    Controls FastAPI application behavior, including server settings, middleware,
    documentation, and performance parameters.
    """

    PROJECT_NAME: str = Field(default="project_name", description="Name of the FastAPI project")
    API_PREFIX: str = Field(default="/api", description="URL prefix for API endpoints")
    MAX_BODY_SIZE: NonNegativeInt | None = Field(
        default=None,
        description="Maximum total request body size in bytes, including files and multipart overhead",
    )
    FORM_LIMITS: FastAPIFormLimits | None = Field(
        default=None,
        description="Limits for automatic form parsing, with FastAPI defaults for omitted keys",
    )
    SERVE_HOST: str = Field(
        default="127.0.0.1",
        description="Host to serve the application on (set to 0.0.0.0 for container/public binding)",
    )
    SERVE_PORT: int = Field(default=8100, description="Port to serve the application on")
    OPENAPI_URL: str | None = Field(default=None, description="URL for OpenAPI schema")
    DOCS_URL: str | None = Field(default=None, description="URL for API documentation")
    RE_DOC_URL: str | None = Field(default=None, description="URL for ReDoc documentation")
    SWAGGER_UI_PARAMS: dict[str, str] | None = Field(
        default={"docExpansion": "none"},
        description="Swagger UI parameters",
    )

    CORS: FastAPICorsConfig = Field(default_factory=FastAPICorsConfig, description="CORS middleware settings")
    GZIP: FastAPIGzipConfig = Field(default_factory=FastAPIGzipConfig, description="GZip response compression settings")
    TRUSTED_HOST: FastAPITrustedHostConfig = Field(
        default_factory=FastAPITrustedHostConfig,
        description="TrustedHost middleware settings",
    )
    HTTPS_REDIRECT: FastAPIHttpsRedirectConfig = Field(
        default_factory=FastAPIHttpsRedirectConfig,
        description="HTTPS redirect middleware settings",
    )
