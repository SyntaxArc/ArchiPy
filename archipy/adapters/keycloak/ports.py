"""Keycloak port definitions for ArchiPy."""

from abc import abstractmethod
from collections.abc import Iterable
from typing import Any

from keycloak.uma_permissions import UMAPermission

# Define type aliases for better type hinting
KeycloakResponseType = dict[str, Any]
KeycloakRoleType = dict[str, Any]
KeycloakUserType = dict[str, Any]
KeycloakGroupType = dict[str, Any]
KeycloakTokenType = dict[str, Any]
KeycloakOrganizationType = dict[str, Any]

# Define a type for the public key return type
# Using Any for JWK.JWK object, since we don't want to depend on jwcrypto types
PublicKeyType = Any


class KeycloakPort:
    """Interface for Keycloak operations providing a standardized access pattern.

    This interface defines the contract for Keycloak adapters, ensuring consistent
    implementation of Keycloak operations across different adapters. It covers essential
    functionality including authentication, user management, and role management.
    """

    # Token Operations
    @abstractmethod
    def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials."""
        raise NotImplementedError

    @abstractmethod
    def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token."""
        raise NotImplementedError

    # User Operations
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType]:
        """Search for users by username, email, or name."""
        raise NotImplementedError

    @abstractmethod
    def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user."""
        raise NotImplementedError

    # Role Operations
    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleType]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role."""
        raise NotImplementedError

    @abstractmethod
    def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        raise NotImplementedError

    @abstractmethod
    def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user."""
        raise NotImplementedError

    @abstractmethod
    def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user."""
        raise NotImplementedError

    @abstractmethod
    def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role(self, role_name: str) -> dict[str, Any]:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role."""
        raise NotImplementedError

    # Client Operations
    @abstractmethod
    def get_client_id(self, client_name: str) -> str:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_secret(self, client_id: str) -> str:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    def get_service_account_id(self) -> str:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    # System Operations
    @abstractmethod
    def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens."""
        raise NotImplementedError

    @abstractmethod
    def get_well_known_config(self) -> dict[str, Any]:
        """Get the well-known OpenID configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_certs(self) -> dict[str, Any]:
        """Get the JWT verification certificates."""
        raise NotImplementedError

    # Authorization
    @abstractmethod
    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call."""
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError

    @abstractmethod
    def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role."""
        raise NotImplementedError

    @abstractmethod
    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled)."""
        raise NotImplementedError

    @abstractmethod
    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError

    @abstractmethod
    def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError

    # Organization Operations
    @abstractmethod
    def get_organizations(self, query: dict | None = None) -> list[KeycloakOrganizationType]:
        """Fetch all organizations. Returns list of OrganizationRepresentation, filtered by query."""
        raise NotImplementedError

    @abstractmethod
    def get_organization(self, organization_id: str) -> KeycloakOrganizationType:
        """Get representation of the organization by ID."""
        raise NotImplementedError

    @abstractmethod
    def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        raise NotImplementedError

    @abstractmethod
    def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_idps(self, organization_id: str) -> list[dict[str, Any]]:
        """Get IDPs by organization id."""
        raise NotImplementedError

    @abstractmethod
    def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationType]:
        """Get organizations by user id. Returns list of organizations the user is member of."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_members(self, organization_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        raise NotImplementedError

    @abstractmethod
    def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization."""
        raise NotImplementedError

    @abstractmethod
    # Group Operations
    @abstractmethod
    def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        raise NotImplementedError

    @abstractmethod
    def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        raise NotImplementedError

    @abstractmethod
    def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        raise NotImplementedError

    @abstractmethod
    def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        raise NotImplementedError

    @abstractmethod
    def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        raise NotImplementedError

    @abstractmethod
    def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        raise NotImplementedError

    @abstractmethod
    def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        raise NotImplementedError

    @abstractmethod
    def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        raise NotImplementedError

    @abstractmethod
    def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        raise NotImplementedError

    # Authentication Flow Operations
    @abstractmethod
    def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_subflow(self, payload: dict, flow_alias: str, skip_exists: bool = False) -> bytes:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError

    # Client Scope Operations
    @abstractmethod
    def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_default_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_optional_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        raise NotImplementedError

    # Authorization Service Operations
    @abstractmethod
    def create_client_authz_resource(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_policy(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permission_associated_policies(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        raise NotImplementedError

    # UMA Operations
    @abstractmethod
    def resource_set_create(self, payload: dict) -> dict[str, Any]:
        """Create a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    def resource_set_update(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    def resource_set_list(
        self,
    ) -> list[dict[str, Any]]:
        """List all UMA resource sets."""
        raise NotImplementedError

    @abstractmethod
    def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """List UMA resource set IDs with optional filters."""
        raise NotImplementedError

    @abstractmethod
    def policy_resource_create(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Create a UMA policy for a resource."""
        raise NotImplementedError

    @abstractmethod
    def policy_update(self, policy_id: str, payload: dict) -> bytes:
        """Update a UMA policy."""
        raise NotImplementedError

    @abstractmethod
    def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy."""
        raise NotImplementedError

    @abstractmethod
    def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """Query UMA policies."""
        raise NotImplementedError

    @abstractmethod
    def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket."""
        raise NotImplementedError

    @abstractmethod
    def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token."""
        raise NotImplementedError

    # Component Operations
    @abstractmethod
    def create_component(self, payload: dict) -> str:
        """Create a Keycloak component."""
        raise NotImplementedError

    @abstractmethod
    def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_components(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    def update_component(self, component_id: str, payload: dict) -> dict[str, Any]:
        """Update a component."""
        raise NotImplementedError

    @abstractmethod
    def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component."""
        raise NotImplementedError

    def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization."""
        raise NotImplementedError


class AsyncKeycloakPort:
    """Asynchronous interface for Keycloak operations providing a standardized access pattern.

    This interface defines the contract for async Keycloak adapters, ensuring consistent
    implementation of Keycloak operations across different adapters. It covers essential
    functionality including authentication, user management, and role management.
    """

    # Token Operations
    @abstractmethod
    async def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    async def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    async def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    async def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials."""
        raise NotImplementedError

    @abstractmethod
    async def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token."""
        raise NotImplementedError

    # User Operations
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    async def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType]:
        """Search for users by username, email, or name."""
        raise NotImplementedError

    @abstractmethod
    async def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user."""
        raise NotImplementedError

    # Role Operations
    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleType]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    async def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role."""
        raise NotImplementedError

    @abstractmethod
    async def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    async def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    async def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        raise NotImplementedError

    @abstractmethod
    async def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user."""
        raise NotImplementedError

    @abstractmethod
    async def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user."""
        raise NotImplementedError

    @abstractmethod
    async def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role(self, role_name: str) -> dict[str, Any]:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role."""
        raise NotImplementedError

    # Client Operations
    @abstractmethod
    async def get_client_id(self, client_name: str) -> str:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_secret(self, client_id: str) -> str:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    async def get_service_account_id(self) -> str:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    # System Operations
    @abstractmethod
    async def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens."""
        raise NotImplementedError

    @abstractmethod
    async def get_well_known_config(self) -> dict[str, Any]:
        """Get the well-known OpenID configuration."""
        raise NotImplementedError

    @abstractmethod
    async def get_certs(self) -> dict[str, Any]:
        """Get the JWT verification certificates."""
        raise NotImplementedError

    # Authorization
    @abstractmethod
    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    async def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    async def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled)."""
        raise NotImplementedError

    @abstractmethod
    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError

    @abstractmethod
    async def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError

    # Organization Operations
    @abstractmethod
    async def get_organizations(self, query: dict | None = None) -> list[KeycloakOrganizationType]:
        """Fetch all organizations. Returns list of OrganizationRepresentation, filtered by query."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization(self, organization_id: str) -> KeycloakOrganizationType:
        """Get representation of the organization by ID."""
        raise NotImplementedError

    @abstractmethod
    async def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        raise NotImplementedError

    @abstractmethod
    async def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_idps(self, organization_id: str) -> list[dict[str, Any]]:
        """Get IDPs by organization id."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationType]:
        """Get organizations by user id. Returns list of organizations the user is member of."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_members(self, organization_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        raise NotImplementedError

    @abstractmethod
    async def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization."""
        raise NotImplementedError

    @abstractmethod
    # Group Operations
    @abstractmethod
    async def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        raise NotImplementedError

    @abstractmethod
    async def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    async def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        raise NotImplementedError

    @abstractmethod
    async def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        raise NotImplementedError

    @abstractmethod
    async def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        raise NotImplementedError

    @abstractmethod
    async def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        raise NotImplementedError

    @abstractmethod
    async def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    async def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        raise NotImplementedError

    @abstractmethod
    async def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        raise NotImplementedError

    # Authentication Flow Operations
    @abstractmethod
    async def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_subflow(
        self,
        payload: dict,
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    async def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError

    # Client Scope Operations
    @abstractmethod
    async def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    async def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        raise NotImplementedError

    # Authorization Service Operations
    @abstractmethod
    async def create_client_authz_resource(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    async def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        raise NotImplementedError

    # UMA Operations
    @abstractmethod
    async def resource_set_create(self, payload: dict) -> dict[str, Any]:
        """Create a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    async def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    async def resource_set_update(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    async def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set."""
        raise NotImplementedError

    @abstractmethod
    async def resource_set_list(
        self,
    ) -> list[dict[str, Any]]:
        """List all UMA resource sets."""
        raise NotImplementedError

    @abstractmethod
    async def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """List UMA resource set IDs with optional filters."""
        raise NotImplementedError

    @abstractmethod
    async def policy_resource_create(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Create a UMA policy for a resource."""
        raise NotImplementedError

    @abstractmethod
    async def policy_update(self, policy_id: str, payload: dict) -> bytes:
        """Update a UMA policy."""
        raise NotImplementedError

    @abstractmethod
    async def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy."""
        raise NotImplementedError

    @abstractmethod
    async def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """Query UMA policies."""
        raise NotImplementedError

    @abstractmethod
    async def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket."""
        raise NotImplementedError

    @abstractmethod
    async def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token."""
        raise NotImplementedError

    # Component Operations
    @abstractmethod
    async def create_component(self, payload: dict) -> str:
        """Create a Keycloak component."""
        raise NotImplementedError

    @abstractmethod
    async def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_components(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    async def update_component(self, component_id: str, payload: dict) -> dict[str, Any]:
        """Update a component."""
        raise NotImplementedError

    @abstractmethod
    async def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component."""
        raise NotImplementedError

    async def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization."""
        raise NotImplementedError
