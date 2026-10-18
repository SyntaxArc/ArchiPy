"""General application configuration (file, pagination, datetime)."""

from pydantic import BaseModel, Field

from archipy.models.runtime_settings import DEFAULT_PAGINATION_MAX_ITEMS


class FileConfig(BaseModel):
    """Configuration settings for file handling capabilities.

    Controls file link security, expiration policies, and file type restrictions.
    """

    SECRET_KEY: str | None = Field(default=None, description="Secret key used for generating secure file links")
    DEFAULT_EXPIRY_MINUTES: int = Field(
        default=60,
        ge=1,
        description="Default number of minutes until link expiration",  # Default 60 minutes (1 hour)
    )
    ALLOWED_EXTENSIONS: list[str] = Field(default=["jpg", "jpeg", "png"], description="List of allowed file extensions")


class PaginationConfig(BaseModel):
    """Configuration settings for pagination limits.

    ``MAX_ITEMS`` bounds how deep a page request may reach, and it is the default ``COUNT_THRESHOLD`` of the
    SQLAlchemy configs: past the last reachable row an exact total is of no use to a paged API.
    """

    MAX_ITEMS: int = Field(
        default=DEFAULT_PAGINATION_MAX_ITEMS,
        ge=1,
        description="Largest page * page_size a pagination request may reach. Also the default COUNT_THRESHOLD of "
        "the SQLAlchemy configs",
    )


class DatetimeConfig(BaseModel):
    """Configuration settings for date and time handling.

    Controls API connections for specialized date/time services
    and date caching behavior.
    """

    TIME_IR_API_KEY: str | None = Field(
        default="ZAVdqwuySASubByCed5KYuYMzb9uB2f7",
        description="API key for time.ir service",
    )
    TIME_IR_API_ENDPOINT: str | None = Field(
        default="https://api.time.ir/v1/event/fa/events/calendar",
        description="Endpoint for time.ir service",
    )
    REQUEST_TIMEOUT: int = Field(default=5, description="Request timeout in seconds")
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    CACHE_TTL: int = Field(default=86400, description="Cache time-to-live in seconds (24 hours)")
    HISTORICAL_CACHE_TTL: int = Field(
        default=604800,
        description="Cache time-to-live for historical dates in seconds (7 days)",
    )
