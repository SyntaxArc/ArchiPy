"""Keycloak configuration."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields

_TRUE_WORDS = frozenset({"true", "1", "yes", "on", "t", "y"})
_FALSE_WORDS = frozenset({"false", "0", "no", "off", "f", "n"})


class KeycloakAdminConfig(BaseModel):
    """Admin mode settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = False
    USERNAME: str | None = None
    PASSWORD: SecretStr | None = Field(default=None)
    REALM_NAME: str = "master"


class KeycloakTlsConfig(BaseModel):
    """TLS and client certificate settings."""

    model_config = ConfigDict(extra="forbid")

    VERIFY_SSL: bool | str = Field(
        default=True,
        description="True/False toggles TLS verification; a string is the path of a CA bundle to verify against",
    )
    CLIENT_CERT_FILE: str | None = Field(
        default=None,
        description="Path of a client certificate (PEM) for mutual TLS; a combined cert+key file needs no key file",
    )
    CLIENT_KEY_FILE: str | None = Field(
        default=None,
        description="Path of the private key matching CLIENT_CERT_FILE",
    )

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
    def _check_client_key_has_cert(self) -> Self:
        if self.CLIENT_KEY_FILE and not self.CLIENT_CERT_FILE:
            msg = "CLIENT_KEY_FILE requires CLIENT_CERT_FILE"
            raise ValueError(msg)
        return self


class KeycloakTokenValidationConfig(BaseModel):
    """Local token validation settings."""

    model_config = ConfigDict(extra="forbid")

    LEEWAY_SECONDS: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds when validating token expiry (python-keycloak defaults to 60)",
    )
    EXPECTED_ISSUER: str | None = Field(
        default=None,
        description=(
            "Required `iss` claim of locally verified tokens. When set, a mismatching issuer (and a `typ` other than "
            "Bearer) is rejected. When unset, a mismatch against `{SERVER_URL}/realms/{REALM_NAME}` only emits a "
            "DeprecationWarning; enforcement becomes the default in 6.0."
        ),
    )
    EXPECTED_AUDIENCE: str | None = Field(
        default=None,
        description=(
            "Required `aud` claim of locally verified tokens (typically CLIENT_ID). When set, tokens whose audience "
            "does not include it (and tokens whose `typ` is not Bearer) are rejected."
        ),
    )
    REQUIRE_ORGANIZATION: bool = Field(
        default=False,
        description="Require a selected organization in FastAPI and gRPC guards unless the guard overrides this value",
    )


