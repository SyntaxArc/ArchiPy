"""Keycloak key representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import Field

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakKeysMetadataDTO(KeycloakResponseDTO):
    """Keycloak ``KeysMetadataRepresentation`` as returned by the admin API."""

    active: dict[str, str] | None = None
    keys_value: list[KeycloakKeyMetadataDTO] | None = Field(default=None, alias="keys")


class KeycloakKeysMetadataRequestDTO(KeycloakRequestDTO):
    """Keycloak ``KeysMetadataRepresentation`` payload sent to the admin API."""

    active: dict[str, str] | None = None
    keys_value: list[KeycloakKeyMetadataRequestDTO] | None = Field(default=None, alias="keys")


class KeycloakKeyMetadataDTO(KeycloakResponseDTO):
    """Keycloak ``KeyMetadataRepresentation`` as returned by the admin API."""

    provider_id: str | None = None
    provider_priority: int | None = None
    kid: str | None = None
    status: str | None = None
    type: str | None = None
    algorithm: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    use: str | None = None
    valid_to: int | None = None


class KeycloakKeyMetadataRequestDTO(KeycloakRequestDTO):
    """Keycloak ``KeyMetadataRepresentation`` payload sent to the admin API."""

    provider_id: str | None = None
    provider_priority: int | None = None
    kid: str | None = None
    status: str | None = None
    type: str | None = None
    algorithm: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    use: str | None = None
    valid_to: int | None = None
