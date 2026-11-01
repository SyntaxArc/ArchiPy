"""Keycloak configuration."""

from pydantic import BaseModel, Field, field_validator, model_validator

_TRUE_WORDS = frozenset({"true", "1", "yes", "on", "t", "y"})
_FALSE_WORDS = frozenset({"false", "0", "no", "off", "f", "n"})


class KeycloakConfig(BaseModel):
    """Configuration settings for Keycloak integration.

    Controls connection parameters and authentication settings for the Keycloak
    identity and access management service.
    """

    SERVER_URL: str | None = None
    CLIENT_ID: str | None = None
    REALM_NAME: str = "master"
    CLIENT_SECRET_KEY: str | None = None
    VERIFY_SSL: bool | str = Field(
        default=True,
        description="True/False toggles TLS verification; a string is the path of a CA bundle to verify against",
    )
    TIMEOUT: float = Field(default=10, gt=0, description="Request timeout in seconds (fractions allowed)")
    CLIENT_CERT_FILE: str | None = Field(
        default=None,
        description="Path of a client certificate (PEM) for mutual TLS; a combined cert+key file needs no key file",
    )
    CLIENT_KEY_FILE: str | None = Field(
        default=None,
        description="Path of the private key matching CLIENT_CERT_FILE",
    )
    MAX_RETRIES: int = Field(default=1, ge=0, description="Total times an HTTP request to Keycloak is retried")
    POOL_MAXSIZE: int | None = Field(default=None, ge=1, description="Maximum connections kept in the pool")
    PROXIES: dict[str, str] | None = Field(
        default=None,
        description='Proxy URL by URL pattern, e.g. {"https://": "http://proxy:3128"} or {"all://": ...}',
    )
    CUSTOM_HEADERS: dict[str, str] | None = Field(
        default=None,
        description="Extra HTTP headers sent with every request to Keycloak",
    )
    TOKEN_LEEWAY_SECONDS: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds when validating token expiry (python-keycloak defaults to 60)",
    )
    REMOTE_CACHE_TTL_SECONDS: float = Field(
        default=0.0,
        ge=0,
        description=(
            "Seconds the Keycloak auth decorators/dependencies cache UserInfo and UMA permission lookups per access "
            "token. 0 disables the cache. A revoked token or changed permission stays accepted for up to this long, "
            "so keep it short (a few seconds)."
        ),
    )
    IS_ADMIN_MODE_ENABLED: bool = False
    ADMIN_USERNAME: str | None = None
    ADMIN_PASSWORD: str | None = None
    ADMIN_REALM_NAME: str = "master"

    @field_validator("VERIFY_SSL", mode="before")
    @classmethod
    def _parse_verify_ssl(cls, value: object) -> object:
        """Keep boolean spellings from env vars ("false", "0", ...) as booleans; any other string is a CA path."""
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in _TRUE_WORDS:
                return True
            if lowered in _FALSE_WORDS:
                return False
        return value

    @model_validator(mode="after")
    def _check_client_key_has_cert(self) -> KeycloakConfig:
        if self.CLIENT_KEY_FILE and not self.CLIENT_CERT_FILE:
            msg = "CLIENT_KEY_FILE requires CLIENT_CERT_FILE"
            raise ValueError(msg)
        return self
