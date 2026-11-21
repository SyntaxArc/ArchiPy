"""Email configuration."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields


class EmailTlsConfig(BaseModel):
    """TLS settings of the SMTP connection."""

    model_config = ConfigDict(extra="forbid")

    MODE: Literal["auto", "none", "starttls", "implicit"] = Field(
        default="auto",
        description=(
            "Transport security. 'starttls' requires a successful STARTTLS upgrade, 'implicit' opens a TLS "
            "connection from the start (SMTPS, port 465), 'none' sends in clear text. 'auto' (default, deprecated) "
            "upgrades only when the server offers STARTTLS, without verifying the certificate, and continues in "
            "clear text otherwise"
        ),
    )
    CA_FILE: str | None = Field(
        default=None,
        description="PEM file with the CA certificates that verify the server (TLS_MODE 'starttls' or 'implicit')",
    )
    VERIFY: bool = Field(
        default=True,
        description="Verify the server certificate and host name (TLS_MODE 'starttls' or 'implicit')",
    )


class EmailPoolConfig(BaseModel):
    """Connection pool settings."""

    model_config = ConfigDict(extra="forbid")

    SIZE: int = Field(default=5, ge=1, description="Connection pool size")
    CONNECTION_TIMEOUT: int = Field(default=30, gt=0, description="Connection timeout in seconds")
    CONNECTION_REFRESH_SECONDS: int = Field(
        default=300,
        ge=1,
        description="Idle seconds after which a pooled SMTP connection is reconnected",
    )


class EmailAttachmentsConfig(BaseModel):
    """Attachment limits."""

    model_config = ConfigDict(extra="forbid")

    URL_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Timeout in seconds for downloading URL attachments",
    )
    URL_ALLOWED_HOSTS: list[str] | None = Field(
        default=None,
        description="Host names URL attachments may be downloaded from; None allows any host (http and https only)",
    )
    MAX_SIZE: int = Field(default=5 * 1024 * 1024, description="Maximum attachment size in bytes")


class EmailConfig(BaseModel):
    """Configuration settings for email service integration.

    Controls SMTP server connection parameters, authentication,
    and email sending behavior.
    """

    SMTP_SERVER: str | None = Field(default=None, description="SMTP server host")
    SMTP_PORT: int = Field(default=587, description="SMTP server port")
    USERNAME: str | None = Field(default=None, description="SMTP username")
    PASSWORD: str | None = Field(default=None, description="SMTP password")
    FROM_ADDRESS: str | None = Field(
        default=None,
        description="Sender address of outgoing emails; defaults to USERNAME, which is invalid for API-key usernames",
    )
    LOCAL_HOSTNAME: str | None = Field(default=None, description="Host name sent in EHLO; defaults to the local FQDN")
    SOURCE_ADDRESS: str | None = Field(default=None, description="Local address the SMTP socket binds to")
    SOURCE_PORT: int = Field(default=0, ge=0, le=65535, description="Local port bound with SOURCE_ADDRESS (0 = any)")
    MAX_RETRIES: int = Field(default=3, ge=1, description="Maximum retry attempts")

    TLS: EmailTlsConfig = Field(default_factory=EmailTlsConfig, description="TLS settings of the SMTP connection")
    POOL: EmailPoolConfig = Field(default_factory=EmailPoolConfig, description="Connection pool settings")
    ATTACHMENTS: EmailAttachmentsConfig = Field(default_factory=EmailAttachmentsConfig, description="Attachment limits")

    TLS_MODE: Literal["auto", "none", "starttls", "implicit"] = Field(
        default="auto",
        description=(
            "Transport security. 'starttls' requires a successful STARTTLS upgrade, 'implicit' opens a TLS "
            "connection from the start (SMTPS, port 465), 'none' sends in clear text. 'auto' (default, deprecated) "
            "upgrades only when the server offers STARTTLS, without verifying the certificate, and continues in "
            "clear text otherwise"
        ),
        deprecated=deprecated_flat_message("EMAIL", "TLS_MODE", "TLS", "MODE"),
    )
    TLS_CA_FILE: str | None = Field(
        default=None,
        description="PEM file with the CA certificates that verify the server (TLS_MODE 'starttls' or 'implicit')",
        deprecated=deprecated_flat_message("EMAIL", "TLS_CA_FILE", "TLS", "CA_FILE"),
    )
    TLS_VERIFY: bool = Field(
        default=True,
        description="Verify the server certificate and host name (TLS_MODE 'starttls' or 'implicit')",
        deprecated=deprecated_flat_message("EMAIL", "TLS_VERIFY", "TLS", "VERIFY"),
    )
    POOL_SIZE: int = Field(
        default=5,
        ge=1,
        description="Connection pool size",
        deprecated=deprecated_flat_message("EMAIL", "POOL_SIZE", "POOL", "SIZE"),
    )
    CONNECTION_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Connection timeout in seconds",
        deprecated=deprecated_flat_message("EMAIL", "CONNECTION_TIMEOUT", "POOL", "CONNECTION_TIMEOUT"),
    )
    CONNECTION_REFRESH_SECONDS: int = Field(
        default=300,
        ge=1,
        description="Idle seconds after which a pooled SMTP connection is reconnected",
        deprecated=deprecated_flat_message("EMAIL", "CONNECTION_REFRESH_SECONDS", "POOL", "CONNECTION_REFRESH_SECONDS"),
    )
    ATTACHMENT_URL_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Timeout in seconds for downloading URL attachments",
        deprecated=deprecated_flat_message("EMAIL", "ATTACHMENT_URL_TIMEOUT", "ATTACHMENTS", "URL_TIMEOUT"),
    )
    ATTACHMENT_URL_ALLOWED_HOSTS: list[str] | None = Field(
        default=None,
        description="Host names URL attachments may be downloaded from; None allows any host (http and https only)",
        deprecated=deprecated_flat_message("EMAIL", "ATTACHMENT_URL_ALLOWED_HOSTS", "ATTACHMENTS", "URL_ALLOWED_HOSTS"),
    )
    ATTACHMENT_MAX_SIZE: int = Field(
        default=5 * 1024 * 1024,
        description="Maximum attachment size in bytes",
        deprecated=deprecated_flat_message("EMAIL", "ATTACHMENT_MAX_SIZE", "ATTACHMENTS", "MAX_SIZE"),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "TLS",
            EmailTlsConfig,
            {"TLS_MODE": "MODE", "TLS_CA_FILE": "CA_FILE", "TLS_VERIFY": "VERIFY"},
        )
        fold_flat_fields(
            self,
            "POOL",
            EmailPoolConfig,
            {
                "POOL_SIZE": "SIZE",
                "CONNECTION_TIMEOUT": "CONNECTION_TIMEOUT",
                "CONNECTION_REFRESH_SECONDS": "CONNECTION_REFRESH_SECONDS",
            },
        )
        fold_flat_fields(
            self,
            "ATTACHMENTS",
            EmailAttachmentsConfig,
            {
                "ATTACHMENT_URL_TIMEOUT": "URL_TIMEOUT",
                "ATTACHMENT_URL_ALLOWED_HOSTS": "URL_ALLOWED_HOSTS",
                "ATTACHMENT_MAX_SIZE": "MAX_SIZE",
            },
        )
        return self
