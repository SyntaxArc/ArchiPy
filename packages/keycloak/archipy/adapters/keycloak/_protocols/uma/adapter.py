"""Keycloak adapter mixins for UMA operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
)
from archipy.models.dtos.keycloak.common_dtos import KeycloakDeleteResultDTO, KeycloakUpdateResultDTO
from archipy.models.dtos.keycloak.uma_dtos import (
    KeycloakUmaPolicyDTO,
    KeycloakUmaPolicyRequestDTO,
    KeycloakUmaResourceDTO,
    KeycloakUmaResourceRequestDTO,
    KeycloakUmaTicketDTO,
)
from archipy.models.errors import InsufficientPermissionsError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from keycloak.uma_permissions import UMAPermission

UMA_TICKET_GRANT = "urn:ietf:params:oauth:grant-type:uma-ticket"


def _all_granted(wanted: list[UMAPermission], granted: object) -> bool:
    """Return whether the granted permissions of a UMA ``permissions`` response cover every wanted permission."""
    if not isinstance(granted, list):
        return False
    scopes_by_resource: dict[str, set[str]] = {}
    for entry in granted:
        if not isinstance(entry, dict):
            continue
        scopes = set(entry.get("scopes") or [])
        for key in (entry.get("rsname"), entry.get("rsid")):
            if key:
                scopes_by_resource.setdefault(str(key), set()).update(scopes)
    for permission in wanted:
        scopes = scopes_by_resource.get(str(permission.resource))
        if scopes is None or (permission.scope and permission.scope not in scopes):
            return False
    return True


class KeycloakUmaMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for UMA operations."""

    def resource_set_create(self, payload: KeycloakUmaResourceRequestDTO | dict[str, Any]) -> KeycloakUmaResourceDTO:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        return to_dto(
            KeycloakUmaResourceDTO,
            self._call_keycloak(
                "resource_set_create",
                lambda: self.uma_adapter.resource_set_create(payload=to_request_payload(payload)),
            ),
        )

    def resource_set_read(self, resource_id: str) -> KeycloakUmaResourceDTO:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        return to_dto(
            KeycloakUmaResourceDTO,
            self._call_keycloak(
                "resource_set_read",
                lambda: self.uma_adapter.resource_set_read(resource_id=resource_id),
            ),
        )

    def resource_set_update(
        self,
        resource_id: str,
        payload: KeycloakUmaResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "resource_set_update",
                lambda: self.uma_adapter.resource_set_update(
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def resource_set_delete(self, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "resource_set_delete",
                lambda: self.uma_adapter.resource_set_delete(resource_id=resource_id),
            ),
        )

    def resource_set_list(self) -> list[KeycloakUmaResourceDTO]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """
        return to_dto_list(
            KeycloakUmaResourceDTO,
            self._call_keycloak(
                "resource_set_list",
                lambda: list(self.uma_adapter.resource_set_list()),
            ),
        )

    def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[str]:
        """List UMA resource set IDs with optional filters.

        Args:
            name: Filter by resource name.
            exact_name: Require exact name match when True.
            uri: Filter by resource URI.
            owner: Filter by owner.
            resource_type: Filter by resource type.
            scope: Filter by scope.
            matchingUri: Match URI patterns when True.
            first: Pagination offset.
            maximum: Max results (-1 for unlimited).

        Returns:
            Matching resource set IDs / summaries.
        """
        return self._call_keycloak(
            "resource_set_list_ids",
            lambda: self.uma_adapter.resource_set_list_ids(
                name=name,
                exact_name=exact_name,
                uri=uri,
                owner=owner,
                resource_type=resource_type,
                scope=scope,
                matchingUri=matchingUri,
                first=first,
                maximum=maximum,
            ),
        )

    def policy_resource_create(
        self,
        resource_id: str,
        payload: KeycloakUmaPolicyRequestDTO | dict[str, Any],
    ) -> KeycloakUmaPolicyDTO:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        return to_dto(
            KeycloakUmaPolicyDTO,
            self._call_keycloak(
                "policy_resource_create",
                lambda: self.uma_adapter.policy_resource_create(
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def policy_update(
        self,
        policy_id: str,
        payload: KeycloakUmaPolicyRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "policy_update",
                lambda: self.uma_adapter.policy_update(
                    policy_id=policy_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    def policy_delete(self, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "policy_delete",
                lambda: self.uma_adapter.policy_delete(policy_id=policy_id),
            ),
        )

    def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[KeycloakUmaPolicyDTO]:
        """Query UMA policies.

        Args:
            resource: Filter by resource.
            name: Filter by policy name.
            scope: Filter by scope.
            first: Pagination offset.
            maximum: Max results (-1 for unlimited).

        Returns:
            Matching policy representations.
        """
        return to_dto_list(
            KeycloakUmaPolicyDTO,
            self._call_keycloak(
                "policy_query",
                lambda: self.uma_adapter.policy_query(
                    resource=resource,
                    name=name,
                    scope=scope,
                    first=first,
                    maximum=maximum,
                ),
            ),
        )

    def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> KeycloakUmaTicketDTO:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        return to_dto(
            KeycloakUmaTicketDTO,
            self._call_keycloak(
                "permission_ticket_create",
                lambda: self.uma_adapter.permission_ticket_create(permissions=permissions),
            ),
        )

    def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True only when every requested permission is granted.
        """
        wanted = list(permissions)
        if not wanted:
            return True  # everyone has the empty set of permissions, which Keycloak cannot evaluate
        form: dict[str, Any] = {
            "grant_type": UMA_TICKET_GRANT,
            "permission": [str(permission) for permission in wanted],  # one form field per permission
            "response_mode": "permissions",  # "decision" is true when any single permission is granted
            "audience": self.configs.CLIENT_ID,
            **extra_payload,
        }
        try:
            decision = self._bearer_request(
                "permissions_check",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/protocol/openid-connect/token",
                token=token,
                form=form,
            )
        except InsufficientPermissionsError:
            return False
        return _all_granted(wanted, decision)


class AsyncKeycloakUmaMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for UMA operations."""

    async def resource_set_create(
        self,
        payload: KeycloakUmaResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUmaResourceDTO:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        return to_dto(
            KeycloakUmaResourceDTO,
            await self._async_call_keycloak(
                "resource_set_create",
                lambda: self.uma_adapter.a_resource_set_create(payload=to_request_payload(payload)),
            ),
        )

    async def resource_set_read(self, resource_id: str) -> KeycloakUmaResourceDTO:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        return to_dto(
            KeycloakUmaResourceDTO,
            await self._async_call_keycloak(
                "resource_set_read",
                lambda: self.uma_adapter.a_resource_set_read(resource_id=resource_id),
            ),
        )

    async def resource_set_update(
        self,
        resource_id: str,
        payload: KeycloakUmaResourceRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "resource_set_update",
                lambda: self.uma_adapter.a_resource_set_update(
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def resource_set_delete(self, resource_id: str) -> KeycloakDeleteResultDTO:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "resource_set_delete",
                lambda: self.uma_adapter.a_resource_set_delete(resource_id=resource_id),
            ),
        )

    async def resource_set_list(self) -> list[KeycloakUmaResourceDTO]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """

        async def _list() -> list[dict[str, Any]]:
            return [item async for item in self.uma_adapter.a_resource_set_list()]

        return to_dto_list(KeycloakUmaResourceDTO, await self._async_call_keycloak("resource_set_list", _list))

    async def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[str]:
        """List UMA resource set IDs with optional filters.

        Args:
            name: Filter by resource name.
            exact_name: Require exact name match when True.
            uri: Filter by resource URI.
            owner: Filter by owner.
            resource_type: Filter by resource type.
            scope: Filter by scope.
            matchingUri: Match URI patterns when True.
            first: Pagination offset.
            maximum: Max results (-1 for unlimited).

        Returns:
            Matching resource set IDs / summaries.
        """
        return await self._async_call_keycloak(
            "resource_set_list_ids",
            lambda: self.uma_adapter.a_resource_set_list_ids(
                name=name,
                exact_name=exact_name,
                uri=uri,
                owner=owner,
                resource_type=resource_type,
                scope=scope,
                matchingUri=matchingUri,
                first=first,
                maximum=maximum,
            ),
        )

    async def policy_resource_create(
        self,
        resource_id: str,
        payload: KeycloakUmaPolicyRequestDTO | dict[str, Any],
    ) -> KeycloakUmaPolicyDTO:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        return to_dto(
            KeycloakUmaPolicyDTO,
            await self._async_call_keycloak(
                "policy_resource_create",
                lambda: self.uma_adapter.a_policy_resource_create(
                    resource_id=resource_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def policy_update(
        self,
        policy_id: str,
        payload: KeycloakUmaPolicyRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "policy_update",
                lambda: self.uma_adapter.a_policy_update(
                    policy_id=policy_id,
                    payload=to_request_payload(payload),
                ),
            ),
        )

    async def policy_delete(self, policy_id: str) -> KeycloakDeleteResultDTO:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "policy_delete",
                lambda: self.uma_adapter.a_policy_delete(policy_id=policy_id),
            ),
        )

    async def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[KeycloakUmaPolicyDTO]:
        """Query UMA policies.

        Args:
            resource: Filter by resource.
            name: Filter by policy name.
            scope: Filter by scope.
            first: Pagination offset.
            maximum: Max results (-1 for unlimited).

        Returns:
            Matching policy representations.
        """
        return to_dto_list(
            KeycloakUmaPolicyDTO,
            await self._async_call_keycloak(
                "policy_query",
                lambda: self.uma_adapter.a_policy_query(
                    resource=resource,
                    name=name,
                    scope=scope,
                    first=first,
                    maximum=maximum,
                ),
            ),
        )

    async def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> KeycloakUmaTicketDTO:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        return to_dto(
            KeycloakUmaTicketDTO,
            await self._async_call_keycloak(
                "permission_ticket_create",
                lambda: self.uma_adapter.a_permission_ticket_create(permissions=permissions),
            ),
        )

    async def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True only when every requested permission is granted.
        """
        wanted = list(permissions)
        if not wanted:
            return True  # everyone has the empty set of permissions, which Keycloak cannot evaluate
        form: dict[str, Any] = {
            "grant_type": UMA_TICKET_GRANT,
            "permission": [str(permission) for permission in wanted],  # one form field per permission
            "response_mode": "permissions",  # "decision" is true when any single permission is granted
            "audience": self.configs.CLIENT_ID,
            **extra_payload,
        }
        try:
            decision = await self._async_bearer_request(
                "permissions_check",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/protocol/openid-connect/token",
                token=token,
                form=form,
            )
        except InsufficientPermissionsError:
            return False
        return _all_granted(wanted, decision)
