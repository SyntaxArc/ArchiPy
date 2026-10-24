"""Keycloak port mixins for client scope operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.client_scope_dtos import (
        KeycloakClientScopeDTO,
        KeycloakClientScopeRequestDTO,
        KeycloakProtocolMapperDTO,
        KeycloakProtocolMapperRequestDTO,
    )
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakCreateResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )


class KeycloakClientScopesPort:
    """Sync Keycloak port interface for client scope operations."""

    @abstractmethod
    def get_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope(self, client_scope_id: str) -> KeycloakClientScopeDTO:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_by_name(self, client_scope_name: str) -> KeycloakClientScopeDTO | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    def create_client_scope(
        self,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_scope(self, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client_scope(self, client_scope_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_mapper_from_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_mapper_to_client(
        self,
        client_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_mappers_from_client(self, client_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    def update_client_mapper(
        self,
        client_id: str,
        mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> KeycloakDeleteResultDTO:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_default_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_optional_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_default_default_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_default_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_default_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    def get_default_optional_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    def add_default_optional_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    def delete_default_optional_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm optional default client scope."""
        raise NotImplementedError


class AsyncKeycloakClientScopesPort:
    """Async Keycloak port interface for client scope operations."""

    @abstractmethod
    async def get_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get all client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope(self, client_scope_id: str) -> KeycloakClientScopeDTO:
        """Get a client scope by ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_by_name(self, client_scope_name: str) -> KeycloakClientScopeDTO | None:
        """Get a client scope by name."""
        raise NotImplementedError

    @abstractmethod
    async def create_client_scope(
        self,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> str:
        """Create a new client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_scope(self, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client_scope(self, client_scope_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper in a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_mapper_from_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Delete a protocol mapper from a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_mapper_to_client(
        self,
        client_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_mappers_from_client(self, client_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_mapper(
        self,
        client_id: str,
        mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper on a client."""
        raise NotImplementedError

    @abstractmethod
    async def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> KeycloakDeleteResultDTO:
        """Remove a protocol mapper from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_default_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get default client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add a default client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a default client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_optional_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get optional client scopes for a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add an optional client scope to a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove an optional client scope from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_default_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_default_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_default_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def get_default_optional_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm optional default client scopes."""
        raise NotImplementedError

    @abstractmethod
    async def add_default_optional_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm optional default client scope."""
        raise NotImplementedError

    @abstractmethod
    async def delete_default_optional_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm optional default client scope."""
        raise NotImplementedError
