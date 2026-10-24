"""Keycloak adapter mixins for roles addressed by id."""

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
    to_wire_roles,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.management_permission_dtos import (
    KeycloakManagementPermissionDTO,
    KeycloakManagementPermissionRequestDTO,
)
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleRequestDTO


class KeycloakRolesByIdMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for roles addressed by id."""

    def get_role_by_id(self, role_id: str) -> KeycloakRoleDTO:
        """Get a role by its id.

        Args:
            role_id: Role identifier.

        Returns:
            The role.
        """
        return to_dto(
            KeycloakRoleDTO,
            self._admin_request(
                "get_role_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_role_by_id(
        self,
        role_id: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a role by its id.

        Args:
            role_id: Role identifier.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_role_by_id",
                "put",
                f"/roles-by-id/{segment(role_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_role_by_id(self, role_id: str) -> KeycloakDeleteResultDTO:
        """Delete a role by its id.

        Args:
            role_id: Role identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_role_by_id",
                "delete",
                f"/roles-by-id/{segment(role_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_role_composites_by_id(self, role_id: str, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List the composite children of a role.

        Args:
            role_id: Role identifier.
            query: Optional ``search``, ``first`` and ``max``.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_role_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite role.

        Args:
            role_id: Role identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_role_composites_by_id",
                "post",
                f"/roles-by-id/{segment(role_id)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite role.

        Args:
            role_id: Role identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_role_composites_by_id",
                "delete",
                f"/roles-by-id/{segment(role_id)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_role_client_composites_by_id(self, role_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a role that belong to a client.

        Args:
            role_id: Role identifier.
            client_uuid: Client UUID.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_role_client_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_role_realm_composites_by_id(self, role_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a role.

        Args:
            role_id: Role identifier.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_role_realm_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_role_management_permissions_by_id(self, role_id: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a role.

        Args:
            role_id: Role identifier.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_role_management_permissions_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_role_management_permissions_by_id(
        self,
        role_id: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a role.

        Args:
            role_id: Role identifier.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_role_management_permissions_by_id",
                "put",
                f"/roles-by-id/{segment(role_id)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakRolesByIdMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for roles addressed by id."""

    async def get_role_by_id(self, role_id: str) -> KeycloakRoleDTO:
        """Get a role by its id.

        Args:
            role_id: Role identifier.

        Returns:
            The role.
        """
        return to_dto(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_role_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_role_by_id(
        self,
        role_id: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a role by its id.

        Args:
            role_id: Role identifier.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_role_by_id",
                "put",
                f"/roles-by-id/{segment(role_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_role_by_id(self, role_id: str) -> KeycloakDeleteResultDTO:
        """Delete a role by its id.

        Args:
            role_id: Role identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_role_by_id",
                "delete",
                f"/roles-by-id/{segment(role_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_role_composites_by_id(
        self,
        role_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a role.

        Args:
            role_id: Role identifier.
            query: Optional ``search``, ``first`` and ``max``.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_role_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite role.

        Args:
            role_id: Role identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_role_composites_by_id",
                "post",
                f"/roles-by-id/{segment(role_id)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite role.

        Args:
            role_id: Role identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_role_composites_by_id",
                "delete",
                f"/roles-by-id/{segment(role_id)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_role_client_composites_by_id(self, role_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a role that belong to a client.

        Args:
            role_id: Role identifier.
            client_uuid: Client UUID.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_role_client_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_role_realm_composites_by_id(self, role_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a role.

        Args:
            role_id: Role identifier.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_role_realm_composites_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_role_management_permissions_by_id(self, role_id: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a role.

        Args:
            role_id: Role identifier.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_role_management_permissions_by_id",
                "get",
                f"/roles-by-id/{segment(role_id)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_role_management_permissions_by_id(
        self,
        role_id: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a role.

        Args:
            role_id: Role identifier.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_role_management_permissions_by_id",
                "put",
                f"/roles-by-id/{segment(role_id)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )
