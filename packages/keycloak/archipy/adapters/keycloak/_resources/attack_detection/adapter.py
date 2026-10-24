"""Keycloak adapter mixins for brute force attack detection."""

from __future__ import annotations

from http import HTTPStatus

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_mutation_result,
)
from archipy.models.dtos.keycloak.attack_detection_dtos import KeycloakBruteForceStatusDTO
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakDeleteResultDTO,
)


class KeycloakAttackDetectionMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for brute force attack detection."""

    def get_user_brute_force_status(self, user_id: str) -> KeycloakBruteForceStatusDTO:
        """Get the brute force detection status of a user.

        Args:
            user_id: User identifier.

        Returns:
            The status.
        """
        return to_dto(
            KeycloakBruteForceStatusDTO,
            self._admin_request(
                "get_user_brute_force_status",
                "get",
                f"/attack-detection/brute-force/users/{segment(user_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def clear_user_brute_force(self, user_id: str) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of a user.

        Args:
            user_id: User identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "clear_user_brute_force",
                "delete",
                f"/attack-detection/brute-force/users/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def clear_all_brute_force(self) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of every user in the realm.

        Args:
            (none)

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "clear_all_brute_force",
                "delete",
                "/attack-detection/brute-force/users",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakAttackDetectionMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for brute force attack detection."""

    async def get_user_brute_force_status(self, user_id: str) -> KeycloakBruteForceStatusDTO:
        """Get the brute force detection status of a user.

        Args:
            user_id: User identifier.

        Returns:
            The status.
        """
        return to_dto(
            KeycloakBruteForceStatusDTO,
            await self._async_admin_request(
                "get_user_brute_force_status",
                "get",
                f"/attack-detection/brute-force/users/{segment(user_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def clear_user_brute_force(self, user_id: str) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of a user.

        Args:
            user_id: User identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "clear_user_brute_force",
                "delete",
                f"/attack-detection/brute-force/users/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def clear_all_brute_force(self) -> KeycloakDeleteResultDTO:
        """Clear the failed login counters of every user in the realm.

        Args:
            (none)

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "clear_all_brute_force",
                "delete",
                "/attack-detection/brute-force/users",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
