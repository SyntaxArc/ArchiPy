"""Keycloak adapter mixins for client initial access tokens for dynamic client registration."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
)
from archipy.models.dtos.keycloak.client_initial_access_dtos import (
    KeycloakClientInitialAccessCreateRequestDTO,
    KeycloakClientInitialAccessDTO,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakDeleteResultDTO,
)


class KeycloakClientInitialAccessMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client initial access tokens for dynamic client registration."""

    def get_client_initial_access_tokens(self) -> list[KeycloakClientInitialAccessDTO]:
        """List the client initial access tokens of the realm.

        Args:
            (none)

        Returns:
            The tokens, without their secret value.
        """
        return to_dto_list(
            KeycloakClientInitialAccessDTO,
            self._admin_request(
                "get_client_initial_access_tokens",
                "get",
                "/clients-initial-access",
                expected=(HTTPStatus.OK,),
            ),
        )

    def create_client_initial_access(
        self,
        payload: KeycloakClientInitialAccessCreateRequestDTO | dict[str, Any],
    ) -> KeycloakClientInitialAccessDTO:
        """Create a client initial access token.

        Args:
            payload: Expiration in seconds and how many clients it can register.

        Returns:
            The token, with its secret value (only returned now).
        """
        return to_dto(
            KeycloakClientInitialAccessDTO,
            self._admin_request(
                "create_client_initial_access",
                "post",
                "/clients-initial-access",
                body=to_request_payload(payload),
                expected=(
                    HTTPStatus.OK,
                    HTTPStatus.CREATED,
                ),
            ),
        )

    def delete_client_initial_access(self, access_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client initial access token.

        Args:
            access_id: Token identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_initial_access",
                "delete",
                f"/clients-initial-access/{segment(access_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakClientInitialAccessMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client initial access tokens for dynamic client registration."""

    async def get_client_initial_access_tokens(self) -> list[KeycloakClientInitialAccessDTO]:
        """List the client initial access tokens of the realm.

        Args:
            (none)

        Returns:
            The tokens, without their secret value.
        """
        return to_dto_list(
            KeycloakClientInitialAccessDTO,
            await self._async_admin_request(
                "get_client_initial_access_tokens",
                "get",
                "/clients-initial-access",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def create_client_initial_access(
        self,
        payload: KeycloakClientInitialAccessCreateRequestDTO | dict[str, Any],
    ) -> KeycloakClientInitialAccessDTO:
        """Create a client initial access token.

        Args:
            payload: Expiration in seconds and how many clients it can register.

        Returns:
            The token, with its secret value (only returned now).
        """
        return to_dto(
            KeycloakClientInitialAccessDTO,
            await self._async_admin_request(
                "create_client_initial_access",
                "post",
                "/clients-initial-access",
                body=to_request_payload(payload),
                expected=(
                    HTTPStatus.OK,
                    HTTPStatus.CREATED,
                ),
            ),
        )

    async def delete_client_initial_access(self, access_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client initial access token.

        Args:
            access_id: Token identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_initial_access",
                "delete",
                f"/clients-initial-access/{segment(access_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
