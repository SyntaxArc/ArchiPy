"""Keycloak UMA 2.0 protocol DTOs (resource registration, policies, permission tickets).

The UMA endpoints mix camelCase and snake_case names, so every wire name is spelled out as an alias. Unknown
fields are kept in both directions because Keycloak accepts extra UMA attributes.
"""

from pydantic import ConfigDict, Field, JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakUmaScopeDTO(KeycloakResponseDTO):
    """A scope of a UMA resource set."""

    model_config = ConfigDict(alias_generator=None)

    id: str | None = None
    name: str | None = None
    icon_uri: str | None = None


class KeycloakUmaOwnerDTO(KeycloakResponseDTO):
    """The owner of a UMA resource set."""

    id: str | None = None
    name: str | None = None


class KeycloakUmaResourceDTO(KeycloakResponseDTO):
    """UMA resource set returned by the resource registration endpoint."""

    model_config = ConfigDict(alias_generator=None)

    internal_id: str | None = Field(default=None, alias="_id")
    name: str | None = None
    type: str | None = None
    uris: list[str] | None = None
    scopes: list[KeycloakUmaScopeDTO] | None = None
    resource_scopes: list[KeycloakUmaScopeDTO] | None = None
    icon_uri: str | None = None
    owner: KeycloakUmaOwnerDTO | None = None
    owner_managed_access: bool | None = Field(default=None, alias="ownerManagedAccess")
    display_name: str | None = Field(default=None, alias="displayName")
    attributes: dict[str, list[str]] | None = None


class KeycloakUmaResourceRequestDTO(KeycloakRequestDTO):
    """UMA resource set payload for create and update. Keycloak rejects unknown fields, so does this DTO."""

    model_config = ConfigDict(alias_generator=None)

    name: str | None = None
    type: str | None = None
    uri: str | None = None
    uris: list[str] | None = None
    scopes: list[JsonValue] | None = None
    resource_scopes: list[JsonValue] | None = None
    icon_uri: str | None = None
    owner: JsonValue | None = None
    owner_managed_access: bool | None = Field(default=None, alias="ownerManagedAccess")
    display_name: str | None = Field(default=None, alias="displayName")
    attributes: dict[str, list[str]] | None = None


class KeycloakUmaPolicyDTO(KeycloakResponseDTO):
    """UMA permission policy returned by the policy endpoint."""

    id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    logic: str | None = None
    decision_strategy: str | None = None
    owner: str | None = None
    scopes: list[str] | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None
    clients: list[str] | None = None
    users: list[str] | None = None
    condition: str | None = None


class KeycloakUmaPolicyRequestDTO(KeycloakRequestDTO):
    """UMA permission policy payload for create and update. Keycloak rejects unknown fields, so does this DTO."""

    name: str | None = None
    description: str | None = None
    type: str | None = None
    owner: str | None = None
    scopes: list[str] | None = None
    roles: list[str] | None = None
    groups: list[str] | None = None
    clients: list[str] | None = None
    users: list[str] | None = None
    condition: str | None = None
    logic: str | None = None
    decision_strategy: str | None = None


class KeycloakUmaTicketDTO(KeycloakResponseDTO):
    """Response of a permission ticket request."""

    ticket: str | None = None
