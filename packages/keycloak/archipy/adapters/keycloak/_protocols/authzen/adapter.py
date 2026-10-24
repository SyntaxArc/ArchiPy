"""Keycloak adapter mixins for authzen authorization decisions (experimental)."""

from __future__ import annotations

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
)
from archipy.models.dtos.keycloak.authzen_dtos import (
    KeycloakAuthzenConfigurationDTO,
    KeycloakAuthzenEvaluationDTO,
    KeycloakAuthzenEvaluationRequestDTO,
    KeycloakAuthzenEvaluationsDTO,
    KeycloakAuthzenEvaluationsRequestDTO,
)


class KeycloakAuthzenMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for authzen authorization decisions (experimental)."""

    def get_authzen_configuration(self) -> KeycloakAuthzenConfigurationDTO:
        """Get the AuthZEN discovery document of the realm.

        Returns:
            The decision point and the evaluation endpoints.

        Raises:
            Mapped application errors; ``ResourceNotFoundError`` when the server's ``authzen`` feature is off.
        """
        return to_dto(
            KeycloakAuthzenConfigurationDTO,
            self._bearer_request(
                "get_authzen_configuration",
                "get",
                f"realms/{segment(self.configs.REALM_NAME)}/.well-known/authzen-configuration",
            ),
        )

    def authzen_evaluation(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationRequestDTO,
    ) -> KeycloakAuthzenEvaluationDTO:
        """Ask whether a subject may perform an action on a resource.

        Args:
            token: Bearer token issued to a client with authorization enabled.
            request: Subject, resource, action and context.

        Returns:
            The decision.
        """
        return to_dto(
            KeycloakAuthzenEvaluationDTO,
            self._bearer_request(
                "authzen_evaluation",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/authzen/access/v1/evaluation",
                token=token,
                json_body=request.to_payload(),
            ),
        )

    def authzen_evaluations(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationsRequestDTO,
    ) -> KeycloakAuthzenEvaluationsDTO:
        """Evaluate several access requests in one call.

        Args:
            token: Bearer token issued to a client with authorization enabled.
            request: Batch with default subject, resource, action and context, and the individual evaluations.

        Returns:
            The decisions, in request order.
        """
        return to_dto(
            KeycloakAuthzenEvaluationsDTO,
            self._bearer_request(
                "authzen_evaluations",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/authzen/access/v1/evaluations",
                token=token,
                json_body=request.to_payload(),
            ),
        )


class AsyncKeycloakAuthzenMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for authzen authorization decisions (experimental)."""

    async def get_authzen_configuration(self) -> KeycloakAuthzenConfigurationDTO:
        """Get the AuthZEN discovery document of the realm.

        Returns:
            The decision point and the evaluation endpoints.

        Raises:
            Mapped application errors; ``ResourceNotFoundError`` when the server's ``authzen`` feature is off.
        """
        return to_dto(
            KeycloakAuthzenConfigurationDTO,
            await self._async_bearer_request(
                "get_authzen_configuration",
                "get",
                f"realms/{segment(self.configs.REALM_NAME)}/.well-known/authzen-configuration",
            ),
        )

    async def authzen_evaluation(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationRequestDTO,
    ) -> KeycloakAuthzenEvaluationDTO:
        """Ask whether a subject may perform an action on a resource.

        Args:
            token: Bearer token issued to a client with authorization enabled.
            request: Subject, resource, action and context.

        Returns:
            The decision.
        """
        return to_dto(
            KeycloakAuthzenEvaluationDTO,
            await self._async_bearer_request(
                "authzen_evaluation",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/authzen/access/v1/evaluation",
                token=token,
                json_body=request.to_payload(),
            ),
        )

    async def authzen_evaluations(
        self,
        token: str,
        request: KeycloakAuthzenEvaluationsRequestDTO,
    ) -> KeycloakAuthzenEvaluationsDTO:
        """Evaluate several access requests in one call.

        Args:
            token: Bearer token issued to a client with authorization enabled.
            request: Batch with default subject, resource, action and context, and the individual evaluations.

        Returns:
            The decisions, in request order.
        """
        return to_dto(
            KeycloakAuthzenEvaluationsDTO,
            await self._async_bearer_request(
                "authzen_evaluations",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/authzen/access/v1/evaluations",
                token=token,
                json_body=request.to_payload(),
            ),
        )
