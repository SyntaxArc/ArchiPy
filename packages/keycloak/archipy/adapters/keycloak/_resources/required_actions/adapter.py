"""Keycloak adapter mixins for required actions."""

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
from archipy.models.dtos.keycloak.authenticator_dtos import KeycloakUnregisteredRequiredActionDTO
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.required_action_dtos import (
    KeycloakRequiredActionConfigDTO,
    KeycloakRequiredActionConfigInfoDTO,
    KeycloakRequiredActionConfigRequestDTO,
    KeycloakRequiredActionProviderDTO,
    KeycloakRequiredActionProviderRequestDTO,
)


class KeycloakRequiredActionsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for required actions."""

    def get_required_actions(self) -> list[KeycloakRequiredActionProviderDTO]:
        """List the required actions registered in the realm.

        Args:
            (none)

        Returns:
            The required actions.
        """
        return to_dto_list(
            KeycloakRequiredActionProviderDTO,
            self._admin_request(
                "get_required_actions",
                "get",
                "/authentication/required-actions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_required_action(self, alias: str) -> KeycloakRequiredActionProviderDTO:
        """Get a required action by alias.

        Args:
            alias: Required action alias.

        Returns:
            The required action.
        """
        return to_dto(
            KeycloakRequiredActionProviderDTO,
            self._admin_request(
                "get_required_action",
                "get",
                f"/authentication/required-actions/{segment(alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_required_action(
        self,
        alias: str,
        payload: KeycloakRequiredActionProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a required action.

        Args:
            alias: Required action alias.
            payload: Required action representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_required_action",
                "put",
                f"/authentication/required-actions/{segment(alias)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_required_action(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete a required action.

        Args:
            alias: Required action alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_required_action",
                "delete",
                f"/authentication/required-actions/{segment(alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def register_required_action(self, provider_id: str, name: str) -> KeycloakCreateResultDTO:
        """Register an unregistered required action provider in the realm.

        Args:
            provider_id: Provider id.
            name: Display name.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            self._admin_request(
                "register_required_action",
                "post",
                "/authentication/register-required-action",
                body={"providerId": provider_id, "name": name},
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    def get_unregistered_required_actions(self) -> list[KeycloakUnregisteredRequiredActionDTO]:
        """List the required action providers that are not registered in the realm.

        Args:
            (none)

        Returns:
            The unregistered providers.
        """
        return to_dto_list(
            KeycloakUnregisteredRequiredActionDTO,
            self._admin_request(
                "get_unregistered_required_actions",
                "get",
                "/authentication/unregistered-required-actions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def raise_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action up in the order.

        Args:
            alias: Required action alias.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "raise_required_action_priority",
                "post",
                f"/authentication/required-actions/{segment(alias)}/raise-priority",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def lower_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action down in the order.

        Args:
            alias: Required action alias.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "lower_required_action_priority",
                "post",
                f"/authentication/required-actions/{segment(alias)}/lower-priority",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_required_action_config(self, alias: str) -> KeycloakRequiredActionConfigDTO:
        """Get the settings of a required action.

        Args:
            alias: Required action alias.

        Returns:
            The settings.
        """
        return to_dto(
            KeycloakRequiredActionConfigDTO,
            self._admin_request(
                "get_required_action_config",
                "get",
                f"/authentication/required-actions/{segment(alias)}/config",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_required_action_config(
        self,
        alias: str,
        config: KeycloakRequiredActionConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Set the settings of a required action.

        Args:
            alias: Required action alias.
            config: The settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_required_action_config",
                "put",
                f"/authentication/required-actions/{segment(alias)}/config",
                body=to_request_payload(config),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_required_action_config(self, alias: str) -> KeycloakDeleteResultDTO:
        """Remove the settings of a required action.

        Args:
            alias: Required action alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_required_action_config",
                "delete",
                f"/authentication/required-actions/{segment(alias)}/config",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_required_action_config_description(self, alias: str) -> KeycloakRequiredActionConfigInfoDTO:
        """Describe the settings a required action accepts.

        Args:
            alias: Required action alias.

        Returns:
            The settings description.
        """
        return to_dto(
            KeycloakRequiredActionConfigInfoDTO,
            self._admin_request(
                "get_required_action_config_description",
                "get",
                f"/authentication/required-actions/{segment(alias)}/config-description",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakRequiredActionsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for required actions."""

    async def get_required_actions(self) -> list[KeycloakRequiredActionProviderDTO]:
        """List the required actions registered in the realm.

        Args:
            (none)

        Returns:
            The required actions.
        """
        return to_dto_list(
            KeycloakRequiredActionProviderDTO,
            await self._async_admin_request(
                "get_required_actions",
                "get",
                "/authentication/required-actions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_required_action(self, alias: str) -> KeycloakRequiredActionProviderDTO:
        """Get a required action by alias.

        Args:
            alias: Required action alias.

        Returns:
            The required action.
        """
        return to_dto(
            KeycloakRequiredActionProviderDTO,
            await self._async_admin_request(
                "get_required_action",
                "get",
                f"/authentication/required-actions/{segment(alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_required_action(
        self,
        alias: str,
        payload: KeycloakRequiredActionProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a required action.

        Args:
            alias: Required action alias.
            payload: Required action representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_required_action",
                "put",
                f"/authentication/required-actions/{segment(alias)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_required_action(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete a required action.

        Args:
            alias: Required action alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_required_action",
                "delete",
                f"/authentication/required-actions/{segment(alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def register_required_action(self, provider_id: str, name: str) -> KeycloakCreateResultDTO:
        """Register an unregistered required action provider in the realm.

        Args:
            provider_id: Provider id.
            name: Display name.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            await self._async_admin_request(
                "register_required_action",
                "post",
                "/authentication/register-required-action",
                body={"providerId": provider_id, "name": name},
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    async def get_unregistered_required_actions(self) -> list[KeycloakUnregisteredRequiredActionDTO]:
        """List the required action providers that are not registered in the realm.

        Args:
            (none)

        Returns:
            The unregistered providers.
        """
        return to_dto_list(
            KeycloakUnregisteredRequiredActionDTO,
            await self._async_admin_request(
                "get_unregistered_required_actions",
                "get",
                "/authentication/unregistered-required-actions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def raise_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action up in the order.

        Args:
            alias: Required action alias.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "raise_required_action_priority",
                "post",
                f"/authentication/required-actions/{segment(alias)}/raise-priority",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def lower_required_action_priority(self, alias: str) -> KeycloakUpdateResultDTO:
        """Move a required action down in the order.

        Args:
            alias: Required action alias.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "lower_required_action_priority",
                "post",
                f"/authentication/required-actions/{segment(alias)}/lower-priority",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_required_action_config(self, alias: str) -> KeycloakRequiredActionConfigDTO:
        """Get the settings of a required action.

        Args:
            alias: Required action alias.

        Returns:
            The settings.
        """
        return to_dto(
            KeycloakRequiredActionConfigDTO,
            await self._async_admin_request(
                "get_required_action_config",
                "get",
                f"/authentication/required-actions/{segment(alias)}/config",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_required_action_config(
        self,
        alias: str,
        config: KeycloakRequiredActionConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Set the settings of a required action.

        Args:
            alias: Required action alias.
            config: The settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_required_action_config",
                "put",
                f"/authentication/required-actions/{segment(alias)}/config",
                body=to_request_payload(config),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_required_action_config(self, alias: str) -> KeycloakDeleteResultDTO:
        """Remove the settings of a required action.

        Args:
            alias: Required action alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_required_action_config",
                "delete",
                f"/authentication/required-actions/{segment(alias)}/config",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_required_action_config_description(self, alias: str) -> KeycloakRequiredActionConfigInfoDTO:
        """Describe the settings a required action accepts.

        Args:
            alias: Required action alias.

        Returns:
            The settings description.
        """
        return to_dto(
            KeycloakRequiredActionConfigInfoDTO,
            await self._async_admin_request(
                "get_required_action_config_description",
                "get",
                f"/authentication/required-actions/{segment(alias)}/config-description",
                expected=(HTTPStatus.OK,),
            ),
        )
