"""HashiCorp Vault adapter implementation using hvac."""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING, Any, NoReturn, override

import hvac.exceptions
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout as RequestsTimeout

from archipy.adapters.vault.ports import VaultPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import VaultConfig
from archipy.configs.vault_settings_source import create_vault_client
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.dtos.vault_lease_dto import VaultLeaseDTO
from archipy.models.errors import (
    BaseError,
    ConfigurationError,
    InvalidArgumentError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    UnavailableError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def _lease_from_response(
    response: dict[str, Any],
    *,
    default_lease_id: str = "",
    include_credential_data: bool = True,
) -> VaultLeaseDTO:
    """Build a ``VaultLeaseDTO`` from an hvac lease response.

    Prefer top-level ``lease_id`` / ``lease_duration`` (hvac sys renew / database
    generate_credentials). Fall back to nested ``data`` when needed.

    Args:
        response: Parsed JSON response from hvac.
        default_lease_id: Fallback lease id when the response omits one.
        include_credential_data: When True, copy ``response["data"]`` into the DTO.

    Returns:
        Normalized lease DTO.
    """
    lease_source = response if "lease_id" in response else (response.get("data") or response)
    if not isinstance(lease_source, dict):
        lease_source = {}
    credential_data = dict(response.get("data") or {}) if include_credential_data else {}
    return VaultLeaseDTO(
        lease_id=str(lease_source.get("lease_id", default_lease_id)),
        lease_duration=int(lease_source.get("lease_duration", 0)),
        renewable=bool(lease_source.get("renewable", False)),
        data=credential_data,
    )


class VaultExceptionHandlerMixin:
    """Map hvac/network exceptions to ArchiPy domain errors."""

    @classmethod
    def _handle_vault_exception(cls, exception: Exception, operation: str) -> NoReturn:
        """Convert Vault client failures into domain errors.

        Args:
            exception: Original exception from hvac or requests.
            operation: Name of the failing operation.

        Raises:
            NotFoundError: When the path or secret does not exist.
            PermissionDeniedError: When authz fails.
            InvalidArgumentError: When Vault rejects the request parameters.
            UnavailableError: When Vault is down or rate-limited.
            NetworkError: When the network call fails.
            ConfigurationError: For other Vault errors.
        """
        if isinstance(exception, hvac.exceptions.InvalidPath):
            raise NotFoundError(resource_type="vault_secret") from exception
        if isinstance(exception, hvac.exceptions.Forbidden | hvac.exceptions.Unauthorized):
            raise PermissionDeniedError(
                additional_data={"details": f"Permission denied for Vault operation: {operation}"},
            ) from exception
        if isinstance(exception, hvac.exceptions.InvalidRequest | hvac.exceptions.ParamValidationError):
            raise InvalidArgumentError(argument_name=operation) from exception
        if isinstance(exception, hvac.exceptions.VaultDown | hvac.exceptions.RateLimitExceeded):
            raise UnavailableError(resource_type="Vault", additional_data={"operation": operation}) from exception
        if isinstance(exception, RequestsConnectionError | RequestsTimeout):
            raise NetworkError(service="Vault") from exception
        if isinstance(exception, hvac.exceptions.VaultError):
            raise ConfigurationError(operation=operation, reason=str(exception)) from exception
        raise ConfigurationError(operation=operation, reason=str(exception)) from exception


class VaultAdapter(VaultPort, VaultExceptionHandlerMixin):
    """Concrete Vault adapter wrapping ``hvac.Client``."""

    def __init__(self, vault_configs: VaultConfig | None = None) -> None:
        """Initialize the Vault adapter.

        Args:
            vault_configs: Optional Vault configuration. If None, uses
                ``BaseConfig.global_config().VAULT``.

        Raises:
            ConfigurationError: If authentication or connection fails.
            InvalidArgumentError: If required configuration is missing.
        """
        if vault_configs is not None:
            self.configs = vault_configs
        else:
            global_config = BaseConfig.global_config()
            vault_config = getattr(global_config, "VAULT", None)
            if not isinstance(vault_config, VaultConfig):
                raise InvalidArgumentError(argument_name="VAULT")
            self.configs = vault_config

        if not self.configs.ADDR:
            raise InvalidArgumentError(argument_name="ADDR")

        try:
            self._client = create_vault_client(self.configs)
        except ConfigurationError:
            raise
        except Exception as e:
            raise ConfigurationError(operation="vault_connect", reason=str(e)) from e

        self.token_renew_count = 0

        # Per-instance TTL cache so SECRET_CACHE_TTL on this config is honored.
        # Class-level decoration cannot see instance config and resolves TTL too early.
        ttl = max(self.configs.SECRET_CACHE_TTL, 0)
        self._read_secret_cached: Any | None = None
        if ttl > 0:
            cached = ttl_cache_decorator(ttl_seconds=ttl, maxsize=100)(VaultAdapter._read_secret_uncached)
            self._read_secret_cached = cached.__get__(self, VaultAdapter)

    def _mount(self, mount_point: str | None) -> str:
        """Resolve the KV mount point."""
        return mount_point if mount_point is not None else self.configs.MOUNT_POINT

    def _run[T](self, operation: str, fn: Callable[[], T]) -> T:
        """Execute a Vault call, mapping client failures to domain errors.

        Args:
            operation: Operation name for error context.
            fn: Zero-arg callable performing the Vault client work.

        Returns:
            Whatever ``fn`` returns.

        Raises:
            BaseError: Domain errors raised by ``fn`` are re-raised unchanged.
            ConfigurationError: For unmapped Vault/client failures.
        """
        self._maybe_renew_token()
        try:
            return fn()
        except BaseError:
            raise
        except Exception as e:
            self._handle_vault_exception(e, operation)

    def _maybe_renew_token(self) -> None:
        """Renew the client token when AUTO_RENEW_TOKEN is enabled and TTL is low."""
        if not self.configs.AUTO_RENEW_TOKEN:
            return
        try:
            lookup = self._client.auth.token.lookup_self()
            ttl = int(lookup.get("data", {}).get("ttl", 0))
            if ttl <= self.configs.RENEW_THRESHOLD_SECONDS:
                self._client.auth.token.renew_self()
                self.token_renew_count += 1
                logger.debug("Renewed Vault token (previous TTL=%s)", ttl)
        except Exception as e:
            self._handle_vault_exception(e, "renew_token")

    def clear_secret_cache(self) -> None:
        """Clear all cached ``read_secret`` results."""
        cached = self._read_secret_cached
        if cached is not None and hasattr(cached, "clear_cache"):
            cached.clear_cache()

    def _read_secret_uncached(self, path: str, mount_point: str | None = None) -> dict[str, Any]:
        """Fetch a KV v2 secret without using the instance cache."""
        mount = self._mount(mount_point)

        def _read() -> dict[str, Any]:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=mount,
                raise_on_deleted_version=True,
            )
            data = response.get("data", {}).get("data") or {}
            if not isinstance(data, dict):
                raise ConfigurationError(
                    operation="read_secret",
                    reason=f"Vault secret at '{path}' did not return a dict payload",
                )
            return {str(k): v for k, v in data.items()}

        return self._run("read_secret", _read)

    @override
    def read_secret(self, path: str, mount_point: str | None = None) -> dict[str, Any]:
        """Read a KV v2 secret.

        Args:
            path: Secret path within the mount.
            mount_point: Optional KV v2 mount override.

        Returns:
            Secret key/value payload.

        Raises:
            InvalidArgumentError: If path is empty.
            NotFoundError: If the secret does not exist.
            PermissionDeniedError: If access is denied.
            ConfigurationError: For other Vault errors.
        """
        if not path:
            raise InvalidArgumentError(argument_name="path")
        if self._read_secret_cached is not None:
            return self._read_secret_cached(path, mount_point)
        return self._read_secret_uncached(path, mount_point)

    @override
    def write_secret(
        self,
        path: str,
        secret: dict[str, Any],
        mount_point: str | None = None,
    ) -> None:
        """Write a KV v2 secret.

        Args:
            path: Secret path within the mount.
            secret: Key/value payload to store.
            mount_point: Optional KV v2 mount override.

        Raises:
            InvalidArgumentError: If path is empty or secret is empty.
            PermissionDeniedError: If access is denied.
            ConfigurationError: For other Vault errors.
        """
        if not path:
            raise InvalidArgumentError(argument_name="path")
        if not secret:
            raise InvalidArgumentError(argument_name="secret")
        mount = self._mount(mount_point)

        def _write() -> None:
            self._client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret,
                mount_point=mount,
            )
            self.clear_secret_cache()

        self._run("write_secret", _write)

    @override
    def delete_secret(self, path: str, mount_point: str | None = None) -> None:
        """Delete a KV v2 secret including metadata and all versions.

        Args:
            path: Secret path within the mount.
            mount_point: Optional KV v2 mount override.

        Raises:
            InvalidArgumentError: If path is empty.
            NotFoundError: If the secret does not exist.
            PermissionDeniedError: If access is denied.
            ConfigurationError: For other Vault errors.
        """
        if not path:
            raise InvalidArgumentError(argument_name="path")
        mount = self._mount(mount_point)

        def _delete() -> None:
            self._client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path,
                mount_point=mount,
            )
            self.clear_secret_cache()

        self._run("delete_secret", _delete)

    @override
    def list_secrets(self, path: str, mount_point: str | None = None) -> list[str]:
        """List secret keys under a path.

        Args:
            path: Path prefix to list.
            mount_point: Optional KV v2 mount override.

        Returns:
            List of key names.

        Raises:
            NotFoundError: If the path does not exist.
            PermissionDeniedError: If access is denied.
            ConfigurationError: For other Vault errors.
        """
        mount = self._mount(mount_point)

        def _list() -> list[str]:
            response = self._client.secrets.kv.v2.list_secrets(path=path, mount_point=mount)
            keys = response.get("data", {}).get("keys") or []
            return [str(key) for key in keys]

        return self._run("list_secrets", _list)

    @override
    def get_dynamic_credentials(
        self,
        mount_point: str,
        role: str,
        *,
        parameters: dict[str, Any] | None = None,
    ) -> VaultLeaseDTO:
        """Generate dynamic credentials for a secrets-engine role.

        Args:
            mount_point: Secrets engine mount (e.g. ``database`` or ``ssh``).
            role: Role name that generates credentials.
            parameters: Optional engine-specific parameters. When provided (including
                an empty dict), issues a write to ``{mount}/creds/{role}`` (needed for
                engines like SSH OTP). When ``None``, uses the typed database API
                ``secrets.database.generate_credentials``, falling back to a generic
                read for non-database engines.

        Returns:
            Lease metadata and credential payload.

        Raises:
            InvalidArgumentError: If mount_point or role is empty.
            PermissionDeniedError: If access is denied.
            ConfigurationError: For other Vault errors.
        """
        if not mount_point:
            raise InvalidArgumentError(argument_name="mount_point")
        if not role:
            raise InvalidArgumentError(argument_name="role")
        path = f"{mount_point}/creds/{role}"

        def _get_creds() -> VaultLeaseDTO:
            if parameters is not None:
                response = self._client.write(path, **parameters)
            else:
                try:
                    response = self._client.secrets.database.generate_credentials(
                        name=role,
                        mount_point=mount_point,
                    )
                except hvac.exceptions.InvalidPath, hvac.exceptions.UnexpectedError:
                    response = self._client.read(path)
            if response is None:
                raise NotFoundError(resource_type="vault_role")
            return _lease_from_response(response, include_credential_data=True)

        return self._run("get_dynamic_credentials", _get_creds)

    @override
    def renew_lease(self, lease_id: str, increment: int | None = None) -> VaultLeaseDTO:
        """Renew a dynamic secret lease.

        Args:
            lease_id: Lease identifier to renew.
            increment: Optional requested TTL extension in seconds.

        Returns:
            Updated lease metadata.

        Raises:
            InvalidArgumentError: If lease_id is empty.
            ConfigurationError: For Vault errors.
        """
        if not lease_id:
            raise InvalidArgumentError(argument_name="lease_id")

        def _renew() -> VaultLeaseDTO:
            kwargs: dict[str, Any] = {"lease_id": lease_id}
            if increment is not None:
                kwargs["increment"] = increment
            response = self._client.sys.renew_lease(**kwargs)
            return _lease_from_response(
                response,
                default_lease_id=lease_id,
                include_credential_data=False,
            )

        return self._run("renew_lease", _renew)

    @override
    def revoke_lease(self, lease_id: str) -> None:
        """Revoke a dynamic secret lease.

        Args:
            lease_id: Lease identifier to revoke.

        Raises:
            InvalidArgumentError: If lease_id is empty.
            ConfigurationError: For Vault errors.
        """
        if not lease_id:
            raise InvalidArgumentError(argument_name="lease_id")
        self._run("revoke_lease", lambda: self._client.sys.revoke_lease(lease_id=lease_id))

    @override
    def encrypt(self, key_name: str, plaintext: str, mount_point: str = "transit") -> str:
        """Encrypt plaintext using the transit secrets engine.

        Args:
            key_name: Transit key name.
            plaintext: UTF-8 plaintext to encrypt.
            mount_point: Transit mount point.

        Returns:
            Vault ciphertext string.

        Raises:
            InvalidArgumentError: If key_name or plaintext is empty.
            ConfigurationError: For Vault errors.
        """
        if not key_name:
            raise InvalidArgumentError(argument_name="key_name")
        if plaintext == "":
            raise InvalidArgumentError(argument_name="plaintext")
        encoded = base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

        def _encrypt() -> str:
            response = self._client.secrets.transit.encrypt_data(
                name=key_name,
                plaintext=encoded,
                mount_point=mount_point,
            )
            return str(response["data"]["ciphertext"])

        return self._run("encrypt", _encrypt)

    @override
    def decrypt(self, key_name: str, ciphertext: str, mount_point: str = "transit") -> str:
        """Decrypt ciphertext using the transit secrets engine.

        Args:
            key_name: Transit key name.
            ciphertext: Vault ciphertext string.
            mount_point: Transit mount point.

        Returns:
            Decoded UTF-8 plaintext.

        Raises:
            InvalidArgumentError: If key_name or ciphertext is empty.
            ConfigurationError: For Vault errors.
        """
        if not key_name:
            raise InvalidArgumentError(argument_name="key_name")
        if not ciphertext:
            raise InvalidArgumentError(argument_name="ciphertext")

        def _decrypt() -> str:
            response = self._client.secrets.transit.decrypt_data(
                name=key_name,
                ciphertext=ciphertext,
                mount_point=mount_point,
            )
            encoded = str(response["data"]["plaintext"])
            return base64.b64decode(encoded.encode("ascii")).decode("utf-8")

        return self._run("decrypt", _decrypt)
