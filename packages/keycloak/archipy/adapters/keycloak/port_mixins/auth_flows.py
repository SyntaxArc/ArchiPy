"""Keycloak port mixins for authentication flow operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakAuthFlowsPort:
    """Sync Keycloak port interface for authentication flow operations."""

    @abstractmethod
    def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def create_authentication_flow_subflow(self, payload: dict, flow_alias: str, skip_exists: bool = False) -> bytes:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError


class AsyncKeycloakAuthFlowsPort:
    """Async Keycloak port interface for authentication flow operations."""

    @abstractmethod
    async def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def create_authentication_flow_subflow(
        self,
        payload: dict,
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        raise NotImplementedError

    @abstractmethod
    async def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        raise NotImplementedError

    @abstractmethod
    async def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        raise NotImplementedError

    @abstractmethod
    async def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        raise NotImplementedError
