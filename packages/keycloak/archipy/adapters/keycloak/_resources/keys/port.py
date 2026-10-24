"""Keycloak port mixins for realm keys."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.key_dtos import KeycloakKeysMetadataDTO


class KeycloakKeysPort:
    """Sync Keycloak port interface for realm keys."""

    @abstractmethod
    def get_realm_keys(self) -> KeycloakKeysMetadataDTO:
        """Get the active key ids and the metadata of every key of the realm."""
        raise NotImplementedError


class AsyncKeycloakKeysPort:
    """Async Keycloak port interface for realm keys."""

    @abstractmethod
    async def get_realm_keys(self) -> KeycloakKeysMetadataDTO:
        """Get the active key ids and the metadata of every key of the realm."""
        raise NotImplementedError
