"""Keycloak management permission representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakManagementPermissionDTO(KeycloakResponseDTO):
    """Keycloak ``ManagementPermissionReference`` as returned by the admin API."""

    enabled: bool | None = None
    resource: str | None = None
    scope_permissions: dict[str, str] | None = None


class KeycloakManagementPermissionRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ManagementPermissionReference`` payload sent to the admin API."""

    enabled: bool | None = None
    resource: str | None = None
    scope_permissions: dict[str, str] | None = None
