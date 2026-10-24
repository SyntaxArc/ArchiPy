"""Keycloak port mixins for client attribute certificates."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.certificate_dtos import (
        KeycloakCertificateDTO,
        KeycloakKeyStoreConfigRequestDTO,
    )


class KeycloakClientCertificatesPort:
    """Sync Keycloak port interface for client attribute certificates."""

    @abstractmethod
    def get_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Get the certificate stored in a client attribute."""
        raise NotImplementedError

    @abstractmethod
    def generate_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Generate a new key pair and certificate for a client attribute."""
        raise NotImplementedError

    @abstractmethod
    def download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Download the client attribute's key and certificate as a key store."""
        raise NotImplementedError

    @abstractmethod
    def generate_and_download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Generate a new key pair for a client attribute and download it as a key store."""
        raise NotImplementedError


class AsyncKeycloakClientCertificatesPort:
    """Async Keycloak port interface for client attribute certificates."""

    @abstractmethod
    async def get_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Get the certificate stored in a client attribute."""
        raise NotImplementedError

    @abstractmethod
    async def generate_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Generate a new key pair and certificate for a client attribute."""
        raise NotImplementedError

    @abstractmethod
    async def download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Download the client attribute's key and certificate as a key store."""
        raise NotImplementedError

    @abstractmethod
    async def generate_and_download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Generate a new key pair for a client attribute and download it as a key store."""
        raise NotImplementedError
