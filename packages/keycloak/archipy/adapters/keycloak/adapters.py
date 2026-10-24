"""Keycloak adapters composed from per-concern mixins."""

from __future__ import annotations

from archipy.adapters.keycloak._connection import AsyncKeycloakConnectionMixin, KeycloakConnectionMixin
from archipy.adapters.keycloak._resources import (
    AsyncKeycloakAttackDetectionMixin,
    AsyncKeycloakAuthFlowsMixin,
    AsyncKeycloakAuthMixin,
    AsyncKeycloakAuthzMixin,
    AsyncKeycloakClientCertificatesMixin,
    AsyncKeycloakClientInitialAccessMixin,
    AsyncKeycloakClientRegistrationPolicyMixin,
    AsyncKeycloakClientScopesMixin,
    AsyncKeycloakClientsMixin,
    AsyncKeycloakComponentsMixin,
    AsyncKeycloakGroupsMixin,
    AsyncKeycloakIdentityProvidersMixin,
    AsyncKeycloakKeysMixin,
    AsyncKeycloakOrganizationGroupsMixin,
    AsyncKeycloakOrganizationsMixin,
    AsyncKeycloakProtocolMappersMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakRoleMappingsMixin,
    AsyncKeycloakRolesByIdMixin,
    AsyncKeycloakRolesMixin,
    AsyncKeycloakScopeMappingsMixin,
    AsyncKeycloakUmaMixin,
    AsyncKeycloakUsersMixin,
    KeycloakAttackDetectionMixin,
    KeycloakAuthFlowsMixin,
    KeycloakAuthMixin,
    KeycloakAuthzMixin,
    KeycloakClientCertificatesMixin,
    KeycloakClientInitialAccessMixin,
    KeycloakClientRegistrationPolicyMixin,
    KeycloakClientScopesMixin,
    KeycloakClientsMixin,
    KeycloakComponentsMixin,
    KeycloakGroupsMixin,
    KeycloakIdentityProvidersMixin,
    KeycloakKeysMixin,
    KeycloakOrganizationGroupsMixin,
    KeycloakOrganizationsMixin,
    KeycloakProtocolMappersMixin,
    KeycloakRealmsMixin,
    KeycloakRoleMappingsMixin,
    KeycloakRolesByIdMixin,
    KeycloakRolesMixin,
    KeycloakScopeMappingsMixin,
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
    KeycloakRoleMappingsMixin,
    KeycloakScopeMappingsMixin,
    KeycloakClientsMixin,
    KeycloakRealmsMixin,
    KeycloakOrganizationsMixin,
    KeycloakOrganizationGroupsMixin,
    KeycloakGroupsMixin,
    KeycloakAuthFlowsMixin,
    KeycloakClientScopesMixin,
    KeycloakProtocolMappersMixin,
    KeycloakAuthzMixin,
    KeycloakUmaMixin,
    KeycloakComponentsMixin,
    KeycloakAttackDetectionMixin,
    KeycloakClientInitialAccessMixin,
    KeycloakClientRegistrationPolicyMixin,
    KeycloakKeysMixin,
    KeycloakClientCertificatesMixin,
    KeycloakIdentityProvidersMixin,
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
    AsyncKeycloakRoleMappingsMixin,
    AsyncKeycloakScopeMappingsMixin,
    AsyncKeycloakClientsMixin,
    AsyncKeycloakRealmsMixin,
    AsyncKeycloakOrganizationsMixin,
    AsyncKeycloakOrganizationGroupsMixin,
    AsyncKeycloakGroupsMixin,
    AsyncKeycloakAuthFlowsMixin,
    AsyncKeycloakClientScopesMixin,
    AsyncKeycloakProtocolMappersMixin,
    AsyncKeycloakAuthzMixin,
    AsyncKeycloakUmaMixin,
    AsyncKeycloakComponentsMixin,
    AsyncKeycloakAttackDetectionMixin,
    AsyncKeycloakClientInitialAccessMixin,
    AsyncKeycloakClientRegistrationPolicyMixin,
    AsyncKeycloakKeysMixin,
    AsyncKeycloakClientCertificatesMixin,
    AsyncKeycloakIdentityProvidersMixin,
    AsyncKeycloakPort,
):
    """Async concrete implementation of the AsyncKeycloakPort interface using python-keycloak library.

    This implementation includes TTL caching for appropriate operations to improve performance
    while ensuring cache entries expire after a configured time to prevent stale data.
    """
