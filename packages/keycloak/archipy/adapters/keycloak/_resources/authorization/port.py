"""Keycloak port mixins for authorization service operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.authz_dtos import (
    KeycloakAuthzPolicyDTO,
    KeycloakAuthzResourceDTO,
    KeycloakAuthzScopeDTO,
    KeycloakAuthzScopeRequestDTO,
    KeycloakAuthzSettingsRequestDTO,
)
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
    from archipy.models.dtos.keycloak.authz_evaluation_dtos import (
        KeycloakAuthzPolicyEvaluationRequestRequestDTO,
        KeycloakAuthzPolicyEvaluationResponseDTO,
        KeycloakAuthzPolicyProviderDTO,
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

    @abstractmethod
    def update_client_authz_settings(
        self,
        client_id: str,
        settings: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the resource server settings of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resources_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzResourceDTO]:
        """List the resources of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def search_client_authz_resource(self, client_id: str, name: str) -> KeycloakAuthzResourceDTO:
        """Find a resource by its exact name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resource_attributes(self, client_id: str, resource_id: str) -> dict[str, list[str]]:
        """Get the attributes of a resource."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resource_permissions(self, client_id: str, resource_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a resource."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_resource_scopes(self, client_id: str, resource_id: str) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a resource."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scopes_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def search_client_authz_scope(self, client_id: str, name: str) -> KeycloakAuthzScopeDTO:
        """Find a scope by its exact name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakAuthzScopeDTO:
        """Get a scope by its id."""
        raise NotImplementedError

    @abstractmethod
    def update_client_authz_scope(
        self,
        client_id: str,
        scope_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scope_permissions(self, client_id: str, scope_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_scope_resources(self, client_id: str, scope_id: str) -> list[KeycloakAuthzResourceDTO]:
        """List the resources that have a scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policies_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the policies of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def search_client_authz_policy(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a policy by its exact name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_policy_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the policy types the server offers."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permissions_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def search_client_authz_permission(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a permission by its exact name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_authz_permission_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the permission types the server offers."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_client_authz_policies(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the policies for a user and resources, as the admin console's evaluation tool does."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_client_authz_permissions(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the permissions for a user and resources."""
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

    @abstractmethod
    async def update_client_authz_settings(
        self,
        client_id: str,
        settings: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the resource server settings of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resources_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzResourceDTO]:
        """List the resources of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def search_client_authz_resource(self, client_id: str, name: str) -> KeycloakAuthzResourceDTO:
        """Find a resource by its exact name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resource_attributes(self, client_id: str, resource_id: str) -> dict[str, list[str]]:
        """Get the attributes of a resource."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resource_permissions(
        self,
        client_id: str,
        resource_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a resource."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_resource_scopes(self, client_id: str, resource_id: str) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a resource."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scopes_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def search_client_authz_scope(self, client_id: str, name: str) -> KeycloakAuthzScopeDTO:
        """Find a scope by its exact name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakAuthzScopeDTO:
        """Get a scope by its id."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_authz_scope(
        self,
        client_id: str,
        scope_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scope_permissions(self, client_id: str, scope_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_scope_resources(self, client_id: str, scope_id: str) -> list[KeycloakAuthzResourceDTO]:
        """List the resources that have a scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policies_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the policies of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def search_client_authz_policy(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a policy by its exact name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_policy_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the policy types the server offers."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permissions_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions of a client, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def search_client_authz_permission(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a permission by its exact name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_authz_permission_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the permission types the server offers."""
        raise NotImplementedError

    @abstractmethod
    async def evaluate_client_authz_policies(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the policies for a user and resources, as the admin console's evaluation tool does."""
        raise NotImplementedError

    @abstractmethod
    async def evaluate_client_authz_permissions(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the permissions for a user and resources."""
        raise NotImplementedError
