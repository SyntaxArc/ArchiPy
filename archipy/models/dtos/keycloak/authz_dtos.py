"""Keycloak authz representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import Field, JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthzResourceOwnerDTO(KeycloakResponseDTO):
    """Keycloak ``ResourceOwnerRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None


class KeycloakAuthzResourceOwnerRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ResourceOwnerRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None


class KeycloakAuthzScopeDTO(KeycloakResponseDTO):
    """Keycloak ``ScopeRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    icon_uri: str | None = None
    policies: list[KeycloakAuthzPolicyDTO] | None = None
    resources: list[KeycloakAuthzResourceDTO] | None = None
    display_name: str | None = None


class KeycloakAuthzScopeRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ScopeRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    icon_uri: str | None = None
    policies: list[KeycloakAuthzPolicyRequestDTO] | None = None
    resources: list[KeycloakAuthzResourceRequestDTO] | None = None
    display_name: str | None = None


class KeycloakAuthzResourceDTO(KeycloakResponseDTO):
    """Keycloak ``ResourceRepresentation`` as returned by the admin API."""

    internal_id: str | None = Field(default=None, alias="_id")
    name: str | None = None
    uris: list[str] | None = None
    type: str | None = None
    scopes: list[KeycloakAuthzScopeDTO] | None = None
    icon_uri: str | None = Field(default=None, alias="icon_uri")
    owner: dict[str, JsonValue] | None = None
    owner_managed_access: bool | None = None
    display_name: str | None = None
    attributes: dict[str, list[str]] | None = None
    uri: str | None = None
    scopes_uma: list[KeycloakAuthzScopeDTO] | None = None


class KeycloakAuthzResourceRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ResourceRepresentation`` payload sent to the admin API."""

    internal_id: str | None = Field(default=None, alias="_id")
    name: str | None = None
    uris: list[str] | None = None
    type: str | None = None
    scopes: list[KeycloakAuthzScopeRequestDTO] | None = None
    icon_uri: str | None = Field(default=None, alias="icon_uri")
    owner: dict[str, JsonValue] | None = None
    owner_managed_access: bool | None = None
    display_name: str | None = None
    attributes: dict[str, list[str]] | None = None
    uri: str | None = None
    scopes_uma: list[KeycloakAuthzScopeRequestDTO] | None = None


class KeycloakAuthzPolicyDTO(KeycloakResponseDTO):
    """Keycloak ``PolicyRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    policies: list[str] | None = None
    resources: list[str] | None = None
    scopes: list[str] | None = None
    logic: str | None = None
    decision_strategy: str | None = None
    owner: str | None = None
    resource_type: str | None = None
    resources_data: list[KeycloakAuthzResourceDTO] | None = None
    scopes_data: list[KeycloakAuthzScopeDTO] | None = None
    config: dict[str, str] | None = None


class KeycloakAuthzPolicyRequestDTO(KeycloakRequestDTO):
    """Keycloak ``PolicyRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    policies: list[str] | None = None
    resources: list[str] | None = None
    scopes: list[str] | None = None
    logic: str | None = None
    decision_strategy: str | None = None
    owner: str | None = None
    resource_type: str | None = None
    resources_data: list[KeycloakAuthzResourceRequestDTO] | None = None
    scopes_data: list[KeycloakAuthzScopeRequestDTO] | None = None
    config: dict[str, str] | None = None


class KeycloakAuthzSettingsDTO(KeycloakResponseDTO):
    """Keycloak ``ResourceServerRepresentation`` as returned by the admin API."""

    id: str | None = None
    client_id: str | None = None
    name: str | None = None
    allow_remote_resource_management: bool | None = None
    policy_enforcement_mode: str | None = None
    resources: list[KeycloakAuthzResourceDTO] | None = None
    policies: list[KeycloakAuthzPolicyDTO] | None = None
    scopes: list[KeycloakAuthzScopeDTO] | None = None
    decision_strategy: str | None = None
    authorization_schema: dict[str, JsonValue] | None = None


class KeycloakAuthzSettingsRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ResourceServerRepresentation`` payload sent to the admin API."""

    id: str | None = None
    client_id: str | None = None
    name: str | None = None
    allow_remote_resource_management: bool | None = None
    policy_enforcement_mode: str | None = None
    resources: list[KeycloakAuthzResourceRequestDTO] | None = None
    policies: list[KeycloakAuthzPolicyRequestDTO] | None = None
    scopes: list[KeycloakAuthzScopeRequestDTO] | None = None
    decision_strategy: str | None = None
    authorization_schema: dict[str, JsonValue] | None = None
