"""Keycloak port mixins for role mappings."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import KeycloakAssignResultDTO, KeycloakDeleteResultDTO
    from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleMappingsDTO


class KeycloakRoleMappingsPort:
    """Sync Keycloak port interface for role mappings."""

    @abstractmethod
    def get_user_role_mappings(self, user_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    def get_user_realm_role_mappings(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_user_realm_role_mappings_available(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_user_realm_role_mappings_composite(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    def delete_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    def get_user_client_role_mappings(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_user_client_role_mappings_available(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_user_client_role_mappings_composite(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    def delete_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    def get_group_role_mappings(self, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a group."""
        raise NotImplementedError

    @abstractmethod
    def get_group_realm_role_mappings_available(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_group_realm_role_mappings_composite(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def get_group_client_role_mappings_available(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a group that are available to assign."""
        raise NotImplementedError


class AsyncKeycloakRoleMappingsPort:
    """Async Keycloak port interface for role mappings."""

    @abstractmethod
    async def get_user_role_mappings(self, user_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_realm_role_mappings(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_realm_role_mappings_available(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_realm_role_mappings_composite(self, user_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a user that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user_realm_role_mappings(
        self,
        user_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_client_role_mappings(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_client_role_mappings_available(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_client_role_mappings_composite(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a user that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user_client_role_mappings(
        self,
        user_id: str,
        client_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the role mappings of a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_role_mappings(self, group_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client role mappings of a group."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_realm_role_mappings_available(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_realm_role_mappings_composite(self, group_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a group that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def get_group_client_role_mappings_available(self, group_id: str, client_id: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a group that are available to assign."""
        raise NotImplementedError
