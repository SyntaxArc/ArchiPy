"""Email configuration."""

from typing import Literal

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
    TLS_MODE: Literal["auto", "none", "starttls", "implicit"] = Field(
        default="auto",
        description=(
            "Transport security. 'starttls' requires a successful STARTTLS upgrade, 'implicit' opens a TLS "
            "connection from the start (SMTPS, port 465), 'none' sends in clear text. 'auto' (default, deprecated) "
            "upgrades only when the server offers STARTTLS, without verifying the certificate, and continues in "
            "clear text otherwise"
        ),
    )
    TLS_CA_FILE: str | None = Field(
        default=None,
        description="PEM file with the CA certificates that verify the server (TLS_MODE 'starttls' or 'implicit')",
    )
    TLS_VERIFY: bool = Field(
        default=True,
        description="Verify the server certificate and host name (TLS_MODE 'starttls' or 'implicit')",
    )
    LOCAL_HOSTNAME: str | None = Field(default=None, description="Host name sent in EHLO; defaults to the local FQDN")
    SOURCE_ADDRESS: str | None = Field(default=None, description="Local address the SMTP socket binds to")
    SOURCE_PORT: int = Field(default=0, ge=0, le=65535, description="Local port bound with SOURCE_ADDRESS (0 = any)")
    POOL_SIZE: int = Field(default=5, description="Connection pool size")
    CONNECTION_TIMEOUT: int = Field(default=30, description="Connection timeout in seconds")
    CONNECTION_REFRESH_SECONDS: int = Field(
        default=300,
        ge=1,
        description="Idle seconds after which a pooled SMTP connection is reconnected",
    )
    MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts")
    ATTACHMENT_MAX_SIZE: int = Field(default=5 * 1024 * 1024, description="Maximum attachment size in bytes")
