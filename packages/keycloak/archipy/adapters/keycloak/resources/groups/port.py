"""Keycloak port mixins for group operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakGroupsCountDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO, KeycloakGroupRequestDTO
    from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO
    from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO


class KeycloakGroupsPort:
    """Sync Keycloak port interface for group operations."""

    @abstractmethod
    # Group Operations
    @abstractmethod
    def create_group(
        self,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
        parent: str | None = None,
        skip_exists: bool = False,
    ) -> str | None:
        """Create a new group."""
        raise NotImplementedError

    @abstractmethod
    def update_group(
        self,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group(self, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group(
        self,
        group_id: str,
        full_hierarchy: bool = False,
        query: dict[str, Any] | None = None,
    ) -> KeycloakGroupDTO:
        """Get group representation by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_group_by_path(self, path: str) -> KeycloakGroupDTO:
        """Get group representation by path."""
        raise NotImplementedError

    @abstractmethod
    def get_group_children(
        self,
        group_id: str,
        query: dict[str, Any] | None = None,
        full_hierarchy: bool = False,
    ) -> list[KeycloakGroupDTO]:
        """Get child groups of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_groups(self, query: dict[str, Any] | None = None, full_hierarchy: bool = False) -> list[KeycloakGroupDTO]:
        """Get all groups, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    def get_subgroups(self, group: KeycloakGroupDTO | dict[str, Any], path: str) -> KeycloakGroupDTO | None:
        """Get subgroups for a group at the given path."""
        raise NotImplementedError

    @abstractmethod
    def groups_count(self, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Get the number of groups matching the query."""
        raise NotImplementedError

    @abstractmethod
    def group_user_add(self, user_id: str, group_id: str) -> KeycloakAssignResultDTO:
        """Add a user to a group."""
        raise NotImplementedError

    @abstractmethod
    def group_user_remove(self, user_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from a group."""
        raise NotImplementedError

    @abstractmethod
    def group_set_permissions(self, group_id: str, enabled: bool = True) -> KeycloakUpdateResultDTO:
        """Enable or disable fine-grained permissions for a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_members(self, group_id: str, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """Get members of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_client_roles(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """Get client roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[KeycloakRoleDTO]:
        """Get realm roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    def assign_group_client_roles(
        self,
        group_id: str,
        client_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to a group."""
        raise NotImplementedError

    @abstractmethod
    def assign_group_realm_roles(
        self,
        group_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group_client_roles(
        self,
        group_id: str,
        client_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from a group."""
        raise NotImplementedError

    @abstractmethod
    def delete_group_realm_roles(
        self,
        group_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from a group."""
        raise NotImplementedError

    @abstractmethod
    def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[KeycloakRoleDTO]:
        """Get composite client roles of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[KeycloakGroupDTO]:
        """Get groups that have a specific client role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_groups(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
        brief_representation: bool = True,
    ) -> list[KeycloakGroupDTO]:
        """Get groups that have a specific realm role."""
        raise NotImplementedError


class AsyncKeycloakGroupsPort:
    """Async Keycloak port interface for group operations."""

    @abstractmethod
    # Group Operations
    @abstractmethod
    async def create_group(
        self,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
        parent: str | None = None,
        skip_exists: bool = False,
    ) -> str | None:
        """Create a new group."""
        raise NotImplementedError

    @abstractmethod
    async def update_group(
        self,
        group_id: str,
        payload: KeycloakGroupRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group(self, group_id: str) -> KeycloakDeleteResultDTO:
        """Delete a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group(
        self,
        group_id: str,
        full_hierarchy: bool = False,
        query: dict[str, Any] | None = None,
    ) -> KeycloakGroupDTO:
        """Get group representation by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_by_path(self, path: str) -> KeycloakGroupDTO:
        """Get group representation by path."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_children(
        self,
        group_id: str,
        query: dict[str, Any] | None = None,
        full_hierarchy: bool = False,
    ) -> list[KeycloakGroupDTO]:
        """Get child groups of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_groups(
        self,
        query: dict[str, Any] | None = None,
        full_hierarchy: bool = False,
    ) -> list[KeycloakGroupDTO]:
        """Get all groups, optionally filtered by query."""
        raise NotImplementedError

    @abstractmethod
    async def get_subgroups(self, group: KeycloakGroupDTO | dict[str, Any], path: str) -> KeycloakGroupDTO | None:
        """Get subgroups for a group at the given path."""
        raise NotImplementedError

    @abstractmethod
    async def groups_count(self, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Get the number of groups matching the query."""
        raise NotImplementedError

    @abstractmethod
    async def group_user_add(self, user_id: str, group_id: str) -> KeycloakAssignResultDTO:
        """Add a user to a group."""
        raise NotImplementedError

    @abstractmethod
    async def group_user_remove(self, user_id: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from a group."""
        raise NotImplementedError

    @abstractmethod
    async def group_set_permissions(self, group_id: str, enabled: bool = True) -> KeycloakUpdateResultDTO:
        """Enable or disable fine-grained permissions for a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_members(self, group_id: str, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """Get members of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_client_roles(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """Get client roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[KeycloakRoleDTO]:
        """Get realm roles assigned to a group."""
        raise NotImplementedError

    @abstractmethod
    async def assign_group_client_roles(
        self,
        group_id: str,
        client_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakAssignResultDTO:
        """Assign client roles to a group."""
        raise NotImplementedError

    @abstractmethod
    async def assign_group_realm_roles(
        self,
        group_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakAssignResultDTO:
        """Assign realm roles to a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group_client_roles(
        self,
        group_id: str,
        client_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from a group."""
        raise NotImplementedError

    @abstractmethod
    async def delete_group_realm_roles(
        self,
        group_id: str,
        roles: str | KeycloakRoleDTO | list[str] | list[KeycloakRoleDTO],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[KeycloakRoleDTO]:
        """Get composite client roles of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[KeycloakGroupDTO]:
        """Get groups that have a specific client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_groups(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
        brief_representation: bool = True,
    ) -> list[KeycloakGroupDTO]:
        """Get groups that have a specific realm role."""
        raise NotImplementedError
