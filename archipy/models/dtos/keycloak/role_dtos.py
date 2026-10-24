"""Keycloak role representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakRoleCompositesDTO(KeycloakResponseDTO):
    """Keycloak ``Composites`` as returned by the admin API."""

    realm: list[str] | None = None
    client: dict[str, list[str]] | None = None
    application: dict[str, list[str]] | None = None


class KeycloakRoleCompositesRequestDTO(KeycloakRequestDTO):
    """Keycloak ``Composites`` payload sent to the admin API."""

    realm: list[str] | None = None
    client: dict[str, list[str]] | None = None
    application: dict[str, list[str]] | None = None


class KeycloakRoleDTO(KeycloakResponseDTO):
    """Keycloak ``RoleRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    scope_param_required: bool | None = None
    composite: bool | None = None
    composites: KeycloakRoleCompositesDTO | None = None
    client_role: bool | None = None
    container_id: str | None = None
    attributes: dict[str, list[str]] | None = None


class KeycloakRoleRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RoleRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    scope_param_required: bool | None = None
    composite: bool | None = None
    composites: KeycloakRoleCompositesRequestDTO | None = None
    client_role: bool | None = None
    container_id: str | None = None
    attributes: dict[str, list[str]] | None = None
