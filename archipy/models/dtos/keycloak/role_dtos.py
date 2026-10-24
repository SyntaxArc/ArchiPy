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


class KeycloakClientRoleMappingsDTO(KeycloakResponseDTO):
    """Keycloak ``ClientMappingsRepresentation`` as returned by the admin API."""

    id: str | None = None
    client: str | None = None
    mappings: list[KeycloakRoleDTO] | None = None


class KeycloakClientRoleMappingsRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientMappingsRepresentation`` payload sent to the admin API."""

    id: str | None = None
    client: str | None = None
    mappings: list[KeycloakRoleRequestDTO] | None = None


class KeycloakRoleMappingsDTO(KeycloakResponseDTO):
    """Keycloak ``MappingsRepresentation`` as returned by the admin API."""

    realm_mappings: list[KeycloakRoleDTO] | None = None
    client_mappings: dict[str, KeycloakClientRoleMappingsDTO] | None = None


class KeycloakRoleMappingsRequestDTO(KeycloakRequestDTO):
    """Keycloak ``MappingsRepresentation`` payload sent to the admin API."""

    realm_mappings: list[KeycloakRoleRequestDTO] | None = None
    client_mappings: dict[str, KeycloakClientRoleMappingsRequestDTO] | None = None
