"""Keycloak adapter mixins for role operations."""

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
    KeycloakRoleType,
)
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.errors import (
    InternalError,
)

logger = logging.getLogger(__name__)


class KeycloakRolesMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for role operations."""

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleType] | None:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_realm_roles_of_user(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user.

        Args:
            user_id: User's ID
            client_id: Client ID

        Returns:
            List of client-specific roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_client_roles_of_user(user_id, client_id)
        except KeycloakError as e:
            raise InternalError() from e

    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user.

        Args:
            user_id: User's ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = self.admin_adapter.get_realm_role(role_name)
            # Assign role to user
            self.admin_adapter.assign_realm_roles(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_realm_role")

    def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user.

        Args:
            user_id: User's ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = self.admin_adapter.get_realm_role(role_name)
            # Remove role from user
            self.admin_adapter.delete_realm_roles_of_user(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_realm_role")

    def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get client
            client = self.admin_adapter.get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Get role representation
            # Keycloak admin adapter methods accept these types at runtime
            role = self.admin_adapter.get_client_role(client, role_name)
            # Assign role to user
            self.admin_adapter.assign_client_role(user_id, client, [role])

            # Clear role-related caches
            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_client_role")

    def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role.

        Args:
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if realm role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            self.admin_adapter.create_realm_role(role_data, skip_exists=skip_exists)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "clear_cache"):
                self.get_realm_roles.clear_cache()

            return self.admin_adapter.get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role.

        Args:
            client_id: Client ID or client name
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if client role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            resolved_client_id = self.admin_adapter.get_client_id(client_id)
            if resolved_client_id is None:
                raise ValueError(f"Client ID not found: {client_id}")

            # Prepare role data
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            # Create client role
            self.admin_adapter.create_client_role(resolved_client_id, role_data, skip_exists=skip_exists)

            # Clear related caches if they exist
            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()

            # Return created role
            return self.admin_adapter.get_client_role(resolved_client_id, role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_role")

    def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role.

        Args:
            role_name: Role name to delete

        Raises:
            ValueError: If role deletion fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.delete_realm_role(role_name)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "clear_cache"):
                self.get_realm_roles.clear_cache()

            # We also need to clear user role caches since they might contain this role
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_realm_role")

    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_roles(self) -> list[dict[str, Any]] | None:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_realm_roles()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_role(self, role_name: str) -> dict | None:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return self.admin_adapter.get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role")

    def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        try:
            client = self.admin_adapter.get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Keycloak admin adapter methods accept these types at runtime
            role = self.admin_adapter.get_client_role(client, role_name)
            self.admin_adapter.delete_client_roles_of_user(user_id, client, [role])

            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_role")

    def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role.

        Args:
            token: Access token
            role_name: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        # Not caching this result as token validation is time-sensitive
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles
            realm_access = user_info.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if role_name in roles:
                return True

            # Check client roles
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            if role_name in client_roles:
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has any of the roles, False otherwise
        """
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles first
            realm_access = user_info.get("realm_access", {})
            realm_roles = set(realm_access.get("roles", []))
            if role_names.intersection(realm_roles):
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = set(resource_access.get(self.configs.CLIENT_ID, {}).get("roles", []))
            if role_names.intersection(client_roles):
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has all the roles, False otherwise
        """
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Get all user roles
            all_roles = set()

            # Add realm roles
            realm_access = user_info.get("realm_access", {})
            all_roles.update(realm_access.get("roles", []))

            # Add client roles
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            all_roles.update(client_roles)

            # Check if all required roles are present
            return role_names.issubset(all_roles)

        except Exception as e:
            logger.debug(f"All roles check failed: {e!s}")
            return False

    def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role.

        Args:
            composite_role_name: Name of the composite realm role
            child_role_names: List of child role names to add
        """
        try:
            child_roles = []
            for role_name in child_role_names:
                try:
                    role = self.admin_adapter.get_realm_role(role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Child role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                self.admin_adapter.add_composite_realm_roles_to_role(role_name=composite_role_name, roles=child_roles)
                logger.info(f"Added {len(child_roles)} realm roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_realm_roles_to_composite")

    def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role.

        Args:
            composite_role_name: Name of the composite client role
            client_id: Client ID or client name
            child_role_names: List of child role names to add
        """
        try:
            internal_client_id = self.admin_adapter.get_client_id(client_id)
            if internal_client_id is None:
                raise ValueError("client_id resolved to None")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = self.admin_adapter.get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Client role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise ValueError("Client ID not found")
                resolved_client_id: str = internal_client_id
                self.admin_adapter.add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} client roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return self.admin_adapter.get_composite_realm_roles_of_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")


class AsyncKeycloakRolesMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for role operations."""

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleType] | None:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_realm_roles_of_user(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user.

        Args:
            user_id: User's ID
            client_id: Client ID

        Returns:
            List of client-specific roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_client_roles_of_user(user_id, client_id)
        except KeycloakError as e:
            raise InternalError() from e

    async def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user.

        Args:
            user_id: User's ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = await self.admin_adapter.a_get_realm_role(role_name)
            # Assign role to user
            await self.admin_adapter.a_assign_realm_roles(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_realm_role")

    async def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user.

        Args:
            user_id: User's ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = await self.admin_adapter.a_get_realm_role(role_name)
            # Remove role from user
            await self.admin_adapter.a_delete_realm_roles_of_user(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_realm_role")

    async def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get client
            client = await self.admin_adapter.a_get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Get role representation
            # Keycloak admin adapter methods accept these types at runtime
            role = await self.admin_adapter.a_get_client_role(client, role_name)
            # Assign role to user
            await self.admin_adapter.a_assign_client_role(user_id, client, [role])

            # Clear role-related caches
            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_client_role")

    async def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role.

        Args:
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            await self.admin_adapter.a_create_realm_role(role_data, skip_exists=skip_exists)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "cache_clear"):
                self.get_realm_roles.cache_clear()

            return await self.admin_adapter.a_get_realm_role(role_name)

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    async def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role.

        Args:
            client_id: Client ID or client name
            role_name: Role name
            skip_exists: Skip creation if role already exists
            description: Optional role description

        Returns:
            Created role details
        """
        # This is a write operation, no caching needed
        try:
            resolved_client_id = await self.admin_adapter.a_get_client_id(client_id)
            if resolved_client_id is None:
                raise ValueError(f"Client ID not found: {client_id}")

            # Prepare role data
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            # Create client role
            await self.admin_adapter.a_create_client_role(resolved_client_id, role_data, skip_exists=skip_exists)

            # Clear related caches if they exist
            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()

            # Return created role
            return await self.admin_adapter.a_get_client_role(resolved_client_id, role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_role")

    async def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role.

        Args:
            role_name: Role name to delete

        Raises:
            ValueError: If role deletion fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_delete_realm_role(role_name)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "cache_clear"):
                self.get_realm_roles.cache_clear()

            # We also need to clear user role caches since they might contain this role
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_realm_role")

    @alru_cache(ttl=300, maxsize=1)  # Cache for 5 minutes
    async def get_realm_roles(self) -> list[dict[str, Any]] | None:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_realm_roles()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @alru_cache(ttl=300, maxsize=1)  # Cache for 5 minutes
    async def get_realm_role(self, role_name: str) -> dict | None:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return await self.admin_adapter.a_get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role")

    async def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        try:
            client = await self.admin_adapter.a_get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Keycloak admin adapter methods accept these types at runtime
            role = await self.admin_adapter.a_get_client_role(client, role_name)
            await self.admin_adapter.a_delete_client_roles_of_user(user_id, client, [role])

            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_role")

    async def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role.

        Args:
            token: Access token
            role_name: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        # Not caching this result as token validation is time-sensitive
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles
            realm_access = user_info.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if role_name in roles:
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            if role_name in client_roles:
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    async def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has any of the roles, False otherwise
        """
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles first
            realm_access = user_info.get("realm_access", {})
            realm_roles = set(realm_access.get("roles", []))
            if role_names.intersection(realm_roles):
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = set(resource_access.get(self.configs.CLIENT_ID, {}).get("roles", []))
            if role_names.intersection(client_roles):
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    async def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has all the roles, False otherwise
        """
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Get all user roles
            all_roles = set()

            # Add realm roles
            realm_access = user_info.get("realm_access", {})
            all_roles.update(realm_access.get("roles", []))

            # Add roles from the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            all_roles.update(client_roles)

            # Check if all required roles are present
            return role_names.issubset(all_roles)

        except Exception as e:
            logger.debug(f"All roles check failed: {e!s}")
            return False

    async def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role.

        Args:
            composite_role_name: Name of the composite role
            child_role_names: List of child role names to add
        """
        try:
            child_roles = []
            for role_name in child_role_names:
                try:
                    role = await self.admin_adapter.a_get_realm_role(role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Child role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                await self.admin_adapter.a_add_composite_realm_roles_to_role(
                    role_name=composite_role_name,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} realm roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_realm_roles_to_composite")

    async def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role.

        Args:
            composite_role_name: Name of the composite role
            client_id: Client ID or client name
            child_role_names: List of child role names to add
        """
        try:
            internal_client_id = await self.admin_adapter.a_get_client_id(client_id)
            if internal_client_id is None:
                raise ValueError("client_id resolved to None")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = await self.admin_adapter.a_get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Client role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise ValueError("Client ID not found")
                resolved_client_id: str = internal_client_id
                await self.admin_adapter.a_add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} client roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    async def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return await self.admin_adapter.a_get_composite_realm_roles_of_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")
