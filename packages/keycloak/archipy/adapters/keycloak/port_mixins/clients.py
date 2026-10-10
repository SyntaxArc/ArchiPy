"""Keycloak port mixins for client operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakClientsPort:
    """Sync Keycloak port interface for client operations."""

    @abstractmethod
    def get_client_id(self, client_name: str) -> str:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_secret(self, client_id: str) -> str:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    def get_service_account_id(self) -> str:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    @abstractmethod
    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError


class AsyncKeycloakClientsPort:
    """Async Keycloak port interface for client operations."""

    @abstractmethod
    async def get_client_id(self, client_name: str) -> str:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_secret(self, client_id: str) -> str:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    async def get_service_account_id(self) -> str:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    @abstractmethod
    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError
