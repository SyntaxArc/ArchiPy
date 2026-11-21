"""Authentication configuration."""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields


class JwtConfig(BaseModel):
    """JWT and token security settings."""

    model_config = ConfigDict(extra="forbid")

    ACCESS_TOKEN_EXPIRES_IN: int = Field(
        default=1 * 60 * 60,
        description="Access token expiration in seconds",
    )  # 1 hour
    REFRESH_TOKEN_EXPIRES_IN: int = Field(
        default=24 * 60 * 60,
        description="Refresh token expiration in seconds",
    )  # 24 hours
    ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ISSUER: str = Field(default="your-app-name", description="JWT issuer claim")
    AUDIENCE: str = Field(default="your-app-audience", description="JWT audience claim")
    TOKEN_VERSION: int = Field(default=1, description="JWT token version")
    LEEWAY: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds applied to exp, nbf and iat when verifying tokens",
    )
    ENABLE_JTI_CLAIM: bool = Field(default=True, description="Enable JWT ID claim for token tracking")
    ENABLE_TOKEN_ROTATION: bool = Field(default=True, description="Enable refresh token rotation")
    REFRESH_TOKEN_REUSE_INTERVAL: int = Field(default=60, description="Grace period for refresh token reuse in seconds")


class TotpConfig(BaseModel):
    """TOTP settings."""

    model_config = ConfigDict(extra="forbid")

    SECRET_KEY: SecretStr | None = Field(default=None, description="TOTP master key")
    HASH_ALGORITHM: str = Field(
        default="SHA1",
        description="Hash algorithm for TOTP generation (SHA1, SHA256, SHA512)",
    )
    LENGTH: int = Field(default=6, ge=6, le=8, description="TOTP code length")
    EXPIRES_IN: int = Field(default=300, description="TOTP expiration time in seconds (5 minutes)")
    TIME_STEP: int = Field(default=30, description="TOTP time step in seconds")
    VERIFICATION_WINDOW: int = Field(default=1, description="Number of time steps to check before/after")
    MAX_ATTEMPTS: int = Field(default=3, description="Maximum failed TOTP attempts before lockout")
    LOCKOUT_TIME: int = Field(default=300, description="Lockout time in seconds after max attempts")


class RateLimitsConfig(BaseModel):
    """Rate limits per user action."""

    model_config = ConfigDict(extra="forbid")

    LOGIN: int = Field(default=5, description="Maximum login attempts per minute")
    TOTP: int = Field(default=3, description="Maximum TOTP requests per minute")
    PASSWORD_RESET: int = Field(default=3, description="Maximum password reset requests per hour")


class PasswordPolicyConfig(BaseModel):
    """Password hashing and strength policy."""

    model_config = ConfigDict(extra="forbid")

    HASH_ITERATIONS: int = Field(
        default=600000,
        ge=1,
        description="Password hash iterations (PBKDF2-HMAC-SHA256); stored hashes record their own count",
    )
    MIN_LENGTH: int = Field(default=12, ge=8, description="Minimum password length")
    REQUIRE_DIGIT: bool = Field(default=True, description="Whether password requires digits")
    REQUIRE_LOWERCASE: bool = Field(default=True, description="Whether password requires lowercase")
    REQUIRE_SPECIAL: bool = Field(default=True, description="Whether password requires special chars")
    REQUIRE_UPPERCASE: bool = Field(default=True, description="Whether password requires uppercase")
    SALT_LENGTH: int = Field(default=16, description="Password salt length")
    SPECIAL_CHARACTERS: set[str] = Field(default=set("!@#$%^&*()-_+="), description="Set of allowed special characters")
    HISTORY_SIZE: int = Field(
        default=3,
        ge=0,
        description="Number of previous passwords to remember (0 disables the history check)",
    )


