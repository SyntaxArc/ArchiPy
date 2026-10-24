"""Keycloak client scope representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakProtocolMapperDTO(KeycloakResponseDTO):
    """Keycloak ``ProtocolMapperRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    protocol: str | None = None
    protocol_mapper: str | None = None
    consent_required: bool | None = None
    consent_text: str | None = None
    config: dict[str, str] | None = None


class KeycloakProtocolMapperRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ProtocolMapperRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    protocol: str | None = None
    protocol_mapper: str | None = None
    consent_required: bool | None = None
    consent_text: str | None = None
    config: dict[str, str] | None = None


class KeycloakClientScopeDTO(KeycloakResponseDTO):
    """Keycloak ``ClientScopeRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    protocol: str | None = None
    attributes: dict[str, str] | None = None
    protocol_mappers: list[KeycloakProtocolMapperDTO] | None = None


class KeycloakClientScopeRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientScopeRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    protocol: str | None = None
    attributes: dict[str, str] | None = None
    protocol_mappers: list[KeycloakProtocolMapperRequestDTO] | None = None
