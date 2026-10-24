"""Keycloak adapters composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.keycloak._connection import AsyncKeycloakConnectionMixin, KeycloakConnectionMixin
from archipy.adapters.keycloak._resources import (
    AsyncKeycloakAuthFlowsMixin,
    AsyncKeycloakAuthMixin,
    AsyncKeycloakAuthzMixin,
    AsyncKeycloakClientScopesMixin,
    AsyncKeycloakClientsMixin,
    AsyncKeycloakComponentsMixin,
    AsyncKeycloakGroupsMixin,
    AsyncKeycloakOrganizationGroupsMixin,
    AsyncKeycloakOrganizationsMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakRolesByIdMixin,
    AsyncKeycloakRolesMixin,
    AsyncKeycloakUmaMixin,
    AsyncKeycloakUsersMixin,
    KeycloakAuthFlowsMixin,
    KeycloakAuthMixin,
    KeycloakAuthzMixin,
    KeycloakClientScopesMixin,
    KeycloakClientsMixin,
    KeycloakComponentsMixin,
    KeycloakGroupsMixin,
    KeycloakOrganizationGroupsMixin,
    KeycloakOrganizationsMixin,
    KeycloakRealmsMixin,
    KeycloakRolesByIdMixin,
    KeycloakRolesMixin,
    KeycloakUmaMixin,
    KeycloakUsersMixin,
)
from archipy.adapters.keycloak.ports import AsyncKeycloakPort, KeycloakPort

__all__ = [
    "AsyncKeycloakAdapter",
    "KeycloakAdapter",
]


class KeycloakAdapter(
    KeycloakConnectionMixin,
    KeycloakAuthMixin,
    KeycloakUsersMixin,
    KeycloakRolesMixin,
    KeycloakRolesByIdMixin,
    KeycloakClientsMixin,
    KeycloakRealmsMixin,
    KeycloakOrganizationsMixin,
    KeycloakOrganizationGroupsMixin,
    KeycloakGroupsMixin,
    KeycloakAuthFlowsMixin,
    KeycloakClientScopesMixin,
    KeycloakAuthzMixin,
    KeycloakUmaMixin,
    KeycloakComponentsMixin,
    KeycloakPort,
):
    """Concrete implementation of the KeycloakPort interface using python-keycloak library.

    This implementation includes TTL caching for appropriate operations to improve performance
    while ensuring cache entries expire after a configured time to prevent stale data.
    """


class AsyncKeycloakAdapter(
    AsyncKeycloakConnectionMixin,
    AsyncKeycloakAuthMixin,
    AsyncKeycloakUsersMixin,
    AsyncKeycloakRolesMixin,
    AsyncKeycloakRolesByIdMixin,
    AsyncKeycloakClientsMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakOrganizationsMixin,
    AsyncKeycloakOrganizationGroupsMixin,
    AsyncKeycloakGroupsMixin,
    AsyncKeycloakAuthFlowsMixin,
    AsyncKeycloakClientScopesMixin,
    AsyncKeycloakAuthzMixin,
    AsyncKeycloakUmaMixin,
    AsyncKeycloakComponentsMixin,
    AsyncKeycloakPort,
):
    """Async concrete implementation of the AsyncKeycloakPort interface using python-keycloak library.

    This implementation includes TTL caching for appropriate operations to improve performance
    while ensuring cache entries expire after a configured time to prevent stale data.
    """