class AuthConfig(BaseModel):
    """Configuration settings for authentication and security.

    Controls JWT token settings, TOTP configuration, rate limiting,
    password policies, and token security features.
    """

    SECRET_KEY: SecretStr | None = Field(default=None, description="JWT signing key")

    JWT: JwtConfig = Field(default_factory=JwtConfig, description="JWT and token security settings")
    TOTP: TotpConfig = Field(default_factory=TotpConfig, description="TOTP settings")
    RATE_LIMITS: RateLimitsConfig = Field(default_factory=RateLimitsConfig, description="Rate limits per user action")
    PASSWORD_POLICY: PasswordPolicyConfig = Field(
        default_factory=PasswordPolicyConfig,
        description="Password hashing and strength policy",
    )

    ACCESS_TOKEN_EXPIRES_IN: int = Field(
        default=1 * 60 * 60,
        description="Access token expiration in seconds",
        deprecated=deprecated_flat_message("AUTH", "ACCESS_TOKEN_EXPIRES_IN", "JWT", "ACCESS_TOKEN_EXPIRES_IN"),
    )  # 1 hour
    REFRESH_TOKEN_EXPIRES_IN: int = Field(
        default=24 * 60 * 60,
        description="Refresh token expiration in seconds",
        deprecated=deprecated_flat_message("AUTH", "REFRESH_TOKEN_EXPIRES_IN", "JWT", "REFRESH_TOKEN_EXPIRES_IN"),
    )  # 24 hours
    HASH_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm",
        deprecated=deprecated_flat_message("AUTH", "HASH_ALGORITHM", "JWT", "ALGORITHM"),
    )
    JWT_ISSUER: str = Field(
        default="your-app-name",
        description="JWT issuer claim",
        deprecated=deprecated_flat_message("AUTH", "JWT_ISSUER", "JWT", "ISSUER"),
    )
    JWT_AUDIENCE: str = Field(
        default="your-app-audience",
        description="JWT audience claim",
        deprecated=deprecated_flat_message("AUTH", "JWT_AUDIENCE", "JWT", "AUDIENCE"),
    )
    TOKEN_VERSION: int = Field(
        default=1,
        description="JWT token version",
        deprecated=deprecated_flat_message("AUTH", "TOKEN_VERSION", "JWT", "TOKEN_VERSION"),
    )
    JWT_LEEWAY: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds applied to exp, nbf and iat when verifying tokens",
        deprecated=deprecated_flat_message("AUTH", "JWT_LEEWAY", "JWT", "LEEWAY"),
    )
    ENABLE_JTI_CLAIM: bool = Field(
        default=True,
        description="Enable JWT ID claim for token tracking",
        deprecated=deprecated_flat_message("AUTH", "ENABLE_JTI_CLAIM", "JWT", "ENABLE_JTI_CLAIM"),
    )
    ENABLE_TOKEN_ROTATION: bool = Field(
        default=True,
        description="Enable refresh token rotation",
        deprecated=deprecated_flat_message("AUTH", "ENABLE_TOKEN_ROTATION", "JWT", "ENABLE_TOKEN_ROTATION"),
    )
    REFRESH_TOKEN_REUSE_INTERVAL: int = Field(
        default=60,
        description="Grace period for refresh token reuse in seconds",
        deprecated=deprecated_flat_message(
            "AUTH",
            "REFRESH_TOKEN_REUSE_INTERVAL",
            "JWT",
            "REFRESH_TOKEN_REUSE_INTERVAL",
        ),
    )
    TOTP_SECRET_KEY: SecretStr | None = Field(
        default=None,
        description="TOTP master key",
        deprecated=deprecated_flat_message("AUTH", "TOTP_SECRET_KEY", "TOTP", "SECRET_KEY"),
    )
    TOTP_HASH_ALGORITHM: str = Field(
        default="SHA1",
        description="Hash algorithm for TOTP generation (SHA1, SHA256, SHA512)",
        deprecated=deprecated_flat_message("AUTH", "TOTP_HASH_ALGORITHM", "TOTP", "HASH_ALGORITHM"),
    )
    TOTP_LENGTH: int = Field(
        default=6,
        ge=6,
        le=8,
        description="TOTP code length",
        deprecated=deprecated_flat_message("AUTH", "TOTP_LENGTH", "TOTP", "LENGTH"),
    )
    TOTP_EXPIRES_IN: int = Field(
        default=300,
        description="TOTP expiration time in seconds (5 minutes)",
        deprecated=deprecated_flat_message("AUTH", "TOTP_EXPIRES_IN", "TOTP", "EXPIRES_IN"),
    )
    TOTP_TIME_STEP: int = Field(
        default=30,
        description="TOTP time step in seconds",
        deprecated=deprecated_flat_message("AUTH", "TOTP_TIME_STEP", "TOTP", "TIME_STEP"),
    )
    TOTP_VERIFICATION_WINDOW: int = Field(
        default=1,
        description="Number of time steps to check before/after",
        deprecated=deprecated_flat_message("AUTH", "TOTP_VERIFICATION_WINDOW", "TOTP", "VERIFICATION_WINDOW"),
    )
    TOTP_MAX_ATTEMPTS: int = Field(
        default=3,
        description="Maximum failed TOTP attempts before lockout",
        deprecated=deprecated_flat_message("AUTH", "TOTP_MAX_ATTEMPTS", "TOTP", "MAX_ATTEMPTS"),
    )
    TOTP_LOCKOUT_TIME: int = Field(
        default=300,
        description="Lockout time in seconds after max attempts",
        deprecated=deprecated_flat_message("AUTH", "TOTP_LOCKOUT_TIME", "TOTP", "LOCKOUT_TIME"),
    )
    LOGIN_RATE_LIMIT: int = Field(
        default=5,
        description="Maximum login attempts per minute",
        deprecated=deprecated_flat_message("AUTH", "LOGIN_RATE_LIMIT", "RATE_LIMITS", "LOGIN"),
    )
    TOTP_RATE_LIMIT: int = Field(
        default=3,
        description="Maximum TOTP requests per minute",
        deprecated=deprecated_flat_message("AUTH", "TOTP_RATE_LIMIT", "RATE_LIMITS", "TOTP"),
    )
    PASSWORD_RESET_RATE_LIMIT: int = Field(
        default=3,
        description="Maximum password reset requests per hour",
        deprecated=deprecated_flat_message("AUTH", "PASSWORD_RESET_RATE_LIMIT", "RATE_LIMITS", "PASSWORD_RESET"),
    )
    HASH_ITERATIONS: int = Field(
        default=600000,
        ge=1,
        description="Password hash iterations (PBKDF2-HMAC-SHA256); stored hashes record their own count",
        deprecated=deprecated_flat_message("AUTH", "HASH_ITERATIONS", "PASSWORD_POLICY", "HASH_ITERATIONS"),
    )
    MIN_LENGTH: int = Field(
        default=12,
        ge=8,
        description="Minimum password length",
        deprecated=deprecated_flat_message("AUTH", "MIN_LENGTH", "PASSWORD_POLICY", "MIN_LENGTH"),
    )
    REQUIRE_DIGIT: bool = Field(
        default=True,
        description="Whether password requires digits",
        deprecated=deprecated_flat_message("AUTH", "REQUIRE_DIGIT", "PASSWORD_POLICY", "REQUIRE_DIGIT"),
    )
    REQUIRE_LOWERCASE: bool = Field(
        default=True,
        description="Whether password requires lowercase",
        deprecated=deprecated_flat_message("AUTH", "REQUIRE_LOWERCASE", "PASSWORD_POLICY", "REQUIRE_LOWERCASE"),
    )
    REQUIRE_SPECIAL: bool = Field(
        default=True,
        description="Whether password requires special chars",
        deprecated=deprecated_flat_message("AUTH", "REQUIRE_SPECIAL", "PASSWORD_POLICY", "REQUIRE_SPECIAL"),
    )
    REQUIRE_UPPERCASE: bool = Field(
        default=True,
        description="Whether password requires uppercase",
        deprecated=deprecated_flat_message("AUTH", "REQUIRE_UPPERCASE", "PASSWORD_POLICY", "REQUIRE_UPPERCASE"),
    )
    SALT_LENGTH: int = Field(
        default=16,
        description="Password salt length",
        deprecated=deprecated_flat_message("AUTH", "SALT_LENGTH", "PASSWORD_POLICY", "SALT_LENGTH"),
    )
    SPECIAL_CHARACTERS: set[str] = Field(
        default=set("!@#$%^&*()-_+="),
        description="Set of allowed special characters",
        deprecated=deprecated_flat_message("AUTH", "SPECIAL_CHARACTERS", "PASSWORD_POLICY", "SPECIAL_CHARACTERS"),
    )
    PASSWORD_HISTORY_SIZE: int = Field(
        default=3,
        ge=0,
        description="Number of previous passwords to remember (0 disables the history check)",
        deprecated=deprecated_flat_message("AUTH", "PASSWORD_HISTORY_SIZE", "PASSWORD_POLICY", "HISTORY_SIZE"),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "JWT",
            JwtConfig,
            {
                "ACCESS_TOKEN_EXPIRES_IN": "ACCESS_TOKEN_EXPIRES_IN",
                "REFRESH_TOKEN_EXPIRES_IN": "REFRESH_TOKEN_EXPIRES_IN",
                "HASH_ALGORITHM": "ALGORITHM",
                "JWT_ISSUER": "ISSUER",
                "JWT_AUDIENCE": "AUDIENCE",
                "TOKEN_VERSION": "TOKEN_VERSION",
                "JWT_LEEWAY": "LEEWAY",
                "ENABLE_JTI_CLAIM": "ENABLE_JTI_CLAIM",
                "ENABLE_TOKEN_ROTATION": "ENABLE_TOKEN_ROTATION",
                "REFRESH_TOKEN_REUSE_INTERVAL": "REFRESH_TOKEN_REUSE_INTERVAL",
            },
        )
        fold_flat_fields(
            self,
            "TOTP",
            TotpConfig,
            {
                "TOTP_SECRET_KEY": "SECRET_KEY",
                "TOTP_HASH_ALGORITHM": "HASH_ALGORITHM",
                "TOTP_LENGTH": "LENGTH",
                "TOTP_EXPIRES_IN": "EXPIRES_IN",
                "TOTP_TIME_STEP": "TIME_STEP",
                "TOTP_VERIFICATION_WINDOW": "VERIFICATION_WINDOW",
                "TOTP_MAX_ATTEMPTS": "MAX_ATTEMPTS",
                "TOTP_LOCKOUT_TIME": "LOCKOUT_TIME",
            },
        )
        fold_flat_fields(
            self,
            "RATE_LIMITS",
            RateLimitsConfig,
            {"LOGIN_RATE_LIMIT": "LOGIN", "TOTP_RATE_LIMIT": "TOTP", "PASSWORD_RESET_RATE_LIMIT": "PASSWORD_RESET"},
        )
        fold_flat_fields(
            self,
            "PASSWORD_POLICY",
            PasswordPolicyConfig,
            {
                "HASH_ITERATIONS": "HASH_ITERATIONS",
                "MIN_LENGTH": "MIN_LENGTH",
                "REQUIRE_DIGIT": "REQUIRE_DIGIT",
                "REQUIRE_LOWERCASE": "REQUIRE_LOWERCASE",
                "REQUIRE_SPECIAL": "REQUIRE_SPECIAL",
                "REQUIRE_UPPERCASE": "REQUIRE_UPPERCASE",
                "SALT_LENGTH": "SALT_LENGTH",
                "SPECIAL_CHARACTERS": "SPECIAL_CHARACTERS",
                "PASSWORD_HISTORY_SIZE": "HISTORY_SIZE",
            },
        )
        return self
