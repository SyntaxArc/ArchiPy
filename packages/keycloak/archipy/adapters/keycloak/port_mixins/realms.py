"""Keycloak port mixins for realm operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.realm_dtos import KeycloakRealmDTO


class KeycloakRealmsPort:
    """Sync Keycloak port interface for realm operations."""

    @abstractmethod
    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> KeycloakRealmDTO | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    def update_realm(self, realm_name: str, **kwargs: Any) -> KeycloakRealmDTO | None:
        """Update a realm.

        Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).
        """
        raise NotImplementedError


class AsyncKeycloakRealmsPort:
    """Async Keycloak port interface for realm operations."""

    @abstractmethod
    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> KeycloakRealmDTO | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm(self, realm_name: str, **kwargs: Any) -> KeycloakRealmDTO | None:
        """Update a realm.

        Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).
        """
        raise NotImplementedError
