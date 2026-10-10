"""Keycloak port mixins for UMA operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from keycloak.uma_permissions import UMAPermission


class KeycloakUmaPort:
    """Sync Keycloak port interface for UMA operations."""

    @abstractmethod
    def resource_set_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    def resource_set_update(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError

    @abstractmethod
    def resource_set_list(self) -> list[dict[str, Any]]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def policy_resource_create(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        raise NotImplementedError

    @abstractmethod
    def policy_update(self, policy_id: str, payload: dict[str, Any]) -> bytes:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        raise NotImplementedError

    @abstractmethod
    def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        raise NotImplementedError

    @abstractmethod
    def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True when all requested permissions are granted.
        """
        raise NotImplementedError


class AsyncKeycloakUmaPort:
    """Async Keycloak port interface for UMA operations."""

    @abstractmethod
    async def resource_set_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA resource set.

        Args:
            payload: Resource set representation.

        Returns:
            Created resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def resource_set_update(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a UMA resource set.

        Args:
            resource_id: Resource set identifier.
            payload: Updated resource set representation.

        Returns:
            Updated resource set representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set.

        Args:
            resource_id: Resource set identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError

    @abstractmethod
    async def resource_set_list(self) -> list[dict[str, Any]]:
        """List all UMA resource sets.

        Returns:
            List of resource set representations.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def policy_resource_create(self, resource_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a UMA policy for a resource.

        Args:
            resource_id: Resource identifier.
            payload: Policy representation.

        Returns:
            Created policy representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def policy_update(self, policy_id: str, payload: dict[str, Any]) -> bytes:
        """Update a UMA policy.

        Args:
            policy_id: Policy identifier.
            payload: Updated policy representation.

        Returns:
            Raw update response bytes.
        """
        raise NotImplementedError

    @abstractmethod
    async def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy.

        Args:
            policy_id: Policy identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket.

        Args:
            permissions: Permissions to include in the ticket.

        Returns:
            Permission ticket representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token.

        Args:
            token: Access token to evaluate.
            permissions: Permissions to check.
            **extra_payload: Extra fields forwarded to the UMA endpoint.

        Returns:
            True when all requested permissions are granted.
        """
        raise NotImplementedError
