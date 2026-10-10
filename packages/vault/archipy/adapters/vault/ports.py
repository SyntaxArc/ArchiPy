"""Port definitions for HashiCorp Vault operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.vault_lease_dto import VaultLeaseDTO


class VaultPort(ABC):
    """Interface for HashiCorp Vault operations.

    Defines the contract for Vault adapters covering KV v2 secrets, dynamic
    leases, and transit encryption.
    """

    @abstractmethod
    def read_secret(self, path: str, mount_point: str | None = None) -> dict[str, Any]:
        """Read a KV v2 secret.

        Args:
            path: Secret path within the mount.
            mount_point: Optional KV v2 mount override; defaults to config mount.

        Returns:
            Secret key/value payload.
        """
        raise NotImplementedError

    @abstractmethod
    def write_secret(
        self,
        path: str,
        secret: dict[str, Any],
        mount_point: str | None = None,
    ) -> None:
        """Write (create or update) a KV v2 secret.

        Args:
            path: Secret path within the mount.
            secret: Key/value payload to store.
            mount_point: Optional KV v2 mount override; defaults to config mount.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_secret(self, path: str, mount_point: str | None = None) -> None:
        """Delete a KV v2 secret (all versions and metadata).

        Args:
            path: Secret path within the mount.
            mount_point: Optional KV v2 mount override; defaults to config mount.
        """
        raise NotImplementedError

    @abstractmethod
    def list_secrets(self, path: str, mount_point: str | None = None) -> list[str]:
        """List secret keys under a path.

        Args:
            path: Path prefix to list.
            mount_point: Optional KV v2 mount override; defaults to config mount.

        Returns:
            List of key names (directories end with ``/``).
        """
        raise NotImplementedError

    @abstractmethod
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
            parameters: Optional engine-specific parameters (e.g. ``{"ip": "127.0.0.1"}``
                for SSH OTP). When not ``None``, issues a write to ``{mount}/creds/{role}``.
                When ``None``, uses the database secrets engine generate-credentials API
                (with a generic read fallback for other engines).

        Returns:
            Lease metadata and credential payload.
        """
        raise NotImplementedError

    @abstractmethod
    def renew_lease(self, lease_id: str, increment: int | None = None) -> VaultLeaseDTO:
        """Renew a dynamic secret lease.

        Args:
            lease_id: Lease identifier to renew.
            increment: Optional requested TTL extension in seconds.

        Returns:
            Updated lease metadata.
        """
        raise NotImplementedError

    @abstractmethod
    def revoke_lease(self, lease_id: str) -> None:
        """Revoke a dynamic secret lease.

        Args:
            lease_id: Lease identifier to revoke.
        """
        raise NotImplementedError

    @abstractmethod
    def encrypt(self, key_name: str, plaintext: str, mount_point: str = "transit") -> str:
        """Encrypt plaintext using the transit secrets engine.

        Args:
            key_name: Transit key name.
            plaintext: UTF-8 plaintext to encrypt.
            mount_point: Transit mount point.

        Returns:
            Vault ciphertext string (e.g. ``vault:v1:...``).
        """
        raise NotImplementedError

    @abstractmethod
    def decrypt(self, key_name: str, ciphertext: str, mount_point: str = "transit") -> str:
        """Decrypt ciphertext using the transit secrets engine.

        Args:
            key_name: Transit key name.
            ciphertext: Vault ciphertext string.
            mount_point: Transit mount point.

        Returns:
            Decoded UTF-8 plaintext.
        """
        raise NotImplementedError
