"""Keycloak adapter mixins for user operations."""

from __future__ import annotations

import logging
from typing import Any

from async_lru import alru_cache
from keycloak.exceptions import (
    KeycloakError,
    KeycloakGetError,
)

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.adapters.keycloak.ports import (
    KeycloakUserType,
)
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.errors import (
    InternalError,
)

logger = logging.getLogger(__name__)


class KeycloakUsersMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for user operations."""

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return self.admin_adapter.get_user(user_id)
        except KeycloakGetError as e:
            if e.response_code == 404:
                return None
            self._handle_keycloak_exception(e, "get_user_by_id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username.

        Args:
            username: User's username

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = self.admin_adapter.get_users({"username": username})
            return users[0] if users else None
        except KeycloakError as e:
            raise InternalError() from e

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email.

        Args:
            email: User's email

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = self.admin_adapter.get_users({"email": email})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak.

        Args:
            user_data: User data including username, email, etc.

        Returns:
            ID of the created user

        Raises:
            ValueError: If creating user fails
        """
        # This is a write operation, no caching needed
        try:
            user_id = self.admin_adapter.create_user(user_data)

            # Clear related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", user_data)
        else:
            return user_id

    def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.update_user(user_id, user_data)

            # Clear user-related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_user")

    def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password.

        Args:
            user_id: User's ID
            password: New password
            temporary: Whether the password is temporary and should be changed on next login

        Raises:
            ValueError: If password reset fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.set_user_password(user_id, password, temporary)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "reset_password")

    @ttl_cache_decorator(ttl_seconds=30, maxsize=50)  # Cache for 30 seconds with limited entries
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType] | None:
        """Search for users by username, email, or name.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching users

        Raises:
            ValueError: If search fails
        """
        try:
            # Try searching by different fields
            users = []

            # Search by username
            users.extend(self.admin_adapter.get_users({"username": query, "max": max_results}))

            # Search by email if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                email_users = self.admin_adapter.get_users({"email": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in email_users if user["id"] not in user_ids])

            # Search by firstName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                first_name_users = self.admin_adapter.get_users({"firstName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in first_name_users if user["id"] not in user_ids])

            # Search by lastName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                last_name_users = self.admin_adapter.get_users({"lastName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in last_name_users if user["id"] not in user_ids])

            return users[:max_results]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "search_users")

    def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user.

        Args:
            user_id: User's ID

        Raises:
            ValueError: If clearing sessions fails
        """
        try:
            self.admin_adapter.user_logout(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "clear_user_sessions")

    def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            ValueError: If the deletion fails
        """
        try:
            self.admin_adapter.delete_user(user_id=user_id)

            if hasattr(self.get_user_by_username, "clear_cache"):
                self.get_user_by_username.clear_cache()

            logger.info("Successfully deleted user with ID %s", user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_user")


class AsyncKeycloakUsersMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for user operations."""

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return await self.admin_adapter.a_get_user(user_id)
        except KeycloakGetError as e:
            if e.response_code == 404:
                return None
            raise InternalError() from e
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username.

        Args:
            username: User's username

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = await self.admin_adapter.a_get_users({"username": username})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_username")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email.

        Args:
            email: User's email

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = await self.admin_adapter.a_get_users({"email": email})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    async def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak.

        Args:
            user_data: User data including username, email, etc.

        Returns:
            ID of the created user

        Raises:
            ValueError: If creating user fails
        """
        # This is a write operation, no caching needed
        try:
            user_id = await self.admin_adapter.a_create_user(user_data)

            # Clear related caches
            self.clear_all_caches()
        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", user_data)
        else:
            return user_id

    async def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_update_user(user_id, user_data)

            # Clear user-related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_user")

    async def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password.

        Args:
            user_id: User's ID
            password: New password
            temporary: Whether the password is temporary and should be changed on next login

        Raises:
            ValueError: If password reset fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_set_user_password(user_id, password, temporary)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "reset_password")

    @alru_cache(ttl=30, maxsize=50)  # Cache for 30 seconds with limited entries
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType] | None:
        """Search for users by username, email, or name.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching users

        Raises:
            ValueError: If search fails
        """
        try:
            # Try searching by different fields
            users = []

            # Search by username
            users.extend(await self.admin_adapter.a_get_users({"username": query, "max": max_results}))

            # Search by email if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                email_users = await self.admin_adapter.a_get_users({"email": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in email_users if user["id"] not in user_ids])

            # Search by firstName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                first_name_users = await self.admin_adapter.a_get_users({"firstName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in first_name_users if user["id"] not in user_ids])

            # Search by lastName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                last_name_users = await self.admin_adapter.a_get_users({"lastName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in last_name_users if user["id"] not in user_ids])

            return users[:max_results]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "search_users")

    async def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user.

        Args:
            user_id: User's ID

        Raises:
            ValueError: If clearing sessions fails
        """
        try:
            await self.admin_adapter.a_user_logout(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "clear_user_sessions")

    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            ValueError: If the deletion fails
        """
        try:
            await self.admin_adapter.a_delete_user(user_id=user_id)

            if hasattr(self.get_user_by_username, "cache_clear"):
                self.get_user_by_username.cache_clear()

            logger.info("Successfully deleted user with ID %s", user_id)

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_user")
