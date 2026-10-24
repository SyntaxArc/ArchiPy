"""Keycloak port mixins for client registration policy providers."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.component_dtos import KeycloakComponentTypeDTO


class KeycloakClientRegistrationPolicyPort:
    """Sync Keycloak port interface for client registration policy providers."""

    @abstractmethod
    def get_client_registration_policy_providers(self) -> list[KeycloakComponentTypeDTO]:
        """List the client registration policy providers and their settings."""
        raise NotImplementedError


class AsyncKeycloakClientRegistrationPolicyPort:
    """Async Keycloak port interface for client registration policy providers."""

    @abstractmethod
    async def get_client_registration_policy_providers(self) -> list[KeycloakComponentTypeDTO]:
        """List the client registration policy providers and their settings."""
        raise NotImplementedError
