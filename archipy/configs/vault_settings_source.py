"""HashiCorp Vault settings source and shared client factory for ArchiPy.

Provides:
- ``create_vault_client`` — authenticate an ``hvac.Client`` from a ``VaultConfig``
- ``VaultSettingsSource`` — pull KV v2 secrets into ``BaseConfig`` at startup

This module imports ``hvac`` at module level and belongs to the ``vault`` optional
extra. ``BaseConfig`` loads ``VaultSettingsSource`` via ``importlib`` so apps that
do not install ``archipy[vault]`` never import this module.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

import hvac
from pydantic_settings import PydanticBaseSettingsSource
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from archipy.configs.config_template import VaultConfig
from archipy.models.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from pydantic.fields import FieldInfo
    from requests import Response
    from requests.models import PreparedRequest

VaultAuthMethod = Literal[
    "token",
    "approle",
    "kubernetes",
    "userpass",
    "ldap",
    "okta",
    "jwt",
    "aws",
    "azure",
    "gcp",
    "github",
    "cert",
]

logger = logging.getLogger(__name__)

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _read_file_secret(path: str) -> str:
    """Read and strip a secret from a filesystem path.

    Args:
        path: Absolute or relative path to the secret file.

    Returns:
        The file contents with leading/trailing whitespace removed.

    Raises:
        ConfigurationError: If the file cannot be read.
    """
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError as e:
        raise ConfigurationError(
            operation="vault_read_secret_file",
            reason=f"Failed to read secret file '{path}': {e}",
        ) from e


def _resolve_token(config: VaultConfig) -> str | None:
    """Resolve the Vault token from TOKEN_FILE or TOKEN."""
    if config.TOKEN_FILE:
        return _read_file_secret(config.TOKEN_FILE)
    return config.TOKEN


def _resolve_approle_secret_id(config: VaultConfig) -> str | None:
    """Resolve the AppRole secret_id from file or inline value."""
    if config.APPROLE_SECRET_ID_FILE:
        return _read_file_secret(config.APPROLE_SECRET_ID_FILE)
    return config.APPROLE_SECRET_ID


def _resolve_password(config: VaultConfig) -> str | None:
    """Resolve password from PASSWORD_FILE or PASSWORD."""
    if config.PASSWORD_FILE:
        return _read_file_secret(config.PASSWORD_FILE)
    return config.PASSWORD


def _resolve_optional_file_or_value(file_path: str | None, value: str | None) -> str | None:
    """Resolve a secret from an optional file path, else an inline value."""
    if file_path:
        return _read_file_secret(file_path)
    return value


_SUPPORTED_AUTH_METHODS = frozenset(
    {
        "token",
        "approle",
        "kubernetes",
        "userpass",
        "ldap",
        "okta",
        "jwt",
        "aws",
        "azure",
        "gcp",
        "github",
        "cert",
    },
)


def _build_session(config: VaultConfig) -> Session:
    """Build a ``requests.Session`` with retry settings.

    ``CONNECT_TIMEOUT`` / ``READ_TIMEOUT`` are applied as the default
    ``timeout`` tuple on the session via an HTTPAdapter hook on ``send``.

    Args:
        config: Vault configuration.

    Returns:
        A configured ``requests.Session``.
    """
    session = Session()
    retry = Retry(
        total=config.RETRIES_MAX_ATTEMPTS,
        connect=config.RETRIES_MAX_ATTEMPTS,
        read=config.RETRIES_MAX_ATTEMPTS,
        status=config.RETRIES_MAX_ATTEMPTS,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "PUT", "POST", "DELETE", "LIST", "HEAD"}),
    )
    timeout = (config.CONNECT_TIMEOUT, config.READ_TIMEOUT)
    adapter = _TimeoutHTTPAdapter(timeout=timeout, max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class _TimeoutHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that injects a default request timeout."""

    def __init__(
        self,
        timeout: tuple[float, float],
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        max_retries: int | Retry = 0,
        *,
        pool_block: bool = False,
    ) -> None:
        self._timeout = timeout
        super().__init__(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries,
            pool_block=pool_block,
        )

    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: float | tuple[float, float] | tuple[float, None] | None = None,
        verify: bool | str = True,
        cert: bytes | str | tuple[bytes | str, bytes | str] | None = None,
        proxies: Mapping[str, str] | None = None,
    ) -> Response:
        """Send the request, applying the default timeout when unset."""
        effective_timeout = self._timeout if timeout is None else timeout
        return super().send(
            request,
            stream=stream,
            timeout=effective_timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )


