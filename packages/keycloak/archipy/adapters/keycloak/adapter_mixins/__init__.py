"""Deprecated import path; the Keycloak mixins now live in ``archipy.adapters.keycloak.resources``.

Names exported here and the old module paths (for example ``adapter_mixins.roles``) still resolve.
Reading an attribute of an old module path emits a ``DeprecationWarning``. Both are removed in 6.0.0.
"""

from archipy.adapters.keycloak._compat import install_module_aliases
from archipy.adapters.keycloak.resources import *  # noqa: F403
from archipy.adapters.keycloak.resources import __all__  # noqa: F401

install_module_aliases(
    __name__,
    {
        "_shared": "archipy.adapters.keycloak.base",
        "auth": "archipy.adapters.keycloak.protocols.oidc.adapter",
        "auth_flows": "archipy.adapters.keycloak.resources.authentication.adapter",
        "authz": "archipy.adapters.keycloak.resources.authorization.adapter",
        "client_scopes": "archipy.adapters.keycloak.resources.client_scopes.adapter",
        "clients": "archipy.adapters.keycloak.resources.clients.adapter",
        "components": "archipy.adapters.keycloak.resources.components.adapter",
        "connection": "archipy.adapters.keycloak.connection",
        "groups": "archipy.adapters.keycloak.resources.groups.adapter",
        "organization_groups": "archipy.adapters.keycloak.resources.organizations.group_adapter",
        "organizations": "archipy.adapters.keycloak.resources.organizations.adapter",
        "realms": "archipy.adapters.keycloak.resources.realms.adapter",
        "roles": "archipy.adapters.keycloak.resources.roles.adapter",
        "uma": "archipy.adapters.keycloak.protocols.uma.adapter",
        "users": "archipy.adapters.keycloak.resources.users.adapter",
    },
)
