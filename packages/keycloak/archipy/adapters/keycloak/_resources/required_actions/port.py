"""Keycloak port mixins for required actions."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.authenticator_dtos import KeycloakUnregisteredRequiredActionDTO
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakCreateResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.required_action_dtos import (
        KeycloakRequiredActionConfigDTO,
        KeycloakRequiredActionConfigInfoDTO,
        KeycloakRequiredActionConfigRequestDTO,
        KeycloakRequiredActionProviderDTO,
        KeycloakRequiredActionProviderRequestDTO,
    )


class KeycloakRequiredActionsPort:
    """Sync Keycloak port interface for required actions."""

    @abstractmethod
    def get_required_actions(self) -> list[KeycloakRequiredActionProviderDTO]:
        """List the required actions registered in the realm."""
        raise NotImplementedError

    @abstractmethod
    def get_required_action(self, alias: str) -> KeycloakRequiredActionProviderDTO:
        """Get a required action by alias."""
        raise NotImplementedError

    @abstractmethod
    def update_required_action(
        self,
        alias: str,
        payload: KeycloakRequiredActionProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a required action."""
        raise NotImplementedError

    @abstractmethod
    def delete_required_action(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete a required action."""
        raise NotImplementedError

    @abstractmethod
    def register_required_action(self, provider_id: str, name: str) -> KeycloakCreateResultDTO:
        """Register an unregistered required action provider in the realm."""
        raise NotImplementedError

    @abstractmethod
    def get_unregistered_required_actions(self) -> list[KeycloakUnregisteredRequiredActionDTO]:
        """List the required action providers that are not registered in the realm."""
        raise NotImplementedError

    @abstractmethod
    def raise_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action up in the order."""
        raise NotImplementedError

    @abstractmethod
    def lower_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action down in the order."""
        raise NotImplementedError

    @abstractmethod
    def get_required_action_config(self, alias: str) -> KeycloakRequiredActionConfigDTO:
        """Get the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    def update_required_action_config(
        self,
        alias: str,
        config: KeycloakRequiredActionConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Set the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    def delete_required_action_config(self, alias: str) -> KeycloakDeleteResultDTO:
        """Remove the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    def get_required_action_config_description(self, alias: str) -> KeycloakRequiredActionConfigInfoDTO:
        """Describe the settings a required action accepts."""
        raise NotImplementedError


class AsyncKeycloakRequiredActionsPort:
    """Async Keycloak port interface for required actions."""

    @abstractmethod
    async def get_required_actions(self) -> list[KeycloakRequiredActionProviderDTO]:
        """List the required actions registered in the realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_required_action(self, alias: str) -> KeycloakRequiredActionProviderDTO:
        """Get a required action by alias."""
        raise NotImplementedError

    @abstractmethod
    async def update_required_action(
        self,
        alias: str,
        payload: KeycloakRequiredActionProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a required action."""
        raise NotImplementedError

    @abstractmethod
    async def delete_required_action(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete a required action."""
        raise NotImplementedError

    @abstractmethod
    async def register_required_action(self, provider_id: str, name: str) -> KeycloakCreateResultDTO:
        """Register an unregistered required action provider in the realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_unregistered_required_actions(self) -> list[KeycloakUnregisteredRequiredActionDTO]:
        """List the required action providers that are not registered in the realm."""
        raise NotImplementedError

    @abstractmethod
    async def raise_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action up in the order."""
        raise NotImplementedError

    @abstractmethod
    async def lower_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action down in the order."""
        raise NotImplementedError

    @abstractmethod
    async def get_required_action_config(self, alias: str) -> KeycloakRequiredActionConfigDTO:
        """Get the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    async def update_required_action_config(
        self,
        alias: str,
        config: KeycloakRequiredActionConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Set the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    async def delete_required_action_config(self, alias: str) -> KeycloakDeleteResultDTO:
        """Remove the settings of a required action."""
        raise NotImplementedError

    @abstractmethod
    async def get_required_action_config_description(self, alias: str) -> KeycloakRequiredActionConfigInfoDTO:
        """Describe the settings a required action accepts."""
        raise NotImplementedError
