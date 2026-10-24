"""Keycloak adapter mixins for scope mappings."""

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


class KeycloakScopeMappingsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for scope mappings."""

    def get_client_scope_scope_mappings(self, client_scope_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            self._admin_request(
                "get_client_scope_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_scope_realm_scope_mappings(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are assigned.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_realm_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_scope_realm_scope_mappings_available(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are available to assign.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_realm_scope_mappings_available",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_scope_realm_scope_mappings_composite(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are effective (including composite roles).

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_realm_scope_mappings_composite",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_client_scope_realm_scope_mappings",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_scope_realm_scope_mappings",
                "delete",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_scope_client_scope_mappings(self, client_scope_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are assigned.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_client_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_scope_client_scope_mappings_available(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are available to assign.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_client_scope_mappings_available",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_scope_client_scope_mappings_composite(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are effective (including composite roles).

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_scope_client_scope_mappings_composite",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_client_scope_client_scope_mappings",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_scope_client_scope_mappings",
                "delete",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_scope_mappings(self, client_uuid: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client.

        Args:
            client_uuid: Client UUID.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            self._admin_request(
                "get_client_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_realm_scope_mappings(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are assigned.

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_realm_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_realm_scope_mappings_available(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are available to assign.

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_realm_scope_mappings_available",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_realm_scope_mappings_composite(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are effective (including composite roles).

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_realm_scope_mappings_composite",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_client_realm_scope_mappings",
                "post",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_realm_scope_mappings",
                "delete",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_client_scope_mappings(self, client_uuid: str, owner_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are assigned.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_client_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_client_scope_mappings_available(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are available to assign.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_client_scope_mappings_available",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_client_scope_mappings_composite(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are effective (including composite roles).

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_client_scope_mappings_composite",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_client_client_scope_mappings",
                "post",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_client_scope_mappings",
                "delete",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakScopeMappingsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for scope mappings."""

    async def get_client_scope_scope_mappings(self, client_scope_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            await self._async_admin_request(
                "get_client_scope_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_scope_realm_scope_mappings(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are assigned.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_realm_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_scope_realm_scope_mappings_available(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are available to assign.

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_realm_scope_mappings_available",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_scope_realm_scope_mappings_composite(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are effective (including composite roles).

        Args:
            client_scope_id: Client scope identifier.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_realm_scope_mappings_composite",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_client_scope_realm_scope_mappings",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_scope_realm_scope_mappings",
                "delete",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are assigned.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_client_scope_mappings",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_scope_client_scope_mappings_available(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are available to assign.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_client_scope_mappings_available",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_scope_client_scope_mappings_composite(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are effective (including composite roles).

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_scope_client_scope_mappings_composite",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_client_scope_client_scope_mappings",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            client_uuid: UUID of the client that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_scope_client_scope_mappings",
                "delete",
                f"/client-scopes/{segment(client_scope_id)}/scope-mappings/clients/{segment(client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_scope_mappings(self, client_uuid: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client.

        Args:
            client_uuid: Client UUID.

        Returns:
            The realm and client mappings.
        """
        return to_dto(
            KeycloakRoleMappingsDTO,
            await self._async_admin_request(
                "get_client_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_realm_scope_mappings(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are assigned.

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_realm_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_realm_scope_mappings_available(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are available to assign.

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_realm_scope_mappings_available",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_realm_scope_mappings_composite(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are effective (including composite roles).

        Args:
            client_uuid: Client UUID.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_realm_scope_mappings_composite",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_client_realm_scope_mappings",
                "post",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_realm_scope_mappings",
                "delete",
                f"/clients/{segment(client_uuid)}/scope-mappings/realm",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_client_scope_mappings(self, client_uuid: str, owner_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are assigned.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_client_scope_mappings",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_client_scope_mappings_available(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are available to assign.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_client_scope_mappings_available",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}/available",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_client_scope_mappings_composite(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are effective (including composite roles).

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_client_scope_mappings_composite",
                "get",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}/composite",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_client_client_scope_mappings",
                "post",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client.

        Args:
            client_uuid: Client UUID.
            owner_client_uuid: UUID of the client that owns the roles.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_client_scope_mappings",
                "delete",
                f"/clients/{segment(client_uuid)}/scope-mappings/clients/{segment(owner_client_uuid)}",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
