"""Keycloak port mixins for protocol mapper operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakCreateResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.protocol_mapper_dtos import (
        KeycloakProtocolMapperDTO,
        KeycloakProtocolMapperRequestDTO,
    )


class KeycloakProtocolMappersPort:
    """Sync Keycloak port interface for protocol mapper operations."""

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


class AsyncKeycloakProtocolMappersPort:
    """Async Keycloak port interface for protocol mapper operations."""

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
