"""MinIO configuration."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class MinioConfig(BaseModel):
    """Configuration settings for MinIO/S3 object storage integration.

    Controls connection parameters and authentication for S3-compatible
    object storage services using boto3.
    """

    ENDPOINT: str | None = Field(default=None, description="MinIO/S3 server endpoint")
    ACCESS_KEY: str | None = Field(default=None, description="Access key for authentication")
    SECRET_KEY: str | None = Field(default=None, description="Secret key for authentication")
    SECURE: bool = Field(default=False, description="Whether to use secure (HTTPS) connection")
    SESSION_TOKEN: str | None = Field(default=None, description="Session token for temporary credentials")
    REGION: str | None = Field(default=None, description="AWS region for S3 compatibility")
    ADDRESSING_STYLE: Literal["auto", "path", "virtual"] = Field(
        default="auto",
        description="S3 addressing style for URLs",
    )
    SIGNATURE_VERSION: str = Field(default="s3v4", description="AWS signature version (s3v4 recommended)")
    CONNECT_TIMEOUT: int = Field(default=60, description="Connection timeout in seconds")
    READ_TIMEOUT: int = Field(default=60, description="Read timeout in seconds")
    MAX_POOL_CONNECTIONS: int = Field(default=10, description="Maximum number of connections in the pool")
    RETRIES_MAX_ATTEMPTS: int = Field(default=3, description="Maximum retry attempts for failed requests")
    RETRIES_MODE: Literal["legacy", "standard", "adaptive"] = Field(default="standard", description="Retry mode")
    USE_SSL: bool | None = Field(default=None, description="Explicitly set SSL usage (overrides SECURE if set)")
    VERIFY_SSL: bool = Field(default=True, description="Verify SSL certificates")
    CA_BUNDLE: str | None = Field(
        default=None,
        description="Path to a CA bundle used to verify SSL certificates (ignored when VERIFY_SSL is False)",
    )
    REQUEST_CHECKSUM_CALCULATION: Literal["when_supported", "when_required"] | None = Field(
        default=None,
        description=(
            "When boto3 calculates request checksums; 'when_required' suits S3-compatible servers that reject "
            "the default CRC32 checksums. None keeps the boto3 default"
        ),
    )
    RESPONSE_CHECKSUM_VALIDATION: Literal["when_supported", "when_required"] | None = Field(
        default=None,
        description="When boto3 validates response checksums. None keeps the boto3 default",
    )
    CLIENT_CERT: str | None = Field(
        default=None,
        description="Path to a client certificate (PEM) for TLS client authentication",
    )
    CLIENT_KEY: str | None = Field(
        default=None,
        description="Path to the private key of CLIENT_CERT; leave unset when the key is inside the certificate file",
    )
    PROXIES: dict[str, str] | None = Field(
        default=None,
        description=(
            "Proxy URLs by protocol, e.g. {'https': 'http://proxy:3128'}; "
            "may embed credentials, so load it from the environment"
        ),
    )
    PROXIES_CONFIG: dict[str, Any] | None = Field(
        default=None,
        description="Extra botocore proxy settings such as proxy_ca_bundle or proxy_client_cert",
    )
    TCP_KEEPALIVE: bool | None = Field(
        default=None,
        description="Enable the TCP keep-alive socket option. None keeps the botocore default (disabled)",
    )
    USER_AGENT_EXTRA: str | None = Field(
        default=None,
        description="Text appended to the User-Agent header of every request",
    )
    PROFILE_NAME: str | None = Field(
        default=None,
        description=(
            "Shared AWS config/credentials profile (including profiles that assume a role). "
            "Explicit ACCESS_KEY/SECRET_KEY/SESSION_TOKEN take precedence over it"
        ),
    )
