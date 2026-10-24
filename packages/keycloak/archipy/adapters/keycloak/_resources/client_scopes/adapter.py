"""Keycloak adapter mixins for client scope operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    to_dto,
    to_dto_list,
    to_dto_or_none,
    to_mutation_result,
    to_request_payload,
)
from archipy.models.dtos.keycloak.client_scope_dtos import (
    KeycloakClientScopeDTO,
    KeycloakClientScopeRequestDTO,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)


class KeycloakClientScopesMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client scope operations."""

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
