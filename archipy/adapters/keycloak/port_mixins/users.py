"""Keycloak port mixins for user operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.adapters.keycloak.port_mixins._shared import (
        KeycloakUserType,
    )


class KeycloakUsersPort:
    """Sync Keycloak port interface for user operations."""

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType]:
        """Search for users by username, email, or name."""
        raise NotImplementedError

    @abstractmethod
    def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user."""
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError


class AsyncKeycloakUsersPort:
    """Async Keycloak port interface for user operations."""

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    async def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType]:
        """Search for users by username, email, or name."""
        raise NotImplementedError

    @abstractmethod
    async def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID."""
        raise NotImplementedError
