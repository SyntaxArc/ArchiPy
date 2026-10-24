"""Keycloak resource packages: one port and one adapter mixin per Keycloak admin REST resource."""

from archipy.adapters.keycloak.base import KeycloakExceptionHandlerMixin
from archipy.adapters.keycloak.protocols.oidc.adapter import (
    AsyncKeycloakAuthMixin,
    KeycloakAuthMixin,
)
from archipy.adapters.keycloak.protocols.oidc.port import (
    AsyncKeycloakAuthPort,
    KeycloakAuthPort,
)
from archipy.adapters.keycloak.protocols.uma.adapter import (
    AsyncKeycloakUmaMixin,
    KeycloakUmaMixin,
)
from archipy.adapters.keycloak.protocols.uma.port import (
    AsyncKeycloakUmaPort,
    KeycloakUmaPort,
)
from archipy.adapters.keycloak.resources.authentication.adapter import (
    AsyncKeycloakAuthFlowsMixin,
    KeycloakAuthFlowsMixin,
)
from archipy.adapters.keycloak.resources.authentication.port import (
    AsyncKeycloakAuthFlowsPort,
    KeycloakAuthFlowsPort,
)
from archipy.adapters.keycloak.resources.authorization.adapter import (
    AsyncKeycloakAuthzMixin,
    KeycloakAuthzMixin,
)
from archipy.adapters.keycloak.resources.authorization.port import (
    AsyncKeycloakAuthzPort,
    KeycloakAuthzPort,
)
from archipy.adapters.keycloak.resources.client_scopes.adapter import (
    AsyncKeycloakClientScopesMixin,
    KeycloakClientScopesMixin,
)
from archipy.adapters.keycloak.resources.client_scopes.port import (
    AsyncKeycloakClientScopesPort,
    KeycloakClientScopesPort,
)
from archipy.adapters.keycloak.resources.clients.adapter import (
    AsyncKeycloakClientsMixin,
    KeycloakClientsMixin,
)
from archipy.adapters.keycloak.resources.clients.port import (
    AsyncKeycloakClientsPort,
    KeycloakClientsPort,
)
from archipy.adapters.keycloak.resources.components.adapter import (
    AsyncKeycloakComponentsMixin,
    KeycloakComponentsMixin,
)
from archipy.adapters.keycloak.resources.components.port import (
    AsyncKeycloakComponentsPort,
    KeycloakComponentsPort,
)
from archipy.adapters.keycloak.resources.groups.adapter import (
    AsyncKeycloakGroupsMixin,
    KeycloakGroupsMixin,
)
from archipy.adapters.keycloak.resources.groups.port import (
    AsyncKeycloakGroupsPort,
    KeycloakGroupsPort,
)
from archipy.adapters.keycloak.resources.organizations.adapter import (
    AsyncKeycloakOrganizationsMixin,
    KeycloakOrganizationsMixin,
)
from archipy.adapters.keycloak.resources.organizations.group_adapter import (
    AsyncKeycloakOrganizationGroupsMixin,
    KeycloakOrganizationGroupsMixin,
)
from archipy.adapters.keycloak.resources.organizations.group_port import (
    AsyncKeycloakOrganizationGroupsPort,
    KeycloakOrganizationGroupsPort,
)
from archipy.adapters.keycloak.resources.organizations.port import (
    AsyncKeycloakOrganizationsPort,
    KeycloakOrganizationsPort,
)
from archipy.adapters.keycloak.resources.realms.adapter import (
    AsyncKeycloakRealmsMixin,
    KeycloakRealmsMixin,
)
from archipy.adapters.keycloak.resources.realms.port import (
    AsyncKeycloakRealmsPort,
    KeycloakRealmsPort,
)
from archipy.adapters.keycloak.resources.roles.adapter import (
    AsyncKeycloakRolesMixin,
    KeycloakRolesMixin,
)
from archipy.adapters.keycloak.resources.roles.port import (
    AsyncKeycloakRolesPort,
    KeycloakRolesPort,
)
from archipy.adapters.keycloak.resources.users.adapter import (
    AsyncKeycloakUsersMixin,
    KeycloakUsersMixin,
)
from archipy.adapters.keycloak.resources.users.port import (
    AsyncKeycloakUsersPort,
    KeycloakUsersPort,
)
from archipy.adapters.keycloak.type_aliases import (
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
    "AsyncKeycloakAuthFlowsMixin",
    "AsyncKeycloakAuthFlowsPort",
    "AsyncKeycloakAuthMixin",
    "AsyncKeycloakAuthPort",
    "AsyncKeycloakAuthzMixin",
    "AsyncKeycloakAuthzPort",
    "AsyncKeycloakClientScopesMixin",
    "AsyncKeycloakClientScopesPort",
    "AsyncKeycloakClientsMixin",
    "AsyncKeycloakClientsPort",
    "AsyncKeycloakComponentsMixin",
    "AsyncKeycloakComponentsPort",
    "AsyncKeycloakGroupsMixin",
    "AsyncKeycloakGroupsPort",
    "AsyncKeycloakOrganizationGroupsMixin",
    "AsyncKeycloakOrganizationGroupsPort",
    "AsyncKeycloakOrganizationsMixin",
    "AsyncKeycloakOrganizationsPort",
    "AsyncKeycloakRealmsMixin",
    "AsyncKeycloakRealmsPort",
    "AsyncKeycloakRolesMixin",
    "AsyncKeycloakRolesPort",
    "AsyncKeycloakUmaMixin",
    "AsyncKeycloakUmaPort",
    "AsyncKeycloakUsersMixin",
    "AsyncKeycloakUsersPort",
    "KeycloakAuthFlowsMixin",
    "KeycloakAuthFlowsPort",
    "KeycloakAuthMixin",
    "KeycloakAuthPort",
    "KeycloakAuthzMixin",
    "KeycloakAuthzPort",
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
    "KeycloakOrganizationGroupsMixin",
    "KeycloakOrganizationGroupsPort",
    "KeycloakOrganizationType",
    "KeycloakOrganizationsMixin",
    "KeycloakOrganizationsPort",
    "KeycloakProtocolMapperType",
    "KeycloakRealmsMixin",
    "KeycloakRealmsPort",
    "KeycloakResponseType",
    "KeycloakRoleType",
    "KeycloakRolesMixin",
    "KeycloakRolesPort",
    "KeycloakTokenType",
    "KeycloakUmaMixin",
    "KeycloakUmaPort",
    "KeycloakUserType",
    "KeycloakUsersMixin",
    "KeycloakUsersPort",
    "PublicKeyType",
]
