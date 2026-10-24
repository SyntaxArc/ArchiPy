"""Keycloak adapter mixins for role operations."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from async_lru import alru_cache
from keycloak.exceptions import (
    KeycloakError,
    KeycloakGetError,
)

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_claims_dict,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
    to_wire_roles,
)
from archipy.helpers.decorators import ttl_cache
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO
from archipy.models.dtos.keycloak.management_permission_dtos import (
    KeycloakManagementPermissionDTO,
    KeycloakManagementPermissionRequestDTO,
)
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleRequestDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO
from archipy.models.errors import (
    InternalError,
    NotFoundError,
)

logger = logging.getLogger(__name__)

HTTP_NOT_FOUND = 404


class KeycloakRolesMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for role operations."""

    @ttl_cache(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleDTO]:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return [KeycloakRoleDTO.model_validate(r) for r in self.admin_adapter.get_realm_roles_of_user(user_id)]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @ttl_cache(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
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
            return [
                KeycloakRoleDTO.model_validate(r)
                for r in self.admin_adapter.get_client_roles_of_user(user_id, client_id)
            ]
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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")
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
    ) -> KeycloakRoleDTO | None:
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

            return KeycloakRoleDTO.model_validate(self.admin_adapter.get_realm_role(role_name))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
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
                raise NotFoundError(
                    resource_type="keycloak_client",
                    additional_data={"client_id": client_id},
                )

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
            return KeycloakRoleDTO.model_validate(self.admin_adapter.get_client_role(resolved_client_id, role_name))
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

    @ttl_cache(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_roles(self) -> list[KeycloakRoleDTO]:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return [KeycloakRoleDTO.model_validate(r) for r in self.admin_adapter.get_realm_roles()]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @ttl_cache(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_role(self, role_name: str) -> KeycloakRoleDTO:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return KeycloakRoleDTO.model_validate(self.admin_adapter.get_realm_role(role_name))
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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")
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
            user_info = to_claims_dict(self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Role check failed: %s", e)
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
            user_info = to_claims_dict(self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Role check failed: %s", e)
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
            user_info = to_claims_dict(self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("All roles check failed: %s", e)
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
                    if e.response_code == HTTP_NOT_FOUND:
                        logger.warning("Child role not found: %s", role_name)
                        continue
                    raise

            if child_roles:
                self.admin_adapter.add_composite_realm_roles_to_role(role_name=composite_role_name, roles=child_roles)
                logger.info("Added %s realm roles to composite role: %s", len(child_roles), composite_role_name)

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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = self.admin_adapter.get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == HTTP_NOT_FOUND:
                        logger.warning("Client role not found: %s", role_name)
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise NotFoundError(resource_type="keycloak_client")
                resolved_client_id: str = internal_client_id
                self.admin_adapter.add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info("Added %s client roles to composite role: %s", len(child_roles), composite_role_name)

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    def get_composite_realm_roles(self, role_name: str) -> list[KeycloakRoleDTO] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return [
                KeycloakRoleDTO.model_validate(r)
                for r in self.admin_adapter.get_composite_realm_roles_of_role(role_name)
            ]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")

    def get_realm_roles_filtered(self, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List realm roles, filtered by the admin API query parameters.

        Args:
            query: Optional query parameters: ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_realm_roles_filtered",
                "get",
                "/roles",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_role(
        self,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a realm role.

        Args:
            role_name: Realm role name.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_role",
                "put",
                f"/roles/{segment(role_name)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_users_with_realm_role(self, role_name: str, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List the users that have a realm role.

        Args:
            role_name: Realm role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            self._admin_request(
                "get_users_with_realm_role",
                "get",
                f"/roles/{segment(role_name)}/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_groups_with_realm_role(self, role_name: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups that have a realm role.

        Args:
            role_name: Realm role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_groups_with_realm_role",
                "get",
                f"/roles/{segment(role_name)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_realm_role_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_realm_role_composites",
                "get",
                f"/roles/{segment(role_name)}/composites",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_realm_role_realm_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_realm_role_realm_composites",
                "get",
                f"/roles/{segment(role_name)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_realm_role_client_composites(self, role_name: str, target_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role that belong to a client.

        Args:
            role_name: Realm role name.
            target_client_uuid: UUID of the client that owns the children.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_realm_role_client_composites",
                "get",
                f"/roles/{segment(role_name)}/composites/clients/{segment(target_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite realm role.

        Args:
            role_name: Realm role name.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_realm_role_composites",
                "post",
                f"/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite realm role.

        Args:
            role_name: Realm role name.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_role_composites",
                "delete",
                f"/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_role_management_permissions(self, role_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_realm_role_management_permissions",
                "get",
                f"/roles/{segment(role_name)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_role_management_permissions(
        self,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a realm role.

        Args:
            role_name: Realm role name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_realm_role_management_permissions",
                "put",
                f"/roles/{segment(role_name)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_roles_filtered(self, client_uuid: str, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List client roles, filtered by the admin API query parameters.

        Args:
            client_uuid: Client UUID.
            query: Optional query parameters: ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_roles_filtered",
                "get",
                f"/clients/{segment(client_uuid)}/roles",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_client_role(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_client_role",
                "put",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_role_by_name(self, client_uuid: str, role_name: str) -> KeycloakRoleDTO:
        """Get a client role by its name.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The role.
        """
        return to_dto(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_role_by_name",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_client_role(self, client_uuid: str, role_name: str) -> KeycloakDeleteResultDTO:
        """Delete a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_role",
                "delete",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_users_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            self._admin_request(
                "get_users_with_client_role",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_groups_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_groups_with_client_role",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_role_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_role_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_role_realm_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_role_realm_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_role_client_composites(
        self,
        client_uuid: str,
        role_name: str,
        target_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role that belong to a client.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            target_client_uuid: UUID of the client that owns the children.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_role_client_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites/clients/{segment(target_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_client_role_composites",
                "post",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client_role_composites",
                "delete",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
    ) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_client_role_management_permissions",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_client_role_management_permissions",
                "put",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakRolesMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for role operations."""

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleDTO]:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return [
                KeycloakRoleDTO.model_validate(r) for r in await self.admin_adapter.a_get_realm_roles_of_user(user_id)
            ]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleDTO]:
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
            return [
                KeycloakRoleDTO.model_validate(r)
                for r in await self.admin_adapter.a_get_client_roles_of_user(user_id, client_id)
            ]
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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")
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
    ) -> KeycloakRoleDTO | None:
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

            return KeycloakRoleDTO.model_validate(await self.admin_adapter.a_get_realm_role(role_name))

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    async def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> KeycloakRoleDTO | None:
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
                raise NotFoundError(
                    resource_type="keycloak_client",
                    additional_data={"client_id": client_id},
                )

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
            return KeycloakRoleDTO.model_validate(
                await self.admin_adapter.a_get_client_role(resolved_client_id, role_name),
            )
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
    async def get_realm_roles(self) -> list[KeycloakRoleDTO]:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return [KeycloakRoleDTO.model_validate(r) for r in await self.admin_adapter.a_get_realm_roles()]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @alru_cache(ttl=300, maxsize=1)  # Cache for 5 minutes
    async def get_realm_role(self, role_name: str) -> KeycloakRoleDTO:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return KeycloakRoleDTO.model_validate(await self.admin_adapter.a_get_realm_role(role_name))
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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")
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
            user_info = to_claims_dict(await self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Role check failed: %s", e)
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
            user_info = to_claims_dict(await self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Role check failed: %s", e)
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
            user_info = to_claims_dict(await self.get_userinfo(token))
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

        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("All roles check failed: %s", e)
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
                    if e.response_code == HTTP_NOT_FOUND:
                        logger.warning("Child role not found: %s", role_name)
                        continue
                    raise

            if child_roles:
                await self.admin_adapter.a_add_composite_realm_roles_to_role(
                    role_name=composite_role_name,
                    roles=child_roles,
                )
                logger.info("Added %s realm roles to composite role: %s", len(child_roles), composite_role_name)

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
                raise InternalError(error_code="KEYCLOAK_CLIENT_ID_NONE")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = await self.admin_adapter.a_get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == HTTP_NOT_FOUND:
                        logger.warning("Client role not found: %s", role_name)
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise NotFoundError(resource_type="keycloak_client")
                resolved_client_id: str = internal_client_id
                await self.admin_adapter.a_add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info("Added %s client roles to composite role: %s", len(child_roles), composite_role_name)

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    async def get_composite_realm_roles(self, role_name: str) -> list[KeycloakRoleDTO] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return [
                KeycloakRoleDTO.model_validate(r)
                for r in await self.admin_adapter.a_get_composite_realm_roles_of_role(role_name)
            ]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")

    async def get_realm_roles_filtered(self, query: dict[str, Any] | None = None) -> list[KeycloakRoleDTO]:
        """List realm roles, filtered by the admin API query parameters.

        Args:
            query: Optional query parameters: ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_realm_roles_filtered",
                "get",
                "/roles",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_role(
        self,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a realm role.

        Args:
            role_name: Realm role name.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_role",
                "put",
                f"/roles/{segment(role_name)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_users_with_realm_role(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a realm role.

        Args:
            role_name: Realm role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            await self._async_admin_request(
                "get_users_with_realm_role",
                "get",
                f"/roles/{segment(role_name)}/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_groups_with_realm_role(
        self,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a realm role.

        Args:
            role_name: Realm role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_groups_with_realm_role",
                "get",
                f"/roles/{segment(role_name)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_realm_role_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_realm_role_composites",
                "get",
                f"/roles/{segment(role_name)}/composites",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_realm_role_realm_composites(self, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_realm_role_realm_composites",
                "get",
                f"/roles/{segment(role_name)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_realm_role_client_composites(self, role_name: str, target_client_uuid: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a realm role that belong to a client.

        Args:
            role_name: Realm role name.
            target_client_uuid: UUID of the client that owns the children.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_realm_role_client_composites",
                "get",
                f"/roles/{segment(role_name)}/composites/clients/{segment(target_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite realm role.

        Args:
            role_name: Realm role name.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_realm_role_composites",
                "post",
                f"/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_realm_role_composites(
        self,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite realm role.

        Args:
            role_name: Realm role name.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_role_composites",
                "delete",
                f"/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_role_management_permissions(self, role_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a realm role.

        Args:
            role_name: Realm role name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_realm_role_management_permissions",
                "get",
                f"/roles/{segment(role_name)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_role_management_permissions(
        self,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a realm role.

        Args:
            role_name: Realm role name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_realm_role_management_permissions",
                "put",
                f"/roles/{segment(role_name)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_roles_filtered(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List client roles, filtered by the admin API query parameters.

        Args:
            client_uuid: Client UUID.
            query: Optional query parameters: ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_roles_filtered",
                "get",
                f"/clients/{segment(client_uuid)}/roles",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_client_role(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakRoleRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            payload: Role representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_client_role",
                "put",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_role_by_name(self, client_uuid: str, role_name: str) -> KeycloakRoleDTO:
        """Get a client role by its name.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The role.
        """
        return to_dto(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_role_by_name",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_client_role(self, client_uuid: str, role_name: str) -> KeycloakDeleteResultDTO:
        """Delete a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_role",
                "delete",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_users_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserDTO]:
        """List the users that have a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            await self._async_admin_request(
                "get_users_with_client_role",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_groups_with_client_role(
        self,
        client_uuid: str,
        role_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakGroupDTO]:
        """List the groups that have a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            query: Optional query parameters: ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_groups_with_client_role",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_role_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_role_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_role_realm_composites(self, client_uuid: str, role_name: str) -> list[KeycloakRoleDTO]:
        """List the realm roles that are composite children of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_role_realm_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites/realm",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_role_client_composites(
        self,
        client_uuid: str,
        role_name: str,
        target_client_uuid: str,
    ) -> list[KeycloakRoleDTO]:
        """List the composite children of a client role that belong to a client.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            target_client_uuid: UUID of the client that owns the children.

        Returns:
            The child roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_role_client_composites",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites/clients/{segment(target_client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakAssignResultDTO:
        """Add child roles to a composite client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            roles: Roles to add.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_client_role_composites",
                "post",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client_role_composites(
        self,
        client_uuid: str,
        role_name: str,
        roles: list[KeycloakRoleDTO] | list[dict[str, Any]],
    ) -> KeycloakDeleteResultDTO:
        """Remove child roles from a composite client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            roles: Roles to remove.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client_role_composites",
                "delete",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/composites",
                body=to_wire_roles(roles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
    ) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_client_role_management_permissions",
                "get",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_client_role_management_permissions(
        self,
        client_uuid: str,
        role_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client role.

        Args:
            client_uuid: Client UUID.
            role_name: Client role name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_client_role_management_permissions",
                "put",
                f"/clients/{segment(client_uuid)}/roles/{segment(role_name)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )
