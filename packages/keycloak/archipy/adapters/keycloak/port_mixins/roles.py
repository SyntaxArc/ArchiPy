"""Keycloak port mixins for role operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.adapters.keycloak.port_mixins._shared import (
        KeycloakRoleType,
    )


class KeycloakRolesPort:
    """Sync Keycloak port interface for role operations."""

    @abstractmethod
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleType]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
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
    def get_realm_role(self, role_name: str) -> dict[str, Any]:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
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
    ) -> dict[str, Any] | None:
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
    def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError


class AsyncKeycloakRolesPort:
    """Async Keycloak port interface for role operations."""

    @abstractmethod
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleType]:
        """Get roles assigned to a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
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
    async def get_realm_role(self, role_name: str) -> dict[str, Any]:
        """Get realm role."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_roles(self) -> list[dict[str, Any]]:
        """Get all realm roles."""
        raise NotImplementedError

    @abstractmethod
    async def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
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
    ) -> dict[str, Any] | None:
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
    async def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role."""
        raise NotImplementedError
