"""Keycloak resource packages: one port and one adapter mixin per Keycloak admin REST resource."""

from archipy.adapters.keycloak._base import KeycloakExceptionHandlerMixin
from archipy.adapters.keycloak._protocols.authzen.adapter import (
    AsyncKeycloakAuthzenMixin,
    KeycloakAuthzenMixin,
)
from archipy.adapters.keycloak._protocols.authzen.port import (
    AsyncKeycloakAuthzenPort,
    KeycloakAuthzenPort,
)
from archipy.adapters.keycloak._protocols.oidc.adapter import (
    AsyncKeycloakAuthMixin,
    KeycloakAuthMixin,
)
from archipy.adapters.keycloak._protocols.oidc.port import (
    AsyncKeycloakAuthPort,
    KeycloakAuthPort,
)
from archipy.adapters.keycloak._protocols.uma.adapter import (
    AsyncKeycloakUmaMixin,
    KeycloakUmaMixin,
)
from archipy.adapters.keycloak._protocols.uma.port import (
    AsyncKeycloakUmaPort,
    KeycloakUmaPort,
)
from archipy.adapters.keycloak._resources.attack_detection.adapter import (
    AsyncKeycloakAttackDetectionMixin,
    KeycloakAttackDetectionMixin,
)
from archipy.adapters.keycloak._resources.attack_detection.port import (
    AsyncKeycloakAttackDetectionPort,
    KeycloakAttackDetectionPort,
)
from archipy.adapters.keycloak._resources.authentication.adapter import (
    AsyncKeycloakAuthFlowsMixin,
    KeycloakAuthFlowsMixin,
)
from archipy.adapters.keycloak._resources.authentication.port import (
    AsyncKeycloakAuthFlowsPort,
    KeycloakAuthFlowsPort,
)
from archipy.adapters.keycloak._resources.authorization.adapter import (
    AsyncKeycloakAuthzMixin,
    KeycloakAuthzMixin,
)
from archipy.adapters.keycloak._resources.authorization.port import (
    AsyncKeycloakAuthzPort,
    KeycloakAuthzPort,
)
from archipy.adapters.keycloak._resources.client_certificates.adapter import (
    AsyncKeycloakClientCertificatesMixin,
    KeycloakClientCertificatesMixin,
)
from archipy.adapters.keycloak._resources.client_certificates.port import (
    AsyncKeycloakClientCertificatesPort,
    KeycloakClientCertificatesPort,
)
from archipy.adapters.keycloak._resources.client_initial_access.adapter import (
    AsyncKeycloakClientInitialAccessMixin,
    KeycloakClientInitialAccessMixin,
)
from archipy.adapters.keycloak._resources.client_initial_access.port import (
    AsyncKeycloakClientInitialAccessPort,
    KeycloakClientInitialAccessPort,
)
from archipy.adapters.keycloak._resources.client_registration_policy.adapter import (
    AsyncKeycloakClientRegistrationPolicyMixin,
    KeycloakClientRegistrationPolicyMixin,
)
from archipy.adapters.keycloak._resources.client_registration_policy.port import (
    AsyncKeycloakClientRegistrationPolicyPort,
    KeycloakClientRegistrationPolicyPort,
)
from archipy.adapters.keycloak._resources.client_scopes.adapter import (
    AsyncKeycloakClientScopesMixin,
    KeycloakClientScopesMixin,
)
from archipy.adapters.keycloak._resources.client_scopes.port import (
    AsyncKeycloakClientScopesPort,
    KeycloakClientScopesPort,
)
from archipy.adapters.keycloak._resources.clients.adapter import (
    AsyncKeycloakClientsMixin,
    KeycloakClientsMixin,
)
from archipy.adapters.keycloak._resources.clients.port import (
    AsyncKeycloakClientsPort,
    KeycloakClientsPort,
)
from archipy.adapters.keycloak._resources.components.adapter import (
    AsyncKeycloakComponentsMixin,
    KeycloakComponentsMixin,
)
from archipy.adapters.keycloak._resources.components.port import (
    AsyncKeycloakComponentsPort,
    KeycloakComponentsPort,
)
from archipy.adapters.keycloak._resources.groups.adapter import (
    AsyncKeycloakGroupsMixin,
    KeycloakGroupsMixin,
)
from archipy.adapters.keycloak._resources.groups.port import (
    AsyncKeycloakGroupsPort,
    KeycloakGroupsPort,
)
from archipy.adapters.keycloak._resources.identity_providers.adapter import (
    AsyncKeycloakIdentityProvidersMixin,
    KeycloakIdentityProvidersMixin,
)
from archipy.adapters.keycloak._resources.identity_providers.port import (
    AsyncKeycloakIdentityProvidersPort,
    KeycloakIdentityProvidersPort,
)
from archipy.adapters.keycloak._resources.keys.adapter import (
    AsyncKeycloakKeysMixin,
    KeycloakKeysMixin,
)
from archipy.adapters.keycloak._resources.keys.port import (
    AsyncKeycloakKeysPort,
    KeycloakKeysPort,
)
from archipy.adapters.keycloak._resources.organizations.adapter import (
    AsyncKeycloakOrganizationsMixin,
    KeycloakOrganizationsMixin,
)
from archipy.adapters.keycloak._resources.organizations.group_adapter import (
    AsyncKeycloakOrganizationGroupsMixin,
    KeycloakOrganizationGroupsMixin,
)
from archipy.adapters.keycloak._resources.organizations.group_port import (
    AsyncKeycloakOrganizationGroupsPort,
    KeycloakOrganizationGroupsPort,
)
from archipy.adapters.keycloak._resources.organizations.port import (
    AsyncKeycloakOrganizationsPort,
    KeycloakOrganizationsPort,
)
from archipy.adapters.keycloak._resources.protocol_mappers.adapter import (
    AsyncKeycloakProtocolMappersMixin,
    KeycloakProtocolMappersMixin,
)
from archipy.adapters.keycloak._resources.protocol_mappers.port import (
    AsyncKeycloakProtocolMappersPort,
    KeycloakProtocolMappersPort,
)
from archipy.adapters.keycloak._resources.realms.adapter import (
    AsyncKeycloakRealmsMixin,
    KeycloakRealmsMixin,
)
from archipy.adapters.keycloak._resources.realms.port import (
    AsyncKeycloakRealmsPort,
    KeycloakRealmsPort,
)
from archipy.adapters.keycloak._resources.required_actions.adapter import (
    AsyncKeycloakRequiredActionsMixin,
    KeycloakRequiredActionsMixin,
)
from archipy.adapters.keycloak._resources.required_actions.port import (
    AsyncKeycloakRequiredActionsPort,
    KeycloakRequiredActionsPort,
)
from archipy.adapters.keycloak._resources.role_mappings.adapter import (
    AsyncKeycloakRoleMappingsMixin,
    KeycloakRoleMappingsMixin,
)
from archipy.adapters.keycloak._resources.role_mappings.port import (
    AsyncKeycloakRoleMappingsPort,
    KeycloakRoleMappingsPort,
)
from archipy.adapters.keycloak._resources.roles.adapter import (
    AsyncKeycloakRolesMixin,
    KeycloakRolesMixin,
)
from archipy.adapters.keycloak._resources.roles.port import (
    AsyncKeycloakRolesPort,
    KeycloakRolesPort,
)
from archipy.adapters.keycloak._resources.roles_by_id.adapter import (
    AsyncKeycloakRolesByIdMixin,
    KeycloakRolesByIdMixin,
)
from archipy.adapters.keycloak._resources.roles_by_id.port import (
    AsyncKeycloakRolesByIdPort,
    KeycloakRolesByIdPort,
)
from archipy.adapters.keycloak._resources.scope_mappings.adapter import (
    AsyncKeycloakScopeMappingsMixin,
    KeycloakScopeMappingsMixin,
)
from archipy.adapters.keycloak._resources.scope_mappings.port import (
    AsyncKeycloakScopeMappingsPort,
    KeycloakScopeMappingsPort,
)
from archipy.adapters.keycloak._resources.users.adapter import (
    AsyncKeycloakUsersMixin,
    KeycloakUsersMixin,
)
from archipy.adapters.keycloak._resources.users.port import (
    AsyncKeycloakUsersPort,
    KeycloakUsersPort,
)
from archipy.adapters.keycloak._type_aliases import (
    KeycloakClientScopeType,
    KeycloakComponentType,
    KeycloakGroupType,
    KeycloakOrganizationType,
    KeycloakProtocolMapperType,
    KeycloakResponseType,
    KeycloakRoleType,
    KeycloakTokenType,
    KeycloakUserType,
    PublicKeyType,
)

