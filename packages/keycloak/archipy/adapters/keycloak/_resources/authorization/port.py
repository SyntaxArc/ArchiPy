"""Keycloak port mixins for authorization service operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.common_dtos import KeycloakDeleteResultDTO, KeycloakUpdateResultDTO

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.authz_dtos import (
        KeycloakAuthzPolicyDTO,
        KeycloakAuthzPolicyRequestDTO,
        KeycloakAuthzResourceDTO,
        KeycloakAuthzResourceRequestDTO,
        KeycloakAuthzScopeDTO,
        KeycloakAuthzScopeRequestDTO,
        KeycloakAuthzSettingsDTO,
        KeycloakAuthzSettingsRequestDTO,
    )
    from archipy.models.dtos.keycloak.authz_policy_dtos import (
        KeycloakAuthzClientPolicyDTO,
        KeycloakAuthzClientPolicyRequestDTO,
        KeycloakAuthzRolePolicyDTO,
        KeycloakAuthzRolePolicyRequestDTO,
    )
    from archipy.models.dtos.keycloak.common_dtos import KeycloakDeleteResultDTO, KeycloakUpdateResultDTO


class KeycloakAuthzPort:
    """Sync Keycloak port interface for authorization service operations."""

    @abstractmethod
    def create_client_authz_resource(
        self,
        client_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzResourceDTO:
        """Create an authorization resource for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resources(self, client_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get authorization resources for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakAuthzResourceDTO:
        """Get a single authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_resource(
        self,
        client_id: str,
        resource_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_scopes(
        self,
        client_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzScopeDTO:
        """Create authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scopes(self, client_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzRolePolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzRolePolicyDTO:
        """Create a role-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_client_policy(
        self,
        payload: KeycloakAuthzClientPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzClientPolicyDTO:
        """Create a client-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization policies for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a single authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    def create_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permissions(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization permissions for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        scope_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_resource_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        resource_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """Get policies associated with a permission."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_settings(self, client_id: str) -> KeycloakAuthzSettingsDTO:
        """Get authorization settings for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzClientPolicyDTO]:
        """Get client policies for authorization."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get resources associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get scopes associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    def import_client_authz_config(
        self,
        client_id: str,
        payload: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Import authorization configuration for a client."""
        raise NotImplementedError


class AsyncKeycloakAuthzPort:
    """Async Keycloak port interface for authorization service operations."""

    @abstractmethod
    async def create_client_authz_resource(
        self,
        client_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzResourceDTO:
        """Create an authorization resource for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resources(self, client_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get authorization resources for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakAuthzResourceDTO:
        """Get a single authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_resource(
        self,
        client_id: str,
        resource_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization resource."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_scopes(
        self,
        client_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzScopeDTO:
        """Create authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scopes(self, client_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get authorization scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzRolePolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzRolePolicyDTO:
        """Create a role-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_client_policy(
        self,
        payload: KeycloakAuthzClientPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzClientPolicyDTO:
        """Create a client-based authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization policies for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a single authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization policy."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permissions(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization permissions for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        scope_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a scope-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_resource_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        resource_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a resource-based permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """Get policies associated with a permission."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_settings(self, client_id: str) -> KeycloakAuthzSettingsDTO:
        """Get authorization settings for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzClientPolicyDTO]:
        """Get client policies for authorization."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get resources associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get scopes associated with a policy."""
        raise NotImplementedError

    @abstractmethod
    async def import_client_authz_config(
        self,
        client_id: str,
        payload: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Import authorization configuration for a client."""
        raise NotImplementedError
