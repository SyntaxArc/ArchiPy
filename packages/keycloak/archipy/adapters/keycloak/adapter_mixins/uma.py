"""Keycloak adapter mixins for UMA operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from keycloak.uma_permissions import UMAPermission


class KeycloakUmaMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for UMA operations."""

    def resource_set_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        return self._call_keycloak(
            "resource_set_create",
            lambda: self.uma_adapter.resource_set_create(payload=payload),
        )

    def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        return self._call_keycloak(
            "resource_set_read",
            lambda: self.uma_adapter.resource_set_read(resource_id=resource_id),
        )

    def resource_set_update(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        return self._call_keycloak(
            "resource_set_update",
            lambda: self.uma_adapter.resource_set_update(resource_id=resource_id, payload=payload),
        )

    def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        return self._call_keycloak(
            "resource_set_delete",
            lambda: self.uma_adapter.resource_set_delete(resource_id=resource_id),
        )

    def resource_set_list(self) -> list[dict[str, Any]]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """
        return self._call_keycloak(
            "resource_set_list",
            lambda: list(self.uma_adapter.resource_set_list()),
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
    ) -> list[dict[str, Any]]:
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

    def policy_resource_create(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        return self._call_keycloak(
            "policy_resource_create",
            lambda: self.uma_adapter.policy_resource_create(resource_id=resource_id, payload=payload),
        )

    def policy_update(self, policy_id: str, payload: dict[str, Any]) -> bytes:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        return self._call_keycloak(
            "policy_update",
            lambda: self.uma_adapter.policy_update(policy_id=policy_id, payload=payload),
        )

    def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        return self._call_keycloak(
            "policy_delete",
            lambda: self.uma_adapter.policy_delete(policy_id=policy_id),
        )

    def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
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
        return self._call_keycloak(
            "policy_query",
            lambda: self.uma_adapter.policy_query(
                resource=resource,
                name=name,
                scope=scope,
                first=first,
                maximum=maximum,
            ),
        )

    def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        return self._call_keycloak(
            "permission_ticket_create",
            lambda: self.uma_adapter.permission_ticket_create(permissions=permissions),
        )

    def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True when all requested permissions are granted.
        """
        return self._call_keycloak(
            "permissions_check",
            lambda: self.uma_adapter.permissions_check(token=token, permissions=permissions, **extra_payload),
        )


class AsyncKeycloakUmaMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for UMA operations."""

    async def resource_set_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        return await self._async_call_keycloak(
            "resource_set_create",
            lambda: self.uma_adapter.a_resource_set_create(payload=payload),
        )

    async def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        return await self._async_call_keycloak(
            "resource_set_read",
            lambda: self.uma_adapter.a_resource_set_read(resource_id=resource_id),
        )

    async def resource_set_update(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        return await self._async_call_keycloak(
            "resource_set_update",
            lambda: self.uma_adapter.a_resource_set_update(resource_id=resource_id, payload=payload),
        )

    async def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        return await self._async_call_keycloak(
            "resource_set_delete",
            lambda: self.uma_adapter.a_resource_set_delete(resource_id=resource_id),
        )

    async def resource_set_list(self) -> list[dict[str, Any]]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """

        async def _list() -> list[dict[str, Any]]:
            return [item async for item in self.uma_adapter.a_resource_set_list()]

        return await self._async_call_keycloak("resource_set_list", _list)

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
    ) -> list[dict[str, Any]]:
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

    async def policy_resource_create(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        return await self._async_call_keycloak(
            "policy_resource_create",
            lambda: self.uma_adapter.a_policy_resource_create(resource_id=resource_id, payload=payload),
        )

    async def policy_update(self, policy_id: str, payload: dict[str, Any]) -> bytes:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        return await self._async_call_keycloak(
            "policy_update",
            lambda: self.uma_adapter.a_policy_update(policy_id=policy_id, payload=payload),
        )

    async def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        return await self._async_call_keycloak(
            "policy_delete",
            lambda: self.uma_adapter.a_policy_delete(policy_id=policy_id),
        )

    async def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
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
        return await self._async_call_keycloak(
            "policy_query",
            lambda: self.uma_adapter.a_policy_query(
                resource=resource,
                name=name,
                scope=scope,
                first=first,
                maximum=maximum,
            ),
        )

    async def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        return await self._async_call_keycloak(
            "permission_ticket_create",
            lambda: self.uma_adapter.a_permission_ticket_create(permissions=permissions),
        )

    async def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True when all requested permissions are granted.
        """
        return await self._async_call_keycloak(
            "permissions_check",
            lambda: self.uma_adapter.a_permissions_check(token=token, permissions=permissions, **extra_payload),
        )
