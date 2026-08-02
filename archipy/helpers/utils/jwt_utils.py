"""Utility module for JWT token operations with enhanced security and datetime handling.

This module provides a robust JWT handling implementation with support for access and refresh tokens,
cryptographic security, token validation, and comprehensive error handling.
"""

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.errors import InvalidArgumentError, InvalidTokenError, TokenExpiredError

if TYPE_CHECKING:
    from archipy.configs.config_template import AuthConfig


class JWTUtils:
    """Utility class for JWT token operations with enhanced security and datetime handling."""

    @classmethod
    def create_token(
        cls,
        data: dict[str, Any],
        expires_in: int,
        additional_claims: dict[str, Any] | None = None,
        auth_config: AuthConfig | None = None,
    ) -> str:
        """Creates a JWT token with enhanced security features.

        Args:
            data (dict[str, Any]): Base claims data to include in the token.
            expires_in (int): Token expiration time in seconds.
            additional_claims (dict[str, Any] | None): Optional additional claims to include in the token.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            str: The encoded JWT token.

        Raises:
            ValueError: If data is empty or expiration is invalid
        """
        import jwt

        configs = auth_config or BaseConfig.global_config().AUTH
        current_time = DatetimeUtils.get_datetime_utc_now()

        # Define argument names
        arg_data = "data"
        arg_expires_in = "expires_in"

        if not data:
            raise InvalidArgumentError(arg_data)
        if expires_in <= 0:
            raise InvalidArgumentError(arg_expires_in)

        to_encode = data.copy()
        expire = DatetimeUtils.get_datetime_after_given_datetime_or_now(seconds=expires_in, datetime_given=current_time)

        # Add standard claims
        to_encode.update(
            {
                # Registered claims (RFC 7519)
                "iss": configs.JWT_ISSUER,
                "aud": configs.JWT_AUDIENCE,
                "exp": expire,
                "iat": current_time,
                "nbf": current_time,
            },
        )

        # Add JWT ID if enabled
        if configs.ENABLE_JTI_CLAIM:
            to_encode["jti"] = str(uuid4())

        # Add additional claims
        if additional_claims:
            to_encode.update(additional_claims)

        # Validate SECRET_KEY
        secret_key = configs.SECRET_KEY
        if secret_key is None:
            raise InvalidArgumentError("SECRET_KEY")
        return jwt.encode(to_encode, secret_key.get_secret_value(), algorithm=configs.HASH_ALGORITHM)

    @classmethod
    def create_access_token(
        cls,
        user_uuid: UUID,
        additional_claims: dict[str, Any] | None = None,
        auth_config: AuthConfig | None = None,
    ) -> str:
        """Creates an access token for a user.

        Args:
            user_uuid (UUID): The user's UUID to include in the token.
            additional_claims (dict[str, Any] | None): Optional additional claims to include in the token.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            str: The encoded access token.
        """
        configs = auth_config or BaseConfig.global_config().AUTH

        return cls.create_token(
            data={
                "sub": str(user_uuid),
                "type": "access",
                "token_version": configs.TOKEN_VERSION,
            },
            expires_in=configs.ACCESS_TOKEN_EXPIRES_IN,
            additional_claims=additional_claims,
            auth_config=configs,
        )

    @classmethod
    def create_refresh_token(
        cls,
        user_uuid: UUID,
        additional_claims: dict[str, Any] | None = None,
        auth_config: AuthConfig | None = None,
    ) -> str:
        """Creates a refresh token for a user.

        Args:
            user_uuid (UUID): The user's UUID to include in the token.
            additional_claims (dict[str, Any] | None): Optional additional claims to include in the token.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            str: The encoded refresh token.
        """
        configs = auth_config or BaseConfig.global_config().AUTH

        return cls.create_token(
            data={
                "sub": str(user_uuid),
                "type": "refresh",
                "token_version": configs.TOKEN_VERSION,
            },
            expires_in=configs.REFRESH_TOKEN_EXPIRES_IN,
            additional_claims=additional_claims,
            auth_config=configs,
        )

    @classmethod
    def decode_token(
        cls,
        token: str,
        verify_type: str | None = None,
        auth_config: AuthConfig | None = None,
    ) -> dict[str, Any]:
        """Decodes and verifies a JWT token with enhanced security checks.

        Args:
            token (str): The JWT token to decode.
            verify_type (str | None): Optional token type to verify (e.g., "access" or "refresh").
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            dict[str, Any]: The decoded token payload.

        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid (e.g., invalid signature, audience, issuer, or type).
        """
        import jwt
        from jwt.exceptions import (
            ExpiredSignatureError,
            InvalidAudienceError,
            InvalidIssuerError,
            InvalidSignatureError,
            InvalidTokenError as JWTInvalidTokenError,
        )

        configs = auth_config or BaseConfig.global_config().AUTH
        required_claims = ["exp", "iat", "nbf", "aud", "iss", "sub", "type", "token_version"]
        if configs.ENABLE_JTI_CLAIM:
            required_claims.append("jti")

        try:
            # Validate SECRET_KEY
            secret_key = configs.SECRET_KEY
            if secret_key is None:
                raise InvalidArgumentError("SECRET_KEY")

            payload = jwt.decode(
                token,
                secret_key.get_secret_value(),
                algorithms=[configs.HASH_ALGORITHM],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require": required_claims,
                },
                audience=configs.JWT_AUDIENCE,
                issuer=configs.JWT_ISSUER,
            )

            # Verify token type
            if verify_type and payload.get("type") != verify_type:
                raise InvalidTokenError

            # Verify token version
            if payload.get("token_version") != configs.TOKEN_VERSION:
                raise InvalidTokenError

            # Ensure the return type is dict[str, Any] as declared
            return dict(payload)

        except ExpiredSignatureError as exception:
            raise TokenExpiredError from exception
        except InvalidSignatureError as exception:
            raise InvalidTokenError from exception
        except InvalidAudienceError as exception:
            raise InvalidTokenError from exception
        except InvalidIssuerError as exception:
            raise InvalidTokenError from exception
        except JWTInvalidTokenError as exception:
            raise InvalidTokenError from exception

    @classmethod
    def verify_access_token(cls, token: str, auth_config: AuthConfig | None = None) -> dict[str, Any]:
        """Verifies an access token.

        Args:
            token (str): The access token to verify.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            dict[str, Any]: The decoded access token payload.

        Raises:
            InvalidTokenException: If the token is invalid or not an access token.
            TokenExpiredException: If the token has expired.
        """
        configs = auth_config or BaseConfig.global_config().AUTH
        return cls.decode_token(token, verify_type="access", auth_config=configs)

    @classmethod
    def verify_refresh_token(cls, token: str, auth_config: AuthConfig | None = None) -> dict[str, Any]:
        """Verifies a refresh token.

        Args:
            token (str): The refresh token to verify.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            dict[str, Any]: The decoded refresh token payload.

        Raises:
            InvalidTokenException: If the token is invalid or not a refresh token.
            TokenExpiredException: If the token has expired.
        """
        configs = auth_config or BaseConfig.global_config().AUTH
        return cls.decode_token(token, verify_type="refresh", auth_config=configs)

    @staticmethod
    def extract_user_uuid(payload: dict[str, Any]) -> UUID:
        """Extracts the user UUID from the token payload.

        Args:
            payload (dict[str, Any]): The decoded token payload.

        Returns:
            UUID: The user's UUID.

        Raises:
            InvalidTokenException: If the user identifier is invalid or missing.
        """
        try:
            return UUID(payload["sub"])
        except (KeyError, ValueError) as exception:
            raise InvalidTokenError from exception

    @classmethod
    def get_token_expiry(cls, token: str, auth_config: AuthConfig | None = None) -> int:
        """Gets the token expiry timestamp.

        Args:
            token (str): The JWT token.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            int: The token expiry timestamp in seconds.

        Raises:
            InvalidTokenException: If the token is invalid.
        """
        payload = cls.decode_token(token, auth_config=auth_config)
        return int(payload["exp"])