class KeycloakConfig(BaseModel):
    """Configuration settings for Keycloak integration.

    Controls connection parameters and authentication settings for the Keycloak
    identity and access management service.
    """

    SERVER_URL: str | None = None
    CLIENT_ID: str | None = None
    REALM_NAME: str = "master"
    CLIENT_SECRET_KEY: SecretStr | None = Field(default=None)
    TIMEOUT: float = Field(default=10, gt=0, description="Request timeout in seconds (fractions allowed)")
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
    REMOTE_CACHE_TTL_SECONDS: float = Field(
        default=0.0,
        ge=0,
        description=(
            "Seconds the Keycloak auth decorators/dependencies cache UserInfo and UMA permission lookups per access "
            "token. 0 disables the cache. A revoked token or changed permission stays accepted for up to this long, "
            "so keep it short (a few seconds)."
        ),
    )

    ADMIN: KeycloakAdminConfig = Field(default_factory=KeycloakAdminConfig, description="Admin mode settings")
    TLS: KeycloakTlsConfig = Field(default_factory=KeycloakTlsConfig, description="TLS and client certificate settings")
    TOKEN_VALIDATION: KeycloakTokenValidationConfig = Field(
        default_factory=KeycloakTokenValidationConfig,
        description="Local token validation settings",
    )

    IS_ADMIN_MODE_ENABLED: bool = Field(
        default=False,
        deprecated=deprecated_flat_message("KEYCLOAK", "IS_ADMIN_MODE_ENABLED", "ADMIN", "IS_ENABLED"),
    )
    ADMIN_USERNAME: str | None = Field(
        default=None,
        deprecated=deprecated_flat_message("KEYCLOAK", "ADMIN_USERNAME", "ADMIN", "USERNAME"),
    )
    ADMIN_PASSWORD: SecretStr | None = Field(
        default=None,
        deprecated=deprecated_flat_message("KEYCLOAK", "ADMIN_PASSWORD", "ADMIN", "PASSWORD"),
    )
    ADMIN_REALM_NAME: str = Field(
        default="master",
        deprecated=deprecated_flat_message("KEYCLOAK", "ADMIN_REALM_NAME", "ADMIN", "REALM_NAME"),
    )
    VERIFY_SSL: bool | str = Field(
        default=True,
        description="True/False toggles TLS verification; a string is the path of a CA bundle to verify against",
        deprecated=deprecated_flat_message("KEYCLOAK", "VERIFY_SSL", "TLS", "VERIFY_SSL"),
    )
    CLIENT_CERT_FILE: str | None = Field(
        default=None,
        description="Path of a client certificate (PEM) for mutual TLS; a combined cert+key file needs no key file",
        deprecated=deprecated_flat_message("KEYCLOAK", "CLIENT_CERT_FILE", "TLS", "CLIENT_CERT_FILE"),
    )
    CLIENT_KEY_FILE: str | None = Field(
        default=None,
        description="Path of the private key matching CLIENT_CERT_FILE",
        deprecated=deprecated_flat_message("KEYCLOAK", "CLIENT_KEY_FILE", "TLS", "CLIENT_KEY_FILE"),
    )
    TOKEN_LEEWAY_SECONDS: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds when validating token expiry (python-keycloak defaults to 60)",
        deprecated=deprecated_flat_message("KEYCLOAK", "TOKEN_LEEWAY_SECONDS", "TOKEN_VALIDATION", "LEEWAY_SECONDS"),
    )
    EXPECTED_ISSUER: str | None = Field(
        default=None,
        description=(
            "Required `iss` claim of locally verified tokens. When set, a mismatching issuer (and a `typ` other than "
            "Bearer) is rejected. When unset, a mismatch against `{SERVER_URL}/realms/{REALM_NAME}` only emits a "
            "DeprecationWarning; enforcement becomes the default in 6.0."
        ),
        deprecated=deprecated_flat_message("KEYCLOAK", "EXPECTED_ISSUER", "TOKEN_VALIDATION", "EXPECTED_ISSUER"),
    )
    EXPECTED_AUDIENCE: str | None = Field(
        default=None,
        description=(
            "Required `aud` claim of locally verified tokens (typically CLIENT_ID). When set, tokens whose audience "
            "does not include it (and tokens whose `typ` is not Bearer) are rejected."
        ),
        deprecated=deprecated_flat_message("KEYCLOAK", "EXPECTED_AUDIENCE", "TOKEN_VALIDATION", "EXPECTED_AUDIENCE"),
    )
    REQUIRE_ORGANIZATION: bool = Field(
        default=False,
        description="Require a selected organization in FastAPI and gRPC guards unless the guard overrides this value",
        deprecated=deprecated_flat_message(
            "KEYCLOAK",
            "REQUIRE_ORGANIZATION",
            "TOKEN_VALIDATION",
            "REQUIRE_ORGANIZATION",
        ),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "ADMIN",
            KeycloakAdminConfig,
            {
                "IS_ADMIN_MODE_ENABLED": "IS_ENABLED",
                "ADMIN_USERNAME": "USERNAME",
                "ADMIN_PASSWORD": "PASSWORD",
                "ADMIN_REALM_NAME": "REALM_NAME",
            },
        )
        fold_flat_fields(
            self,
            "TLS",
            KeycloakTlsConfig,
            {"VERIFY_SSL": "VERIFY_SSL", "CLIENT_CERT_FILE": "CLIENT_CERT_FILE", "CLIENT_KEY_FILE": "CLIENT_KEY_FILE"},
        )
        fold_flat_fields(
            self,
            "TOKEN_VALIDATION",
            KeycloakTokenValidationConfig,
            {
                "TOKEN_LEEWAY_SECONDS": "LEEWAY_SECONDS",
                "EXPECTED_ISSUER": "EXPECTED_ISSUER",
                "EXPECTED_AUDIENCE": "EXPECTED_AUDIENCE",
                "REQUIRE_ORGANIZATION": "REQUIRE_ORGANIZATION",
            },
        )
        return self

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
