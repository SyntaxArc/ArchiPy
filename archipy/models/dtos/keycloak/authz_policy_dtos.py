"""Keycloak authorization policy DTOs for the role and client policy endpoints.

``POST .../authz/resource-server/policy/role`` and ``.../policy/client`` take their members (``roles``, ``clients``)
as top-level fields, which the generic ``PolicyRepresentation`` of the OpenAPI spec does not describe.
"""

from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzPolicyDTO
from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthzPolicyRoleDTO(KeycloakResponseDTO):
    """One role granted by a role policy.

    Attributes:
        id: Role ID.
        required: Whether the role is required for the policy to grant access.
    """

    id: str | None = None
    required: bool | None = None


class KeycloakAuthzRolePolicyDTO(KeycloakAuthzPolicyDTO):
    """A role policy as returned when it is created."""

    roles: list[KeycloakAuthzPolicyRoleDTO] | None = None


class KeycloakAuthzClientPolicyDTO(KeycloakAuthzPolicyDTO):
    """A client policy as returned when it is created or listed."""

    clients: list[str] | None = None


class KeycloakAuthzRolePolicyRequestDTO(KeycloakRequestDTO):
    """Payload to create a role policy."""

    name: str | None = None
    description: str | None = None
    type: str | None = "role"
    logic: str | None = None
    decision_strategy: str | None = None
    fetch_roles: bool | None = None
    roles: list[KeycloakAuthzPolicyRoleDTO] | None = None


class KeycloakAuthzClientPolicyRequestDTO(KeycloakRequestDTO):
    """Payload to create a client policy."""

    name: str | None = None
    description: str | None = None
    type: str | None = "client"
    logic: str | None = None
    decision_strategy: str | None = None
    clients: list[str] | None = None
