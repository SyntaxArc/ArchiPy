"""Keycloak port mixins for roles addressed by id."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
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


class KeycloakRolesByIdPort:
    """Sync Keycloak port interface for roles addressed by id."""

    @abstractmethod
    def get_role_by_id(self, role_id: str) -> KeycloakRoleDTO:
        """Get a role by its id."""
        raise NotImplementedError

    @abstractmethod
    def update_role_by_id(
        self,
        role_id: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a role by its id."""
        raise NotImplementedError

    @abstractmethod
    def delete_role_by_id(self, role_id: str) -> KeycloakDeleteResultDTO:
        """Delete a role by its id."""
        raise NotImplementedError

    @abstractmethod
    def get_role_composites_by_id(self, role_id: str, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List the composite children of a role."""
        raise NotImplementedError

    @abstractmethod
    def add_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    def delete_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite role."""
        raise NotImplementedError

    @abstractmethod
    def get_role_client_composites_by_id(self, role_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_role_realm_composites_by_id(self, role_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a role."""
        raise NotImplementedError

    @abstractmethod
    def get_role_management_permissions_by_id(self, role_id: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a role."""
        raise NotImplementedError

    @abstractmethod
    def update_role_management_permissions_by_id(
        self,
        role_id: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a role."""
        raise NotImplementedError


class AsyncKeycloakRolesByIdPort:
    """Async Keycloak port interface for roles addressed by id."""

    @abstractmethod
    async def get_role_by_id(self, role_id: str) -> KeycloakRoleDTO:
        """Get a role by its id."""
        raise NotImplementedError

    @abstractmethod
    async def update_role_by_id(
        self,
        role_id: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a role by its id."""
        raise NotImplementedError

    @abstractmethod
    async def delete_role_by_id(self, role_id: str) -> KeycloakDeleteResultDTO:
        """Delete a role by its id."""
        raise NotImplementedError

    @abstractmethod
    async def get_role_composites_by_id(
        self,
        role_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a role."""
        raise NotImplementedError

    @abstractmethod
    async def add_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def delete_role_composites_by_id(
        self,
        role_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite role."""
        raise NotImplementedError

    @abstractmethod
    async def get_role_client_composites_by_id(self, role_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a role that belong to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_role_realm_composites_by_id(self, role_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a role."""
        raise NotImplementedError

    @abstractmethod
    async def get_role_management_permissions_by_id(self, role_id: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a role."""
        raise NotImplementedError

    @abstractmethod
    async def update_role_management_permissions_by_id(
        self,
        role_id: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a role."""
        raise NotImplementedError
