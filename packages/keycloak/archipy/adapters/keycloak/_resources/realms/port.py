"""Keycloak port mixins for realm operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.realm_dtos import KeycloakRealmDTO

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.client_evaluation_dtos import KeycloakGlobalRequestResultDTO
    from archipy.models.dtos.keycloak.client_policy_dtos import (
        KeycloakClientPoliciesDTO,
        KeycloakClientPoliciesRequestDTO,
        KeycloakClientProfilesDTO,
        KeycloakClientProfilesRequestDTO,
        KeycloakClientTypesDTO,
        KeycloakClientTypesRequestDTO,
    )
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakClientSessionStatDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.event_dtos import (
        KeycloakAdminEventDTO,
        KeycloakEventDTO,
        KeycloakRealmEventsConfigDTO,
        KeycloakRealmEventsConfigRequestDTO,
    )
    from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO
    from archipy.models.dtos.keycloak.management_permission_dtos import (
        KeycloakManagementPermissionDTO,
        KeycloakManagementPermissionRequestDTO,
    )
    from archipy.models.dtos.keycloak.partial_import_dtos import (
        KeycloakPartialImportRequestDTO,
        KeycloakPartialImportResultDTO,
    )
    from archipy.models.dtos.keycloak.realm_dtos import KeycloakRealmDTO, KeycloakRealmRequestDTO


class KeycloakRealmsPort:
    """Sync Keycloak port interface for realm operations."""

    @abstractmethod
    def create_realm(
        self,
        realm_name: str,
        skip_exists: bool = True,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    def update_realm(
        self,
        realm_name: str,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Update a realm.

        Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).
        """
        raise NotImplementedError

    @abstractmethod
    def get_realms(self, brief_representation: bool = False) -> list[KeycloakRealmDTO]:
        """List every realm the admin user can see."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_events(self, realm_name: str, query: dict[str, Any] | None = None) -> list[KeycloakEventDTO]:
        """List the user events of a realm."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all user events of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_admin_events(
        self,
        realm_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAdminEventDTO]:
        """List the admin events of a realm."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_admin_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all admin events of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_events_config(self, realm_name: str) -> KeycloakRealmEventsConfigDTO:
        """Get the event settings of a realm."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_events_config(
        self,
        realm_name: str,
        config: KeycloakRealmEventsConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the event settings of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_client_policies(
        self,
        realm_name: str,
        include_global_policies: bool = False,
    ) -> KeycloakClientPoliciesDTO:
        """Get the client policies of a realm."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_client_policies(
        self,
        realm_name: str,
        policies: KeycloakClientPoliciesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client policies of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_client_profiles(
        self,
        realm_name: str,
        include_global_profiles: bool = False,
    ) -> KeycloakClientProfilesDTO:
        """Get the client profiles of a realm."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_client_profiles(
        self,
        realm_name: str,
        profiles: KeycloakClientProfilesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client profiles of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_client_types(self, realm_name: str) -> KeycloakClientTypesDTO:
        """Get the client types of a realm."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_client_types(
        self,
        realm_name: str,
        client_types: KeycloakClientTypesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client types of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_client_session_stats(self, realm_name: str) -> list[KeycloakClientSessionStatDTO]:
        """Get the session counts of every client of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_credential_registrators(self, realm_name: str) -> list[str]:
        """List the required actions that register credentials."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_default_groups(self, realm_name: str) -> list[KeycloakGroupDTO]:
        """List the groups new users of a realm join by default."""
        raise NotImplementedError

    @abstractmethod
    def add_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakAssignResultDTO:
        """Make a group a default group of a realm."""
        raise NotImplementedError

    @abstractmethod
    def remove_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a group from the default groups of a realm."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_localization_locales(self, realm_name: str) -> list[str]:
        """List the locales that have realm localization texts."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        use_realm_default_locale_fallback: bool = False,
    ) -> dict[str, str]:
        """Get the localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        texts: dict[str, str],
    ) -> KeycloakUpdateResultDTO:
        """Add or replace localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_localization(self, realm_name: str, locale: str) -> KeycloakDeleteResultDTO:
        """Delete all localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_localization_text(self, realm_name: str, locale: str, key: str) -> KeycloakDeleteResultDTO:
        """Delete one localization text."""
        raise NotImplementedError

    @abstractmethod
    def logout_all_realm_sessions(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Log out every user of a realm."""
        raise NotImplementedError

    @abstractmethod
    def push_realm_revocation(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Push the realm's revocation policy to the registered client nodes."""
        raise NotImplementedError

    @abstractmethod
    def partial_export_realm(
        self,
        realm_name: str,
        export_clients: bool = False,
        export_groups_and_roles: bool = False,
    ) -> KeycloakRealmDTO:
        """Export a realm without secrets."""
        raise NotImplementedError

    @abstractmethod
    def partial_import_realm(
        self,
        realm_name: str,
        payload: KeycloakPartialImportRequestDTO | dict[str, Any],
    ) -> KeycloakPartialImportResultDTO:
        """Import users, clients, groups, roles and identity providers into a realm."""
        raise NotImplementedError

    @abstractmethod
    def delete_realm_session(
        self,
        realm_name: str,
        session_id: str,
        is_offline: bool = False,
    ) -> KeycloakDeleteResultDTO:
        """Delete one user session of a realm."""
        raise NotImplementedError

    @abstractmethod
    def test_realm_smtp_connection(self, realm_name: str, settings: dict[str, str]) -> KeycloakUpdateResultDTO:
        """Test the SMTP settings of a realm by sending a test email."""
        raise NotImplementedError

    @abstractmethod
    def get_realm_users_management_permissions(self, realm_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of the realm's users."""
        raise NotImplementedError

    @abstractmethod
    def update_realm_users_management_permissions(
        self,
        realm_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of the realm's users."""
        raise NotImplementedError


class AsyncKeycloakRealmsPort:
    """Async Keycloak port interface for realm operations."""

    @abstractmethod
    async def create_realm(
        self,
        realm_name: str,
        skip_exists: bool = True,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Create a new Keycloak realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm(
        self,
        realm_name: str,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Update a realm.

        Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).
        """
        raise NotImplementedError

    @abstractmethod
    async def get_realms(self, brief_representation: bool = False) -> list[KeycloakRealmDTO]:
        """List every realm the admin user can see."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_events(self, realm_name: str, query: dict[str, Any] | None = None) -> list[KeycloakEventDTO]:
        """List the user events of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all user events of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_admin_events(
        self,
        realm_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAdminEventDTO]:
        """List the admin events of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_admin_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all admin events of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_events_config(self, realm_name: str) -> KeycloakRealmEventsConfigDTO:
        """Get the event settings of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_events_config(
        self,
        realm_name: str,
        config: KeycloakRealmEventsConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the event settings of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_client_policies(
        self,
        realm_name: str,
        include_global_policies: bool = False,
    ) -> KeycloakClientPoliciesDTO:
        """Get the client policies of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_client_policies(
        self,
        realm_name: str,
        policies: KeycloakClientPoliciesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client policies of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_client_profiles(
        self,
        realm_name: str,
        include_global_profiles: bool = False,
    ) -> KeycloakClientProfilesDTO:
        """Get the client profiles of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_client_profiles(
        self,
        realm_name: str,
        profiles: KeycloakClientProfilesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client profiles of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_client_types(self, realm_name: str) -> KeycloakClientTypesDTO:
        """Get the client types of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_client_types(
        self,
        realm_name: str,
        client_types: KeycloakClientTypesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client types of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_client_session_stats(self, realm_name: str) -> list[KeycloakClientSessionStatDTO]:
        """Get the session counts of every client of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_credential_registrators(self, realm_name: str) -> list[str]:
        """List the required actions that register credentials."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_default_groups(self, realm_name: str) -> list[KeycloakGroupDTO]:
        """List the groups new users of a realm join by default."""
        raise NotImplementedError

    @abstractmethod
    async def add_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakAssignResultDTO:
        """Make a group a default group of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def remove_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a group from the default groups of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_localization_locales(self, realm_name: str) -> list[str]:
        """List the locales that have realm localization texts."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        use_realm_default_locale_fallback: bool = False,
    ) -> dict[str, str]:
        """Get the localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        texts: dict[str, str],
    ) -> KeycloakUpdateResultDTO:
        """Add or replace localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_localization(self, realm_name: str, locale: str) -> KeycloakDeleteResultDTO:
        """Delete all localization texts of a locale."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_localization_text(self, realm_name: str, locale: str, key: str) -> KeycloakDeleteResultDTO:
        """Delete one localization text."""
        raise NotImplementedError

    @abstractmethod
    async def logout_all_realm_sessions(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Log out every user of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def push_realm_revocation(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Push the realm's revocation policy to the registered client nodes."""
        raise NotImplementedError

    @abstractmethod
    async def partial_export_realm(
        self,
        realm_name: str,
        export_clients: bool = False,
        export_groups_and_roles: bool = False,
    ) -> KeycloakRealmDTO:
        """Export a realm without secrets."""
        raise NotImplementedError

    @abstractmethod
    async def partial_import_realm(
        self,
        realm_name: str,
        payload: KeycloakPartialImportRequestDTO | dict[str, Any],
    ) -> KeycloakPartialImportResultDTO:
        """Import users, clients, groups, roles and identity providers into a realm."""
        raise NotImplementedError

    @abstractmethod
    async def delete_realm_session(
        self,
        realm_name: str,
        session_id: str,
        is_offline: bool = False,
    ) -> KeycloakDeleteResultDTO:
        """Delete one user session of a realm."""
        raise NotImplementedError

    @abstractmethod
    async def test_realm_smtp_connection(self, realm_name: str, settings: dict[str, str]) -> KeycloakUpdateResultDTO:
        """Test the SMTP settings of a realm by sending a test email."""
        raise NotImplementedError

    @abstractmethod
    async def get_realm_users_management_permissions(self, realm_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of the realm's users."""
        raise NotImplementedError

    @abstractmethod
    async def update_realm_users_management_permissions(
        self,
        realm_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of the realm's users."""
        raise NotImplementedError
