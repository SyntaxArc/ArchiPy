"""Keycloak port mixins for authentication flow operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.auth_flow_dtos import (
        KeycloakAuthenticationExecutionDTO,
        KeycloakAuthenticationExecutionInfoDTO,
        KeycloakAuthenticationExecutionInfoRequestDTO,
        KeycloakAuthenticationFlowDTO,
        KeycloakAuthenticationFlowRequestDTO,
        KeycloakAuthenticatorConfigDTO,
        KeycloakAuthenticatorConfigInfoDTO,
        KeycloakAuthenticatorConfigRequestDTO,
    )
    from archipy.models.dtos.keycloak.authenticator_dtos import (
        KeycloakAuthenticationFlowCopyRequestDTO,
        KeycloakAuthenticationFlowExecutionCreateRequestDTO,
        KeycloakAuthenticationSubflowCreateRequestDTO,
        KeycloakAuthenticatorProviderDTO,
    )
    from archipy.models.dtos.keycloak.common_dtos import KeycloakMutationResultDTO


class KeycloakAuthFlowsPort:
    """Sync Keycloak port interface for authentication flow operations."""

    @abstractmethod
    def create_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakMutationResultDTO:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def copy_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowCopyRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flows(
        self,
    ) -> list[KeycloakAuthenticationFlowDTO]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_for_id(self, flow_id: str) -> KeycloakAuthenticationFlowDTO:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow(self, flow_id: str) -> KeycloakMutationResultDTO:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_executions(self, flow_alias: str) -> list[KeycloakAuthenticationExecutionInfoDTO]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_execution(self, execution_id: str) -> KeycloakAuthenticationExecutionDTO:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_execution(
        self,
        payload: KeycloakAuthenticationFlowExecutionCreateRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow_executions(
        self,
        payload: KeycloakAuthenticationExecutionInfoRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_subflow(
        self,
        payload: KeycloakAuthenticationSubflowCreateRequestDTO | dict[str, Any],
        flow_alias: str,
        skip_exists: bool = False,
    ) -> KeycloakMutationResultDTO:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow_execution(self, execution_id: str) -> KeycloakMutationResultDTO:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow(
        self,
        flow_id: str,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
    ) -> KeycloakMutationResultDTO:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_providers(
        self,
    ) -> list[KeycloakAuthenticatorProviderDTO]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_provider_config_description(self, provider_id: str) -> KeycloakAuthenticatorConfigInfoDTO:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_config(self, config_id: str) -> KeycloakAuthenticatorConfigDTO:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    def update_authenticator_config(
        self,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
        config_id: str,
    ) -> KeycloakMutationResultDTO:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def delete_authenticator_config(self, config_id: str) -> KeycloakMutationResultDTO:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def create_execution_config(
        self,
        execution_id: str,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
    ) -> KeycloakMutationResultDTO:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError


class AsyncKeycloakAuthFlowsPort:
    """Async Keycloak port interface for authentication flow operations."""

    @abstractmethod
    async def create_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> KeycloakMutationResultDTO:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def copy_authentication_flow(
        self,
        payload: KeycloakAuthenticationFlowCopyRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flows(
        self,
    ) -> list[KeycloakAuthenticationFlowDTO]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_for_id(self, flow_id: str) -> KeycloakAuthenticationFlowDTO:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow(self, flow_id: str) -> KeycloakMutationResultDTO:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_executions(self, flow_alias: str) -> list[KeycloakAuthenticationExecutionInfoDTO]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_execution(self, execution_id: str) -> KeycloakAuthenticationExecutionDTO:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_execution(
        self,
        payload: KeycloakAuthenticationFlowExecutionCreateRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow_executions(
        self,
        payload: KeycloakAuthenticationExecutionInfoRequestDTO | dict[str, Any],
        flow_alias: str,
    ) -> KeycloakMutationResultDTO:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_subflow(
        self,
        payload: KeycloakAuthenticationSubflowCreateRequestDTO | dict[str, Any],
        flow_alias: str,
        skip_exists: bool = False,
    ) -> KeycloakMutationResultDTO:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow_execution(self, execution_id: str) -> KeycloakMutationResultDTO:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow(
        self,
        flow_id: str,
        payload: KeycloakAuthenticationFlowRequestDTO | dict[str, Any],
    ) -> KeycloakMutationResultDTO:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_providers(
        self,
    ) -> list[KeycloakAuthenticatorProviderDTO]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_provider_config_description(
        self,
        provider_id: str,
    ) -> KeycloakAuthenticatorConfigInfoDTO:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_config(self, config_id: str) -> KeycloakAuthenticatorConfigDTO:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    async def update_authenticator_config(
        self,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
        config_id: str,
    ) -> KeycloakMutationResultDTO:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authenticator_config(self, config_id: str) -> KeycloakMutationResultDTO:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def create_execution_config(
        self,
        execution_id: str,
        payload: KeycloakAuthenticatorConfigRequestDTO | dict[str, Any],
    ) -> KeycloakMutationResultDTO:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError
