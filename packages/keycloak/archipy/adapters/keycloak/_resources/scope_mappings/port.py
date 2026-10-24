"""Keycloak port mixins for scope mappings."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import KeycloakAssignResultDTO, KeycloakDeleteResultDTO
    from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleMappingsDTO


class KeycloakScopeMappingsPort:
    """Sync Keycloak port interface for scope mappings."""

    @abstractmethod
    def get_client_scope_scope_mappings(self, client_scope_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_realm_scope_mappings(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_realm_scope_mappings_available(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_realm_scope_mappings_composite(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_client_scope_mappings(self, client_scope_id: str, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_client_scope_mappings_available(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_client_scope_mappings_composite(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_mappings(self, client_uuid: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_realm_scope_mappings(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_client_realm_scope_mappings_available(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_client_realm_scope_mappings_composite(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_client_scope_mappings(self, client_uuid: str, owner_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are assigned."""
        raise NotImplementedError

    @abstractmethod
    def get_client_client_scope_mappings_available(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    def get_client_client_scope_mappings_composite(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    def add_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client."""
        raise NotImplementedError


class AsyncKeycloakScopeMappingsPort:
    """Async Keycloak port interface for scope mappings."""

    @abstractmethod
    async def get_client_scope_scope_mappings(self, client_scope_id: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_realm_scope_mappings(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_realm_scope_mappings_available(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_realm_scope_mappings_composite(self, client_scope_id: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client scope that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_scope_realm_scope_mappings(
        self,
        client_scope_id: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_client_scope_mappings_available(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_client_scope_mappings_composite(
        self,
        client_scope_id: str,
        client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client scope that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_scope_client_scope_mappings(
        self,
        client_scope_id: str,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_mappings(self, client_uuid: str) -> KeycloakRoleMappingsDTO:
        """Get all realm and client scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_realm_scope_mappings(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_realm_scope_mappings_available(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_realm_scope_mappings_composite(self, client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the realm roles of a client that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add realm roles to the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_realm_scope_mappings(
        self,
        client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove realm roles from the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_client_scope_mappings(self, client_uuid: str, owner_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are assigned."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_client_scope_mappings_available(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are available to assign."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_client_scope_mappings_composite(
        self,
        client_uuid: str,
        owner_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the client roles of a client that are effective (including composite roles)."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add client roles to the scope mappings of a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_client_scope_mappings(
        self,
        client_uuid: str,
        owner_client_uuid: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove client roles from the scope mappings of a client."""
        raise NotImplementedError
