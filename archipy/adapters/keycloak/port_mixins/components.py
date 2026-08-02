"""Keycloak port mixins for component operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any


class KeycloakComponentsPort:
    """Sync Keycloak port interface for component operations."""

    @abstractmethod
    def create_component(self, payload: dict[str, Any]) -> str:
        """Create a Keycloak component.

        Args:
            payload: Component representation.

        Returns:
            Created component ID.
        """
        raise NotImplementedError

    @abstractmethod
    def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID.

        Args:
            component_id: Component identifier.

        Returns:
            Component representation.
        """
        raise NotImplementedError

    @abstractmethod
    def get_components(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query.

        Args:
            query: Optional filter query parameters.

        Returns:
            Matching component representations.
        """
        raise NotImplementedError

    @abstractmethod
    def update_component(self, component_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a component.

        Args:
            component_id: Component identifier.
            payload: Updated component representation.

        Returns:
            Update response payload.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component.

        Args:
            component_id: Component identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError


class AsyncKeycloakComponentsPort:
    """Async Keycloak port interface for component operations."""

    @abstractmethod
    async def create_component(self, payload: dict[str, Any]) -> str:
        """Create a Keycloak component.

        Args:
            payload: Component representation.

        Returns:
            Created component ID.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID.

        Args:
            component_id: Component identifier.

        Returns:
            Component representation.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_components(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query.

        Args:
            query: Optional filter query parameters.

        Returns:
            Matching component representations.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_component(self, component_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Update a component.

        Args:
            component_id: Component identifier.
            payload: Updated component representation.

        Returns:
            Update response payload.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component.

        Args:
            component_id: Component identifier.

        Returns:
            Deletion response payload.
        """
        raise NotImplementedError
