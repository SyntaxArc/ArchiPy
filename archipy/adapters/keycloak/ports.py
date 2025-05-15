"""Keycloak port definitions for ArchiPy."""

from abc import abstractmethod
from typing import Any

# Define type aliases for better type hinting
KeycloakResponseType = dict[str, Any]
KeycloakRoleType = dict[str, Any]
KeycloakUserType = dict[str, Any]
KeycloakGroupType = dict[str, Any]
KeycloakTokenType = dict[str, Any]

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
    def get_token(self, username: str, password: str) -> KeycloakTokenType:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> KeycloakTokenType:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    def get_userinfo(self, token: str) -> KeycloakUserType:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    def get_token_info(self, token: str) -> dict[str, Any]:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    def introspect_token(self, token: str) -> dict[str, Any]:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    def get_client_credentials_token(self) -> KeycloakTokenType:
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
    def create_user(self, user_data: dict[str, Any]) -> str:
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
    def get_realm_role(self, role_name: str) -> dict:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    def create_realm_role(self, role_name: str, description: str | None = None) -> dict[str, Any]:
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
    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError

    @abstractmethod
    def create_client_role(self, client_id: str, role_name: str, description: str | None = None) -> dict[str, Any]:
        """Create a new client role."""
        raise NotImplementedError

    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs) -> dict[str, Any]:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    def create_client(
        self, client_id: str, realm: str | None = None, skip_exists: bool = True, **kwargs
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError


class AsyncKeycloakPort:
    """Asynchronous interface for Keycloak operations providing a standardized access pattern.

    This interface defines the contract for async Keycloak adapters, ensuring consistent
    implementation of Keycloak operations across different adapters. It covers essential
    functionality including authentication, user management, and role management.
    """

    # Token Operations
    @abstractmethod
    async def get_token(self, username: str, password: str) -> KeycloakTokenType:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> KeycloakTokenType:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    async def get_userinfo(self, token: str) -> KeycloakUserType:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    async def get_token_info(self, token: str) -> dict[str, Any]:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    async def introspect_token(self, token: str) -> dict[str, Any]:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_credentials_token(self) -> KeycloakTokenType:
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
    async def create_user(self, user_data: dict[str, Any]) -> str:
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
    async def get_realm_role(self, role_name: str) -> dict:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm_role(self, role_name: str, description: str | None = None) -> dict[str, Any]:
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
    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    async def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_role(
        self, client_id: str, role_name: str, description: str | None = None
    ) -> dict[str, Any]:
        """Create a new client role."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs) -> dict[str, Any] | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    async def create_client(
        self, client_id: str, realm: str | None = None, skip_exists: bool = True, **kwargs
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError
