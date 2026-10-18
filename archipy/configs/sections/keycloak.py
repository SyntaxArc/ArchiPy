"""Keycloak configuration."""

from pydantic import BaseModel, Field


class KeycloakConfig(BaseModel):
    """Configuration settings for Keycloak integration.

    Controls connection parameters and authentication settings for the Keycloak
    identity and access management service.
    """

    SERVER_URL: str | None = None
    CLIENT_ID: str | None = None
    REALM_NAME: str = "master"
    CLIENT_SECRET_KEY: str | None = None
    VERIFY_SSL: bool = True
    TIMEOUT: int = 10
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
