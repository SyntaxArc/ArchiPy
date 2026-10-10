"""Keycloak adapter mixins for component operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)


class KeycloakComponentsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for component operations."""

    def create_component(self, payload: dict[str, Any]) -> str:
        """Create a Keycloak component.

        Args:
            payload: Component representation.

        Returns:
            Created component ID.
        """
        return self._call_keycloak(
            "create_component",
            lambda: self.admin_adapter.create_component(payload=payload),
        )

    def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID.

        Args:
            component_id: Component identifier.

        Returns:
            Component representation.
        """
        return self._call_keycloak(
            "get_component",
            lambda: self.admin_adapter.get_component(component_id=component_id),
        )

    def get_components(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query.

        Args:
            query: Optional filter query parameters.

        Returns:
            Matching component representations.
        """
        return self._call_keycloak(
            "get_components",
            lambda: self.admin_adapter.get_components(query=query),
        )

    def update_component(self, component_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a component.

        Args:
            component_id: Component identifier.
            payload: Updated component representation.

        Returns:
            Update response payload.
        """
        return self._call_keycloak(
            "update_component",
            lambda: self.admin_adapter.update_component(component_id=component_id, payload=payload),
        )

    def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component.

        Args:
            component_id: Component identifier.

        Returns:
            Deletion response payload.
        """
        return self._call_keycloak(
            "delete_component",
            lambda: self.admin_adapter.delete_component(component_id=component_id),
        )


class AsyncKeycloakComponentsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for component operations."""

    async def create_component(self, payload: dict[str, Any]) -> str:
        """Create a Keycloak component.

        Args:
            payload: Component representation.

        Returns:
            Created component ID.
        """
        return await self._async_call_keycloak(
            "create_component",
            lambda: self.admin_adapter.a_create_component(payload=payload),
        )

    async def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID.

        Args:
            component_id: Component identifier.

        Returns:
            Component representation.
        """
        return await self._async_call_keycloak(
            "get_component",
            lambda: self.admin_adapter.a_get_component(component_id=component_id),
        )

    async def get_components(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query.

        Args:
            query: Optional filter query parameters.

        Returns:
            Matching component representations.
        """
        return await self._async_call_keycloak(
            "get_components",
            lambda: self.admin_adapter.a_get_components(query=query),
        )

    async def update_component(self, component_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a component.

        Args:
            component_id: Component identifier.
            payload: Updated component representation.

        Returns:
            Update response payload.
        """
        return await self._async_call_keycloak(
            "update_component",
            lambda: self.admin_adapter.a_update_component(component_id=component_id, payload=payload),
        )

    async def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component.

        Args:
            component_id: Component identifier.

        Returns:
            Deletion response payload.
        """
        return await self._async_call_keycloak(
            "delete_component",
            lambda: self.admin_adapter.a_delete_component(component_id=component_id),
        )
