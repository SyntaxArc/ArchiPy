"""Keycloak port mixins for client scope operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakClientScopesPort:
    """Sync Keycloak port interface for client scope operations."""

    @abstractmethod
    def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_default_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_optional_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        raise NotImplementedError


class AsyncKeycloakClientScopesPort:
    """Async Keycloak port interface for client scope operations."""

    @abstractmethod
    async def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    async def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        raise NotImplementedError
