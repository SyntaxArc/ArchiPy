"""Keycloak port mixins for protocol mapper operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.protocol_mapper_dtos import (
    KeycloakProtocolMapperDTO,
    KeycloakProtocolMapperRequestDTO,
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

    @abstractmethod
    def get_client_scope_protocol_mapper(self, client_scope_id: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client scope."""
        raise NotImplementedError

    @abstractmethod
    def add_client_scope_protocol_mappers(
        self,
        client_scope_id: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client scope in one call."""
        raise NotImplementedError

    @abstractmethod
    def get_client_scope_protocol_mappers_by_protocol(
        self,
        client_scope_id: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client scope for one protocol."""
        raise NotImplementedError

    @abstractmethod
    def get_client_protocol_mapper(self, client_uuid: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client."""
        raise NotImplementedError

    @abstractmethod
    def add_client_protocol_mappers(
        self,
        client_uuid: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client in one call."""
        raise NotImplementedError

    @abstractmethod
    def get_client_protocol_mappers_by_protocol(
        self,
        client_uuid: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client for one protocol."""
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

    @abstractmethod
    async def get_client_scope_protocol_mapper(self, client_scope_id: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client scope."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_scope_protocol_mappers(
        self,
        client_scope_id: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client scope in one call."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_scope_protocol_mappers_by_protocol(
        self,
        client_scope_id: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client scope for one protocol."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_protocol_mapper(self, client_uuid: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client."""
        raise NotImplementedError

    @abstractmethod
    async def add_client_protocol_mappers(
        self,
        client_uuid: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client in one call."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_protocol_mappers_by_protocol(
        self,
        client_uuid: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client for one protocol."""
        raise NotImplementedError
