"""Keycloak adapter mixins for authentication flow operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    to_dto,
    to_dto_list,
    to_request_payload,
)
from archipy.models.dtos.keycloak.auth_flow_dtos import (
    KeycloakAuthenticationExecutionDTO,
    KeycloakAuthenticationExecutionInfoDTO,
    KeycloakAuthenticationExecutionInfoRequestDTO,
    KeycloakAuthenticationExecutionRequestDTO,
    KeycloakAuthenticationFlowDTO,
    KeycloakAuthenticationFlowRequestDTO,
    KeycloakAuthenticatorConfigDTO,
    KeycloakAuthenticatorConfigInfoDTO,
    KeycloakAuthenticatorConfigRequestDTO,
)
from archipy.models.dtos.keycloak.authenticator_dtos import (
    KeycloakAuthenticationFlowCopyRequestDTO,
    KeycloakAuthenticatorProviderDTO,
)


class KeycloakAuthFlowsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for authentication flow operations."""

    def create_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> bytes:
        """Create a new authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow",
            lambda: self.admin_adapter.create_authentication_flow(
                payload=to_request_payload(to_request_payload(payload)),
                skip_exists=skip_exists,
            ),
        )

    def copy_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowCopyRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> bytes:
        """Copy an existing authentication flow."""
        return self._call_keycloak(
            "copy_authentication_flow",
            lambda: self.admin_adapter.copy_authentication_flow(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    def get_authentication_flows(
        self,
    ) -> list[KeycloakAuthenticationFlowDTO]:
        """Get all authentication flows."""
        return to_dto_list(
            KeycloakAuthenticationFlowDTO,
            self._call_keycloak(
                "get_authentication_flows",
                self.admin_adapter.get_authentication_flows,
            ),
        )

    def get_authentication_flow_for_id(self, flow_id: str) -> KeycloakAuthenticationFlowDTO:
        """Get authentication flow by ID."""
        return to_dto(
            KeycloakAuthenticationFlowDTO,
            self._call_keycloak(
                "get_authentication_flow_for_id",
                lambda: self.admin_adapter.get_authentication_flow_for_id(flow_id=flow_id),
            ),
        )

    def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        return self._call_keycloak(
            "delete_authentication_flow",
            lambda: self.admin_adapter.delete_authentication_flow(flow_id=flow_id),
        )

    def get_authentication_flow_executions(self, flow_alias: str) -> list[KeycloakAuthenticationExecutionInfoDTO]:
        """Get executions for an authentication flow."""
        return to_dto_list(
            KeycloakAuthenticationExecutionInfoDTO,
            self._call_keycloak(
                "get_authentication_flow_executions",
                lambda: self.admin_adapter.get_authentication_flow_executions(flow_alias=flow_alias),
            ),
        )

    def get_authentication_flow_execution(self, execution_id: str) -> KeycloakAuthenticationExecutionDTO:
        """Get a single authentication flow execution."""
        return to_dto(
            KeycloakAuthenticationExecutionDTO,
            self._call_keycloak(
                "get_authentication_flow_execution",
                lambda: self.admin_adapter.get_authentication_flow_execution(execution_id=execution_id),
            ),
        )

    def create_authentication_flow_execution(
        self,
        payload: KeycloakAuthenticationExecutionRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> bytes:
        """Create an execution in an authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow_execution",
            lambda: self.admin_adapter.create_authentication_flow_execution(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    def update_authentication_flow_executions(
        self,
        payload: KeycloakAuthenticationExecutionInfoRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        return self._call_keycloak(
            "update_authentication_flow_executions",
            lambda: self.admin_adapter.update_authentication_flow_executions(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    def create_authentication_flow_subflow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        return self._call_keycloak(
            "create_authentication_flow_subflow",
            lambda: self.admin_adapter.create_authentication_flow_subflow(
                payload=to_request_payload(to_request_payload(payload)),
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

    def update_authentication_flow(
        self,
        flow_id: str,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
    ) -> dict[str, Any]:
        """Update an authentication flow."""
        return self._call_keycloak(
            "update_authentication_flow",
            lambda: self.admin_adapter.update_authentication_flow(
                flow_id=flow_id,
                payload=to_request_payload(to_request_payload(payload)),
            ),
        )

    def get_authenticator_providers(
        self,
    ) -> list[KeycloakAuthenticatorProviderDTO]:
        """Get available authenticator providers."""
        return to_dto_list(
            KeycloakAuthenticatorProviderDTO,
            self._call_keycloak(
                "get_authenticator_providers",
                self.admin_adapter.get_authenticator_providers,
            ),
        )

    def get_authenticator_provider_config_description(self, provider_id: str) -> KeycloakAuthenticatorConfigInfoDTO:
        """Get config description for an authenticator provider."""
        return to_dto(
            KeycloakAuthenticatorConfigInfoDTO,
            self._call_keycloak(
                "get_authenticator_provider_config_description",
                lambda: self.admin_adapter.get_authenticator_provider_config_description(provider_id=provider_id),
            ),
        )

    def get_authenticator_config(self, config_id: str) -> KeycloakAuthenticatorConfigDTO:
        """Get authenticator configuration by ID."""
        return to_dto(
            KeycloakAuthenticatorConfigDTO,
            self._call_keycloak(
                "get_authenticator_config",
                lambda: self.admin_adapter.get_authenticator_config(config_id=config_id),
            ),
        )

    def update_authenticator_config(
        self,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
        config_id: str,
    ) -> dict[str, Any]:
        """Update authenticator configuration."""
        return self._call_keycloak(
            "update_authenticator_config",
            lambda: self.admin_adapter.update_authenticator_config(
                payload=to_request_payload(to_request_payload(payload)),
                config_id=config_id,
            ),
        )

    def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        return self._call_keycloak(
            "delete_authenticator_config",
            lambda: self.admin_adapter.delete_authenticator_config(config_id=config_id),
        )

    def create_execution_config(
        self,
        execution_id: str,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Create configuration for an authentication flow execution."""
        return self._call_keycloak(
            "create_execution_config",
            lambda: self.admin_adapter.create_execution_config(
                execution_id=execution_id,
                payload=to_request_payload(to_request_payload(payload)),
            ),
        )


class AsyncKeycloakAuthFlowsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for authentication flow operations."""

    async def create_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> bytes:
        """Create a new authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow",
            lambda: self.admin_adapter.a_create_authentication_flow(
                payload=to_request_payload(to_request_payload(payload)),
                skip_exists=skip_exists,
            ),
        )

    async def copy_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowCopyRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> bytes:
        """Copy an existing authentication flow."""
        return await self._async_call_keycloak(
            "copy_authentication_flow",
            lambda: self.admin_adapter.a_copy_authentication_flow(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    async def get_authentication_flows(
        self,
    ) -> list[KeycloakAuthenticationFlowDTO]:
        """Get all authentication flows."""
        return to_dto_list(
            KeycloakAuthenticationFlowDTO,
            await self._async_call_keycloak(
                "get_authentication_flows",
                self.admin_adapter.a_get_authentication_flows,
            ),
        )

    async def get_authentication_flow_for_id(self, flow_id: str) -> KeycloakAuthenticationFlowDTO:
        """Get authentication flow by ID."""
        return to_dto(
            KeycloakAuthenticationFlowDTO,
            await self._async_call_keycloak(
                "get_authentication_flow_for_id",
                lambda: self.admin_adapter.a_get_authentication_flow_for_id(flow_id=flow_id),
            ),
        )

    async def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        return await self._async_call_keycloak(
            "delete_authentication_flow",
            lambda: self.admin_adapter.a_delete_authentication_flow(flow_id=flow_id),
        )

    async def get_authentication_flow_executions(self, flow_alias: str) -> list[KeycloakAuthenticationExecutionInfoDTO]:
        """Get executions for an authentication flow."""
        return to_dto_list(
            KeycloakAuthenticationExecutionInfoDTO,
            await self._async_call_keycloak(
                "get_authentication_flow_executions",
                lambda: self.admin_adapter.a_get_authentication_flow_executions(flow_alias=flow_alias),
            ),
        )

    async def get_authentication_flow_execution(self, execution_id: str) -> KeycloakAuthenticationExecutionDTO:
        """Get a single authentication flow execution."""
        return to_dto(
            KeycloakAuthenticationExecutionDTO,
            await self._async_call_keycloak(
                "get_authentication_flow_execution",
                lambda: self.admin_adapter.a_get_authentication_flow_execution(execution_id=execution_id),
            ),
        )

    async def create_authentication_flow_execution(
        self,
        payload: KeycloakAuthenticationExecutionRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> bytes:
        """Create an execution in an authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow_execution",
            lambda: self.admin_adapter.a_create_authentication_flow_execution(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    async def update_authentication_flow_executions(
        self,
        payload: KeycloakAuthenticationExecutionInfoRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        return await self._async_call_keycloak(
            "update_authentication_flow_executions",
            lambda: self.admin_adapter.a_update_authentication_flow_executions(
                payload=to_request_payload(to_request_payload(payload)),
                flow_alias=flow_alias,
            ),
        )

    async def create_authentication_flow_subflow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        return await self._async_call_keycloak(
            "create_authentication_flow_subflow",
            lambda: self.admin_adapter.a_create_authentication_flow_subflow(
                payload=to_request_payload(to_request_payload(payload)),
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

    async def update_authentication_flow(
        self,
        flow_id: str,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
    ) -> dict[str, Any]:
        """Update an authentication flow."""
        return await self._async_call_keycloak(
            "update_authentication_flow",
            lambda: self.admin_adapter.a_update_authentication_flow(
                flow_id=flow_id,
                payload=to_request_payload(to_request_payload(payload)),
            ),
        )

    async def get_authenticator_providers(
        self,
    ) -> list[KeycloakAuthenticatorProviderDTO]:
        """Get available authenticator providers."""
        return to_dto_list(
            KeycloakAuthenticatorProviderDTO,
            await self._async_call_keycloak(
                "get_authenticator_providers",
                self.admin_adapter.a_get_authenticator_providers,
            ),
        )

    async def get_authenticator_provider_config_description(
        self,
        provider_id: str,
    ) -> KeycloakAuthenticatorConfigInfoDTO:
        """Get config description for an authenticator provider."""
        return to_dto(
            KeycloakAuthenticatorConfigInfoDTO,
            await self._async_call_keycloak(
                "get_authenticator_provider_config_description",
                lambda: self.admin_adapter.a_get_authenticator_provider_config_description(provider_id=provider_id),
            ),
        )

    async def get_authenticator_config(self, config_id: str) -> KeycloakAuthenticatorConfigDTO:
        """Get authenticator configuration by ID."""
        return to_dto(
            KeycloakAuthenticatorConfigDTO,
            await self._async_call_keycloak(
                "get_authenticator_config",
                lambda: self.admin_adapter.a_get_authenticator_config(config_id=config_id),
            ),
        )

    async def update_authenticator_config(
        self,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
        config_id: str,
    ) -> dict[str, Any]:
        """Update authenticator configuration."""
        return await self._async_call_keycloak(
            "update_authenticator_config",
            lambda: self.admin_adapter.a_update_authenticator_config(
                payload=to_request_payload(to_request_payload(payload)),
                config_id=config_id,
            ),
        )

    async def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        return await self._async_call_keycloak(
            "delete_authenticator_config",
            lambda: self.admin_adapter.a_delete_authenticator_config(config_id=config_id),
        )

    async def create_execution_config(
        self,
        execution_id: str,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
    ) -> bytes:
        """Create configuration for an authentication flow execution."""
        return await self._async_call_keycloak(
            "create_execution_config",
            lambda: self.admin_adapter.a_create_execution_config(
                execution_id=execution_id,
                payload=to_request_payload(to_request_payload(payload)),
            ),
        )
