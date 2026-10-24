"""Keycloak adapter mixins for client scope operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    payload_value,
    to_dto,
    to_dto_list,
    to_dto_or_none,
    to_mutation_result,
    to_request_payload,
    with_created_id,
    with_created_id_async,
)
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


class KeycloakClientScopesMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client scope operations."""

    def _find_scope_mapper_id(self, client_scope_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client scope."""
        return next((m.id for m in self.get_mappers_from_client_scope(client_scope_id) if m.name == name), None)

    def _find_client_mapper_id(self, client_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client."""
        return next((m.id for m in self.get_mappers_from_client(client_id) if m.name == name), None)

    def get_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get all client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_client_scopes",
                self.admin_adapter.get_client_scopes,
            ),
        )

    def get_client_scope(self, client_scope_id: str) -> KeycloakClientScopeDTO:
        """Get a client scope by ID."""
        return to_dto(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_client_scope",
                lambda: self.admin_adapter.get_client_scope(client_scope_id=client_scope_id),
            ),
        )

    def get_client_scope_by_name(self, client_scope_name: str) -> KeycloakClientScopeDTO | None:
        """Get a client scope by name."""
        return to_dto_or_none(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_client_scope_by_name",
                lambda: self.admin_adapter.get_client_scope_by_name(client_scope_name=client_scope_name),
            ),
        )

    def create_client_scope(
        self,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> str:
        """Create a new client scope."""
        return self._call_keycloak(
            "create_client_scope",
            lambda: self.admin_adapter.create_client_scope(
                payload=to_request_payload(payload),
                skip_exists=skip_exists,
            ),
        )

    def update_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client scope."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_client_scope",
                lambda: self.admin_adapter.update_client_scope(
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def delete_client_scope(self, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_client_scope",
                lambda: self.admin_adapter.delete_client_scope(client_scope_id=client_scope_id),
            ),
        )

    def add_mapper_to_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client scope."""
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._call_keycloak(
                    "add_mapper_to_client_scope",
                    lambda: self.admin_adapter.add_mapper_to_client_scope(
                        client_scope_id=client_scope_id,
                        payload=to_request_payload(payload),
                    ),
                ),
            ),
            lambda: self._find_scope_mapper_id(client_scope_id, payload_value(payload, "name", "name")),
        )

    def get_mappers_from_client_scope(self, client_scope_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client scope."""
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            self._call_keycloak(
                "get_mappers_from_client_scope",
                lambda: self.admin_adapter.get_mappers_from_client_scope(client_scope_id=client_scope_id),
            ),
        )

    def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper in a client scope."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_mapper_in_client_scope",
                lambda: self.admin_adapter.update_mapper_in_client_scope(
                    client_scope_id=client_scope_id,
                    protocol_mapper_id=protocol_mapper_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def delete_mapper_from_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Delete a protocol mapper from a client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_mapper_from_client_scope",
                lambda: self.admin_adapter.delete_mapper_from_client_scope(
                    client_scope_id=client_scope_id,
                    protocol_mapper_id=protocol_mapper_id,
                ),
            ),
        )

    def add_mapper_to_client(
        self,
        client_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client."""
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._call_keycloak(
                    "add_mapper_to_client",
                    lambda: self.admin_adapter.add_mapper_to_client(
                        client_id=client_id,
                        payload=to_request_payload(payload),
                    ),
                ),
            ),
            lambda: self._find_client_mapper_id(client_id, payload_value(payload, "name", "name")),
        )

    def get_mappers_from_client(self, client_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client."""
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            self._call_keycloak(
                "get_mappers_from_client",
                lambda: self.admin_adapter.get_mappers_from_client(client_id=client_id),
            ),
        )

    def update_client_mapper(
        self,
        client_id: str,
        mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper on a client."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_client_mapper",
                lambda: self.admin_adapter.update_client_mapper(
                    client_id=client_id,
                    mapper_id=mapper_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> KeycloakDeleteResultDTO:
        """Remove a protocol mapper from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "remove_client_mapper",
                lambda: self.admin_adapter.remove_client_mapper(client_id=client_id, client_mapper_id=client_mapper_id),
            ),
        )

    def get_client_default_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get default client scopes for a client."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_client_default_client_scopes",
                lambda: self.admin_adapter.get_client_default_client_scopes(client_id=client_id),
            ),
        )

    def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add a default client scope to a client."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._call_keycloak(
                "add_client_default_client_scope",
                lambda: self.admin_adapter.add_client_default_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a default client scope from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_client_default_client_scope",
                lambda: self.admin_adapter.delete_client_default_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                ),
            ),
        )

    def get_client_optional_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get optional client scopes for a client."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_client_optional_client_scopes",
                lambda: self.admin_adapter.get_client_optional_client_scopes(client_id=client_id),
            ),
        )

    def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add an optional client scope to a client."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._call_keycloak(
                "add_client_optional_client_scope",
                lambda: self.admin_adapter.add_client_optional_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove an optional client scope from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_client_optional_client_scope",
                lambda: self.admin_adapter.delete_client_optional_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                ),
            ),
        )

    def get_default_default_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm default client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_default_default_client_scopes",
                self.admin_adapter.get_default_default_client_scopes,
            ),
        )

    def add_default_default_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm default client scope."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._call_keycloak(
                "add_default_default_client_scope",
                lambda: self.admin_adapter.add_default_default_client_scope(scope_id=scope_id),
            ),
        )

    def delete_default_default_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm default client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_default_default_client_scope",
                lambda: self.admin_adapter.delete_default_default_client_scope(scope_id=scope_id),
            ),
        )

    def get_default_optional_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm optional default client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            self._call_keycloak(
                "get_default_optional_client_scopes",
                self.admin_adapter.get_default_optional_client_scopes,
            ),
        )

    def add_default_optional_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm optional default client scope."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._call_keycloak(
                "add_default_optional_client_scope",
                lambda: self.admin_adapter.add_default_optional_client_scope(scope_id=scope_id),
            ),
        )

    def delete_default_optional_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm optional default client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_default_optional_client_scope",
                lambda: self.admin_adapter.delete_default_optional_client_scope(scope_id=scope_id),
            ),
        )


class AsyncKeycloakClientScopesMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client scope operations."""

    async def _find_scope_mapper_id(self, client_scope_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client scope."""
        mappers = await self.get_mappers_from_client_scope(client_scope_id)
        return next((m.id for m in mappers if m.name == name), None)

    async def _find_client_mapper_id(self, client_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client."""
        mappers = await self.get_mappers_from_client(client_id)
        return next((m.id for m in mappers if m.name == name), None)

    async def get_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get all client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_client_scopes",
                self.admin_adapter.a_get_client_scopes,
            ),
        )

    async def get_client_scope(self, client_scope_id: str) -> KeycloakClientScopeDTO:
        """Get a client scope by ID."""
        return to_dto(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_client_scope",
                lambda: self.admin_adapter.a_get_client_scope(client_scope_id=client_scope_id),
            ),
        )

    async def get_client_scope_by_name(self, client_scope_name: str) -> KeycloakClientScopeDTO | None:
        """Get a client scope by name."""
        return to_dto_or_none(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_client_scope_by_name",
                lambda: self.admin_adapter.a_get_client_scope_by_name(client_scope_name=client_scope_name),
            ),
        )

    async def create_client_scope(
        self,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
        skip_exists: bool = False,
    ) -> str:
        """Create a new client scope."""
        return await self._async_call_keycloak(
            "create_client_scope",
            lambda: self.admin_adapter.a_create_client_scope(
                payload=to_request_payload(payload),
                skip_exists=skip_exists,
            ),
        )

    async def update_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client scope."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_client_scope",
                lambda: self.admin_adapter.a_update_client_scope(
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def delete_client_scope(self, client_scope_id: str) -> KeycloakDeleteResultDTO:
        """Delete a client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_client_scope",
                lambda: self.admin_adapter.a_delete_client_scope(client_scope_id=client_scope_id),
            ),
        )

    async def add_mapper_to_client_scope(
        self,
        client_scope_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client scope."""
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_call_keycloak(
                    "add_mapper_to_client_scope",
                    lambda: self.admin_adapter.a_add_mapper_to_client_scope(
                        client_scope_id=client_scope_id,
                        payload=to_request_payload(payload),
                    ),
                ),
            ),
            lambda: self._find_scope_mapper_id(client_scope_id, payload_value(payload, "name", "name")),
        )

    async def get_mappers_from_client_scope(self, client_scope_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client scope."""
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            await self._async_call_keycloak(
                "get_mappers_from_client_scope",
                lambda: self.admin_adapter.a_get_mappers_from_client_scope(client_scope_id=client_scope_id),
            ),
        )

    async def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper in a client scope."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_mapper_in_client_scope",
                lambda: self.admin_adapter.a_update_mapper_in_client_scope(
                    client_scope_id=client_scope_id,
                    protocol_mapper_id=protocol_mapper_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def delete_mapper_from_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Delete a protocol mapper from a client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_mapper_from_client_scope",
                lambda: self.admin_adapter.a_delete_mapper_from_client_scope(
                    client_scope_id=client_scope_id,
                    protocol_mapper_id=protocol_mapper_id,
                ),
            ),
        )

    async def add_mapper_to_client(
        self,
        client_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Add a protocol mapper to a client."""
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_call_keycloak(
                    "add_mapper_to_client",
                    lambda: self.admin_adapter.a_add_mapper_to_client(
                        client_id=client_id,
                        payload=to_request_payload(payload),
                    ),
                ),
            ),
            lambda: self._find_client_mapper_id(client_id, payload_value(payload, "name", "name")),
        )

    async def get_mappers_from_client(self, client_id: str) -> list[KeycloakProtocolMapperDTO]:
        """Get protocol mappers for a client."""
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            await self._async_call_keycloak(
                "get_mappers_from_client",
                lambda: self.admin_adapter.a_get_mappers_from_client(client_id=client_id),
            ),
        )

    async def update_client_mapper(
        self,
        client_id: str,
        mapper_id: str,
        payload: KeycloakProtocolMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a protocol mapper on a client."""
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_client_mapper",
                lambda: self.admin_adapter.a_update_client_mapper(
                    client_id=client_id,
                    mapper_id=mapper_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> KeycloakDeleteResultDTO:
        """Remove a protocol mapper from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "remove_client_mapper",
                lambda: self.admin_adapter.a_remove_client_mapper(
                    client_id=client_id,
                    client_mapper_id=client_mapper_id,
                ),
            ),
        )

    async def get_client_default_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get default client scopes for a client."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_client_default_client_scopes",
                lambda: self.admin_adapter.a_get_client_default_client_scopes(client_id=client_id),
            ),
        )

    async def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add a default client scope to a client."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_call_keycloak(
                "add_client_default_client_scope",
                lambda: self.admin_adapter.a_add_client_default_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def delete_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove a default client scope from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_client_default_client_scope",
                lambda: self.admin_adapter.a_delete_client_default_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                ),
            ),
        )

    async def get_client_optional_client_scopes(self, client_id: str) -> list[KeycloakClientScopeDTO]:
        """Get optional client scopes for a client."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_client_optional_client_scopes",
                lambda: self.admin_adapter.a_get_client_optional_client_scopes(client_id=client_id),
            ),
        )

    async def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: KeycloakClientScopeRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Add an optional client scope to a client."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_call_keycloak(
                "add_client_optional_client_scope",
                lambda: self.admin_adapter.a_add_client_optional_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def delete_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
    ) -> KeycloakDeleteResultDTO:
        """Remove an optional client scope from a client."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_client_optional_client_scope",
                lambda: self.admin_adapter.a_delete_client_optional_client_scope(
                    client_id=client_id,
                    client_scope_id=client_scope_id,
                ),
            ),
        )

    async def get_default_default_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm default client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_default_default_client_scopes",
                self.admin_adapter.a_get_default_default_client_scopes,
            ),
        )

    async def add_default_default_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm default client scope."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_call_keycloak(
                "add_default_default_client_scope",
                lambda: self.admin_adapter.a_add_default_default_client_scope(scope_id=scope_id),
            ),
        )

    async def delete_default_default_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm default client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_default_default_client_scope",
                lambda: self.admin_adapter.a_delete_default_default_client_scope(scope_id=scope_id),
            ),
        )

    async def get_default_optional_client_scopes(
        self,
    ) -> list[KeycloakClientScopeDTO]:
        """Get realm optional default client scopes."""
        return to_dto_list(
            KeycloakClientScopeDTO,
            await self._async_call_keycloak(
                "get_default_optional_client_scopes",
                self.admin_adapter.a_get_default_optional_client_scopes,
            ),
        )

    async def add_default_optional_client_scope(self, scope_id: str) -> KeycloakAssignResultDTO:
        """Add a realm optional default client scope."""
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_call_keycloak(
                "add_default_optional_client_scope",
                lambda: self.admin_adapter.a_add_default_optional_client_scope(scope_id=scope_id),
            ),
        )

    async def delete_default_optional_client_scope(self, scope_id: str) -> KeycloakDeleteResultDTO:
        """Remove a realm optional default client scope."""
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_default_optional_client_scope",
                lambda: self.admin_adapter.a_delete_default_optional_client_scope(scope_id=scope_id),
            ),
        )
