import base64
import hashlib
from pathlib import Path

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import FileConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.models.errors import InvalidArgumentError, OutOfRangeError


class FileUtils:
    """A utility class for handling file-related operations, such as creating secure links and validating file names."""

    @staticmethod
    def _create_secure_link_hash(path: str, expires_at: float, file_config: FileConfig | None = None) -> str:
        """Generates a secure hash for a file link based on the file path, expiration timestamp, and secret key.

        Args:
            path (str): The file path to generate the hash for.
            expires_at (float): The expiration timestamp for the link.
            file_config (FileConfig | None): Optional file configuration object. If not provided, uses the global config.

        Returns:
            str: A base64-encoded secure hash for the file link.

        Raises:
            InvalidArgumentError: If the `SECRET_KEY` in the configuration is `None`.
        """
        configs: FileConfig = file_config or BaseConfig.global_config().FILE
        secret: str | None = configs.SECRET_KEY
        if secret is None:
            raise InvalidArgumentError(argument_name="SECRET_KEY")
        _input = f"{expires_at}{path} {secret}"
        # nginx secure_link requires MD5; keep for compatibility (not used for cryptographic security)
        hash_object = hashlib.md5(_input.encode("utf8"))
        return base64.urlsafe_b64encode(hash_object.digest()).decode("utf-8").rstrip("=")

    @classmethod
    def create_secure_link(
        cls,
        path: str,
        minutes: int | None = None,
        file_config: FileConfig | None = None,
    ) -> str:
        """Creates a secure link with expiration for file access.

        Args:
            path (str): The file path to create a secure link for.
            minutes (int | None): Number of minutes until link expiration. Defaults to the config's `DEFAULT_EXPIRY_MINUTES`.
            file_config (FileConfig | None): Optional file configuration object. If not provided, uses the global config.

        Returns:
            str: A secure link with a hash and expiration timestamp.

        Raises:
            InvalidArgumentError: If the `path` is empty.
            OutOfRangeError: If `minutes` is less than 1.
        """
        if not path:
            raise InvalidArgumentError(argument_name="path")

        configs: FileConfig = file_config or BaseConfig.global_config().FILE
        expiry_minutes: int = minutes if minutes is not None else configs.DEFAULT_EXPIRY_MINUTES

        if expiry_minutes < 1:
            raise OutOfRangeError(field_name="minutes")

        expires_at = int(DatetimeUtils.get_datetime_after_given_datetime_or_now(minutes=expiry_minutes).timestamp())
        secure_link_hash = cls._create_secure_link_hash(path, expires_at, file_config)

        return f"{path}?md5={secure_link_hash}&expires_at={expires_at}"

    @classmethod
    def validate_file_name(
        cls,
        file_name: str,
        file_config: FileConfig | None = None,
    ) -> bool:
        """Validates a file name based on allowed extensions.

        Args:
            file_name (str): The file name to validate.
            file_config (FileConfig | None): Optional file configuration object. If not provided, uses the global config.

        Returns:
            bool: `True` if the file name has an allowed extension, `False` otherwise.

        Raises:
            InvalidArgumentError: If `file_name` is not a string or `allowed_extensions` is not a list.
        """
        configs: FileConfig = file_config or BaseConfig.global_config().FILE
        allowed_extensions: list[str] = configs.ALLOWED_EXTENSIONS

        if not isinstance(file_name, str):
            raise InvalidArgumentError(argument_name="file_name")

        if not allowed_extensions:
            raise InvalidArgumentError(argument_name="allowed_extensions")

        file_path = Path(file_name)
        ext = file_path.suffix[1:].lower()
        return ext in allowed_extensions and bool(ext)
