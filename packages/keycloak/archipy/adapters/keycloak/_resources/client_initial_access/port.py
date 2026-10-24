"""Keycloak port mixins for client initial access tokens for dynamic client registration."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.client_initial_access_dtos import (
        KeycloakClientInitialAccessCreateRequestDTO,
        KeycloakClientInitialAccessDTO,
    )
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakDeleteResultDTO,
    )


class KeycloakClientInitialAccessPort:
    """Sync Keycloak port interface for client initial access tokens for dynamic client registration."""

    @abstractmethod
    def get_client_initial_access_tokens(self) -> list[KeycloakClientInitialAccessDTO]:
        """List the client initial access tokens of the realm."""
        raise NotImplementedError

    @abstractmethod
    def create_client_initial_access(
        self,
        payload: KeycloakClientInitialAccessCreateRequestDTO | dict[str, Any],
    ) -> KeycloakClientInitialAccessDTO:
        """Create a client initial access token."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_initial_access(self, access_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client initial access token."""
        raise NotImplementedError


class AsyncKeycloakClientInitialAccessPort:
    """Async Keycloak port interface for client initial access tokens for dynamic client registration."""

    @abstractmethod
    async def get_client_initial_access_tokens(self) -> list[KeycloakClientInitialAccessDTO]:
        """List the client initial access tokens of the realm."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_initial_access(
        self,
        payload: KeycloakClientInitialAccessCreateRequestDTO | dict[str, Any],
    ) -> KeycloakClientInitialAccessDTO:
        """Create a client initial access token."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_initial_access(self, access_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client initial access token."""
        raise NotImplementedError
