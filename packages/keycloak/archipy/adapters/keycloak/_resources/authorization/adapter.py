"""Keycloak adapter mixins for authorization service operations."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
)
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


class KeycloakAuthzMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for authorization service operations."""

    def create_client_authz_resource(
        self,
        client_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzResourceDTO:
        """Create an authorization resource for a client."""
        return to_dto(
            KeycloakAuthzResourceDTO,
            self._call_keycloak(
                "create_client_authz_resource",
                lambda: self.admin_adapter.create_client_authz_resource(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    def get_client_authz_resources(self, client_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get authorization resources for a client."""
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            self._call_keycloak(
                "get_client_authz_resources",
                lambda: self.admin_adapter.get_client_authz_resources(client_id=client_id),
            ),
        )

    def get_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakAuthzResourceDTO:
        """Get a single authorization resource."""
        return to_dto(
            KeycloakAuthzResourceDTO,
            self._call_keycloak(
                "get_client_authz_resource",
                lambda: self.admin_adapter.get_client_authz_resource(client_id=client_id, resource_id=resource_id),
            ),
        )

    def update_client_authz_resource(
        self,
        client_id: str,
        resource_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an authorization resource."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_client_authz_resource",
                lambda: self.admin_adapter.update_client_authz_resource(
                    client_id=client_id,
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization resource."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_client_authz_resource",
                lambda: self.admin_adapter.delete_client_authz_resource(client_id=client_id, resource_id=resource_id),
            ),
        )

    def create_client_authz_scopes(
        self,
        client_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzScopeDTO:
        """Create authorization scopes for a client."""
        return to_dto(
            KeycloakAuthzScopeDTO,
            self._call_keycloak(
                "create_client_authz_scopes",
                lambda: self.admin_adapter.create_client_authz_scopes(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def get_client_authz_scopes(self, client_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get authorization scopes for a client."""
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            self._call_keycloak(
                "get_client_authz_scopes",
                lambda: self.admin_adapter.get_client_authz_scopes(client_id=client_id),
            ),
        )

    def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzRolePolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzRolePolicyDTO:
        """Create a role-based authorization policy."""
        return to_dto(
            KeycloakAuthzRolePolicyDTO,
            self._call_keycloak(
                "create_client_authz_role_based_policy",
                lambda: self.admin_adapter.create_client_authz_role_based_policy(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    def create_client_authz_client_policy(
        self,
        payload: KeycloakAuthzClientPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzClientPolicyDTO:
        """Create a client-based authorization policy."""
        return to_dto(
            KeycloakAuthzClientPolicyDTO,
            self._call_keycloak(
                "create_client_authz_client_policy",
                lambda: self.admin_adapter.create_client_authz_client_policy(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                ),
            ),
        )

    def create_client_authz_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create an authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "create_client_authz_policy",
                lambda: self.admin_adapter.create_client_authz_policy(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    def get_client_authz_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization policies for a client."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "get_client_authz_policies",
                lambda: self.admin_adapter.get_client_authz_policies(client_id=client_id),
            ),
        )

    def get_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a single authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "get_client_authz_policy",
                lambda: self.admin_adapter.get_client_authz_policy(client_id=client_id, policy_id=policy_id),
            ),
        )

    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization policy."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_client_authz_policy",
                lambda: self.admin_adapter.delete_client_authz_policy(client_id=client_id, policy_id=policy_id),
            ),
        )

    def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a resource-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "create_client_authz_resource_based_permission",
                lambda: self.admin_adapter.create_client_authz_resource_based_permission(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    def create_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a scope-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "create_client_authz_scope_permission",
                lambda: self.admin_adapter.create_client_authz_scope_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                ),
            ),
        )

    def get_client_authz_permissions(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization permissions for a client."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "get_client_authz_permissions",
                lambda: self.admin_adapter.get_client_authz_permissions(client_id=client_id),
            ),
        )

    def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a scope-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "get_client_authz_scope_permission",
                lambda: self.admin_adapter.get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id),
            ),
        )

    def update_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        scope_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a scope-based permission."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_client_authz_scope_permission",
                lambda: self.admin_adapter.update_client_authz_scope_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                    scope_id=scope_id,
                ),
            ),
        )

    def update_client_authz_resource_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        resource_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a resource-based permission."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_client_authz_resource_permission",
                lambda: self.admin_adapter.update_client_authz_resource_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                    resource_id=resource_id,
                ),
            ),
        )

    def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """Get policies associated with a permission."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._call_keycloak(
                "get_client_authz_permission_associated_policies",
                lambda: self.admin_adapter.get_client_authz_permission_associated_policies(
                    client_id=client_id,
                    policy_id=policy_id,
                ),
            ),
        )

    def get_client_authz_settings(self, client_id: str) -> KeycloakAuthzSettingsDTO:
        """Get authorization settings for a client."""
        return to_dto(
            KeycloakAuthzSettingsDTO,
            self._call_keycloak(
                "get_client_authz_settings",
                lambda: self.admin_adapter.get_client_authz_settings(client_id=client_id),
            ),
        )

    def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzClientPolicyDTO]:
        """Get client policies for authorization."""
        return to_dto_list(
            KeycloakAuthzClientPolicyDTO,
            self._call_keycloak(
                "get_client_authz_client_policies",
                lambda: self.admin_adapter.get_client_authz_client_policies(client_id=client_id),
            ),
        )

    def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get resources associated with a policy."""
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            self._call_keycloak(
                "get_client_authz_policy_resources",
                lambda: self.admin_adapter.get_client_authz_policy_resources(client_id=client_id, policy_id=policy_id),
            ),
        )

    def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get scopes associated with a policy."""
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            self._call_keycloak(
                "get_client_authz_policy_scopes",
                lambda: self.admin_adapter.get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id),
            ),
        )

    def import_client_authz_config(
        self,
        client_id: str,
        payload: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Import authorization configuration for a client."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "import_client_authz_config",
                lambda: self.admin_adapter.import_client_authz_config(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def update_client_authz_settings(
        self,
        client_id: str,
        settings: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the resource server settings of a client.

        Args:
            client_id: Client UUID.
            settings: Resource server settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_client_authz_settings",
                "put",
                f"/clients/{segment(client_id)}/authz/resource-server",
                body=to_request_payload(settings),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_authz_resources_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzResourceDTO]:
        """List the resources of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``uri``, ``owner``, ``type``, ``scope``, ``deep``, ``first`` and ``max``.

        Returns:
            The resources.
        """
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            self._admin_request(
                "get_client_authz_resources_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def search_client_authz_resource(self, client_id: str, name: str) -> KeycloakAuthzResourceDTO:
        """Find a resource by its exact name.

        Args:
            client_id: Client UUID.
            name: Resource name.

        Returns:
            The resource.
        """
        return to_dto(
            KeycloakAuthzResourceDTO,
            self._admin_request(
                "search_client_authz_resource",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_resource_attributes(self, client_id: str, resource_id: str) -> dict[str, list[str]]:
        """Get the attributes of a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The attributes.
        """
        return self._admin_request(
            "get_client_authz_resource_attributes",
            "get",
            f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/attributes",
            expected=(HTTPStatus.OK,),
        )

    def get_client_authz_resource_permissions(self, client_id: str, resource_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "get_client_authz_resource_permissions",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_resource_scopes(self, client_id: str, resource_id: str) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The scopes.
        """
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            self._admin_request(
                "get_client_authz_resource_scopes",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/scopes",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_scopes_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters: ``name``, ``scopeId``, ``first`` and ``max``.

        Returns:
            The scopes.
        """
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            self._admin_request(
                "get_client_authz_scopes_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def search_client_authz_scope(self, client_id: str, name: str) -> KeycloakAuthzScopeDTO:
        """Find a scope by its exact name.

        Args:
            client_id: Client UUID.
            name: Scope name.

        Returns:
            The scope.
        """
        return to_dto(
            KeycloakAuthzScopeDTO,
            self._admin_request(
                "search_client_authz_scope",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakAuthzScopeDTO:
        """Get a scope by its id.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The scope.
        """
        return to_dto(
            KeycloakAuthzScopeDTO,
            self._admin_request(
                "get_client_authz_scope",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_client_authz_scope(
        self,
        client_id: str,
        scope_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.
            payload: Scope representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_client_authz_scope",
                "put",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_authz_scope",
                "delete",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_authz_scope_permissions(self, client_id: str, scope_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "get_client_authz_scope_permissions",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_scope_resources(self, client_id: str, scope_id: str) -> list[KeycloakAuthzResourceDTO]:
        """List the resources that have a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The resources.
        """
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            self._admin_request(
                "get_client_authz_scope_resources",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}/resources",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_policies_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the policies of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``type``, ``resource``, ``scope``, ``permission``, ``owner``, ``fields``, ``first`` and
                ``max``.

        Returns:
            The policies.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "get_client_authz_policies_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def search_client_authz_policy(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a policy by its exact name.

        Args:
            client_id: Client UUID.
            name: Policy name.

        Returns:
            The policy.
        """
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "search_client_authz_policy",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_policy_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the policy types the server offers.

        Args:
            client_id: Client UUID.

        Returns:
            The policy providers.
        """
        return to_dto_list(
            KeycloakAuthzPolicyProviderDTO,
            self._admin_request(
                "get_client_authz_policy_providers",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/providers",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_permissions_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``type``, ``resource``, ``scope``, ``owner``, ``fields``, ``first`` and ``max``.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "get_client_authz_permissions_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def search_client_authz_permission(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a permission by its exact name.

        Args:
            client_id: Client UUID.
            name: Permission name.

        Returns:
            The permission.
        """
        return to_dto(
            KeycloakAuthzPolicyDTO,
            self._admin_request(
                "search_client_authz_permission",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_authz_permission_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the permission types the server offers.

        Args:
            client_id: Client UUID.

        Returns:
            The permission providers.
        """
        return to_dto_list(
            KeycloakAuthzPolicyProviderDTO,
            self._admin_request(
                "get_client_authz_permission_providers",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/providers",
                expected=(HTTPStatus.OK,),
            ),
        )

    def evaluate_client_authz_policies(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the policies for a user and resources, as the admin console's evaluation tool does.

        Args:
            client_id: Client UUID.
            request: The user, client, resources and context to evaluate.

        Returns:
            The decision per resource.
        """
        return to_dto(
            KeycloakAuthzPolicyEvaluationResponseDTO,
            self._admin_request(
                "evaluate_client_authz_policies",
                "post",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/evaluate",
                body=to_request_payload(request),
                expected=(HTTPStatus.OK,),
            ),
        )

    def evaluate_client_authz_permissions(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the permissions for a user and resources.

        Args:
            client_id: Client UUID.
            request: The user, client, resources and context to evaluate.

        Returns:
            The decision per resource.
        """
        return to_dto(
            KeycloakAuthzPolicyEvaluationResponseDTO,
            self._admin_request(
                "evaluate_client_authz_permissions",
                "post",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/evaluate",
                body=to_request_payload(request),
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakAuthzMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for authorization service operations."""

    async def create_client_authz_resource(
        self,
        client_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzResourceDTO:
        """Create an authorization resource for a client."""
        return to_dto(
            KeycloakAuthzResourceDTO,
            await self._async_call_keycloak(
                "create_client_authz_resource",
                lambda: self.admin_adapter.a_create_client_authz_resource(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    async def get_client_authz_resources(self, client_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get authorization resources for a client."""
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            await self._async_call_keycloak(
                "get_client_authz_resources",
                lambda: self.admin_adapter.a_get_client_authz_resources(client_id=client_id),
            ),
        )

    async def get_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakAuthzResourceDTO:
        """Get a single authorization resource."""
        return to_dto(
            KeycloakAuthzResourceDTO,
            await self._async_call_keycloak(
                "get_client_authz_resource",
                lambda: self.admin_adapter.a_get_client_authz_resource(client_id=client_id, resource_id=resource_id),
            ),
        )

    async def update_client_authz_resource(
        self,
        client_id: str,
        resource_id: str,
        payload: KeycloakAuthzResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an authorization resource."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_client_authz_resource",
                lambda: self.admin_adapter.a_update_client_authz_resource(
                    client_id=client_id,
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization resource."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_client_authz_resource",
                lambda: self.admin_adapter.a_delete_client_authz_resource(client_id=client_id, resource_id=resource_id),
            ),
        )

    async def create_client_authz_scopes(
        self,
        client_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzScopeDTO:
        """Create authorization scopes for a client."""
        return to_dto(
            KeycloakAuthzScopeDTO,
            await self._async_call_keycloak(
                "create_client_authz_scopes",
                lambda: self.admin_adapter.a_create_client_authz_scopes(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def get_client_authz_scopes(self, client_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get authorization scopes for a client."""
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            await self._async_call_keycloak(
                "get_client_authz_scopes",
                lambda: self.admin_adapter.a_get_client_authz_scopes(client_id=client_id),
            ),
        )

    async def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzRolePolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzRolePolicyDTO:
        """Create a role-based authorization policy."""
        return to_dto(
            KeycloakAuthzRolePolicyDTO,
            await self._async_call_keycloak(
                "create_client_authz_role_based_policy",
                lambda: self.admin_adapter.a_create_client_authz_role_based_policy(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    async def create_client_authz_client_policy(
        self,
        payload: KeycloakAuthzClientPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzClientPolicyDTO:
        """Create a client-based authorization policy."""
        return to_dto(
            KeycloakAuthzClientPolicyDTO,
            await self._async_call_keycloak(
                "create_client_authz_client_policy",
                lambda: self.admin_adapter.a_create_client_authz_client_policy(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                ),
            ),
        )

    async def create_client_authz_policy(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create an authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "create_client_authz_policy",
                lambda: self.admin_adapter.a_create_client_authz_policy(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    async def get_client_authz_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization policies for a client."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_policies",
                lambda: self.admin_adapter.a_get_client_authz_policies(client_id=client_id),
            ),
        )

    async def get_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a single authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_policy",
                lambda: self.admin_adapter.a_get_client_authz_policy(client_id=client_id, policy_id=policy_id),
            ),
        )

    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete an authorization policy."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_client_authz_policy",
                lambda: self.admin_adapter.a_delete_client_authz_policy(client_id=client_id, policy_id=policy_id),
            ),
        )

    async def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a resource-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "create_client_authz_resource_based_permission",
                lambda: self.admin_adapter.a_create_client_authz_resource_based_permission(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                    skip_exists=skip_exists,
                ),
            ),
        )

    async def create_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a scope-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "create_client_authz_scope_permission",
                lambda: self.admin_adapter.a_create_client_authz_scope_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                ),
            ),
        )

    async def get_client_authz_permissions(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get authorization permissions for a client."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_permissions",
                lambda: self.admin_adapter.a_get_client_authz_permissions(client_id=client_id),
            ),
        )

    async def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> KeycloakAuthzPolicyDTO:
        """Get a scope-based permission."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_scope_permission",
                lambda: self.admin_adapter.a_get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id),
            ),
        )

    async def update_client_authz_scope_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        scope_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a scope-based permission."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_client_authz_scope_permission",
                lambda: self.admin_adapter.a_update_client_authz_scope_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                    scope_id=scope_id,
                ),
            ),
        )

    async def update_client_authz_resource_permission(
        self,
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
        resource_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Update a resource-based permission."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_client_authz_resource_permission",
                lambda: self.admin_adapter.a_update_client_authz_resource_permission(
                    payload=to_request_payload(payload),
                    client_id=client_id,
                    resource_id=resource_id,
                ),
            ),
        )

    async def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """Get policies associated with a permission."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_permission_associated_policies",
                lambda: self.admin_adapter.a_get_client_authz_permission_associated_policies(
                    client_id=client_id,
                    policy_id=policy_id,
                ),
            ),
        )

    async def get_client_authz_settings(self, client_id: str) -> KeycloakAuthzSettingsDTO:
        """Get authorization settings for a client."""
        return to_dto(
            KeycloakAuthzSettingsDTO,
            await self._async_call_keycloak(
                "get_client_authz_settings",
                lambda: self.admin_adapter.a_get_client_authz_settings(client_id=client_id),
            ),
        )

    async def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzClientPolicyDTO]:
        """Get client policies for authorization."""
        return to_dto_list(
            KeycloakAuthzClientPolicyDTO,
            await self._async_call_keycloak(
                "get_client_authz_client_policies",
                lambda: self.admin_adapter.a_get_client_authz_client_policies(client_id=client_id),
            ),
        )

    async def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[KeycloakAuthzResourceDTO]:
        """Get resources associated with a policy."""
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            await self._async_call_keycloak(
                "get_client_authz_policy_resources",
                lambda: self.admin_adapter.a_get_client_authz_policy_resources(
                    client_id=client_id,
                    policy_id=policy_id,
                ),
            ),
        )

    async def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[KeycloakAuthzScopeDTO]:
        """Get scopes associated with a policy."""
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            await self._async_call_keycloak(
                "get_client_authz_policy_scopes",
                lambda: self.admin_adapter.a_get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id),
            ),
        )

    async def import_client_authz_config(
        self,
        client_id: str,
        payload: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Import authorization configuration for a client."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "import_client_authz_config",
                lambda: self.admin_adapter.a_import_client_authz_config(
                    client_id=client_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def update_client_authz_settings(
        self,
        client_id: str,
        settings: KeycloakAuthzSettingsRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the resource server settings of a client.

        Args:
            client_id: Client UUID.
            settings: Resource server settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_client_authz_settings",
                "put",
                f"/clients/{segment(client_id)}/authz/resource-server",
                body=to_request_payload(settings),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_authz_resources_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzResourceDTO]:
        """List the resources of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``uri``, ``owner``, ``type``, ``scope``, ``deep``, ``first`` and ``max``.

        Returns:
            The resources.
        """
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            await self._async_admin_request(
                "get_client_authz_resources_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def search_client_authz_resource(self, client_id: str, name: str) -> KeycloakAuthzResourceDTO:
        """Find a resource by its exact name.

        Args:
            client_id: Client UUID.
            name: Resource name.

        Returns:
            The resource.
        """
        return to_dto(
            KeycloakAuthzResourceDTO,
            await self._async_admin_request(
                "search_client_authz_resource",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_resource_attributes(self, client_id: str, resource_id: str) -> dict[str, list[str]]:
        """Get the attributes of a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The attributes.
        """
        return await self._async_admin_request(
            "get_client_authz_resource_attributes",
            "get",
            f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/attributes",
            expected=(HTTPStatus.OK,),
        )

    async def get_client_authz_resource_permissions(
        self,
        client_id: str,
        resource_id: str,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "get_client_authz_resource_permissions",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_resource_scopes(self, client_id: str, resource_id: str) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a resource.

        Args:
            client_id: Client UUID.
            resource_id: Resource identifier.

        Returns:
            The scopes.
        """
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            await self._async_admin_request(
                "get_client_authz_resource_scopes",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/resource/{segment(resource_id)}/scopes",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_scopes_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzScopeDTO]:
        """List the scopes of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters: ``name``, ``scopeId``, ``first`` and ``max``.

        Returns:
            The scopes.
        """
        return to_dto_list(
            KeycloakAuthzScopeDTO,
            await self._async_admin_request(
                "get_client_authz_scopes_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def search_client_authz_scope(self, client_id: str, name: str) -> KeycloakAuthzScopeDTO:
        """Find a scope by its exact name.

        Args:
            client_id: Client UUID.
            name: Scope name.

        Returns:
            The scope.
        """
        return to_dto(
            KeycloakAuthzScopeDTO,
            await self._async_admin_request(
                "search_client_authz_scope",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakAuthzScopeDTO:
        """Get a scope by its id.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The scope.
        """
        return to_dto(
            KeycloakAuthzScopeDTO,
            await self._async_admin_request(
                "get_client_authz_scope",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_client_authz_scope(
        self,
        client_id: str,
        scope_id: str,
        payload: KeycloakAuthzScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.
            payload: Scope representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_client_authz_scope",
                "put",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_authz_scope(self, client_id: str, scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_authz_scope",
                "delete",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_authz_scope_permissions(self, client_id: str, scope_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions that apply to a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "get_client_authz_scope_permissions",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_scope_resources(self, client_id: str, scope_id: str) -> list[KeycloakAuthzResourceDTO]:
        """List the resources that have a scope.

        Args:
            client_id: Client UUID.
            scope_id: Scope identifier.

        Returns:
            The resources.
        """
        return to_dto_list(
            KeycloakAuthzResourceDTO,
            await self._async_admin_request(
                "get_client_authz_scope_resources",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/scope/{segment(scope_id)}/resources",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_policies_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the policies of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``type``, ``resource``, ``scope``, ``permission``, ``owner``, ``fields``, ``first`` and
                ``max``.

        Returns:
            The policies.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "get_client_authz_policies_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def search_client_authz_policy(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a policy by its exact name.

        Args:
            client_id: Client UUID.
            name: Policy name.

        Returns:
            The policy.
        """
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "search_client_authz_policy",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_policy_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the policy types the server offers.

        Args:
            client_id: Client UUID.

        Returns:
            The policy providers.
        """
        return to_dto_list(
            KeycloakAuthzPolicyProviderDTO,
            await self._async_admin_request(
                "get_client_authz_policy_providers",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/providers",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_permissions_filtered(
        self,
        client_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAuthzPolicyDTO]:
        """List the permissions of a client, filtered by the admin API query parameters.

        Args:
            client_id: Client UUID.
            query: Optional query parameters:
                ``name``, ``type``, ``resource``, ``scope``, ``owner``, ``fields``, ``first`` and ``max``.

        Returns:
            The permissions.
        """
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "get_client_authz_permissions_filtered",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def search_client_authz_permission(self, client_id: str, name: str) -> KeycloakAuthzPolicyDTO:
        """Find a permission by its exact name.

        Args:
            client_id: Client UUID.
            name: Permission name.

        Returns:
            The permission.
        """
        return to_dto(
            KeycloakAuthzPolicyDTO,
            await self._async_admin_request(
                "search_client_authz_permission",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/search",
                params={"name": name},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_authz_permission_providers(self, client_id: str) -> list[KeycloakAuthzPolicyProviderDTO]:
        """List the permission types the server offers.

        Args:
            client_id: Client UUID.

        Returns:
            The permission providers.
        """
        return to_dto_list(
            KeycloakAuthzPolicyProviderDTO,
            await self._async_admin_request(
                "get_client_authz_permission_providers",
                "get",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/providers",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def evaluate_client_authz_policies(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the policies for a user and resources, as the admin console's evaluation tool does.

        Args:
            client_id: Client UUID.
            request: The user, client, resources and context to evaluate.

        Returns:
            The decision per resource.
        """
        return to_dto(
            KeycloakAuthzPolicyEvaluationResponseDTO,
            await self._async_admin_request(
                "evaluate_client_authz_policies",
                "post",
                f"/clients/{segment(client_id)}/authz/resource-server/policy/evaluate",
                body=to_request_payload(request),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def evaluate_client_authz_permissions(
        self,
        client_id: str,
        request: KeycloakAuthzPolicyEvaluationRequestRequestDTO | dict[str, Any],
    ) -> KeycloakAuthzPolicyEvaluationResponseDTO:
        """Evaluate the permissions for a user and resources.

        Args:
            client_id: Client UUID.
            request: The user, client, resources and context to evaluate.

        Returns:
            The decision per resource.
        """
        return to_dto(
            KeycloakAuthzPolicyEvaluationResponseDTO,
            await self._async_admin_request(
                "evaluate_client_authz_permissions",
                "post",
                f"/clients/{segment(client_id)}/authz/resource-server/permission/evaluate",
                body=to_request_payload(request),
                expected=(HTTPStatus.OK,),
            ),
        )
