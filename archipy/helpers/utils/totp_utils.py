"""Utility module for TOTP (Time-based One-Time Password) operations.

This module provides functionality for generating and verifying TOTP codes that are
commonly used for multi-factor authentication.
"""

from __future__ import annotations

import base64
import hmac
import secrets  # Using secrets instead of random for cryptographic operations
import struct
from typing import TYPE_CHECKING, NoReturn

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.errors import (
    BaseError,
    InternalError,
    InvalidArgumentError,
    InvalidTokenError,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from uuid import UUID

    from archipy.configs.config_template import AuthConfig


def _raise_missing_totp_secret() -> NoReturn:
    """Raise InvalidArgumentError outside try bodies (TRY301)."""
    raise InvalidArgumentError(argument_name="TOTP_SECRET_KEY")


def _secret_to_key(secret: str | UUID) -> bytes:
    """Convert a TOTP secret to HMAC key bytes.

    A secret that is valid base32 (such as the output of ``generate_secret_key_for_totp`` or the key shown by an
    authenticator app) is base32-decoded, per RFC 4648/6238. Any other secret (for example a UUID or a free-form
    string) is used as raw UTF-8 bytes.
    """
    text = str(secret)
    normalized = text.replace(" ", "").upper()
    padded = normalized + "=" * (-len(normalized) % 8)
    try:
        return base64.b32decode(padded)
    except ValueError:
        return text.encode("utf-8")


def _compute_totp(key: bytes, time_step_counter: int, hash_algo: str, length: int) -> str:
    """Compute the RFC 6238 code (dynamic truncation, RFC 4226) for one time step counter."""
    hmac_result = hmac.new(key, struct.pack(">Q", time_step_counter), hash_algo).digest()
    offset = hmac_result[-1] & 0xF
    truncated_hash = (
        ((hmac_result[offset] & 0x7F) << 24)
        | ((hmac_result[offset + 1] & 0xFF) << 16)
        | ((hmac_result[offset + 2] & 0xFF) << 8)
        | (hmac_result[offset + 3] & 0xFF)
    )
    return str(truncated_hash % (10**length)).zfill(length)


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
            A tuple containing the generated TOTP code and its expiration time. The expiration
            is ``TOTP_EXPIRES_IN`` from now, capped at the moment ``verify_totp`` stops accepting the code. A code
            stays valid for that whole period: this helper keeps no state, so callers must enforce single use and
            attempt limits (``TOTP_MAX_ATTEMPTS``, ``TOTP_LOCKOUT_TIME``) themselves, for example with a cache.

        Raises:
            InvalidArgumentError: If the secret is invalid or empty.
        """
        if not secret:
            raise InvalidArgumentError(
                argument_name="secret",
            )

        configs = auth_config or BaseConfig.global_config().AUTH

        # Get current timestamp and calculate time step
        current_time = DatetimeUtils.get_epoch_time_now()
        time_step_counter = int(current_time / configs.TOTP_TIME_STEP)

        # Use the dedicated TOTP hash algorithm from config, with fallback to SHA1
        hash_algo = getattr(configs, "TOTP_HASH_ALGORITHM", "SHA1")
        totp_code = _compute_totp(_secret_to_key(secret), time_step_counter, hash_algo, configs.TOTP_LENGTH)

        # The code is accepted until the last step of the verification window ends, so never report a later expiry.
        valid_until = (time_step_counter + configs.TOTP_VERIFICATION_WINDOW + 1) * configs.TOTP_TIME_STEP
        lifetime = min(configs.TOTP_EXPIRES_IN, max(valid_until - current_time, 0))
        expires_in = DatetimeUtils.get_datetime_after_given_datetime_or_now(seconds=lifetime)

        return totp_code, expires_in

    @classmethod
    def verify_totp(
        cls,
        secret: str | UUID,
        totp_code: str,
        auth_config: AuthConfig | None = None,
        replay_guard: Callable[[int], bool] | None = None,
    ) -> bool:
        """Verifies a TOTP code against the provided secret.

        This helper keeps no state. Two protections therefore belong to the caller: counting failed attempts
        (``TOTP_MAX_ATTEMPTS`` / ``TOTP_LOCKOUT_TIME`` are not enforced here) and rejecting a code that was already
        used. For the second one pass ``replay_guard``.

        Args:
            secret: The secret key used to generate the TOTP code.
            totp_code: The TOTP code to verify.
            auth_config: Optional auth configuration override. If not provided, uses the global config.
            replay_guard: Optional callback invoked with the matched time step (an ``int`` counter) once the code
                is valid. Return ``True`` to accept the code, ``False`` to reject it as already used. Typical use is
                an atomic "store the step if it is greater than the last accepted one" on the user record or in
                Redis (RFC 6238 section 5.2). It is not called for invalid codes.

        Returns:
            `True` if the TOTP code is valid, `False` otherwise (including a code whose length differs from
            ``TOTP_LENGTH``).

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

        if not (totp_code.isascii() and totp_code.isdigit()):
            raise InvalidTokenError

        configs = auth_config or BaseConfig.global_config().AUTH

        # The expected length comes from the config, never from the caller's input.
        if len(totp_code) != configs.TOTP_LENGTH:
            return False

        current_time = DatetimeUtils.get_epoch_time_now()

        # Use the dedicated TOTP hash algorithm from config, with fallback to SHA1
        hash_algo = getattr(configs, "TOTP_HASH_ALGORITHM", "SHA1")

        key = _secret_to_key(secret)
        current_step = int(current_time / configs.TOTP_TIME_STEP)

        # Check every step in the window without early exit so timing does not reveal which step matched
        matched_step: int | None = None
        for i in range(-configs.TOTP_VERIFICATION_WINDOW, configs.TOTP_VERIFICATION_WINDOW + 1):
            computed_totp = _compute_totp(key, current_step + i, hash_algo, configs.TOTP_LENGTH)
            if hmac.compare_digest(totp_code, computed_totp):
                matched_step = current_step + i

        if matched_step is None:
            return False
        return replay_guard is None or bool(replay_guard(matched_step))

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
        except BaseError:
            raise
        except Exception as e:
            # Convert any other errors to our custom errors
            raise InternalError(additional_data={"operation": "generate_secret_key_for_totp"}) from e
