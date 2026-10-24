"""Keycloak component representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakComponentDTO(KeycloakResponseDTO):
    """Keycloak ``ComponentRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    provider_id: str | None = None
    provider_type: str | None = None
    parent_id: str | None = None
    sub_type: str | None = None
    config: dict[str, JsonValue] | None = None


class KeycloakComponentRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ComponentRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    provider_id: str | None = None
    provider_type: str | None = None
    parent_id: str | None = None
    sub_type: str | None = None
    config: dict[str, JsonValue] | None = None
