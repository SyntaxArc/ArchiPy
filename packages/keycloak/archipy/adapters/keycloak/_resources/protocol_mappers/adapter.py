"""Keycloak adapter mixins for protocol mapper operations."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    payload_value,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
    with_created_id,
    with_created_id_async,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakCreateResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.protocol_mapper_dtos import (
    KeycloakProtocolMapperDTO,
    KeycloakProtocolMapperRequestDTO,
)


class KeycloakProtocolMappersMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for protocol mapper operations."""

    def _find_scope_mapper_id(self, client_scope_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client scope."""
        return next((m.id for m in self.get_mappers_from_client_scope(client_scope_id) if m.name == name), None)

    def _find_client_mapper_id(self, client_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client."""
        return next((m.id for m in self.get_mappers_from_client(client_id) if m.name == name), None)

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

    def get_client_scope_protocol_mapper(self, client_scope_id: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakProtocolMapperDTO,
            self._admin_request(
                "get_client_scope_protocol_mapper",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/models/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_scope_protocol_mappers(
        self,
        client_scope_id: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client scope in one call.

        Args:
            client_scope_id: Client scope identifier.
            mappers: Mappers to add.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            self._admin_request(
                "add_client_scope_protocol_mappers",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/add-models",
                body=[to_request_payload(mapper) for mapper in mappers],
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    def get_client_scope_protocol_mappers_by_protocol(
        self,
        client_scope_id: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client scope for one protocol.

        Args:
            client_scope_id: Client scope identifier.
            protocol: ``openid-connect``, ``saml`` or ``docker-v2``.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            self._admin_request(
                "get_client_scope_protocol_mappers_by_protocol",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/protocol/{segment(protocol)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_protocol_mapper(self, client_uuid: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client.

        Args:
            client_uuid: Client UUID.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakProtocolMapperDTO,
            self._admin_request(
                "get_client_protocol_mapper",
                "get",
                f"/clients/{segment(client_uuid)}/protocol-mappers/models/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_protocol_mappers(
        self,
        client_uuid: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client in one call.

        Args:
            client_uuid: Client UUID.
            mappers: Mappers to add.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            self._admin_request(
                "add_client_protocol_mappers",
                "post",
                f"/clients/{segment(client_uuid)}/protocol-mappers/add-models",
                body=[to_request_payload(mapper) for mapper in mappers],
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    def get_client_protocol_mappers_by_protocol(
        self,
        client_uuid: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client for one protocol.

        Args:
            client_uuid: Client UUID.
            protocol: ``openid-connect``, ``saml`` or ``docker-v2``.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            self._admin_request(
                "get_client_protocol_mappers_by_protocol",
                "get",
                f"/clients/{segment(client_uuid)}/protocol-mappers/protocol/{segment(protocol)}",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakProtocolMappersMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for protocol mapper operations."""

    async def _find_scope_mapper_id(self, client_scope_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client scope."""
        mappers = await self.get_mappers_from_client_scope(client_scope_id)
        return next((m.id for m in mappers if m.name == name), None)

    async def _find_client_mapper_id(self, client_id: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of the client."""
        mappers = await self.get_mappers_from_client(client_id)
        return next((m.id for m in mappers if m.name == name), None)

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

    async def get_client_scope_protocol_mapper(self, client_scope_id: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client scope.

        Args:
            client_scope_id: Client scope identifier.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakProtocolMapperDTO,
            await self._async_admin_request(
                "get_client_scope_protocol_mapper",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/models/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_scope_protocol_mappers(
        self,
        client_scope_id: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client scope in one call.

        Args:
            client_scope_id: Client scope identifier.
            mappers: Mappers to add.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            await self._async_admin_request(
                "add_client_scope_protocol_mappers",
                "post",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/add-models",
                body=[to_request_payload(mapper) for mapper in mappers],
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    async def get_client_scope_protocol_mappers_by_protocol(
        self,
        client_scope_id: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client scope for one protocol.

        Args:
            client_scope_id: Client scope identifier.
            protocol: ``openid-connect``, ``saml`` or ``docker-v2``.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            await self._async_admin_request(
                "get_client_scope_protocol_mappers_by_protocol",
                "get",
                f"/client-scopes/{segment(client_scope_id)}/protocol-mappers/protocol/{segment(protocol)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_protocol_mapper(self, client_uuid: str, mapper_id: str) -> KeycloakProtocolMapperDTO:
        """Get one protocol mapper of a client.

        Args:
            client_uuid: Client UUID.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakProtocolMapperDTO,
            await self._async_admin_request(
                "get_client_protocol_mapper",
                "get",
                f"/clients/{segment(client_uuid)}/protocol-mappers/models/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_protocol_mappers(
        self,
        client_uuid: str,
        mappers: list[KeycloakProtocolMapperRequestDTO] | list[dict[str, Any]],
    ) -> KeycloakCreateResultDTO:
        """Add several protocol mappers to a client in one call.

        Args:
            client_uuid: Client UUID.
            mappers: Mappers to add.

        Returns:
            The create result.
        """
        return to_mutation_result(
            KeycloakCreateResultDTO,
            await self._async_admin_request(
                "add_client_protocol_mappers",
                "post",
                f"/clients/{segment(client_uuid)}/protocol-mappers/add-models",
                body=[to_request_payload(mapper) for mapper in mappers],
                expected=(
                    HTTPStatus.CREATED,
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.OK,
                ),
            ),
        )

    async def get_client_protocol_mappers_by_protocol(
        self,
        client_uuid: str,
        protocol: str,
    ) -> list[KeycloakProtocolMapperDTO]:
        """List the protocol mappers of a client for one protocol.

        Args:
            client_uuid: Client UUID.
            protocol: ``openid-connect``, ``saml`` or ``docker-v2``.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakProtocolMapperDTO,
            await self._async_admin_request(
                "get_client_protocol_mappers_by_protocol",
                "get",
                f"/clients/{segment(client_uuid)}/protocol-mappers/protocol/{segment(protocol)}",
                expected=(HTTPStatus.OK,),
            ),
        )
