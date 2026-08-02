"""Keycloak port interfaces composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.keycloak.port_mixins import (
    AsyncKeycloakAuthFlowsPort,
    AsyncKeycloakAuthPort,
    AsyncKeycloakAuthzPort,
    AsyncKeycloakClientScopesPort,
    AsyncKeycloakClientsPort,
    AsyncKeycloakComponentsPort,
    AsyncKeycloakGroupsPort,
    AsyncKeycloakOrganizationsPort,
    AsyncKeycloakRealmsPort,
    AsyncKeycloakRolesPort,
    AsyncKeycloakUmaPort,
    AsyncKeycloakUsersPort,
    KeycloakAuthFlowsPort,
    KeycloakAuthPort,
    KeycloakAuthzPort,
    KeycloakClientScopesPort,
    KeycloakClientsPort,
    KeycloakComponentsPort,
    KeycloakGroupsPort,
    KeycloakGroupType,
    KeycloakOrganizationsPort,
    KeycloakOrganizationType,
    KeycloakRealmsPort,
    KeycloakResponseType,
    KeycloakRolesPort,
    KeycloakRoleType,
    KeycloakTokenType,
    KeycloakUmaPort,
    KeycloakUsersPort,
    KeycloakUserType,
    PublicKeyType,
)

__all__ = [
    "AsyncKeycloakPort",
    "KeycloakGroupType",
    "KeycloakOrganizationType",
    "KeycloakPort",
    "KeycloakResponseType",
    "KeycloakRoleType",
    "KeycloakTokenType",
    "KeycloakUserType",
    "PublicKeyType",
]


class KeycloakPort(
    KeycloakAuthPort,
    KeycloakUsersPort,
    KeycloakRolesPort,
    KeycloakClientsPort,
    KeycloakRealmsPort,
    KeycloakOrganizationsPort,
    KeycloakGroupsPort,
    KeycloakAuthFlowsPort,
    KeycloakClientScopesPort,
    KeycloakAuthzPort,
    KeycloakUmaPort,
    KeycloakComponentsPort,
):
    """Interface for Keycloak operations providing a standardized access pattern.

    This interface defines the contract for Keycloak adapters, ensuring consistent
    implementation of Keycloak operations across different adapters. It covers essential
    functionality including authentication, user management, and role management.
    """


class AsyncKeycloakPort(
    AsyncKeycloakAuthPort,
    AsyncKeycloakUsersPort,
    AsyncKeycloakRolesPort,
    AsyncKeycloakClientsPort,
    AsyncKeycloakRealmsPort,
    AsyncKeycloakOrganizationsPort,
    AsyncKeycloakGroupsPort,
    AsyncKeycloakAuthFlowsPort,
    AsyncKeycloakClientScopesPort,
    AsyncKeycloakAuthzPort,
    AsyncKeycloakUmaPort,
    AsyncKeycloakComponentsPort,
):
    """Asynchronous interface for Keycloak operations providing a standardized access pattern.

    This interface defines the contract for async Keycloak adapters, ensuring consistent
    implementation of Keycloak operations across different adapters. It covers essential
    functionality including authentication, user management, and role management.
    """
