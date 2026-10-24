"""Keycloak adapter mixins for authorization service operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
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

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import KeycloakMutationResultDTO


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
    ) -> KeycloakMutationResultDTO:
        """Update an authorization resource."""
        return to_mutation_result(
            self._call_keycloak(
                "update_client_authz_resource",
                lambda: self.admin_adapter.update_client_authz_resource(
                    client_id=client_id,
                    resource_id=resource_id,
                    payload=to_request_payload(to_request_payload(payload)),
                ),
            ),
        )

    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakMutationResultDTO:
        """Delete an authorization resource."""
        return to_mutation_result(
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
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a role-based authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
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
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a client-based authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
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

    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakMutationResultDTO:
        """Delete an authorization policy."""
        return to_mutation_result(
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
    ) -> KeycloakMutationResultDTO:
        """Update a scope-based permission."""
        return to_mutation_result(
            self._call_keycloak(
                "update_client_authz_scope_permission",
                lambda: self.admin_adapter.update_client_authz_scope_permission(
                    payload=to_request_payload(to_request_payload(payload)),
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
    ) -> KeycloakMutationResultDTO:
        """Update a resource-based permission."""
        return to_mutation_result(
            self._call_keycloak(
                "update_client_authz_resource_permission",
                lambda: self.admin_adapter.update_client_authz_resource_permission(
                    payload=to_request_payload(to_request_payload(payload)),
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

    def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get client policies for authorization."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
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
    ) -> KeycloakMutationResultDTO:
        """Import authorization configuration for a client."""
        return to_mutation_result(
            self._call_keycloak(
                "import_client_authz_config",
                lambda: self.admin_adapter.import_client_authz_config(
                    client_id=client_id,
                    payload=to_request_payload(to_request_payload(payload)),
                ),
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
    ) -> KeycloakMutationResultDTO:
        """Update an authorization resource."""
        return to_mutation_result(
            await self._async_call_keycloak(
                "update_client_authz_resource",
                lambda: self.admin_adapter.a_update_client_authz_resource(
                    client_id=client_id,
                    resource_id=resource_id,
                    payload=to_request_payload(to_request_payload(payload)),
                ),
            ),
        )

    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> KeycloakMutationResultDTO:
        """Delete an authorization resource."""
        return to_mutation_result(
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
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a role-based authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
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
        payload: KeycloakAuthzPolicyRequestDTO | dict[str, Any],
        client_id: str,
    ) -> KeycloakAuthzPolicyDTO:
        """Create a client-based authorization policy."""
        return to_dto(
            KeycloakAuthzPolicyDTO,
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

    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> KeycloakMutationResultDTO:
        """Delete an authorization policy."""
        return to_mutation_result(
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
    ) -> KeycloakMutationResultDTO:
        """Update a scope-based permission."""
        return to_mutation_result(
            await self._async_call_keycloak(
                "update_client_authz_scope_permission",
                lambda: self.admin_adapter.a_update_client_authz_scope_permission(
                    payload=to_request_payload(to_request_payload(payload)),
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
    ) -> KeycloakMutationResultDTO:
        """Update a resource-based permission."""
        return to_mutation_result(
            await self._async_call_keycloak(
                "update_client_authz_resource_permission",
                lambda: self.admin_adapter.a_update_client_authz_resource_permission(
                    payload=to_request_payload(to_request_payload(payload)),
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

    async def get_client_authz_client_policies(self, client_id: str) -> list[KeycloakAuthzPolicyDTO]:
        """Get client policies for authorization."""
        return to_dto_list(
            KeycloakAuthzPolicyDTO,
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
    ) -> KeycloakMutationResultDTO:
        """Import authorization configuration for a client."""
        return to_mutation_result(
            await self._async_call_keycloak(
                "import_client_authz_config",
                lambda: self.admin_adapter.a_import_client_authz_config(
                    client_id=client_id,
                    payload=to_request_payload(to_request_payload(payload)),
                ),
            ),
        )
