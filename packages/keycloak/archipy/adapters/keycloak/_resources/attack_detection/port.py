"""Keycloak port mixins for brute force attack detection."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.attack_detection_dtos import KeycloakBruteForceStatusDTO
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakDeleteResultDTO,
    )


class KeycloakAttackDetectionPort:
    """Sync Keycloak port interface for brute force attack detection."""

    @abstractmethod
    def get_user_brute_force_status(self, user_id: str) -> KeycloakBruteForceStatusDTO:
        """Get the brute force detection status of a user."""
        raise NotImplementedError

    @abstractmethod
    def clear_user_brute_force(self, user_id: str) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of a user."""
        raise NotImplementedError

    @abstractmethod
    def clear_all_brute_force(self) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of every user in the realm."""
        raise NotImplementedError


class AsyncKeycloakAttackDetectionPort:
    """Async Keycloak port interface for brute force attack detection."""

    @abstractmethod
    async def get_user_brute_force_status(self, user_id: str) -> KeycloakBruteForceStatusDTO:
        """Get the brute force detection status of a user."""
        raise NotImplementedError

    @abstractmethod
    async def clear_user_brute_force(self, user_id: str) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of a user."""
        raise NotImplementedError

    @abstractmethod
    async def clear_all_brute_force(self) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of every user in the realm."""
        raise NotImplementedError
