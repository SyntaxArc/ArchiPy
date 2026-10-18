"""Authentication configuration."""

from pydantic import BaseModel, Field, SecretStr


class AuthConfig(BaseModel):
    """Configuration settings for authentication and security.

    Controls JWT token settings, TOTP configuration, rate limiting,
    password policies, and token security features.
    """

    # JWT Settings
    SECRET_KEY: SecretStr | None = Field(default=None, description="JWT signing key")
    ACCESS_TOKEN_EXPIRES_IN: int = Field(
        default=1 * 60 * 60,
        description="Access token expiration in seconds",
    )  # 1 hour
    REFRESH_TOKEN_EXPIRES_IN: int = Field(
        default=24 * 60 * 60,
        description="Refresh token expiration in seconds",
    )  # 24 hours
    HASH_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_ISSUER: str = Field(default="your-app-name", description="JWT issuer claim")
    JWT_AUDIENCE: str = Field(default="your-app-audience", description="JWT audience claim")
    TOKEN_VERSION: int = Field(default=1, description="JWT token version")
    JWT_LEEWAY: int = Field(
        default=0,
        ge=0,
        description="Clock-skew tolerance in seconds applied to exp, nbf and iat when verifying tokens",
    )

    # TOTP Settings
    TOTP_SECRET_KEY: SecretStr | None = Field(default=None, description="TOTP master key")
    TOTP_HASH_ALGORITHM: str = Field(
        default="SHA1",
        description="Hash algorithm for TOTP generation (SHA1, SHA256, SHA512)",
    )
    TOTP_LENGTH: int = Field(default=6, ge=6, le=8, description="TOTP code length")
    TOTP_EXPIRES_IN: int = Field(default=300, description="TOTP expiration time in seconds (5 minutes)")
    TOTP_TIME_STEP: int = Field(default=30, description="TOTP time step in seconds")
    TOTP_VERIFICATION_WINDOW: int = Field(default=1, description="Number of time steps to check before/after")
    TOTP_MAX_ATTEMPTS: int = Field(default=3, description="Maximum failed TOTP attempts before lockout")
    TOTP_LOCKOUT_TIME: int = Field(default=300, description="Lockout time in seconds after max attempts")

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT: int = Field(default=5, description="Maximum login attempts per minute")
    TOTP_RATE_LIMIT: int = Field(default=3, description="Maximum TOTP requests per minute")
    PASSWORD_RESET_RATE_LIMIT: int = Field(default=3, description="Maximum password reset requests per hour")

    # Password Policy
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
    PASSWORD_HISTORY_SIZE: int = Field(
        default=3,
        ge=0,
        description="Number of previous passwords to remember (0 disables the history check)",
    )

    # Token Security
    ENABLE_JTI_CLAIM: bool = Field(default=True, description="Enable JWT ID claim for token tracking")
    ENABLE_TOKEN_ROTATION: bool = Field(default=True, description="Enable refresh token rotation")
    REFRESH_TOKEN_REUSE_INTERVAL: int = Field(default=60, description="Grace period for refresh token reuse in seconds")
