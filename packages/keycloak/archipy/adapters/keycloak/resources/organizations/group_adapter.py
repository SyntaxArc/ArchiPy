"""Keycloak adapter mixins for organization group operations."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any
from urllib.parse import quote

from archipy.adapters.keycloak.base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    payload_value,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
    to_wire_roles,
    with_created_id,
    with_created_id_async,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO, KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleMappingsDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO


class KeycloakOrganizationGroupsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for organization group operations."""

    def _find_organization_group_id(self, organization_id: str, path: str) -> str | None:
        """Return the id of the organization group at ``path``."""
        return self.get_organization_group_by_path(organization_id, path).id

    def _find_organization_subgroup_id(self, organization_id: str, group_id: str, name: str | None) -> str | None:
        """Return the id of the child group ``name`` of an organization group."""
        children = self.get_organization_group_children(organization_id, group_id)
        return next((child.id for child in children if child.name == name), None)

    def get_organization_groups(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups of an organization.

        Args:
            organization_id: Organization identifier.
            query: Optional query parameters such as ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_groups",
                "get",
                f"/organizations/{segment(organization_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def create_organization_group(
        self,
        organization_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a top-level group in an organization.

        Args:
            organization_id: Organization identifier.
            payload: Group representation.

        Returns:
            The create result with the id of the new group.
        """
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._admin_request(
                    "create_organization_group",
                    "post",
                    f"/organizations/{segment(organization_id)}/groups",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_organization_group_id(
                organization_id,
                "/" + (payload_value(payload, "name", "name") or ""),
            ),
        )

    def get_organization_group(self, organization_id: str, group_id: str) -> KeycloakGroupDTO:
        """Get an organization group by id.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The group.
        """
        return to_dto(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_group",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_by_path(self, organization_id: str, path: str) -> KeycloakGroupDTO:
        """Get an organization group by its path.

        Args:
            organization_id: Organization identifier.
            path: Group path, such as ``/team/sub``.

        Returns:
            The group.
        """
        return to_dto(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_group_by_path",
                "get",
                f"/organizations/{segment(organization_id)}/groups/group-by-path/{quote(path.lstrip('/'), safe='/')}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_organization_group(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            payload: Group representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_organization_group",
                "put",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_organization_group(self, organization_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_organization_group",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organization_group_children(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the child groups of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            query: Optional query parameters.

        Returns:
            The child groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_group_children",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/children",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def create_organization_subgroup(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a child group under an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            payload: Group representation.

        Returns:
            The create result with the id of the new group.
        """
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._admin_request(
                    "create_organization_subgroup",
                    "post",
                    f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/children",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_organization_subgroup_id(
                organization_id,
                group_id,
                payload_value(payload, "name", "name"),
            ),
        )

    def get_organization_group_members(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the members of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            query: Optional query parameters.

        Returns:
            The members.
        """
        return to_dto_list(
            KeycloakUserDTO,
            self._admin_request(
                "get_organization_group_members",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_user_to_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakAssignResultDTO:
        """Add a user to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            user_id: User identifier.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_user_to_organization_group",
                "put",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def remove_user_from_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            user_id: User identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "remove_user_from_organization_group",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organization_member_groups(
        self,
        organization_id: str,
        member_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups a member belongs to.

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.
            query: Optional query parameters.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_member_groups",
                "get",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_idp_groups(
        self,
        organization_id: str,
        idp_alias: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups of an identity provider.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.
            query: Optional query parameters.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_organization_idp_groups",
                "get",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_role_mappings(self, organization_id: str, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all role mappings of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The realm and client role mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            self._admin_request(
                "get_organization_group_role_mappings",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_realm_roles(self, organization_id: str, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are assigned.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_realm_roles",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_realm_roles_available(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are available to assign.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_realm_roles_available",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_realm_roles_composite(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are effective (including composite).

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_realm_roles_composite",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def assign_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            roles: Roles to assign.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "assign_organization_group_realm_roles",
                "post",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_organization_group_realm_roles",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are assigned.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_client_roles",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_client_roles_available(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are available to assign.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_client_roles_available",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_group_client_roles_composite(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are effective (including composite).

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_organization_group_client_roles_composite",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def assign_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.
            roles: Roles to assign.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "assign_organization_group_client_roles",
                "post",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_organization_group_client_roles",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakOrganizationGroupsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for organization group operations."""

    async def _find_organization_group_id(self, organization_id: str, path: str) -> str | None:
        """Return the id of the organization group at ``path``."""
        return (await self.get_organization_group_by_path(organization_id, path)).id

    async def _find_organization_subgroup_id(
        self,
        organization_id: str,
        group_id: str,
        name: str | None,
    ) -> str | None:
        """Return the id of the child group ``name`` of an organization group."""
        children = await self.get_organization_group_children(organization_id, group_id)
        return next((child.id for child in children if child.name == name), None)

    async def get_organization_groups(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups of an organization.

        Args:
            organization_id: Organization identifier.
            query: Optional query parameters such as ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_groups",
                "get",
                f"/organizations/{segment(organization_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def create_organization_group(
        self,
        organization_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a top-level group in an organization.

        Args:
            organization_id: Organization identifier.
            payload: Group representation.

        Returns:
            The create result with the id of the new group.
        """
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_admin_request(
                    "create_organization_group",
                    "post",
                    f"/organizations/{segment(organization_id)}/groups",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_organization_group_id(
                organization_id,
                "/" + (payload_value(payload, "name", "name") or ""),
            ),
        )

    async def get_organization_group(self, organization_id: str, group_id: str) -> KeycloakGroupDTO:
        """Get an organization group by id.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The group.
        """
        return to_dto(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_group",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_by_path(self, organization_id: str, path: str) -> KeycloakGroupDTO:
        """Get an organization group by its path.

        Args:
            organization_id: Organization identifier.
            path: Group path, such as ``/team/sub``.

        Returns:
            The group.
        """
        return to_dto(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_group_by_path",
                "get",
                f"/organizations/{segment(organization_id)}/groups/group-by-path/{quote(path.lstrip('/'), safe='/')}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_organization_group(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            payload: Group representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_organization_group",
                "put",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_organization_group(self, organization_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_organization_group",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organization_group_children(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the child groups of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            query: Optional query parameters.

        Returns:
            The child groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_group_children",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/children",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def create_organization_subgroup(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a child group under an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            payload: Group representation.

        Returns:
            The create result with the id of the new group.
        """
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_admin_request(
                    "create_organization_subgroup",
                    "post",
                    f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/children",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_organization_subgroup_id(
                organization_id,
                group_id,
                payload_value(payload, "name", "name"),
            ),
        )

    async def get_organization_group_members(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the members of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            query: Optional query parameters.

        Returns:
            The members.
        """
        return to_dto_list(
            KeycloakUserDTO,
            await self._async_admin_request(
                "get_organization_group_members",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_user_to_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakAssignResultDTO:
        """Add a user to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            user_id: User identifier.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_user_to_organization_group",
                "put",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def remove_user_from_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            user_id: User identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "remove_user_from_organization_group",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/members/{segment(user_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organization_member_groups(
        self,
        organization_id: str,
        member_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups a member belongs to.

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.
            query: Optional query parameters.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_member_groups",
                "get",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_idp_groups(
        self,
        organization_id: str,
        idp_alias: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups of an identity provider.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.
            query: Optional query parameters.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_organization_idp_groups",
                "get",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_role_mappings(
        self,
        organization_id: str,
        group_id: str,
    ) -> KeycloakRoleMappingsDTO:
        """Get all role mappings of an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The realm and client role mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            await self._async_admin_request(
                "get_organization_group_role_mappings",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_realm_roles(self, organization_id: str, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are assigned.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_realm_roles",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_realm_roles_available(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are available to assign.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_realm_roles_available",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_realm_roles_composite(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are effective (including composite).

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_realm_roles_composite",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def assign_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            roles: Roles to assign.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "assign_organization_group_realm_roles",
                "post",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_organization_group_realm_roles",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are assigned.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_client_roles",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_client_roles_available(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are available to assign.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_client_roles_available",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_group_client_roles_composite(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are effective (including composite).

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_organization_group_client_roles_composite",
                "get",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def assign_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.
            roles: Roles to assign.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "assign_organization_group_client_roles",
                "post",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from an organization group.

        Args:
            organization_id: Organization identifier.
            group_id: Organization group identifier.
            client_id: Client UUID.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_organization_group_client_roles",
                "delete",
                f"/organizations/{segment(organization_id)}/groups/{segment(group_id)}/role-mappings/clients/{segment(client_id)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
