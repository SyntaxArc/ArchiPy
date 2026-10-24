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


class KeycloakComponentTypeDTO(KeycloakResponseDTO):
    """Keycloak ``ComponentTypeRepresentation`` as returned by the admin API."""

    id: str | None = None
    help_text: str | None = None
    properties: list[KeycloakConfigPropertyDTO] | None = None
    client_properties: list[KeycloakConfigPropertyDTO] | None = None
    metadata: dict[str, JsonValue] | None = None


class KeycloakComponentTypeRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ComponentTypeRepresentation`` payload sent to the admin API."""

    id: str | None = None
    help_text: str | None = None
    properties: list[KeycloakConfigPropertyRequestDTO] | None = None
    client_properties: list[KeycloakConfigPropertyRequestDTO] | None = None
    metadata: dict[str, JsonValue] | None = None


class KeycloakConfigPropertyDTO(KeycloakResponseDTO):
    """Keycloak ``ConfigPropertyRepresentation`` as returned by the admin API."""

    name: str | None = None
    label: str | None = None
    help_text: str | None = None
    type: str | None = None
    default_value: JsonValue | None = None
    options: list[str] | None = None
    secret: bool | None = None
    required: bool | None = None
    read_only: bool | None = None


class KeycloakConfigPropertyRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ConfigPropertyRepresentation`` payload sent to the admin API."""

    name: str | None = None
    label: str | None = None
    help_text: str | None = None
    type: str | None = None
    default_value: JsonValue | None = None
    options: list[str] | None = None
    secret: bool | None = None
    required: bool | None = None
    read_only: bool | None = None
