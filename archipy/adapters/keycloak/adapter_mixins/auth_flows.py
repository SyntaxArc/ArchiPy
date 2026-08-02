"""Keycloak adapter mixins for authentication flow operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)


class KeycloakAuthFlowsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for authentication flow operations."""

    def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow",
            lambda: self.admin_adapter.create_authentication_flow(payload=payload, skip_exists=skip_exists),
        )

    def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        return self._call_keycloak(
            "copy_authentication_flow",
            lambda: self.admin_adapter.copy_authentication_flow(payload=payload, flow_alias=flow_alias),
        )

    def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        return self._call_keycloak(
            "get_authentication_flows",
            lambda: self.admin_adapter.get_authentication_flows(),
        )

    def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        return self._call_keycloak(
            "get_authentication_flow_for_id",
            lambda: self.admin_adapter.get_authentication_flow_for_id(flow_id=flow_id),
        )

    def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        return self._call_keycloak(
            "delete_authentication_flow",
            lambda: self.admin_adapter.delete_authentication_flow(flow_id=flow_id),
        )

    def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        return self._call_keycloak(
            "get_authentication_flow_executions",
            lambda: self.admin_adapter.get_authentication_flow_executions(flow_alias=flow_alias),
        )

    def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        return self._call_keycloak(
            "get_authentication_flow_execution",
            lambda: self.admin_adapter.get_authentication_flow_execution(execution_id=execution_id),
        )

    def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow_execution",
            lambda: self.admin_adapter.create_authentication_flow_execution(payload=payload, flow_alias=flow_alias),
        )

    def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        return self._call_keycloak(
            "update_authentication_flow_executions",
            lambda: self.admin_adapter.update_authentication_flow_executions(payload=payload, flow_alias=flow_alias),
        )

    def create_authentication_flow_subflow(self, payload: dict, flow_alias: str, skip_exists: bool = False) -> bytes:
        """Create a subflow in an authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow_subflow",
            lambda: self.admin_adapter.create_authentication_flow_subflow(
                payload=payload,
                flow_alias=flow_alias,
                skip_exists=skip_exists,
            ),
        )

    def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        return self._call_keycloak(
            "delete_authentication_flow_execution",
            lambda: self.admin_adapter.delete_authentication_flow_execution(execution_id=execution_id),
        )

    def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        return self._call_keycloak(
            "change_execution_priority",
            lambda: self.admin_adapter.change_execution_priority(execution_id=execution_id, diff=diff),
        )

    def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        return self._call_keycloak(
            "update_authentication_flow",
            lambda: self.admin_adapter.update_authentication_flow(flow_id=flow_id, payload=payload),
        )

    def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        return self._call_keycloak(
            "get_authenticator_providers",
            lambda: self.admin_adapter.get_authenticator_providers(),
        )

    def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        return self._call_keycloak(
            "get_authenticator_provider_config_description",
            lambda: self.admin_adapter.get_authenticator_provider_config_description(provider_id=provider_id),
        )

    def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        return self._call_keycloak(
            "get_authenticator_config",
            lambda: self.admin_adapter.get_authenticator_config(config_id=config_id),
        )

    def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        return self._call_keycloak(
            "update_authenticator_config",
            lambda: self.admin_adapter.update_authenticator_config(payload=payload, config_id=config_id),
        )

    def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        return self._call_keycloak(
            "delete_authenticator_config",
            lambda: self.admin_adapter.delete_authenticator_config(config_id=config_id),
        )

    def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        return self._call_keycloak(
            "create_execution_config",
            lambda: self.admin_adapter.create_execution_config(execution_id=execution_id, payload=payload),
        )


class AsyncKeycloakAuthFlowsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for authentication flow operations."""

    async def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow",
            lambda: self.admin_adapter.a_create_authentication_flow(payload=payload, skip_exists=skip_exists),
        )

    async def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        return await self._async_call_keycloak(
            "copy_authentication_flow",
            lambda: self.admin_adapter.a_copy_authentication_flow(payload=payload, flow_alias=flow_alias),
        )

    async def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        return await self._async_call_keycloak(
            "get_authentication_flows",
            lambda: self.admin_adapter.a_get_authentication_flows(),
        )

    async def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        return await self._async_call_keycloak(
            "get_authentication_flow_for_id",
            lambda: self.admin_adapter.a_get_authentication_flow_for_id(flow_id=flow_id),
        )

    async def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        return await self._async_call_keycloak(
            "delete_authentication_flow",
            lambda: self.admin_adapter.a_delete_authentication_flow(flow_id=flow_id),
        )

    async def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        return await self._async_call_keycloak(
            "get_authentication_flow_executions",
            lambda: self.admin_adapter.a_get_authentication_flow_executions(flow_alias=flow_alias),
        )

    async def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        return await self._async_call_keycloak(
            "get_authentication_flow_execution",
            lambda: self.admin_adapter.a_get_authentication_flow_execution(execution_id=execution_id),
        )

    async def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow_execution",
            lambda: self.admin_adapter.a_create_authentication_flow_execution(
                payload=payload,
                flow_alias=flow_alias,
            ),
        )

    async def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        return await self._async_call_keycloak(
            "update_authentication_flow_executions",
            lambda: self.admin_adapter.a_update_authentication_flow_executions(
                payload=payload,
                flow_alias=flow_alias,
            ),
        )

    async def create_authentication_flow_subflow(
        self,
        payload: dict,
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow_subflow",
            lambda: self.admin_adapter.a_create_authentication_flow_subflow(
                payload=payload,
                flow_alias=flow_alias,
                skip_exists=skip_exists,
            ),
        )

    async def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        return await self._async_call_keycloak(
            "delete_authentication_flow_execution",
            lambda: self.admin_adapter.a_delete_authentication_flow_execution(execution_id=execution_id),
        )

    async def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        return await self._async_call_keycloak(
            "change_execution_priority",
            lambda: self.admin_adapter.a_change_execution_priority(execution_id=execution_id, diff=diff),
        )

    async def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        return await self._async_call_keycloak(
            "update_authentication_flow",
            lambda: self.admin_adapter.a_update_authentication_flow(flow_id=flow_id, payload=payload),
        )

    async def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        return await self._async_call_keycloak(
            "get_authenticator_providers",
            lambda: self.admin_adapter.a_get_authenticator_providers(),
        )

    async def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        return await self._async_call_keycloak(
            "get_authenticator_provider_config_description",
            lambda: self.admin_adapter.a_get_authenticator_provider_config_description(provider_id=provider_id),
        )

    async def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        return await self._async_call_keycloak(
            "get_authenticator_config",
            lambda: self.admin_adapter.a_get_authenticator_config(config_id=config_id),
        )

    async def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        return await self._async_call_keycloak(
            "update_authenticator_config",
            lambda: self.admin_adapter.a_update_authenticator_config(payload=payload, config_id=config_id),
        )

    async def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        return await self._async_call_keycloak(
            "delete_authenticator_config",
            lambda: self.admin_adapter.a_delete_authenticator_config(config_id=config_id),
        )

    async def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        return await self._async_call_keycloak(
            "create_execution_config",
            lambda: self.admin_adapter.a_create_execution_config(execution_id=execution_id, payload=payload),
        )