def create_vault_client(config: VaultConfig) -> hvac.Client:
    """Build and authenticate an ``hvac.Client`` from a ``VaultConfig``.

    Resolves file-based secrets, applies TLS/mTLS and timeout/retry settings,
    then authenticates using the configured ``AUTH_METHOD``.

    Args:
        config: Vault connection and authentication settings.

    Returns:
        An authenticated ``hvac.Client``.

    Raises:
        ConfigurationError: If required auth fields are missing or authentication fails.
    """
    if not config.ADDR:
        raise ConfigurationError(operation="vault_connect", reason="VAULT.ADDR is required when Vault is enabled")

    verify: bool | str = config.CA_CERT_PATH or config.VERIFY_SSL
    cert: tuple[str, str] | None = None
    if config.CLIENT_CERT_PATH and config.CLIENT_KEY_PATH:
        cert = (config.CLIENT_CERT_PATH, config.CLIENT_KEY_PATH)
    elif config.CLIENT_CERT_PATH or config.CLIENT_KEY_PATH:
        raise ConfigurationError(
            operation="vault_tls",
            reason="Both CLIENT_CERT_PATH and CLIENT_KEY_PATH must be set for mutual TLS",
        )

    session = _build_session(config)
    client = hvac.Client(
        url=config.ADDR,
        namespace=config.NAMESPACE,
        verify=verify,
        cert=cert,
        session=session,
    )

    try:
        _authenticate(client, config)
    except ConfigurationError:
        raise
    except Exception as e:
        raise ConfigurationError(
            operation="vault_auth",
            reason=f"Vault authentication failed ({config.AUTH_METHOD}): {e}",
        ) from e

    if not client.is_authenticated():
        raise ConfigurationError(
            operation="vault_auth",
            reason=f"Vault client is not authenticated after {config.AUTH_METHOD} auth",
        )

    return client


def _set_client_token_from_auth_response(client: hvac.Client, response: dict[str, Any]) -> None:
    """Assign ``client.token`` from an hvac auth login response."""
    client.token = response["auth"]["client_token"]


