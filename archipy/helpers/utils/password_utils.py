"""Password hashing and validation utilities."""

from __future__ import annotations

# src/helpers/password_helper.py
import hashlib
import hmac
import os
import secrets  # Use secrets instead of random for cryptographic operations
import string
from base64 import b64decode, b64encode
from typing import TYPE_CHECKING

from archipy.configs.base_config import BaseConfig
from archipy.models.errors import InvalidPasswordError

if TYPE_CHECKING:
    from archipy.configs.config_template import AuthConfig
    from archipy.models.types.language_type import LanguageType


_HASH_SCHEME = "pbkdf2_sha256"
_HASH_SEPARATOR = "$"
# Iteration count used by the pre-versioned format when the setting was left at its old default.
_LEGACY_DEFAULT_ITERATIONS = 100_000


class PasswordUtils:
    """A utility class for handling password-related operations, such as hashing, verification, and validation."""

    @staticmethod
    def hash_password(password: str, auth_config: AuthConfig | None = None) -> str:
        """Hashes a password using PBKDF2 with SHA256.

        Args:
            password (str): The password to hash.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            str: A self-describing string in the format ``pbkdf2_sha256$<iterations>$<salt>$<hash>`` where salt and
                hash are base64-encoded. The iteration count is stored with the hash, so changing
                ``HASH_ITERATIONS`` or ``SALT_LENGTH`` later does not invalidate existing hashes.
        """
        configs = auth_config or BaseConfig.global_config().AUTH
        salt = os.urandom(configs.SALT_LENGTH)
        iterations = configs.HASH_ITERATIONS
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)

        return _HASH_SEPARATOR.join(
            (_HASH_SCHEME, str(iterations), b64encode(salt).decode("utf-8"), b64encode(pw_hash).decode("utf-8")),
        )

    @staticmethod
    def verify_password(password: str, stored_password: str, auth_config: AuthConfig | None = None) -> bool:
        """Verifies a password against a stored hash.

        Both the current ``pbkdf2_sha256$...`` format and the legacy format (base64 of ``salt + hash``, written by
        earlier versions) are accepted. Legacy hashes carry no parameters, so they are tried with the configured
        ``HASH_ITERATIONS`` and, if that differs, with the former default of 100000.

        Args:
            password (str): The password to verify.
            stored_password (str): The stored password hash to compare against.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            bool: True if the password matches the stored hash, False otherwise.
        """
        try:
            configs = auth_config or BaseConfig.global_config().AUTH

            if stored_password.startswith(_HASH_SCHEME + _HASH_SEPARATOR):
                _, iterations, salt_b64, hash_b64 = stored_password.split(_HASH_SEPARATOR)
                salt = b64decode(salt_b64.encode("utf-8"), validate=True)
                stored_hash = b64decode(hash_b64.encode("utf-8"), validate=True)
                return PasswordUtils._matches(password, salt, stored_hash, int(iterations))

            # Legacy format: base64(salt + hash)
            decoded = b64decode(stored_password.encode("utf-8"))
            salt = decoded[: configs.SALT_LENGTH]
            stored_hash = decoded[configs.SALT_LENGTH :]
            candidates = dict.fromkeys((configs.HASH_ITERATIONS, _LEGACY_DEFAULT_ITERATIONS))
            return any(PasswordUtils._matches(password, salt, stored_hash, count) for count in candidates)
        except ValueError, TypeError, IndexError:
            # Catch specific exceptions that could occur during decoding or comparison
            return False

    @staticmethod
    def _matches(password: str, salt: bytes, stored_hash: bytes, iterations: int) -> bool:
        """Hash ``password`` with the given parameters and compare in constant time."""
        if iterations < 1:
            return False
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(pw_hash, stored_hash)

    @staticmethod
    def validate_password(
        password: str,
        auth_config: AuthConfig | None = None,
    ) -> None:
        """Validates a password against the password policy.

        Args:
            password (str): The password to validate.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Raises:
            InvalidPasswordError: If the password does not meet the policy requirements.
        """
        configs = auth_config or BaseConfig.global_config().AUTH
        errors = []

        if len(password) < configs.MIN_LENGTH:
            errors.append(f"Password must be at least {configs.MIN_LENGTH} characters long.")

        if configs.REQUIRE_DIGIT and not any(char.isdigit() for char in password):
            errors.append("Password must contain at least one digit.")

        if configs.REQUIRE_LOWERCASE and not any(char.islower() for char in password):
            errors.append("Password must contain at least one lowercase letter.")

        if configs.REQUIRE_UPPERCASE and not any(char.isupper() for char in password):
            errors.append("Password must contain at least one uppercase letter.")

        if configs.REQUIRE_SPECIAL and not any(char in configs.SPECIAL_CHARACTERS for char in password):
            errors.append(f"Password must contain at least one special character: {configs.SPECIAL_CHARACTERS}")

        if errors:
            raise InvalidPasswordError(requirements=errors)

    @staticmethod
    def generate_password(auth_config: AuthConfig | None = None) -> str:
        """Generates a random password that meets the policy requirements.

        Args:
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.

        Returns:
            str: A randomly generated password that meets the policy requirements.
        """
        configs = auth_config or BaseConfig.global_config().AUTH

        lowercase_chars = string.ascii_lowercase
        uppercase_chars = string.ascii_uppercase
        digit_chars = string.digits
        special_chars = "".join(configs.SPECIAL_CHARACTERS)

        # Initialize with required characters
        password_chars = []
        if configs.REQUIRE_LOWERCASE:
            password_chars.append(secrets.choice(lowercase_chars))
        if configs.REQUIRE_UPPERCASE:
            password_chars.append(secrets.choice(uppercase_chars))
        if configs.REQUIRE_DIGIT:
            password_chars.append(secrets.choice(digit_chars))
        if configs.REQUIRE_SPECIAL:
            password_chars.append(secrets.choice(special_chars))

        # Calculate remaining length
        remaining_length = max(0, configs.MIN_LENGTH - len(password_chars))

        # Add random characters to meet minimum length
        all_chars = lowercase_chars + uppercase_chars + digit_chars + special_chars
        password_chars.extend(secrets.choice(all_chars) for _ in range(remaining_length))

        # Shuffle the password characters
        shuffled = list(password_chars)
        secrets.SystemRandom().shuffle(shuffled)

        return "".join(shuffled)

    @classmethod
    def validate_password_history(
        cls,
        new_password: str,
        password_history: list[str],
        auth_config: AuthConfig | None = None,
        lang: LanguageType | None = None,
    ) -> None:
        """Validates a new password against the password history.

        Args:
            new_password (str): The new password to validate.
            password_history (list[str]): A list of previous password hashes.
            auth_config (AuthConfig | None): Optional auth configuration override.
                If not provided, uses the global config.
            lang (LanguageType): The language to use for error messages. Defaults to Persian.

        Raises:
            InvalidPasswordError: If the new password has been used recently or does not meet the policy requirements.
        """
        configs = auth_config or BaseConfig.global_config().AUTH

        # First validate against password policy
        cls.validate_password(new_password, configs)

        # Check password history (a size of 0 disables the check)
        history_size = max(configs.PASSWORD_HISTORY_SIZE, 0)
        if history_size and any(
            cls.verify_password(new_password, old_password, configs)
            for old_password in password_history[-history_size:]
        ):
            raise InvalidPasswordError(requirements=["Password has been used recently"], lang=lang)
