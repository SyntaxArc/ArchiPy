"""Keycloak adapter mixins for user operations."""

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
    to_dto,
    to_dto_list,
    to_dto_or_none,
    to_mutation_result,
    to_request_payload,
)
from archipy.helpers.decorators import ttl_cache
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakDeleteResultDTO,
    KeycloakGroupsCountDTO,
    KeycloakImpersonationDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO
from archipy.models.dtos.keycloak.session_dtos import KeycloakUserSessionDTO
from archipy.models.dtos.keycloak.user_dtos import (
    KeycloakCredentialDTO,
    KeycloakFederatedIdentityDTO,
    KeycloakFederatedIdentityRequestDTO,
    KeycloakUserConsentDTO,
    KeycloakUserDTO,
    KeycloakUserRequestDTO,
)
from archipy.models.dtos.keycloak.user_profile_dtos import (
    KeycloakUserProfileConfigDTO,
    KeycloakUserProfileConfigRequestDTO,
    KeycloakUserProfileMetadataDTO,
)
from archipy.models.errors import (
    InternalError,
)

logger = logging.getLogger(__name__)

HTTP_NOT_FOUND = 404


class KeycloakUsersMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for user operations."""

    @ttl_cache(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_id(self, user_id: str) -> KeycloakUserDTO | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return to_dto_or_none(KeycloakUserDTO, self.admin_adapter.get_user(user_id))
        except KeycloakGetError as e:
            if e.response_code == HTTP_NOT_FOUND:
                return None
            self._handle_keycloak_exception(e, "get_user_by_id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @ttl_cache(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_username(self, username: str) -> KeycloakUserDTO | None:
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
            return to_dto_or_none(KeycloakUserDTO, users[0] if users else None)
        except KeycloakError as e:
            raise InternalError() from e

    @ttl_cache(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_email(self, email: str) -> KeycloakUserDTO | None:
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
            return to_dto_or_none(KeycloakUserDTO, users[0] if users else None)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    def create_user(self, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> str | None:
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
            user_id = self.admin_adapter.create_user(to_request_payload(user_data))

            # Clear related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", to_request_payload(user_data))
        else:
            return user_id

    def update_user(self, user_id: str, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.update_user(user_id, to_request_payload(user_data))

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

    @ttl_cache(ttl_seconds=30, maxsize=50)  # Cache for 30 seconds with limited entries
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserDTO]:
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

            return to_dto_list(KeycloakUserDTO, users[:max_results])
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

    def get_users(self, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List users, filtered by any of the admin API user query parameters.

        Args:
            query: Optional query parameters such as ``search``, ``email``, ``enabled``, ``first`` and ``max``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            self._admin_request(
                "get_users",
                "get",
                "/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def count_users(self, query: dict[str, Any] | None = None) -> int:
        """Count the users matching the query.

        Args:
            query: Optional query parameters such as ``search``, ``email`` and ``enabled``.

        Returns:
            The number of users.
        """
        return self._admin_request(
            "count_users",
            "get",
            "/users/count",
            params=query,
            expected=(HTTPStatus.OK,),
        )

    def get_user_profile_config(self) -> KeycloakUserProfileConfigDTO:
        """Get the realm's user profile configuration.

        Args:
            (none)

        Returns:
            The user profile configuration.
        """
        return to_dto(
            KeycloakUserProfileConfigDTO,
            self._admin_request(
                "get_user_profile_config",
                "get",
                "/users/profile",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_user_profile_config(
        self,
        config: KeycloakUserProfileConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUserProfileConfigDTO:
        """Replace the realm's user profile configuration.

        Args:
            config: The user profile configuration.

        Returns:
            The stored configuration.
        """
        return to_dto(
            KeycloakUserProfileConfigDTO,
            self._admin_request(
                "update_user_profile_config",
                "put",
                "/users/profile",
                body=to_request_payload(config),
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_profile_metadata(self) -> KeycloakUserProfileMetadataDTO:
        """Get the user profile metadata of the realm.

        Args:
            (none)

        Returns:
            The metadata.
        """
        return to_dto(
            KeycloakUserProfileMetadataDTO,
            self._admin_request(
                "get_user_profile_metadata",
                "get",
                "/users/profile/metadata",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups a user belongs to.

        Args:
            user_id: User identifier.
            query: Optional query parameters such as ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_user_groups",
                "get",
                f"/users/{segment(user_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def count_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Count the groups a user belongs to.

        Args:
            user_id: User identifier.
            query: Optional query parameters such as ``search``.

        Returns:
            The count.
        """
        return to_dto(
            KeycloakGroupsCountDTO,
            self._admin_request(
                "count_user_groups",
                "get",
                f"/users/{segment(user_id)}/groups/count",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_credentials(self, user_id: str) -> list[KeycloakCredentialDTO]:
        """List the credentials of a user.

        Args:
            user_id: User identifier.

        Returns:
            The credentials.
        """
        return to_dto_list(
            KeycloakCredentialDTO,
            self._admin_request(
                "get_user_credentials",
                "get",
                f"/users/{segment(user_id)}/credentials",
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_user_credential(self, user_id: str, credential_id: str) -> KeycloakDeleteResultDTO:
        """Delete a credential of a user.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_user_credential",
                "delete",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def move_user_credential_to_first(self, user_id: str, credential_id: str) -> KeycloakUpdateResultDTO:
        """Move a credential to the top of the user's credential list.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "move_user_credential_to_first",
                "post",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}/moveToFirst",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def move_user_credential_after(
        self,
        user_id: str,
        credential_id: str,
        previous_credential_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Move a credential after another one.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.
            previous_credential_id: Credential that must come before it.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "move_user_credential_after",
                "post",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}/moveAfter/{segment(previous_credential_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def disable_user_credential_types(self, user_id: str, credential_types: list[str]) -> KeycloakUpdateResultDTO:
        """Disable credential types of a user.

        Args:
            user_id: User identifier.
            credential_types: Credential types to disable, such as ``password``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "disable_user_credential_types",
                "put",
                f"/users/{segment(user_id)}/disable-credential-types",
                body=credential_types,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_user_configured_credential_types(self, user_id: str) -> list[str]:
        """List the credential types a user has configured in user storage.

        Args:
            user_id: User identifier.

        Returns:
            The credential types.
        """
        return self._admin_request(
            "get_user_configured_credential_types",
            "get",
            f"/users/{segment(user_id)}/configured-user-storage-credential-types",
            expected=(HTTPStatus.OK,),
        )

    def get_user_consents(self, user_id: str) -> list[KeycloakUserConsentDTO]:
        """List the client consents of a user.

        Args:
            user_id: User identifier.

        Returns:
            The consents.
        """
        return to_dto_list(
            KeycloakUserConsentDTO,
            self._admin_request(
                "get_user_consents",
                "get",
                f"/users/{segment(user_id)}/consents",
                expected=(HTTPStatus.OK,),
            ),
        )

    def revoke_user_consent(self, user_id: str, client_id: str) -> KeycloakDeleteResultDTO:
        """Revoke the consent a user gave to a client.

        Args:
            user_id: User identifier.
            client_id: Client ID (not the UUID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "revoke_user_consent",
                "delete",
                f"/users/{segment(user_id)}/consents/{segment(client_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_user_federated_identities(self, user_id: str) -> list[KeycloakFederatedIdentityDTO]:
        """List the identity provider links of a user.

        Args:
            user_id: User identifier.

        Returns:
            The links.
        """
        return to_dto_list(
            KeycloakFederatedIdentityDTO,
            self._admin_request(
                "get_user_federated_identities",
                "get",
                f"/users/{segment(user_id)}/federated-identity",
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_user_federated_identity(
        self,
        user_id: str,
        provider: str,
        payload: KeycloakFederatedIdentityRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Link a user to an identity provider account.

        Args:
            user_id: User identifier.
            provider: Identity provider alias.
            payload: The external account.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_user_federated_identity",
                "post",
                f"/users/{segment(user_id)}/federated-identity/{segment(provider)}",
                body=to_request_payload(payload),
                expected=(
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.CREATED,
                ),
            ),
        )

    def remove_user_federated_identity(self, user_id: str, provider: str) -> KeycloakDeleteResultDTO:
        """Remove the link between a user and an identity provider.

        Args:
            user_id: User identifier.
            provider: Identity provider alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "remove_user_federated_identity",
                "delete",
                f"/users/{segment(user_id)}/federated-identity/{segment(provider)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_user_sessions(self, user_id: str) -> list[KeycloakUserSessionDTO]:
        """List the active sessions of a user.

        Args:
            user_id: User identifier.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            self._admin_request(
                "get_user_sessions",
                "get",
                f"/users/{segment(user_id)}/sessions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_offline_sessions(self, user_id: str, client_uuid: str) -> list[KeycloakUserSessionDTO]:
        """List the offline sessions of a user for a client.

        Args:
            user_id: User identifier.
            client_uuid: Client UUID.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            self._admin_request(
                "get_user_offline_sessions",
                "get",
                f"/users/{segment(user_id)}/offline-sessions/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_user_unmanaged_attributes(self, user_id: str) -> dict[str, list[str]]:
        """Get the attributes of a user that the user profile does not manage.

        Args:
            user_id: User identifier.

        Returns:
            The attributes.
        """
        return self._admin_request(
            "get_user_unmanaged_attributes",
            "get",
            f"/users/{segment(user_id)}/unmanagedAttributes",
            expected=(HTTPStatus.OK,),
        )

    def impersonate_user(self, user_id: str) -> KeycloakImpersonationDTO:
        """Start an impersonation session for a user.

        Args:
            user_id: User identifier.

        Returns:
            Where to continue as the user.
        """
        return to_dto(
            KeycloakImpersonationDTO,
            self._admin_request(
                "impersonate_user",
                "post",
                f"/users/{segment(user_id)}/impersonation",
                expected=(HTTPStatus.OK,),
            ),
        )

    def execute_user_actions_email(
        self,
        user_id: str,
        actions: list[str],
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a link to perform required actions. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            actions: Required actions, such as ``UPDATE_PASSWORD``.
            query: Optional query parameters: ``client_id``, ``lifespan`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "execute_user_actions_email",
                "put",
                f"/users/{segment(user_id)}/execute-actions-email",
                body=actions,
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def send_user_verify_email(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakUpdateResultDTO:
        """Email a user an address verification link. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            query: Optional query parameters: ``client_id``, ``lifespan`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "send_user_verify_email",
                "put",
                f"/users/{segment(user_id)}/send-verify-email",
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def send_user_reset_password_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a password reset link. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            query: Optional query parameters: ``client_id`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "send_user_reset_password_email",
                "put",
                f"/users/{segment(user_id)}/reset-password-email",
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakUsersMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for user operations."""

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_id(self, user_id: str) -> KeycloakUserDTO | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return to_dto_or_none(KeycloakUserDTO, await self.admin_adapter.a_get_user(user_id))
        except KeycloakGetError as e:
            if e.response_code == HTTP_NOT_FOUND:
                return None
            raise InternalError() from e
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_username(self, username: str) -> KeycloakUserDTO | None:
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
            return to_dto_or_none(KeycloakUserDTO, users[0] if users else None)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_username")

    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_email(self, email: str) -> KeycloakUserDTO | None:
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
            return to_dto_or_none(KeycloakUserDTO, users[0] if users else None)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    async def create_user(self, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> str | None:
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
            user_id = await self.admin_adapter.a_create_user(to_request_payload(user_data))

            # Clear related caches
            self.clear_all_caches()
        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", to_request_payload(user_data))
        else:
            return user_id

    async def update_user(self, user_id: str, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_update_user(user_id, to_request_payload(user_data))

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
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserDTO]:
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

            return to_dto_list(KeycloakUserDTO, users[:max_results])
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

    async def get_users(self, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List users, filtered by any of the admin API user query parameters.

        Args:
            query: Optional query parameters such as ``search``, ``email``, ``enabled``, ``first`` and ``max``.

        Returns:
            The users.
        """
        return to_dto_list(
            KeycloakUserDTO,
            await self._async_admin_request(
                "get_users",
                "get",
                "/users",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def count_users(self, query: dict[str, Any] | None = None) -> int:
        """Count the users matching the query.

        Args:
            query: Optional query parameters such as ``search``, ``email`` and ``enabled``.

        Returns:
            The number of users.
        """
        return await self._async_admin_request(
            "count_users",
            "get",
            "/users/count",
            params=query,
            expected=(HTTPStatus.OK,),
        )

    async def get_user_profile_config(self) -> KeycloakUserProfileConfigDTO:
        """Get the realm's user profile configuration.

        Args:
            (none)

        Returns:
            The user profile configuration.
        """
        return to_dto(
            KeycloakUserProfileConfigDTO,
            await self._async_admin_request(
                "get_user_profile_config",
                "get",
                "/users/profile",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_user_profile_config(
        self,
        config: KeycloakUserProfileConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUserProfileConfigDTO:
        """Replace the realm's user profile configuration.

        Args:
            config: The user profile configuration.

        Returns:
            The stored configuration.
        """
        return to_dto(
            KeycloakUserProfileConfigDTO,
            await self._async_admin_request(
                "update_user_profile_config",
                "put",
                "/users/profile",
                body=to_request_payload(config),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_profile_metadata(self) -> KeycloakUserProfileMetadataDTO:
        """Get the user profile metadata of the realm.

        Args:
            (none)

        Returns:
            The metadata.
        """
        return to_dto(
            KeycloakUserProfileMetadataDTO,
            await self._async_admin_request(
                "get_user_profile_metadata",
                "get",
                "/users/profile/metadata",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups a user belongs to.

        Args:
            user_id: User identifier.
            query: Optional query parameters such as ``search``, ``first``, ``max`` and ``briefRepresentation``.

        Returns:
            The groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_user_groups",
                "get",
                f"/users/{segment(user_id)}/groups",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def count_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Count the groups a user belongs to.

        Args:
            user_id: User identifier.
            query: Optional query parameters such as ``search``.

        Returns:
            The count.
        """
        return to_dto(
            KeycloakGroupsCountDTO,
            await self._async_admin_request(
                "count_user_groups",
                "get",
                f"/users/{segment(user_id)}/groups/count",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_credentials(self, user_id: str) -> list[KeycloakCredentialDTO]:
        """List the credentials of a user.

        Args:
            user_id: User identifier.

        Returns:
            The credentials.
        """
        return to_dto_list(
            KeycloakCredentialDTO,
            await self._async_admin_request(
                "get_user_credentials",
                "get",
                f"/users/{segment(user_id)}/credentials",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_user_credential(self, user_id: str, credential_id: str) -> KeycloakDeleteResultDTO:
        """Delete a credential of a user.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_user_credential",
                "delete",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def move_user_credential_to_first(self, user_id: str, credential_id: str) -> KeycloakUpdateResultDTO:
        """Move a credential to the top of the user's credential list.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "move_user_credential_to_first",
                "post",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}/moveToFirst",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def move_user_credential_after(
        self,
        user_id: str,
        credential_id: str,
        previous_credential_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Move a credential after another one.

        Args:
            user_id: User identifier.
            credential_id: Credential identifier.
            previous_credential_id: Credential that must come before it.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "move_user_credential_after",
                "post",
                f"/users/{segment(user_id)}/credentials/{segment(credential_id)}/moveAfter/{segment(previous_credential_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def disable_user_credential_types(self, user_id: str, credential_types: list[str]) -> KeycloakUpdateResultDTO:
        """Disable credential types of a user.

        Args:
            user_id: User identifier.
            credential_types: Credential types to disable, such as ``password``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "disable_user_credential_types",
                "put",
                f"/users/{segment(user_id)}/disable-credential-types",
                body=credential_types,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_user_configured_credential_types(self, user_id: str) -> list[str]:
        """List the credential types a user has configured in user storage.

        Args:
            user_id: User identifier.

        Returns:
            The credential types.
        """
        return await self._async_admin_request(
            "get_user_configured_credential_types",
            "get",
            f"/users/{segment(user_id)}/configured-user-storage-credential-types",
            expected=(HTTPStatus.OK,),
        )

    async def get_user_consents(self, user_id: str) -> list[KeycloakUserConsentDTO]:
        """List the client consents of a user.

        Args:
            user_id: User identifier.

        Returns:
            The consents.
        """
        return to_dto_list(
            KeycloakUserConsentDTO,
            await self._async_admin_request(
                "get_user_consents",
                "get",
                f"/users/{segment(user_id)}/consents",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def revoke_user_consent(self, user_id: str, client_id: str) -> KeycloakDeleteResultDTO:
        """Revoke the consent a user gave to a client.

        Args:
            user_id: User identifier.
            client_id: Client ID (not the UUID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "revoke_user_consent",
                "delete",
                f"/users/{segment(user_id)}/consents/{segment(client_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_user_federated_identities(self, user_id: str) -> list[KeycloakFederatedIdentityDTO]:
        """List the identity provider links of a user.

        Args:
            user_id: User identifier.

        Returns:
            The links.
        """
        return to_dto_list(
            KeycloakFederatedIdentityDTO,
            await self._async_admin_request(
                "get_user_federated_identities",
                "get",
                f"/users/{segment(user_id)}/federated-identity",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_user_federated_identity(
        self,
        user_id: str,
        provider: str,
        payload: KeycloakFederatedIdentityRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Link a user to an identity provider account.

        Args:
            user_id: User identifier.
            provider: Identity provider alias.
            payload: The external account.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_user_federated_identity",
                "post",
                f"/users/{segment(user_id)}/federated-identity/{segment(provider)}",
                body=to_request_payload(payload),
                expected=(
                    HTTPStatus.NO_CONTENT,
                    HTTPStatus.CREATED,
                ),
            ),
        )

    async def remove_user_federated_identity(self, user_id: str, provider: str) -> KeycloakDeleteResultDTO:
        """Remove the link between a user and an identity provider.

        Args:
            user_id: User identifier.
            provider: Identity provider alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "remove_user_federated_identity",
                "delete",
                f"/users/{segment(user_id)}/federated-identity/{segment(provider)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_user_sessions(self, user_id: str) -> list[KeycloakUserSessionDTO]:
        """List the active sessions of a user.

        Args:
            user_id: User identifier.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            await self._async_admin_request(
                "get_user_sessions",
                "get",
                f"/users/{segment(user_id)}/sessions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_offline_sessions(self, user_id: str, client_uuid: str) -> list[KeycloakUserSessionDTO]:
        """List the offline sessions of a user for a client.

        Args:
            user_id: User identifier.
            client_uuid: Client UUID.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            await self._async_admin_request(
                "get_user_offline_sessions",
                "get",
                f"/users/{segment(user_id)}/offline-sessions/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_user_unmanaged_attributes(self, user_id: str) -> dict[str, list[str]]:
        """Get the attributes of a user that the user profile does not manage.

        Args:
            user_id: User identifier.

        Returns:
            The attributes.
        """
        return await self._async_admin_request(
            "get_user_unmanaged_attributes",
            "get",
            f"/users/{segment(user_id)}/unmanagedAttributes",
            expected=(HTTPStatus.OK,),
        )

    async def impersonate_user(self, user_id: str) -> KeycloakImpersonationDTO:
        """Start an impersonation session for a user.

        Args:
            user_id: User identifier.

        Returns:
            Where to continue as the user.
        """
        return to_dto(
            KeycloakImpersonationDTO,
            await self._async_admin_request(
                "impersonate_user",
                "post",
                f"/users/{segment(user_id)}/impersonation",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def execute_user_actions_email(
        self,
        user_id: str,
        actions: list[str],
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a link to perform required actions. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            actions: Required actions, such as ``UPDATE_PASSWORD``.
            query: Optional query parameters: ``client_id``, ``lifespan`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "execute_user_actions_email",
                "put",
                f"/users/{segment(user_id)}/execute-actions-email",
                body=actions,
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def send_user_verify_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user an address verification link. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            query: Optional query parameters: ``client_id``, ``lifespan`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "send_user_verify_email",
                "put",
                f"/users/{segment(user_id)}/send-verify-email",
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def send_user_reset_password_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a password reset link. Needs SMTP configured on the realm.

        Args:
            user_id: User identifier.
            query: Optional query parameters: ``client_id`` and ``redirect_uri``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "send_user_reset_password_email",
                "put",
                f"/users/{segment(user_id)}/reset-password-email",
                params=query,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