def _authenticate_token(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with a static Vault token."""
    token = _resolve_token(config)
    if not token:
        raise ConfigurationError(
            operation="vault_auth",
            reason="TOKEN or TOKEN_FILE is required for token auth",
        )
    client.token = token


def _authenticate_approle(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with AppRole."""
    if not config.APPROLE_ROLE_ID:
        raise ConfigurationError(
            operation="vault_auth",
            reason="APPROLE_ROLE_ID is required for approle auth",
        )
    secret_id = _resolve_approle_secret_id(config)
    if not secret_id:
        raise ConfigurationError(
            operation="vault_auth",
            reason="APPROLE_SECRET_ID or APPROLE_SECRET_ID_FILE is required for approle auth",
        )
    response = client.auth.approle.login(
        role_id=config.APPROLE_ROLE_ID,
        secret_id=secret_id,
        mount_point=config.APPROLE_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_kubernetes(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with Kubernetes service account JWT."""
    if not config.KUBERNETES_ROLE:
        raise ConfigurationError(
            operation="vault_auth",
            reason="KUBERNETES_ROLE is required for kubernetes auth",
        )
    jwt = _read_file_secret(config.KUBERNETES_JWT_PATH)
    response = client.auth.kubernetes.login(
        role=config.KUBERNETES_ROLE,
        jwt=jwt,
        mount_point=config.KUBERNETES_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_username_password(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with userpass, ldap, or okta."""
    if not config.USERNAME:
        raise ConfigurationError(
            operation="vault_auth",
            reason="USERNAME is required for userpass/ldap/okta auth",
        )
    password = _resolve_password(config)
    if not password:
        raise ConfigurationError(
            operation="vault_auth",
            reason="PASSWORD or PASSWORD_FILE is required for userpass/ldap/okta auth",
        )
    if config.AUTH_METHOD == "userpass":
        response = client.auth.userpass.login(
            username=config.USERNAME,
            password=password,
            mount_point=config.USERPASS_MOUNT_POINT,
        )
    elif config.AUTH_METHOD == "ldap":
        response = client.auth.ldap.login(
            username=config.USERNAME,
            password=password,
            mount_point=config.LDAP_MOUNT_POINT,
        )
    else:
        response = client.auth.okta.login(
            username=config.USERNAME,
            password=password,
            mount_point=config.OKTA_MOUNT_POINT,
        )
    _set_client_token_from_auth_response(client, response)


def _authenticate_jwt(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with the JWT auth method."""
    if not config.JWT_ROLE:
        raise ConfigurationError(operation="vault_auth", reason="JWT_ROLE is required for jwt auth")
    jwt = _resolve_optional_file_or_value(config.JWT_FILE, config.JWT)
    if not jwt:
        raise ConfigurationError(
            operation="vault_auth",
            reason="JWT or JWT_FILE is required for jwt auth",
        )
    response = client.auth.jwt.jwt_login(
        role=config.JWT_ROLE,
        jwt=jwt,
        path=config.JWT_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_aws(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with AWS IAM."""
    if not config.AWS_ACCESS_KEY or not config.AWS_SECRET_KEY:
        raise ConfigurationError(
            operation="vault_auth",
            reason="AWS_ACCESS_KEY and AWS_SECRET_KEY are required for aws auth",
        )
    response = client.auth.aws.iam_login(
        access_key=config.AWS_ACCESS_KEY,
        secret_key=config.AWS_SECRET_KEY,
        session_token=config.AWS_SESSION_TOKEN,
        role=config.AWS_ROLE,
        region=config.AWS_REGION,
        mount_point=config.AWS_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_azure(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with Azure."""
    if not config.AZURE_ROLE:
        raise ConfigurationError(operation="vault_auth", reason="AZURE_ROLE is required for azure auth")
    jwt = _resolve_optional_file_or_value(config.AZURE_JWT_FILE, config.AZURE_JWT)
    if not jwt:
        raise ConfigurationError(
            operation="vault_auth",
            reason="AZURE_JWT or AZURE_JWT_FILE is required for azure auth",
        )
    response = client.auth.azure.login(
        role=config.AZURE_ROLE,
        jwt=jwt,
        subscription_id=config.AZURE_SUBSCRIPTION_ID,
        resource_group_name=config.AZURE_RESOURCE_GROUP_NAME,
        vm_name=config.AZURE_VM_NAME,
        vmss_name=config.AZURE_VMSS_NAME,
        mount_point=config.AZURE_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_gcp(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with GCP."""
    if not config.GCP_ROLE:
        raise ConfigurationError(operation="vault_auth", reason="GCP_ROLE is required for gcp auth")
    jwt = _resolve_optional_file_or_value(config.GCP_JWT_FILE, config.GCP_JWT)
    if not jwt:
        raise ConfigurationError(
            operation="vault_auth",
            reason="GCP_JWT or GCP_JWT_FILE is required for gcp auth",
        )
    response = client.auth.gcp.login(
        role=config.GCP_ROLE,
        jwt=jwt,
        mount_point=config.GCP_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


def _authenticate_github(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with a GitHub personal access token."""
    token = _resolve_optional_file_or_value(config.GITHUB_TOKEN_FILE, config.GITHUB_TOKEN)
    if not token:
        raise ConfigurationError(
            operation="vault_auth",
            reason="GITHUB_TOKEN or GITHUB_TOKEN_FILE is required for github auth",
        )
    response = client.auth.github.login(token=token, mount_point=config.GITHUB_MOUNT_POINT)
    _set_client_token_from_auth_response(client, response)


def _authenticate_cert(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate with the TLS certificates auth method."""
    cert_pem = ""
    key_pem = ""
    if config.CLIENT_CERT_PATH:
        cert_pem = _read_file_secret(config.CLIENT_CERT_PATH)
    if config.CLIENT_KEY_PATH:
        key_pem = _read_file_secret(config.CLIENT_KEY_PATH)
    response = client.auth.cert.login(
        name=config.CERT_NAME,
        cert_pem=cert_pem,
        key_pem=key_pem,
        mount_point=config.CERT_MOUNT_POINT,
    )
    _set_client_token_from_auth_response(client, response)


_AUTH_HANDLERS: dict[str, Callable[[hvac.Client, VaultConfig], None]] = {
    "token": _authenticate_token,
    "approle": _authenticate_approle,
    "kubernetes": _authenticate_kubernetes,
    "userpass": _authenticate_username_password,
    "ldap": _authenticate_username_password,
    "okta": _authenticate_username_password,
    "jwt": _authenticate_jwt,
    "aws": _authenticate_aws,
    "azure": _authenticate_azure,
    "gcp": _authenticate_gcp,
    "github": _authenticate_github,
    "cert": _authenticate_cert,
}


def _authenticate(client: hvac.Client, config: VaultConfig) -> None:
    """Authenticate the client using the configured auth method.

    Args:
        client: Unauthenticated hvac client.
        config: Vault configuration.

    Raises:
        ConfigurationError: If required credentials for the auth method are missing.
    """
    handler = _AUTH_HANDLERS.get(config.AUTH_METHOD)
    if handler is None:
        raise ConfigurationError(
            operation="vault_auth",
            reason=f"Unsupported AUTH_METHOD: {config.AUTH_METHOD}",
        )
    handler(client, config)


def _env_truthy(name: str) -> bool:
    """Return True if the named env var is a truthy string."""
    return os.environ.get(name, "").strip().lower() in _TRUTHY


def _parse_secret_paths(raw: str | None) -> list[str]:
    """Parse VAULT__SECRET_PATHS from JSON array or comma-separated string."""
    if not raw or not raw.strip():
        return []
    text = raw.strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise ConfigurationError(
                operation="vault_secret_paths",
                reason=f"VAULT__SECRET_PATHS is not valid JSON: {e}",
            ) from e
        if not isinstance(parsed, list):
            raise ConfigurationError(
                operation="vault_secret_paths",
                reason="VAULT__SECRET_PATHS JSON value must be a list of strings",
            )
        return [str(item) for item in parsed]
    return [part.strip() for part in text.split(",") if part.strip()]


def _env_float(name: str, default: float) -> float:
    """Parse a float env var or return ``default``."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as e:
        raise ConfigurationError(operation="vault_config", reason=f"Invalid float for {name}: {raw}") from e


def _env_int(name: str, default: int) -> int:
    """Parse an int env var or return ``default``."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as e:
        raise ConfigurationError(operation="vault_config", reason=f"Invalid int for {name}: {raw}") from e


def _env_opt(name: str) -> str | None:
    """Return a non-empty env var value, else ``None``."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return None
    return value


def _env_mount(name: str, default: str) -> str:
    """Return an env mount/path value or ``default``."""
    return os.environ.get(name, default) or default


def _vault_config_from_env() -> VaultConfig:
    """Build a ``VaultConfig`` from raw ``VAULT__*`` environment variables.

    Used by ``VaultSettingsSource`` before the full settings pipeline is built.
    """
    auth_method = os.environ.get("VAULT__AUTH_METHOD", "token").strip().lower() or "token"
    if auth_method not in _SUPPORTED_AUTH_METHODS:
        raise ConfigurationError(
            operation="vault_config",
            reason=f"Invalid VAULT__AUTH_METHOD: {auth_method}",
        )

    verify_raw = os.environ.get("VAULT__VERIFY_SSL")
    verify_ssl = True if verify_raw is None or verify_raw.strip() == "" else verify_raw.strip().lower() in _TRUTHY

    return VaultConfig(
        ENABLED=_env_truthy("VAULT__ENABLED"),
        ADDR=_env_opt("VAULT__ADDR"),
        NAMESPACE=_env_opt("VAULT__NAMESPACE"),
        AUTH_METHOD=cast("VaultAuthMethod", auth_method),
        TOKEN=_env_opt("VAULT__TOKEN"),
        TOKEN_FILE=_env_opt("VAULT__TOKEN_FILE"),
        APPROLE_ROLE_ID=_env_opt("VAULT__APPROLE_ROLE_ID"),
        APPROLE_SECRET_ID=_env_opt("VAULT__APPROLE_SECRET_ID"),
        APPROLE_SECRET_ID_FILE=_env_opt("VAULT__APPROLE_SECRET_ID_FILE"),
        APPROLE_MOUNT_POINT=_env_mount("VAULT__APPROLE_MOUNT_POINT", "approle"),
        KUBERNETES_ROLE=_env_opt("VAULT__KUBERNETES_ROLE"),
        KUBERNETES_JWT_PATH=(
            os.environ.get("VAULT__KUBERNETES_JWT_PATH") or "/var/run/secrets/kubernetes.io/serviceaccount/token"
        ),
        KUBERNETES_MOUNT_POINT=_env_mount("VAULT__KUBERNETES_MOUNT_POINT", "kubernetes"),
        USERNAME=_env_opt("VAULT__USERNAME"),
        PASSWORD=_env_opt("VAULT__PASSWORD"),
        PASSWORD_FILE=_env_opt("VAULT__PASSWORD_FILE"),
        USERPASS_MOUNT_POINT=_env_mount("VAULT__USERPASS_MOUNT_POINT", "userpass"),
        LDAP_MOUNT_POINT=_env_mount("VAULT__LDAP_MOUNT_POINT", "ldap"),
        OKTA_MOUNT_POINT=_env_mount("VAULT__OKTA_MOUNT_POINT", "okta"),
        JWT_ROLE=_env_opt("VAULT__JWT_ROLE"),
        JWT=_env_opt("VAULT__JWT"),
        JWT_FILE=_env_opt("VAULT__JWT_FILE"),
        JWT_MOUNT_POINT=_env_mount("VAULT__JWT_MOUNT_POINT", "jwt"),
        AWS_ACCESS_KEY=_env_opt("VAULT__AWS_ACCESS_KEY"),
        AWS_SECRET_KEY=_env_opt("VAULT__AWS_SECRET_KEY"),
        AWS_SESSION_TOKEN=_env_opt("VAULT__AWS_SESSION_TOKEN"),
        AWS_ROLE=_env_opt("VAULT__AWS_ROLE"),
        AWS_REGION=_env_mount("VAULT__AWS_REGION", "us-east-1"),
        AWS_MOUNT_POINT=_env_mount("VAULT__AWS_MOUNT_POINT", "aws"),
        AZURE_ROLE=_env_opt("VAULT__AZURE_ROLE"),
        AZURE_JWT=_env_opt("VAULT__AZURE_JWT"),
        AZURE_JWT_FILE=_env_opt("VAULT__AZURE_JWT_FILE"),
        AZURE_SUBSCRIPTION_ID=_env_opt("VAULT__AZURE_SUBSCRIPTION_ID"),
        AZURE_RESOURCE_GROUP_NAME=_env_opt("VAULT__AZURE_RESOURCE_GROUP_NAME"),
        AZURE_VM_NAME=_env_opt("VAULT__AZURE_VM_NAME"),
        AZURE_VMSS_NAME=_env_opt("VAULT__AZURE_VMSS_NAME"),
        AZURE_MOUNT_POINT=_env_mount("VAULT__AZURE_MOUNT_POINT", "azure"),
        GCP_ROLE=_env_opt("VAULT__GCP_ROLE"),
        GCP_JWT=_env_opt("VAULT__GCP_JWT"),
        GCP_JWT_FILE=_env_opt("VAULT__GCP_JWT_FILE"),
        GCP_MOUNT_POINT=_env_mount("VAULT__GCP_MOUNT_POINT", "gcp"),
        GITHUB_TOKEN=_env_opt("VAULT__GITHUB_TOKEN"),
        GITHUB_TOKEN_FILE=_env_opt("VAULT__GITHUB_TOKEN_FILE"),
        GITHUB_MOUNT_POINT=_env_mount("VAULT__GITHUB_MOUNT_POINT", "github"),
        CERT_NAME=os.environ.get("VAULT__CERT_NAME", "") or "",
        CERT_MOUNT_POINT=_env_mount("VAULT__CERT_MOUNT_POINT", "cert"),
        MOUNT_POINT=_env_mount("VAULT__MOUNT_POINT", "secret"),
        SECRET_PATHS=_parse_secret_paths(os.environ.get("VAULT__SECRET_PATHS")),
        VERIFY_SSL=verify_ssl,
        CA_CERT_PATH=_env_opt("VAULT__CA_CERT_PATH"),
        CLIENT_CERT_PATH=_env_opt("VAULT__CLIENT_CERT_PATH"),
        CLIENT_KEY_PATH=_env_opt("VAULT__CLIENT_KEY_PATH"),
        CONNECT_TIMEOUT=_env_float("VAULT__CONNECT_TIMEOUT", 5.0),
        READ_TIMEOUT=_env_float("VAULT__READ_TIMEOUT", 10.0),
        RETRIES_MAX_ATTEMPTS=_env_int("VAULT__RETRIES_MAX_ATTEMPTS", 3),
        AUTO_RENEW_TOKEN=_env_truthy("VAULT__AUTO_RENEW_TOKEN"),
        RENEW_THRESHOLD_SECONDS=_env_int("VAULT__RENEW_THRESHOLD_SECONDS", 60),
        SECRET_CACHE_TTL=_env_int("VAULT__SECRET_CACHE_TTL", 0),
    )


def _nest_flat_keys(data: dict[str, Any], delimiter: str = "__") -> dict[str, Any]:
    """Convert flat keys with a delimiter into nested dictionaries.

    Example:
        ``{"REDIS__PASSWORD": "x"}`` → ``{"REDIS": {"PASSWORD": "x"}}``
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        parts = key.split(delimiter)
        current = result
        for part in parts[:-1]:
            next_value = current.setdefault(part, {})
            if not isinstance(next_value, dict):
                # Conflict: treat leaf as nested container only when free
                next_value = {}
                current[part] = next_value
            current = next_value
        current[parts[-1]] = value
    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge ``override`` into ``base`` (mutates and returns ``base``)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class VaultSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads KV v2 secrets from HashiCorp Vault.

    Returns an empty dict when ``VAULT__ENABLED`` is not truthy so apps that
    do not use Vault pay zero cost and do not need ``hvac`` installed.
    """

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        """Unused; Vault values are provided via ``__call__``.

        Args:
            field: Pydantic field info (unused).
            field_name: Field name (unused).

        Returns:
            Empty sentinel tuple required by the base class interface.
        """
        _ = field
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Fetch and merge Vault secrets into a nested settings dict.

        Returns:
            Nested configuration dict suitable for pydantic-settings merging.

        Raises:
            ConfigurationError: If Vault is enabled but authentication or reads fail.
        """
        if not _env_truthy("VAULT__ENABLED"):
            return {}

        config = _vault_config_from_env()
        if not config.SECRET_PATHS:
            logger.warning("VAULT__ENABLED is true but VAULT__SECRET_PATHS is empty; skipping Vault load")
            return {}

        try:
            client = create_vault_client(config)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(operation="vault_connect", reason=str(e)) from e

        merged: dict[str, Any] = {}
        for path in config.SECRET_PATHS:
            try:
                response = client.secrets.kv.v2.read_secret_version(
                    path=path,
                    mount_point=config.MOUNT_POINT,
                    raise_on_deleted_version=True,
                )
            except Exception as e:
                raise ConfigurationError(
                    operation="vault_read_secret",
                    reason=f"Failed to read Vault secret at '{config.MOUNT_POINT}/{path}': {e}",
                ) from e

            secret_data = response.get("data", {}).get("data") or {}
            if not isinstance(secret_data, dict):
                raise ConfigurationError(
                    operation="vault_read_secret",
                    reason=f"Vault secret at '{path}' did not return a dict payload",
                )
            nested = _nest_flat_keys({str(k): v for k, v in secret_data.items()})
            _deep_merge(merged, nested)

        return merged
