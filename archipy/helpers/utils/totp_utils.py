"""Utility module for TOTP (Time-based One-Time Password) operations.

This module provides functionality for generating and verifying TOTP codes that are
commonly used for multi-factor authentication.
"""

import base64
import hmac
import secrets  # Using secrets instead of random for cryptographic operations
import struct
from typing import TYPE_CHECKING, NoReturn
from uuid import UUID

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.errors import (
    InternalError,
    InvalidArgumentError,
    InvalidTokenError,
)

if TYPE_CHECKING:
    from datetime import datetime

    from archipy.configs.config_template import AuthConfig


def _raise_missing_totp_secret() -> NoReturn:
    """Raise InvalidArgumentError outside try bodies (TRY301)."""
    raise InvalidArgumentError(argument_name="TOTP_SECRET_KEY")


class TOTPUtils:
    """Utility class for TOTP (Time-based One-Time Password) operations.

    This class provides methods for generating and verifying TOTP codes, as well as generating
    secure secret keys for TOTP initialization.

    Uses the following configuration parameters from AuthConfig:
    - TOTP_SECRET_KEY: Master secret key for generating TOTP secrets
    - TOTP_HASH_ALGORITHM: Hash algorithm used for TOTP generation (default: SHA1)
    - TOTP_LENGTH: Number of digits in generated TOTP codes
    - TOTP_TIME_STEP: Time step in seconds between TOTP code changes
    - TOTP_EXPIRES_IN: TOTP validity period in seconds
    - TOTP_VERIFICATION_WINDOW: Number of time steps to check before/after
    - SALT_LENGTH: Length of random bytes for secure key generation
    """

    @classmethod
    def generate_totp(cls, secret: str | UUID, auth_config: AuthConfig | None = None) -> tuple[str, datetime]:
        """Generates a TOTP code using the configured hash algorithm.

        Args:
            secret: The secret key used to generate the TOTP code.
            auth_config: Optional auth configuration override. If not provided, uses the global config.

        Returns:
            A tuple containing the generated TOTP code and its expiration time.

        Raises:
            InvalidArgumentError: If the secret is invalid or empty.
        """
        if not secret:
            raise InvalidArgumentError(
                argument_name="secret",
            )

        configs = auth_config or BaseConfig.global_config().AUTH

        # Convert secret to bytes if it's UUID
        if isinstance(secret, UUID):
            secret = str(secret)

        # Get current timestamp and calculate time step
        current_time = DatetimeUtils.get_epoch_time_now()
        time_step_counter = int(current_time / configs.TOTP_TIME_STEP)

        # Generate HMAC hash
        secret_bytes = str(secret).encode("utf-8")
        time_bytes = struct.pack(">Q", time_step_counter)

        # Use the dedicated TOTP hash algorithm from config, with fallback to SHA1
        hash_algo = getattr(configs, "TOTP_HASH_ALGORITHM", "SHA1")

        hmac_obj = hmac.new(secret_bytes, time_bytes, hash_algo)
        hmac_result = hmac_obj.digest()

        # Get offset and truncate
        offset = hmac_result[-1] & 0xF
        truncated_hash = (
            ((hmac_result[offset] & 0x7F) << 24)
            | ((hmac_result[offset + 1] & 0xFF) << 16)
            | ((hmac_result[offset + 2] & 0xFF) << 8)
            | (hmac_result[offset + 3] & 0xFF)
        )

        # Generate TOTP code
        totp_code = str(truncated_hash % (10**configs.TOTP_LENGTH)).zfill(configs.TOTP_LENGTH)

        # Calculate expiration time
        expires_in = DatetimeUtils.get_datetime_after_given_datetime_or_now(seconds=configs.TOTP_EXPIRES_IN)

        return totp_code, expires_in

    @classmethod
    def verify_totp(cls, secret: str | UUID, totp_code: str, auth_config: AuthConfig | None = None) -> bool:
        """Verifies a TOTP code against the provided secret.

        Args:
            secret: The secret key used to generate the TOTP code.
            totp_code: The TOTP code to verify.
            auth_config: Optional auth configuration override. If not provided, uses the global config.

        Returns:
            `True` if the TOTP code is valid, `False` otherwise.

        Raises:
            InvalidArgumentError: If the secret is invalid or empty.
            InvalidTokenError: If the TOTP code format is invalid.
        """
        if not secret:
            raise InvalidArgumentError(
                argument_name="secret",
            )

        if not totp_code:
            raise InvalidArgumentError(
                argument_name="totp_code",
            )

        if not totp_code.isdigit():
            raise InvalidTokenError

        configs = auth_config or BaseConfig.global_config().AUTH

        current_time = DatetimeUtils.get_epoch_time_now()

        # Use the dedicated TOTP hash algorithm from config, with fallback to SHA1
        hash_algo = getattr(configs, "TOTP_HASH_ALGORITHM", "SHA1")

        # Check codes within verification window
        for i in range(-configs.TOTP_VERIFICATION_WINDOW, configs.TOTP_VERIFICATION_WINDOW + 1):
            time_step_counter = int(current_time / configs.TOTP_TIME_STEP) + i

            secret_bytes = str(secret).encode("utf-8")
            time_bytes = struct.pack(">Q", time_step_counter)
            hmac_obj = hmac.new(secret_bytes, time_bytes, hash_algo)
            hmac_result = hmac_obj.digest()

            offset = hmac_result[-1] & 0xF
            truncated_hash = (
                ((hmac_result[offset] & 0x7F) << 24)
                | ((hmac_result[offset + 1] & 0xFF) << 16)
                | ((hmac_result[offset + 2] & 0xFF) << 8)
                | (hmac_result[offset + 3] & 0xFF)
            )

            computed_totp = str(truncated_hash % (10 ** len(totp_code))).zfill(len(totp_code))

            if hmac.compare_digest(totp_code, computed_totp):
                return True

        return False

    @staticmethod
    def generate_secret_key_for_totp(auth_config: AuthConfig | None = None) -> str:
        """Generates a random secret key for TOTP initialization.

        Args:
            auth_config: Optional auth configuration override. If not provided, uses the global config.

        Returns:
            A base32-encoded secret key for TOTP initialization.

        Raises:
            InvalidArgumentError: If the TOTP_SECRET_KEY is not configured.
            InternalError: If there is an error generating the secret key.
        """
        try:
            configs = auth_config or BaseConfig.global_config().AUTH

            # Use secrets module instead of random for better security
            random_bytes = secrets.token_bytes(configs.SALT_LENGTH)

            # Check if TOTP secret key is configured
            if not configs.TOTP_SECRET_KEY:
                _raise_missing_totp_secret()

            master_key = configs.TOTP_SECRET_KEY.get_secret_value().encode("utf-8")

            # Use the dedicated TOTP hash algorithm from config, with fallback to SHA1
            hash_algo = getattr(configs, "TOTP_HASH_ALGORITHM", "SHA1")

            # Use HMAC with master key for additional security
            hmac_obj = hmac.new(master_key, random_bytes, hash_algo)
            return base64.b32encode(hmac_obj.digest()).decode("utf-8")
        except Exception as e:
            # Convert any errors to our custom errors
            raise InternalError() from e
