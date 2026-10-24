"""Keycloak port mixins for role operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO
    from archipy.models.dtos.keycloak.management_permission_dtos import (
        KeycloakManagementPermissionDTO,
        KeycloakManagementPermissionRequestDTO,
    )
    from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleRequestDTO
    from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO


class KeycloakRolesPort:
    """Sync Keycloak port interface for role operations."""

    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleDTO]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """Get client-specific roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role."""
        raise NotImplementedError

    @abstractmethod
    def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        raise NotImplementedError

    @abstractmethod
    def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user."""
        raise NotImplementedError

    @abstractmethod
    def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user."""
        raise NotImplementedError

    @abstractmethod
    def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role(self, role_name: str) -> KeycloakRoleDTO:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_roles(self) -> list[KeycloakRoleDTO]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
        """Create a new realm role."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role."""
        raise NotImplementedError

    @abstractmethod
    def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
        """Create a new client role."""
        raise NotImplementedError

    @abstractmethod
    def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    def get_composite_realm_roles(self, role_name: str) -> list[KeycloakRoleDTO] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_roles_filtered(self, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List realm roles, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_role(
        self,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_users_with_realm_role(self, role_name: str, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List the users that have a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_groups_with_realm_role(self, role_name: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups that have a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_realm_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_client_composites(self, role_name: str, target_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    def add_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite realm role."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_role_management_permissions(self, role_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a realm role."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_role_management_permissions(
        self,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_roles_filtered(self, client_uuid: str, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List client roles, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def update_client_role(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_by_name(self, client_uuid: str, role_name: str) -> KeycloakRoleDTO:
        """Get a client role by its name."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_role(self, client_uuid: str, role_name: str) -> KeycloakDeleteResultDTO:
        """Delete a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_users_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_groups_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_realm_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a client role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_client_composites(
        self,
        client_uuid: str,
        role_name: str,
        target_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite client role."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite client role."""
        raise NotImplementedError

    @abstractmethod
    def get_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
    ) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client role."""
        raise NotImplementedError

    @abstractmethod
    def update_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client role."""
        raise NotImplementedError


class AsyncKeycloakRolesPort:
    """Async Keycloak port interface for role operations."""

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleDTO]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """Get client-specific roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    async def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role."""
        raise NotImplementedError

    @abstractmethod
    async def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    async def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all of the specified roles."""
        raise NotImplementedError

    @abstractmethod
    async def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user."""
        raise NotImplementedError

    @abstractmethod
    async def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user."""
        raise NotImplementedError

    @abstractmethod
    async def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user."""
        raise NotImplementedError

    @abstractmethod
    async def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role(self, role_name: str) -> KeycloakRoleDTO:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_roles(self) -> list[KeycloakRoleDTO]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
        """Create a new realm role."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
        """Create a new client role."""
        raise NotImplementedError

    @abstractmethod
    async def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def get_composite_realm_roles(self, role_name: str) -> list[KeycloakRoleDTO] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_roles_filtered(self, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List realm roles, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_role(
        self,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_users_with_realm_role(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_groups_with_realm_role(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_realm_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_client_composites(self, role_name: str, target_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite realm role."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_role_management_permissions(self, role_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_role_management_permissions(
        self,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_roles_filtered(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List client roles, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_role(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_by_name(self, client_uuid: str, role_name: str) -> KeycloakRoleDTO:
        """Get a client role by its name."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_role(self, client_uuid: str, role_name: str) -> KeycloakDeleteResultDTO:
        """Delete a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_users_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_groups_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_realm_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_client_composites(
        self,
        client_uuid: str,
        role_name: str,
        target_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite client role."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite client role."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
    ) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client role."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client role."""
        raise NotImplementedError
