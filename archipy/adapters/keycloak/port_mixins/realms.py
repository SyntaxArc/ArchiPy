"""Keycloak port mixins for realm operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakRealmsPort:
    """Sync Keycloak port interface for realm operations."""

    @abstractmethod
    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled)."""
        raise NotImplementedError


class AsyncKeycloakRealmsPort:
    """Async Keycloak port interface for realm operations."""

    @abstractmethod
    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled)."""
        raise NotImplementedError
