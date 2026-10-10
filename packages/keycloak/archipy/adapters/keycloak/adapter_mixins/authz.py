"""Keycloak adapter mixins for authorization service operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)


class KeycloakAuthzMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for authorization service operations."""

    def create_client_authz_resource(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        return self._call_keycloak(
            "create_client_authz_resource",
            lambda: self.admin_adapter.create_client_authz_resource(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        return self._call_keycloak(
            "get_client_authz_resources",
            lambda: self.admin_adapter.get_client_authz_resources(client_id=client_id),
        )

    def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        return self._call_keycloak(
            "get_client_authz_resource",
            lambda: self.admin_adapter.get_client_authz_resource(client_id=client_id, resource_id=resource_id),
        )

    def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        return self._call_keycloak(
            "update_client_authz_resource",
            lambda: self.admin_adapter.update_client_authz_resource(
                client_id=client_id,
                resource_id=resource_id,
                payload=payload,
            ),
        )

    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        return self._call_keycloak(
            "delete_client_authz_resource",
            lambda: self.admin_adapter.delete_client_authz_resource(client_id=client_id, resource_id=resource_id),
        )

    def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        return self._call_keycloak(
            "create_client_authz_scopes",
            lambda: self.admin_adapter.create_client_authz_scopes(client_id=client_id, payload=payload),
        )

    def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        return self._call_keycloak(
            "get_client_authz_scopes",
            lambda: self.admin_adapter.get_client_authz_scopes(client_id=client_id),
        )

    def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        return self._call_keycloak(
            "create_client_authz_role_based_policy",
            lambda: self.admin_adapter.create_client_authz_role_based_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        return self._call_keycloak(
            "create_client_authz_client_policy",
            lambda: self.admin_adapter.create_client_authz_client_policy(payload=payload, client_id=client_id),
        )

    def create_client_authz_policy(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization policy."""
        return self._call_keycloak(
            "create_client_authz_policy",
            lambda: self.admin_adapter.create_client_authz_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        return self._call_keycloak(
            "get_client_authz_policies",
            lambda: self.admin_adapter.get_client_authz_policies(client_id=client_id),
        )

    def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        return self._call_keycloak(
            "get_client_authz_policy",
            lambda: self.admin_adapter.get_client_authz_policy(client_id=client_id, policy_id=policy_id),
        )

    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        return self._call_keycloak(
            "delete_client_authz_policy",
            lambda: self.admin_adapter.delete_client_authz_policy(client_id=client_id, policy_id=policy_id),
        )

    def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        return self._call_keycloak(
            "create_client_authz_resource_based_permission",
            lambda: self.admin_adapter.create_client_authz_resource_based_permission(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        return self._call_keycloak(
            "create_client_authz_scope_permission",
            lambda: self.admin_adapter.create_client_authz_scope_permission(payload=payload, client_id=client_id),
        )

    def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        return self._call_keycloak(
            "get_client_authz_permissions",
            lambda: self.admin_adapter.get_client_authz_permissions(client_id=client_id),
        )

    def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        return self._call_keycloak(
            "get_client_authz_scope_permission",
            lambda: self.admin_adapter.get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id),
        )

    def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        return self._call_keycloak(
            "update_client_authz_scope_permission",
            lambda: self.admin_adapter.update_client_authz_scope_permission(
                payload=payload,
                client_id=client_id,
                scope_id=scope_id,
            ),
        )

    def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        return self._call_keycloak(
            "update_client_authz_resource_permission",
            lambda: self.admin_adapter.update_client_authz_resource_permission(
                payload=payload,
                client_id=client_id,
                resource_id=resource_id,
            ),
        )

    def get_client_authz_permission_associated_policies(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        return self._call_keycloak(
            "get_client_authz_permission_associated_policies",
            lambda: self.admin_adapter.get_client_authz_permission_associated_policies(
                client_id=client_id,
                policy_id=policy_id,
            ),
        )

    def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        return self._call_keycloak(
            "get_client_authz_settings",
            lambda: self.admin_adapter.get_client_authz_settings(client_id=client_id),
        )

    def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        return self._call_keycloak(
            "get_client_authz_client_policies",
            lambda: self.admin_adapter.get_client_authz_client_policies(client_id=client_id),
        )

    def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        return self._call_keycloak(
            "get_client_authz_policy_resources",
            lambda: self.admin_adapter.get_client_authz_policy_resources(client_id=client_id, policy_id=policy_id),
        )

    def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        return self._call_keycloak(
            "get_client_authz_policy_scopes",
            lambda: self.admin_adapter.get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id),
        )

    def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        return self._call_keycloak(
            "import_client_authz_config",
            lambda: self.admin_adapter.import_client_authz_config(client_id=client_id, payload=payload),
        )


class AsyncKeycloakAuthzMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for authorization service operations."""

    async def create_client_authz_resource(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        return await self._async_call_keycloak(
            "create_client_authz_resource",
            lambda: self.admin_adapter.a_create_client_authz_resource(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    async def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        return await self._async_call_keycloak(
            "get_client_authz_resources",
            lambda: self.admin_adapter.a_get_client_authz_resources(client_id=client_id),
        )

    async def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        return await self._async_call_keycloak(
            "get_client_authz_resource",
            lambda: self.admin_adapter.a_get_client_authz_resource(client_id=client_id, resource_id=resource_id),
        )

    async def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        return await self._async_call_keycloak(
            "update_client_authz_resource",
            lambda: self.admin_adapter.a_update_client_authz_resource(
                client_id=client_id,
                resource_id=resource_id,
                payload=payload,
            ),
        )

    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        return await self._async_call_keycloak(
            "delete_client_authz_resource",
            lambda: self.admin_adapter.a_delete_client_authz_resource(client_id=client_id, resource_id=resource_id),
        )

    async def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        return await self._async_call_keycloak(
            "create_client_authz_scopes",
            lambda: self.admin_adapter.a_create_client_authz_scopes(client_id=client_id, payload=payload),
        )

    async def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        return await self._async_call_keycloak(
            "get_client_authz_scopes",
            lambda: self.admin_adapter.a_get_client_authz_scopes(client_id=client_id),
        )

    async def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        return await self._async_call_keycloak(
            "create_client_authz_role_based_policy",
            lambda: self.admin_adapter.a_create_client_authz_role_based_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    async def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        return await self._async_call_keycloak(
            "create_client_authz_client_policy",
            lambda: self.admin_adapter.a_create_client_authz_client_policy(payload=payload, client_id=client_id),
        )

    async def create_client_authz_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization policy."""
        return await self._async_call_keycloak(
            "create_client_authz_policy",
            lambda: self.admin_adapter.a_create_client_authz_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    async def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        return await self._async_call_keycloak(
            "get_client_authz_policies",
            lambda: self.admin_adapter.a_get_client_authz_policies(client_id=client_id),
        )

    async def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        return await self._async_call_keycloak(
            "get_client_authz_policy",
            lambda: self.admin_adapter.a_get_client_authz_policy(client_id=client_id, policy_id=policy_id),
        )

    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        return await self._async_call_keycloak(
            "delete_client_authz_policy",
            lambda: self.admin_adapter.a_delete_client_authz_policy(client_id=client_id, policy_id=policy_id),
        )

    async def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        return await self._async_call_keycloak(
            "create_client_authz_resource_based_permission",
            lambda: self.admin_adapter.a_create_client_authz_resource_based_permission(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            ),
        )

    async def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        return await self._async_call_keycloak(
            "create_client_authz_scope_permission",
            lambda: self.admin_adapter.a_create_client_authz_scope_permission(payload=payload, client_id=client_id),
        )

    async def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        return await self._async_call_keycloak(
            "get_client_authz_permissions",
            lambda: self.admin_adapter.a_get_client_authz_permissions(client_id=client_id),
        )

    async def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        return await self._async_call_keycloak(
            "get_client_authz_scope_permission",
            lambda: self.admin_adapter.a_get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id),
        )

    async def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        return await self._async_call_keycloak(
            "update_client_authz_scope_permission",
            lambda: self.admin_adapter.a_update_client_authz_scope_permission(
                payload=payload,
                client_id=client_id,
                scope_id=scope_id,
            ),
        )

    async def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        return await self._async_call_keycloak(
            "update_client_authz_resource_permission",
            lambda: self.admin_adapter.a_update_client_authz_resource_permission(
                payload=payload,
                client_id=client_id,
                resource_id=resource_id,
            ),
        )

    async def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        return await self._async_call_keycloak(
            "get_client_authz_permission_associated_policies",
            lambda: self.admin_adapter.a_get_client_authz_permission_associated_policies(
                client_id=client_id,
                policy_id=policy_id,
            ),
        )

    async def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        return await self._async_call_keycloak(
            "get_client_authz_settings",
            lambda: self.admin_adapter.a_get_client_authz_settings(client_id=client_id),
        )

    async def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        return await self._async_call_keycloak(
            "get_client_authz_client_policies",
            lambda: self.admin_adapter.a_get_client_authz_client_policies(client_id=client_id),
        )

    async def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        return await self._async_call_keycloak(
            "get_client_authz_policy_resources",
            lambda: self.admin_adapter.a_get_client_authz_policy_resources(
                client_id=client_id,
                policy_id=policy_id,
            ),
        )

    async def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        return await self._async_call_keycloak(
            "get_client_authz_policy_scopes",
            lambda: self.admin_adapter.a_get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id),
        )

    async def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        return await self._async_call_keycloak(
            "import_client_authz_config",
            lambda: self.admin_adapter.a_import_client_authz_config(client_id=client_id, payload=payload),
        )
