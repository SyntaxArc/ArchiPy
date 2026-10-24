"""Deprecated import path; the Keycloak mixins now live in ``archipy.adapters.keycloak.resources``.

Names exported here and the old module paths (for example ``port_mixins.roles``) still resolve.
Reading an attribute of an old module path emits a ``DeprecationWarning``. Both are removed in 6.0.0.
"""

from archipy.adapters.keycloak._compat import install_module_aliases
from archipy.adapters.keycloak.resources import *  # noqa: F403
from archipy.adapters.keycloak.resources import __all__  # noqa: F401

install_module_aliases(
    __name__,
    {
        "_shared": "archipy.adapters.keycloak.type_aliases",
        "auth": "archipy.adapters.keycloak.protocols.oidc.port",
        "auth_flows": "archipy.adapters.keycloak.resources.authentication.port",
        "authz": "archipy.adapters.keycloak.resources.authorization.port",
        "client_scopes": "archipy.adapters.keycloak.resources.client_scopes.port",
        "clients": "archipy.adapters.keycloak.resources.clients.port",
        "components": "archipy.adapters.keycloak.resources.components.port",
        "groups": "archipy.adapters.keycloak.resources.groups.port",
        "organization_groups": "archipy.adapters.keycloak.resources.organizations.group_port",
        "organizations": "archipy.adapters.keycloak.resources.organizations.port",
        "realms": "archipy.adapters.keycloak.resources.realms.port",
        "roles": "archipy.adapters.keycloak.resources.roles.port",
        "uma": "archipy.adapters.keycloak.protocols.uma.port",
        "users": "archipy.adapters.keycloak.resources.users.port",
    },
)
