"""Keycloak adapter mixins for realm keys."""

from __future__ import annotations

from http import HTTPStatus

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    to_dto,
)
from archipy.models.dtos.keycloak.key_dtos import KeycloakKeysMetadataDTO


class KeycloakKeysMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for realm keys."""

    def get_realm_keys(self) -> KeycloakKeysMetadataDTO:
        """Get the active key ids and the metadata of every key of the realm.

        Args:
            (none)

        Returns:
            The keys.
        """
        return to_dto(
            KeycloakKeysMetadataDTO,
            self._admin_request(
                "get_realm_keys",
                "get",
                "/keys",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakKeysMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for realm keys."""

    async def get_realm_keys(self) -> KeycloakKeysMetadataDTO:
        """Get the active key ids and the metadata of every key of the realm.

        Args:
            (none)

        Returns:
            The keys.
        """
        return to_dto(
            KeycloakKeysMetadataDTO,
            await self._async_admin_request(
                "get_realm_keys",
                "get",
                "/keys",
                expected=(HTTPStatus.OK,),
            ),
        )
