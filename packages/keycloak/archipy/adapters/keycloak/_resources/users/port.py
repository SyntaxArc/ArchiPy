"""Keycloak port mixins for user operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.user_dtos import (
    KeycloakUserDTO,
    KeycloakUserRequestDTO,
)

if TYPE_CHECKING:
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


class KeycloakUsersPort:
    """Sync Keycloak port interface for user operations."""

    @abstractmethod
    def get_user_by_id(self, user_id: str) -> KeycloakUserDTO | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_username(self, username: str) -> KeycloakUserDTO | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    def get_user_by_email(self, email: str) -> KeycloakUserDTO | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    def create_user(self, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    def update_user(self, user_id: str, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserDTO]:
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

    @abstractmethod
    def get_users(self, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List users, filtered by any of the admin API user query parameters."""
        raise NotImplementedError

    @abstractmethod
    def count_users(self, query: dict[str, Any] | None = None) -> int:
        """Count the users matching the query."""
        raise NotImplementedError

    @abstractmethod
    def get_user_profile_config(self) -> KeycloakUserProfileConfigDTO:
        """Get the realm's user profile configuration."""
        raise NotImplementedError

    @abstractmethod
    def update_user_profile_config(
        self,
        config: KeycloakUserProfileConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUserProfileConfigDTO:
        """Replace the realm's user profile configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_user_profile_metadata(self) -> KeycloakUserProfileMetadataDTO:
        """Get the user profile metadata of the realm."""
        raise NotImplementedError

    @abstractmethod
    def get_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups a user belongs to."""
        raise NotImplementedError

    @abstractmethod
    def count_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Count the groups a user belongs to."""
        raise NotImplementedError

    @abstractmethod
    def get_user_credentials(self, user_id: str) -> list[KeycloakCredentialDTO]:
        """List the credentials of a user."""
        raise NotImplementedError

    @abstractmethod
    def delete_user_credential(self, user_id: str, credential_id: str) -> KeycloakDeleteResultDTO:
        """Delete a credential of a user."""
        raise NotImplementedError

    @abstractmethod
    def move_user_credential_to_first(self, user_id: str, credential_id: str) -> KeycloakUpdateResultDTO:
        """Move a credential to the top of the user's credential list."""
        raise NotImplementedError

    @abstractmethod
    def move_user_credential_after(
        self,
        user_id: str,
        credential_id: str,
        previous_credential_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Move a credential after another one."""
        raise NotImplementedError

    @abstractmethod
    def disable_user_credential_types(self, user_id: str, credential_types: list[str]) -> KeycloakUpdateResultDTO:
        """Disable credential types of a user."""
        raise NotImplementedError

    @abstractmethod
    def get_user_configured_credential_types(self, user_id: str) -> list[str]:
        """List the credential types a user has configured in user storage."""
        raise NotImplementedError

    @abstractmethod
    def get_user_consents(self, user_id: str) -> list[KeycloakUserConsentDTO]:
        """List the client consents of a user."""
        raise NotImplementedError

    @abstractmethod
    def revoke_user_consent(self, user_id: str, client_id: str) -> KeycloakDeleteResultDTO:
        """Revoke the consent a user gave to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_user_federated_identities(self, user_id: str) -> list[KeycloakFederatedIdentityDTO]:
        """List the identity provider links of a user."""
        raise NotImplementedError

    @abstractmethod
    def add_user_federated_identity(
        self,
        user_id: str,
        provider: str,
        payload: KeycloakFederatedIdentityRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Link a user to an identity provider account."""
        raise NotImplementedError

    @abstractmethod
    def remove_user_federated_identity(self, user_id: str, provider: str) -> KeycloakDeleteResultDTO:
        """Remove the link between a user and an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def get_user_sessions(self, user_id: str) -> list[KeycloakUserSessionDTO]:
        """List the active sessions of a user."""
        raise NotImplementedError

    @abstractmethod
    def get_user_offline_sessions(self, user_id: str, client_uuid: str) -> list[KeycloakUserSessionDTO]:
        """List the offline sessions of a user for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_user_unmanaged_attributes(self, user_id: str) -> dict[str, list[str]]:
        """Get the attributes of a user that the user profile does not manage."""
        raise NotImplementedError

    @abstractmethod
    def impersonate_user(self, user_id: str) -> KeycloakImpersonationDTO:
        """Start an impersonation session for a user."""
        raise NotImplementedError

    @abstractmethod
    def execute_user_actions_email(
        self,
        user_id: str,
        actions: list[str],
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a link to perform required actions. Needs SMTP configured on the realm."""
        raise NotImplementedError

    @abstractmethod
    def send_user_verify_email(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakUpdateResultDTO:
        """Email a user an address verification link. Needs SMTP configured on the realm."""
        raise NotImplementedError

    @abstractmethod
    def send_user_reset_password_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a password reset link. Needs SMTP configured on the realm."""
        raise NotImplementedError


class AsyncKeycloakUsersPort:
    """Async Keycloak port interface for user operations."""

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> KeycloakUserDTO | None:
        """Get user details by user ID."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_username(self, username: str) -> KeycloakUserDTO | None:
        """Get user details by username."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_by_email(self, email: str) -> KeycloakUserDTO | None:
        """Get user details by email."""
        raise NotImplementedError

    @abstractmethod
    async def create_user(self, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> str | None:
        """Create a new user in Keycloak."""
        raise NotImplementedError

    @abstractmethod
    async def update_user(self, user_id: str, user_data: KeycloakUserRequestDTO | dict[str, Any]) -> None:
        """Update user details."""
        raise NotImplementedError

    @abstractmethod
    async def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password."""
        raise NotImplementedError

    @abstractmethod
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserDTO]:
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

    @abstractmethod
    async def get_users(self, query: dict[str, Any] | None = None) -> list[KeycloakUserDTO]:
        """List users, filtered by any of the admin API user query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def count_users(self, query: dict[str, Any] | None = None) -> int:
        """Count the users matching the query."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_profile_config(self) -> KeycloakUserProfileConfigDTO:
        """Get the realm's user profile configuration."""
        raise NotImplementedError

    @abstractmethod
    async def update_user_profile_config(
        self,
        config: KeycloakUserProfileConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUserProfileConfigDTO:
        """Replace the realm's user profile configuration."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_profile_metadata(self) -> KeycloakUserProfileMetadataDTO:
        """Get the user profile metadata of the realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> list[KeycloakGroupDTO]:
        """List the groups a user belongs to."""
        raise NotImplementedError

    @abstractmethod
    async def count_user_groups(self, user_id: str, query: dict[str, Any] | None = None) -> KeycloakGroupsCountDTO:
        """Count the groups a user belongs to."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_credentials(self, user_id: str) -> list[KeycloakCredentialDTO]:
        """List the credentials of a user."""
        raise NotImplementedError

    @abstractmethod
    async def delete_user_credential(self, user_id: str, credential_id: str) -> KeycloakDeleteResultDTO:
        """Delete a credential of a user."""
        raise NotImplementedError

    @abstractmethod
    async def move_user_credential_to_first(self, user_id: str, credential_id: str) -> KeycloakUpdateResultDTO:
        """Move a credential to the top of the user's credential list."""
        raise NotImplementedError

    @abstractmethod
    async def move_user_credential_after(
        self,
        user_id: str,
        credential_id: str,
        previous_credential_id: str,
    ) -> KeycloakUpdateResultDTO:
        """Move a credential after another one."""
        raise NotImplementedError

    @abstractmethod
    async def disable_user_credential_types(self, user_id: str, credential_types: list[str]) -> KeycloakUpdateResultDTO:
        """Disable credential types of a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_configured_credential_types(self, user_id: str) -> list[str]:
        """List the credential types a user has configured in user storage."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_consents(self, user_id: str) -> list[KeycloakUserConsentDTO]:
        """List the client consents of a user."""
        raise NotImplementedError

    @abstractmethod
    async def revoke_user_consent(self, user_id: str, client_id: str) -> KeycloakDeleteResultDTO:
        """Revoke the consent a user gave to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_federated_identities(self, user_id: str) -> list[KeycloakFederatedIdentityDTO]:
        """List the identity provider links of a user."""
        raise NotImplementedError

    @abstractmethod
    async def add_user_federated_identity(
        self,
        user_id: str,
        provider: str,
        payload: KeycloakFederatedIdentityRequestDTO | dict[str, Any],
    ) -> KeycloakAssignResultDTO:
        """Link a user to an identity provider account."""
        raise NotImplementedError

    @abstractmethod
    async def remove_user_federated_identity(self, user_id: str, provider: str) -> KeycloakDeleteResultDTO:
        """Remove the link between a user and an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_sessions(self, user_id: str) -> list[KeycloakUserSessionDTO]:
        """List the active sessions of a user."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_offline_sessions(self, user_id: str, client_uuid: str) -> list[KeycloakUserSessionDTO]:
        """List the offline sessions of a user for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_unmanaged_attributes(self, user_id: str) -> dict[str, list[str]]:
        """Get the attributes of a user that the user profile does not manage."""
        raise NotImplementedError

    @abstractmethod
    async def impersonate_user(self, user_id: str) -> KeycloakImpersonationDTO:
        """Start an impersonation session for a user."""
        raise NotImplementedError

    @abstractmethod
    async def execute_user_actions_email(
        self,
        user_id: str,
        actions: list[str],
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a link to perform required actions. Needs SMTP configured on the realm."""
        raise NotImplementedError

    @abstractmethod
    async def send_user_verify_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user an address verification link. Needs SMTP configured on the realm."""
        raise NotImplementedError

    @abstractmethod
    async def send_user_reset_password_email(
        self,
        user_id: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUpdateResultDTO:
        """Email a user a password reset link. Needs SMTP configured on the realm."""
        raise NotImplementedError
