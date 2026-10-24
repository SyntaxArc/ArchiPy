"""Keycloak certificate representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakCertificateDTO(KeycloakResponseDTO):
    """Keycloak ``CertificateRepresentation`` as returned by the admin API."""

    private_key: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    kid: str | None = None
    jwks: str | None = None


class KeycloakCertificateRequestDTO(KeycloakRequestDTO):
    """Keycloak ``CertificateRepresentation`` payload sent to the admin API."""

    private_key: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    kid: str | None = None
    jwks: str | None = None


class KeycloakKeyStoreConfigDTO(KeycloakResponseDTO):
    """Keycloak ``KeyStoreConfig`` as returned by the admin API."""

    realm_certificate: bool | None = None
    store_password: str | None = None
    key_password: str | None = None
    key_alias: str | None = None
    realm_alias: str | None = None
    format: str | None = None
    key_size: int | None = None
    validity: int | None = None


class KeycloakKeyStoreConfigRequestDTO(KeycloakRequestDTO):
    """Keycloak ``KeyStoreConfig`` payload sent to the admin API."""

    realm_certificate: bool | None = None
    store_password: str | None = None
    key_password: str | None = None
    key_alias: str | None = None
    realm_alias: str | None = None
    format: str | None = None
    key_size: int | None = None
    validity: int | None = None
