"""Email configuration."""

from pydantic import BaseModel, Field


class EmailConfig(BaseModel):
    """Configuration settings for email service integration.

    Controls SMTP server connection parameters, authentication,
    and email sending behavior.
    """

    SMTP_SERVER: str | None = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    USERNAME: str | None = Field(default=None, description="SMTP username")
    PASSWORD: str | None = Field(default=None, description="SMTP password")
    POOL_SIZE: int = Field(default=5, description="Connection pool size")
    CONNECTION_TIMEOUT: int = Field(default=30, description="Connection timeout in seconds")
    CONNECTION_REFRESH_SECONDS: int = Field(
        default=300,
        ge=1,
        description="Idle seconds after which a pooled SMTP connection is reconnected",
    )
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    ATTACHMENT_MAX_SIZE: int = Field(default=5 * 1024 * 1024, description="Maximum attachment size in bytes")
