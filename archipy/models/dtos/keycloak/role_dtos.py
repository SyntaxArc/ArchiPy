"""Keycloak role representation DTOs."""

from pydantic import Field

from archipy.models.dtos.keycloak.base import KeycloakResponseDTO


class KeycloakRoleCompositesDTO(KeycloakResponseDTO):
    """Child roles of a composite role.

    Attributes:
        realm: Names of composite realm roles.
        client: Composite client roles, keyed by client ID.
    """

    realm: list[str] | None = None
    client: dict[str, list[str]] | None = None


class KeycloakRoleDTO(KeycloakResponseDTO):
    """Keycloak ``RoleRepresentation`` as returned by the admin API.

    Attributes:
        id: Role ID.
        name: Role name.
        description: Role description.
        scope_param_required: Whether the ``scope`` parameter is required to request the role.
        composite: Whether the role is composite.
        composites: Child roles when the role is composite.
        client_role: Whether the role belongs to a client.
        container_id: ID of the realm or client that owns the role.
        attributes: Custom role attributes.
    """

    id: str | None = None
    name: str | None = None
    description: str | None = None
    scope_param_required: bool | None = None
    composite: bool | None = None
    composites: KeycloakRoleCompositesDTO | None = None
    client_role: bool | None = None
    container_id: str | None = None
    attributes: dict[str, list[str]] | None = Field(default=None)
