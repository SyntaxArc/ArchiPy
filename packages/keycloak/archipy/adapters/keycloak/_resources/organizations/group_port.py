"""Keycloak port mixins for organization group operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakCreateResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO, KeycloakGroupRequestDTO
    from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleMappingsDTO
    from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO


class KeycloakOrganizationGroupsPort:
    """Sync Keycloak port interface for organization group operations."""

    @abstractmethod
    def get_organization_groups(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups of an organization."""
        raise NotImplementedError

    @abstractmethod
    def create_organization_group(
        self,
        organization_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a top-level group in an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group(self, organization_id: str, group_id: str) -> KeycloakGroupDTO:
        """Get an organization group by id."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_by_path(self, organization_id: str, path: str) -> KeycloakGroupDTO:
        """Get an organization group by its path."""
        raise NotImplementedError

    @abstractmethod
    def update_organization_group(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an organization group."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization_group(self, organization_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization group."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_children(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the child groups of an organization group."""
        raise NotImplementedError

    @abstractmethod
    def create_organization_subgroup(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a child group under an organization group."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_members(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the members of an organization group."""
        raise NotImplementedError

    @abstractmethod
    def add_user_to_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakAssignResultDTO:
        """Add a user to an organization group."""
        raise NotImplementedError

    @abstractmethod
    def remove_user_from_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization group."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_member_groups(
        self,
        organization_id: str,
        member_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups a member belongs to."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_idp_groups(
        self,
        organization_id: str,
        idp_alias: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_role_mappings(self, organization_id: str, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all role mappings of an organization group."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_realm_roles(self, organization_id: str, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_realm_roles_available(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_realm_roles_composite(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are effective (including composite)."""
        raise NotImplementedError

    @abstractmethod
    def assign_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to an organization group."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from an organization group."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_client_roles_available(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_group_client_roles_composite(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are effective (including composite)."""
        raise NotImplementedError

    @abstractmethod
    def assign_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to an organization group."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from an organization group."""
        raise NotImplementedError


class AsyncKeycloakOrganizationGroupsPort:
    """Async Keycloak port interface for organization group operations."""

    @abstractmethod
    async def get_organization_groups(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups of an organization."""
        raise NotImplementedError

    @abstractmethod
    async def create_organization_group(
        self,
        organization_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a top-level group in an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group(self, organization_id: str, group_id: str) -> KeycloakGroupDTO:
        """Get an organization group by id."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_by_path(self, organization_id: str, path: str) -> KeycloakGroupDTO:
        """Get an organization group by its path."""
        raise NotImplementedError

    @abstractmethod
    async def update_organization_group(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization_group(self, organization_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_children(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the child groups of an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def create_organization_subgroup(
        self,
        organization_id: str,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a child group under an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_members(
        self,
        organization_id: str,
        group_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the members of an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def add_user_to_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakAssignResultDTO:
        """Add a user to an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def remove_user_from_organization_group(
        self,
        organization_id: str,
        group_id: str,
        user_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_member_groups(
        self,
        organization_id: str,
        member_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups a member belongs to."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_idp_groups(
        self,
        organization_id: str,
        idp_alias: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the organization groups of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_role_mappings(
        self,
        organization_id: str,
        group_id: str,
    ) -> KeycloakRoleMappingsDTO:
        """Get all role mappings of an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_realm_roles(self, organization_id: str, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_realm_roles_available(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_realm_roles_composite(
        self,
        organization_id: str,
        group_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the realm roles of an organization group that are effective (including composite)."""
        raise NotImplementedError

    @abstractmethod
    async def assign_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization_group_realm_roles(
        self,
        organization_id: str,
        group_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_client_roles_available(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_group_client_roles_composite(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of an organization group that are effective (including composite)."""
        raise NotImplementedError

    @abstractmethod
    async def assign_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to an organization group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization_group_client_roles(
        self,
        organization_id: str,
        group_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from an organization group."""
        raise NotImplementedError
