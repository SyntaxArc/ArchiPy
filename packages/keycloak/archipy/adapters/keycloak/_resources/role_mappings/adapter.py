"""Keycloak adapter mixins for role mappings."""

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
    to_wire_roles,
)
from archipy.models.dtos.keycloak.common_dtos import KeycloakAssignResultDTO, KeycloakDeleteResultDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleMappingsDTO


class KeycloakRoleMappingsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for role mappings."""

    def get_user_role_mappings(self, user_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a user.

        Args:
            user_id: User identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            self._admin_request(
                "get_user_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_realm_role_mappings(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are assigned.

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_realm_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_realm_role_mappings_available(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are available to assign.

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_realm_role_mappings_available",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_realm_role_mappings_composite(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are effective (including composite roles).

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_realm_role_mappings_composite",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the role mappings of a user.

        Args:
            user_id: User identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_user_realm_role_mappings",
                "post",
                f"/users/{segment(user_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the role mappings of a user.

        Args:
            user_id: User identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_user_realm_role_mappings",
                "delete",
                f"/users/{segment(user_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_user_client_role_mappings(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are assigned.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_client_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_client_role_mappings_available(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are available to assign.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_client_role_mappings_available",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_client_role_mappings_composite(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are effective (including composite roles).

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_user_client_role_mappings_composite",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the role mappings of a user.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_user_client_role_mappings",
                "post",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the role mappings of a user.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_user_client_role_mappings",
                "delete",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_group_role_mappings(self, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a group.

        Args:
            group_id: Group identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            self._admin_request(
                "get_group_role_mappings",
                "get",
                f"/groups/{segment(group_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_group_realm_role_mappings_available(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are available to assign.

        Args:
            group_id: Group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_group_realm_role_mappings_available",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_group_realm_role_mappings_composite(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are effective (including composite roles).

        Args:
            group_id: Group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_group_realm_role_mappings_composite",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_group_client_role_mappings_available(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a group that are available to assign.

        Args:
            group_id: Group identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_group_client_role_mappings_available",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakRoleMappingsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for role mappings."""

    async def get_user_role_mappings(self, user_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a user.

        Args:
            user_id: User identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            await self._async_admin_request(
                "get_user_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_realm_role_mappings(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are assigned.

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_realm_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_realm_role_mappings_available(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are available to assign.

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_realm_role_mappings_available",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_realm_role_mappings_composite(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are effective (including composite roles).

        Args:
            user_id: User identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_realm_role_mappings_composite",
                "get",
                f"/users/{segment(user_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the role mappings of a user.

        Args:
            user_id: User identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_user_realm_role_mappings",
                "post",
                f"/users/{segment(user_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the role mappings of a user.

        Args:
            user_id: User identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_user_realm_role_mappings",
                "delete",
                f"/users/{segment(user_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_user_client_role_mappings(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are assigned.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_client_role_mappings",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_client_role_mappings_available(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are available to assign.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_client_role_mappings_available",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_client_role_mappings_composite(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are effective (including composite roles).

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_user_client_role_mappings_composite",
                "get",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the role mappings of a user.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_user_client_role_mappings",
                "post",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the role mappings of a user.

        Args:
            user_id: User identifier.
            client_id: Client UUID that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_user_client_role_mappings",
                "delete",
                f"/users/{segment(user_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_group_role_mappings(self, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a group.

        Args:
            group_id: Group identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            await self._async_admin_request(
                "get_group_role_mappings",
                "get",
                f"/groups/{segment(group_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_group_realm_role_mappings_available(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are available to assign.

        Args:
            group_id: Group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_group_realm_role_mappings_available",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_group_realm_role_mappings_composite(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are effective (including composite roles).

        Args:
            group_id: Group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_group_realm_role_mappings_composite",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_group_client_role_mappings_available(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a group that are available to assign.

        Args:
            group_id: Group identifier.
            client_id: Client UUID that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_group_client_role_mappings_available",
                "get",
                f"/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )
