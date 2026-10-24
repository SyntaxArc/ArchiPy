"""Keycloak port mixins for authzen authorization decisions (experimental)."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.authzen_dtos import (
        KeycloakAuthzenConfigurationDTO,
        KeycloakAuthzenEvaluationDTO,
        KeycloakAuthzenEvaluationRequestDTO,
        KeycloakAuthzenEvaluationsDTO,
        KeycloakAuthzenEvaluationsRequestDTO,
    )


class KeycloakAuthzenPort:
    """Sync Keycloak port interface for authzen authorization decisions (experimental)."""

    @abstractmethod
    def get_authzen_configuration(self) -> KeycloakAuthzenConfigurationDTO:
        """Get the AuthZEN discovery document of the realm."""
        raise NotImplementedError

    @abstractmethod
    def authzen_evaluation(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationRequestDTO,
    ) -> KeycloakAuthzenEvaluationDTO:
        """Ask whether a subject may perform an action on a resource."""
        raise NotImplementedError

    @abstractmethod
    def authzen_evaluations(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationsRequestDTO,
    ) -> KeycloakAuthzenEvaluationsDTO:
        """Evaluate several access requests in one call."""
        raise NotImplementedError


class AsyncKeycloakAuthzenPort:
    """Async Keycloak port interface for authzen authorization decisions (experimental)."""

    @abstractmethod
    async def get_authzen_configuration(self) -> KeycloakAuthzenConfigurationDTO:
        """Get the AuthZEN discovery document of the realm."""
        raise NotImplementedError

    @abstractmethod
    async def authzen_evaluation(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationRequestDTO,
    ) -> KeycloakAuthzenEvaluationDTO:
        """Ask whether a subject may perform an action on a resource."""
        raise NotImplementedError

    @abstractmethod
    async def authzen_evaluations(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationsRequestDTO,
    ) -> KeycloakAuthzenEvaluationsDTO:
        """Evaluate several access requests in one call."""
        raise NotImplementedError