__all__ = [
    "AsyncKeycloakAttackDetectionMixin",
    "AsyncKeycloakAttackDetectionPort",
    "AsyncKeycloakAuthFlowsMixin",
    "AsyncKeycloakAuthFlowsPort",
    "AsyncKeycloakAuthMixin",
    "AsyncKeycloakAuthPort",
    "AsyncKeycloakAuthzMixin",
    "AsyncKeycloakAuthzPort",
    "AsyncKeycloakAuthzenMixin",
    "AsyncKeycloakAuthzenPort",
    "AsyncKeycloakClientCertificatesMixin",
    "AsyncKeycloakClientCertificatesPort",
    "AsyncKeycloakClientInitialAccessMixin",
    "AsyncKeycloakClientInitialAccessPort",
    "AsyncKeycloakClientRegistrationPolicyMixin",
    "AsyncKeycloakClientRegistrationPolicyPort",
    "AsyncKeycloakClientScopesMixin",
    "AsyncKeycloakClientScopesPort",
    "AsyncKeycloakClientsMixin",
    "AsyncKeycloakClientsPort",
    "AsyncKeycloakComponentsMixin",
    "AsyncKeycloakComponentsPort",
    "AsyncKeycloakGroupsMixin",
    "AsyncKeycloakGroupsPort",
    "AsyncKeycloakIdentityProvidersMixin",
    "AsyncKeycloakIdentityProvidersPort",
    "AsyncKeycloakKeysMixin",
    "AsyncKeycloakKeysPort",
    "AsyncKeycloakOrganizationGroupsMixin",
    "AsyncKeycloakOrganizationGroupsPort",
    "AsyncKeycloakOrganizationsMixin",
    "AsyncKeycloakOrganizationsPort",
    "AsyncKeycloakProtocolMappersMixin",
    "AsyncKeycloakProtocolMappersPort",
    "AsyncKeycloakRealmsMixin",
    "AsyncKeycloakRealmsPort",
    "AsyncKeycloakRequiredActionsMixin",
    "AsyncKeycloakRequiredActionsPort",
    "AsyncKeycloakRoleMappingsMixin",
    "AsyncKeycloakRoleMappingsPort",
    "AsyncKeycloakRolesByIdMixin",
    "AsyncKeycloakRolesByIdPort",
    "AsyncKeycloakRolesMixin",
    "AsyncKeycloakRolesPort",
    "AsyncKeycloakScopeMappingsMixin",
    "AsyncKeycloakScopeMappingsPort",
    "AsyncKeycloakUmaMixin",
    "AsyncKeycloakUmaPort",
    "AsyncKeycloakUsersMixin",
    "AsyncKeycloakUsersPort",
    "KeycloakAttackDetectionMixin",
    "KeycloakAttackDetectionPort",
    "KeycloakAuthFlowsMixin",
    "KeycloakAuthFlowsPort",
    "KeycloakAuthMixin",
    "KeycloakAuthPort",
    "KeycloakAuthzMixin",
    "KeycloakAuthzPort",
    "KeycloakAuthzenMixin",
    "KeycloakAuthzenPort",
    "KeycloakClientCertificatesMixin",
    "KeycloakClientCertificatesPort",
    "KeycloakClientInitialAccessMixin",
    "KeycloakClientInitialAccessPort",
    "KeycloakClientRegistrationPolicyMixin",
    "KeycloakClientRegistrationPolicyPort",
    "KeycloakClientScopeType",
    "KeycloakClientScopesMixin",
    "KeycloakClientScopesPort",
    "KeycloakClientsMixin",
    "KeycloakClientsPort",
    "KeycloakComponentType",
    "KeycloakComponentsMixin",
    "KeycloakComponentsPort",
    "KeycloakExceptionHandlerMixin",
    "KeycloakGroupType",
    "KeycloakGroupsMixin",
    "KeycloakGroupsPort",
    "KeycloakIdentityProvidersMixin",
    "KeycloakIdentityProvidersPort",
    "KeycloakKeysMixin",
    "KeycloakKeysPort",
    "KeycloakOrganizationGroupsMixin",
    "KeycloakOrganizationGroupsPort",
    "KeycloakOrganizationType",
    "KeycloakOrganizationsMixin",
    "KeycloakOrganizationsPort",
    "KeycloakProtocolMapperType",
    "KeycloakProtocolMappersMixin",
    "KeycloakProtocolMappersPort",
    "KeycloakRealmsMixin",
    "KeycloakRealmsPort",
    "KeycloakRequiredActionsMixin",
    "KeycloakRequiredActionsPort",
    "KeycloakResponseType",
    "KeycloakRoleMappingsMixin",
    "KeycloakRoleMappingsPort",
    "KeycloakRoleType",
    "KeycloakRolesByIdMixin",
    "KeycloakRolesByIdPort",
    "KeycloakRolesMixin",
    "KeycloakRolesPort",
    "KeycloakScopeMappingsMixin",
    "KeycloakScopeMappingsPort",
    "KeycloakTokenType",
    "KeycloakUmaMixin",
    "KeycloakUmaPort",
    "KeycloakUserType",
    "KeycloakUsersMixin",
    "KeycloakUsersPort",
    "PublicKeyType",
]
