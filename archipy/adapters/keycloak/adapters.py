"""Keycloak adapters composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.keycloak.adapter_mixins import (
    AsyncKeycloakAuthFlowsMixin,
    AsyncKeycloakAuthMixin,
    AsyncKeycloakAuthzMixin,
    AsyncKeycloakClientScopesMixin,
    AsyncKeycloakClientsMixin,
    AsyncKeycloakComponentsMixin,
    AsyncKeycloakConnectionMixin,
    AsyncKeycloakGroupsMixin,
    AsyncKeycloakOrganizationsMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakRolesMixin,
    AsyncKeycloakUmaMixin,
    AsyncKeycloakUsersMixin,
    KeycloakAuthFlowsMixin,
    KeycloakAuthMixin,
    KeycloakAuthzMixin,
    KeycloakClientScopesMixin,
    KeycloakClientsMixin,
    KeycloakComponentsMixin,
    KeycloakConnectionMixin,
    KeycloakGroupsMixin,
    KeycloakOrganizationsMixin,
    KeycloakRealmsMixin,
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
    KeycloakClientsMixin,
    KeycloakRealmsMixin,
    KeycloakOrganizationsMixin,
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
    AsyncKeycloakClientsMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakOrganizationsMixin,
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
