"""Keycloak group representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakGroupDTO(KeycloakResponseDTO):
    """Keycloak ``GroupRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    path: str | None = None
    parent_id: str | None = None
    sub_group_count: int | None = None
    sub_groups: list[KeycloakGroupDTO] | None = None
    attributes: dict[str, list[str]] | None = None
    realm_roles: list[str] | None = None
    client_roles: dict[str, list[str]] | None = None
    access: dict[str, bool] | None = None


class KeycloakGroupRequestDTO(KeycloakRequestDTO):
    """Keycloak ``GroupRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    path: str | None = None
    parent_id: str | None = None
    sub_group_count: int | None = None
    sub_groups: list[KeycloakGroupRequestDTO] | None = None
    attributes: dict[str, list[str]] | None = None
    realm_roles: list[str] | None = None
    client_roles: dict[str, list[str]] | None = None
    access: dict[str, bool] | None = None
