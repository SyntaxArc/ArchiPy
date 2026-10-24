"""Keycloak adapter mixins for client registration policy providers."""

from __future__ import annotations

from http import HTTPStatus

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    to_dto_list,
)
from archipy.models.dtos.keycloak.component_dtos import KeycloakComponentTypeDTO


class KeycloakClientRegistrationPolicyMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client registration policy providers."""

    def get_client_registration_policy_providers(self) -> list[KeycloakComponentTypeDTO]:
        """List the client registration policy providers and their settings.

        Args:
            (none)

        Returns:
            The providers.
        """
        return to_dto_list(
            KeycloakComponentTypeDTO,
            self._admin_request(
                "get_client_registration_policy_providers",
                "get",
                "/client-registration-policy/providers",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakClientRegistrationPolicyMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client registration policy providers."""

    async def get_client_registration_policy_providers(self) -> list[KeycloakComponentTypeDTO]:
        """List the client registration policy providers and their settings.

        Args:
            (none)

        Returns:
            The providers.
        """
        return to_dto_list(
            KeycloakComponentTypeDTO,
            await self._async_admin_request(
                "get_client_registration_policy_providers",
                "get",
                "/client-registration-policy/providers",
                expected=(HTTPStatus.OK,),
            ),
        )
