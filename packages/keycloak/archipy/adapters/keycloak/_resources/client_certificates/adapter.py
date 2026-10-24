"""Keycloak adapter mixins for client attribute certificates."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_request_payload,
)
from archipy.models.dtos.keycloak.certificate_dtos import (
    KeycloakCertificateDTO,
    KeycloakKeyStoreConfigRequestDTO,
)


class KeycloakClientCertificatesMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client attribute certificates."""

    def get_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Get the certificate stored in a client attribute.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.

        Returns:
            The certificate.
        """
        return to_dto(
            KeycloakCertificateDTO,
            self._admin_request(
                "get_client_certificate",
                "get",
                f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def generate_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Generate a new key pair and certificate for a client attribute.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.

        Returns:
            The generated certificate, with its private key.
        """
        return to_dto(
            KeycloakCertificateDTO,
            self._admin_request(
                "generate_client_certificate",
                "post",
                f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/generate",
                expected=(HTTPStatus.OK,),
            ),
        )

    def download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Download the client attribute's key and certificate as a key store.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.
            config: Key store format, alias and passwords.

        Returns:
            The key store file.
        """
        return self._admin_request(
            "download_client_keystore",
            "post",
            f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/download",
            body=to_request_payload(config),
            expected=(HTTPStatus.OK,),
        )

    def generate_and_download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Generate a new key pair for a client attribute and download it as a key store.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.
            config: Key store format, alias, passwords and key size.

        Returns:
            The key store file.
        """
        return self._admin_request(
            "generate_and_download_client_keystore",
            "post",
            f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/generate-and-download",
            body=to_request_payload(config),
            expected=(HTTPStatus.OK,),
        )


class AsyncKeycloakClientCertificatesMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client attribute certificates."""

    async def get_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Get the certificate stored in a client attribute.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.

        Returns:
            The certificate.
        """
        return to_dto(
            KeycloakCertificateDTO,
            await self._async_admin_request(
                "get_client_certificate",
                "get",
                f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def generate_client_certificate(self, client_uuid: str, attribute: str) -> KeycloakCertificateDTO:
        """Generate a new key pair and certificate for a client attribute.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.

        Returns:
            The generated certificate, with its private key.
        """
        return to_dto(
            KeycloakCertificateDTO,
            await self._async_admin_request(
                "generate_client_certificate",
                "post",
                f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/generate",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Download the client attribute's key and certificate as a key store.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.
            config: Key store format, alias and passwords.

        Returns:
            The key store file.
        """
        return await self._async_admin_request(
            "download_client_keystore",
            "post",
            f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/download",
            body=to_request_payload(config),
            expected=(HTTPStatus.OK,),
        )

    async def generate_and_download_client_keystore(
        self,
        client_uuid: str,
        attribute: str,
        config: KeycloakKeyStoreConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Generate a new key pair for a client attribute and download it as a key store.

        Args:
            client_uuid: Client UUID.
            attribute: Certificate attribute, such as ``jwt.credential`` or ``saml.signing``.
            config: Key store format, alias, passwords and key size.

        Returns:
            The key store file.
        """
        return await self._async_admin_request(
            "generate_and_download_client_keystore",
            "post",
            f"/clients/{segment(client_uuid)}/certificates/{segment(attribute)}/generate-and-download",
            body=to_request_payload(config),
            expected=(HTTPStatus.OK,),
        )
