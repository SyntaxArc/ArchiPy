"""Authentication configuration."""

from pydantic import BaseModel, ConfigDict, Field, SecretStr


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
