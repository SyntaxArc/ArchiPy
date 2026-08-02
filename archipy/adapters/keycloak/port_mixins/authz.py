"""Keycloak port mixins for authorization service operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakAuthzPort:
    """Sync Keycloak port interface for authorization service operations."""

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


class AsyncKeycloakAuthzPort:
    """Async Keycloak port interface for authorization service operations."""

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
