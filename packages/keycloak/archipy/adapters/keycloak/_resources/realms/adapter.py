"""Keycloak adapter mixins for realm operations."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from keycloak.exceptions import (
    KeycloakError,
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
from archipy.helpers.utils.string_utils import StringUtils
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

logger = logging.getLogger(__name__)


def _realm_update_payload(config: KeycloakRealmRequestDTO | None, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Merge an optional realm DTO with keyword overrides into a RealmRepresentation payload."""
    return {**(config.to_payload() if config is not None else {}), **kwargs}


class KeycloakRealmsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for realm operations."""

    def create_realm(
        self,
        realm_name: str,
        skip_exists: bool = True,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
            config: Optional request DTO; keyword arguments override its values.
            kwargs: Additional optional configurations for the realm

        Returns:
            Realm details
        """
        payload = {
            "realm": realm_name,
            "enabled": kwargs.get("enabled", True),
            "displayName": kwargs.get("display_name", realm_name),
        }

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            # Skip display_name as it's already handled
            if key == "display_name":
                continue

            # Convert Python snake_case to Keycloak camelCase
            camel_key = StringUtils.snake_to_camel_case(key)
            payload[camel_key] = value

        if config is not None:
            payload = {**payload, **config.to_payload()}

        try:
            self.admin_adapter.create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug("Failed to create realm: %s", e)

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return to_dto_or_none(
                        KeycloakRealmDTO,
                        {"realm": realm_name, "status": "already_exists", "config": payload},
                    )

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return to_dto_or_none(KeycloakRealmDTO, {"realm": realm_name, "status": "created", "config": payload})

    def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details
        """
        try:
            return to_dto_or_none(KeycloakRealmDTO, self.admin_adapter.get_realm(realm_name))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    def update_realm(
        self,
        realm_name: str,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Update a realm. Kwargs are RealmRepresentation.

        Args:
            realm_name: Realm name (not the realm id).
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: RealmRepresentation attributes to update (e.g. displayName).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return to_dto_or_none(
                KeycloakRealmDTO,
                self.admin_adapter.update_realm(realm_name, _realm_update_payload(config, kwargs)),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")

    def get_realms(self, brief_representation: bool = False) -> list[KeycloakRealmDTO]:
        """List every realm the admin user can see.

        Args:
            brief_representation: Return only the basic realm fields.

        Returns:
            The realms.
        """
        return to_dto_list(
            KeycloakRealmDTO,
            self._admin_request(
                "get_realms",
                "get",
                "",
                realm="",
                params={"briefRepresentation": brief_representation},
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_realm(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm",
                "delete",
                "",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_events(self, realm_name: str, query: dict[str, Any] | None = None) -> list[KeycloakEventDTO]:
        """List the user events of a realm.

        Args:
            realm_name: Realm name.
            query: Optional query parameters:
                ``type``, ``user``, ``client``, ``dateFrom``, ``dateTo``, ``first`` and ``max``.

        Returns:
            The events.
        """
        return to_dto_list(
            KeycloakEventDTO,
            self._admin_request(
                "get_realm_events",
                "get",
                "/events",
                realm=realm_name,
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_realm_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all user events of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_events",
                "delete",
                "/events",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_admin_events(
        self,
        realm_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAdminEventDTO]:
        """List the admin events of a realm.

        Args:
            realm_name: Realm name.
            query: Optional query parameters:
                ``operationTypes``, ``resourceTypes``, ``resourcePath``, ``dateFrom``, ``dateTo``,
                ``first`` and ``max``.

        Returns:
            The admin events.
        """
        return to_dto_list(
            KeycloakAdminEventDTO,
            self._admin_request(
                "get_realm_admin_events",
                "get",
                "/admin-events",
                realm=realm_name,
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_realm_admin_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all admin events of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_admin_events",
                "delete",
                "/admin-events",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_events_config(self, realm_name: str) -> KeycloakRealmEventsConfigDTO:
        """Get the event settings of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The event settings.
        """
        return to_dto(
            KeycloakRealmEventsConfigDTO,
            self._admin_request(
                "get_realm_events_config",
                "get",
                "/events/config",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_events_config(
        self,
        realm_name: str,
        config: KeycloakRealmEventsConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the event settings of a realm.

        Args:
            realm_name: Realm name.
            config: Event settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_events_config",
                "put",
                "/events/config",
                realm=realm_name,
                body=to_request_payload(config),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_client_policies(
        self,
        realm_name: str,
        include_global_policies: bool = False,
    ) -> KeycloakClientPoliciesDTO:
        """Get the client policies of a realm.

        Args:
            realm_name: Realm name.
            include_global_policies: Also return the built-in policies.

        Returns:
            The client policies.
        """
        return to_dto(
            KeycloakClientPoliciesDTO,
            self._admin_request(
                "get_realm_client_policies",
                "get",
                "/client-policies/policies",
                realm=realm_name,
                params={"include-global-policies": include_global_policies},
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_client_policies(
        self,
        realm_name: str,
        policies: KeycloakClientPoliciesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client policies of a realm.

        Args:
            realm_name: Realm name.
            policies: Client policies.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_client_policies",
                "put",
                "/client-policies/policies",
                realm=realm_name,
                body=to_request_payload(policies),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_client_profiles(
        self,
        realm_name: str,
        include_global_profiles: bool = False,
    ) -> KeycloakClientProfilesDTO:
        """Get the client profiles of a realm.

        Args:
            realm_name: Realm name.
            include_global_profiles: Also return the built-in profiles.

        Returns:
            The client profiles.
        """
        return to_dto(
            KeycloakClientProfilesDTO,
            self._admin_request(
                "get_realm_client_profiles",
                "get",
                "/client-policies/profiles",
                realm=realm_name,
                params={"include-global-profiles": include_global_profiles},
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_client_profiles(
        self,
        realm_name: str,
        profiles: KeycloakClientProfilesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client profiles of a realm.

        Args:
            realm_name: Realm name.
            profiles: Client profiles.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_client_profiles",
                "put",
                "/client-policies/profiles",
                realm=realm_name,
                body=to_request_payload(profiles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_client_types(self, realm_name: str) -> KeycloakClientTypesDTO:
        """Get the client types of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The client types.
        """
        return to_dto(
            KeycloakClientTypesDTO,
            self._admin_request(
                "get_realm_client_types",
                "get",
                "/client-types",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_client_types(
        self,
        realm_name: str,
        client_types: KeycloakClientTypesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client types of a realm.

        Args:
            realm_name: Realm name.
            client_types: Client types.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_client_types",
                "put",
                "/client-types",
                realm=realm_name,
                body=to_request_payload(client_types),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_client_session_stats(self, realm_name: str) -> list[KeycloakClientSessionStatDTO]:
        """Get the session counts of every client of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The session counts per client.
        """
        return to_dto_list(
            KeycloakClientSessionStatDTO,
            self._admin_request(
                "get_realm_client_session_stats",
                "get",
                "/client-session-stats",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_realm_credential_registrators(self, realm_name: str) -> list[str]:
        """List the required actions that register credentials.

        Args:
            realm_name: Realm name.

        Returns:
            The required action ids.
        """
        return self._admin_request(
            "get_realm_credential_registrators",
            "get",
            "/credential-registrators",
            realm=realm_name,
            expected=(HTTPStatus.OK,),
        )

    def get_realm_default_groups(self, realm_name: str) -> list[KeycloakGroupDTO]:
        """List the groups new users of a realm join by default.

        Args:
            realm_name: Realm name.

        Returns:
            The default groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            self._admin_request(
                "get_realm_default_groups",
                "get",
                "/default-groups",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def add_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakAssignResultDTO:
        """Make a group a default group of a realm.

        Args:
            realm_name: Realm name.
            group_id: Group identifier.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "add_realm_default_group",
                "put",
                f"/default-groups/{segment(group_id)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def remove_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a group from the default groups of a realm.

        Args:
            realm_name: Realm name.
            group_id: Group identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "remove_realm_default_group",
                "delete",
                f"/default-groups/{segment(group_id)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_localization_locales(self, realm_name: str) -> list[str]:
        """List the locales that have realm localization texts.

        Args:
            realm_name: Realm name.

        Returns:
            The locales.
        """
        return self._admin_request(
            "get_realm_localization_locales",
            "get",
            "/localization",
            realm=realm_name,
            expected=(HTTPStatus.OK,),
        )

    def get_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        use_realm_default_locale_fallback: bool = False,
    ) -> dict[str, str]:
        """Get the localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            use_realm_default_locale_fallback: Fall back to the realm default locale.

        Returns:
            The texts by key.
        """
        return self._admin_request(
            "get_realm_localization_texts",
            "get",
            f"/localization/{segment(locale)}",
            realm=realm_name,
            params={"useRealmDefaultLocaleFallback": use_realm_default_locale_fallback},
            expected=(HTTPStatus.OK,),
        )

    def update_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        texts: dict[str, str],
    ) -> KeycloakUpdateResultDTO:
        """Add or replace localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            texts: Texts by key.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_realm_localization_texts",
                "post",
                f"/localization/{segment(locale)}",
                realm=realm_name,
                body=texts,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_realm_localization(self, realm_name: str, locale: str) -> KeycloakDeleteResultDTO:
        """Delete all localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_localization",
                "delete",
                f"/localization/{segment(locale)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_realm_localization_text(self, realm_name: str, locale: str, key: str) -> KeycloakDeleteResultDTO:
        """Delete one localization text.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            key: Text key.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_localization_text",
                "delete",
                f"/localization/{segment(locale)}/{segment(key)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def logout_all_realm_sessions(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Log out every user of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            self._admin_request(
                "logout_all_realm_sessions",
                "post",
                "/logout-all",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def push_realm_revocation(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Push the realm's revocation policy to the registered client nodes.

        Args:
            realm_name: Realm name.

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            self._admin_request(
                "push_realm_revocation",
                "post",
                "/push-revocation",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def partial_export_realm(
        self,
        realm_name: str,
        export_clients: bool = False,
        export_groups_and_roles: bool = False,
    ) -> KeycloakRealmDTO:
        """Export a realm without secrets.

        Args:
            realm_name: Realm name.
            export_clients: Include clients.
            export_groups_and_roles: Include groups and roles.

        Returns:
            The exported realm.
        """
        return to_dto(
            KeycloakRealmDTO,
            self._admin_request(
                "partial_export_realm",
                "post",
                "/partial-export",
                realm=realm_name,
                params={"exportClients": export_clients, "exportGroupsAndRoles": export_groups_and_roles},
                expected=(HTTPStatus.OK,),
            ),
        )

    def partial_import_realm(
        self,
        realm_name: str,
        payload: KeycloakPartialImportRequestDTO | dict[str, Any],
    ) -> KeycloakPartialImportResultDTO:
        """Import users, clients, groups, roles and identity providers into a realm.

        Args:
            realm_name: Realm name.
            payload: What to import and how to treat duplicates.

        Returns:
            Counts and one entry per resource.
        """
        return to_dto(
            KeycloakPartialImportResultDTO,
            self._admin_request(
                "partial_import_realm",
                "post",
                "/partialImport",
                realm=realm_name,
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_realm_session(
        self,
        realm_name: str,
        session_id: str,
        is_offline: bool = False,
    ) -> KeycloakDeleteResultDTO:
        """Delete one user session of a realm.

        Args:
            realm_name: Realm name.
            session_id: Session identifier.
            is_offline: The session is an offline session.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_realm_session",
                "delete",
                f"/sessions/{segment(session_id)}",
                realm=realm_name,
                params={"isOffline": is_offline},
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def test_realm_smtp_connection(self, realm_name: str, settings: dict[str, str]) -> KeycloakUpdateResultDTO:
        """Test the SMTP settings of a realm by sending a test email.

        Args:
            realm_name: Realm name.
            settings: SMTP settings, such as ``host``, ``port`` and ``from``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "test_realm_smtp_connection",
                "post",
                "/testSMTPConnection",
                realm=realm_name,
                body=settings,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_realm_users_management_permissions(self, realm_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of the realm's users.

        Args:
            realm_name: Realm name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_realm_users_management_permissions",
                "get",
                "/users-management-permissions",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_realm_users_management_permissions(
        self,
        realm_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of the realm's users.

        Args:
            realm_name: Realm name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_realm_users_management_permissions",
                "put",
                "/users-management-permissions",
                realm=realm_name,
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakRealmsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for realm operations."""

    async def create_realm(
        self,
        realm_name: str,
        skip_exists: bool = True,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
            config: Optional request DTO; keyword arguments override its values.
            kwargs: Additional optional configurations for the realm

        Returns:
            Dictionary with realm information and status

        Raises:
            InternalError: If realm creation fails
        """
        payload = {
            "realm": realm_name,
            "enabled": kwargs.get("enabled", True),
            "displayName": kwargs.get("display_name", realm_name),
        }

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            # Skip display_name as it's already handled
            if key == "display_name":
                continue

            # Convert Python snake_case to Keycloak camelCase
            camel_key = StringUtils.snake_to_camel_case(key)
            payload[camel_key] = value

        if config is not None:
            payload = {**payload, **config.to_payload()}

        try:
            await self.admin_adapter.a_create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug("Failed to create realm: %s", e)

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return to_dto_or_none(
                        KeycloakRealmDTO,
                        {"realm": realm_name, "status": "already_exists", "config": payload},
                    )

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return to_dto_or_none(KeycloakRealmDTO, {"realm": realm_name, "status": "created", "config": payload})

    async def get_realm(self, realm_name: str) -> KeycloakRealmDTO | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details

        Raises:
            InternalError: If getting realm fails
        """
        try:
            return to_dto_or_none(KeycloakRealmDTO, await self.admin_adapter.a_get_realm(realm_name))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    async def update_realm(
        self,
        realm_name: str,
        config: KeycloakRealmRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakRealmDTO | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).

        Args:
            realm_name: Realm name (not the realm id).
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: RealmRepresentation attributes to update (e.g. displayName, organizationsEnabled).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return to_dto_or_none(
                KeycloakRealmDTO,
                await self.admin_adapter.a_update_realm(realm_name, _realm_update_payload(config, kwargs)),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")

    async def get_realms(self, brief_representation: bool = False) -> list[KeycloakRealmDTO]:
        """List every realm the admin user can see.

        Args:
            brief_representation: Return only the basic realm fields.

        Returns:
            The realms.
        """
        return to_dto_list(
            KeycloakRealmDTO,
            await self._async_admin_request(
                "get_realms",
                "get",
                "",
                realm="",
                params={"briefRepresentation": brief_representation},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_realm(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm",
                "delete",
                "",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_events(self, realm_name: str, query: dict[str, Any] | None = None) -> list[KeycloakEventDTO]:
        """List the user events of a realm.

        Args:
            realm_name: Realm name.
            query: Optional query parameters:
                ``type``, ``user``, ``client``, ``dateFrom``, ``dateTo``, ``first`` and ``max``.

        Returns:
            The events.
        """
        return to_dto_list(
            KeycloakEventDTO,
            await self._async_admin_request(
                "get_realm_events",
                "get",
                "/events",
                realm=realm_name,
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_realm_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all user events of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_events",
                "delete",
                "/events",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_admin_events(
        self,
        realm_name: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakAdminEventDTO]:
        """List the admin events of a realm.

        Args:
            realm_name: Realm name.
            query: Optional query parameters:
                ``operationTypes``, ``resourceTypes``, ``resourcePath``, ``dateFrom``, ``dateTo``,
                ``first`` and ``max``.

        Returns:
            The admin events.
        """
        return to_dto_list(
            KeycloakAdminEventDTO,
            await self._async_admin_request(
                "get_realm_admin_events",
                "get",
                "/admin-events",
                realm=realm_name,
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_realm_admin_events(self, realm_name: str) -> KeycloakDeleteResultDTO:
        """Delete all admin events of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_admin_events",
                "delete",
                "/admin-events",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_events_config(self, realm_name: str) -> KeycloakRealmEventsConfigDTO:
        """Get the event settings of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The event settings.
        """
        return to_dto(
            KeycloakRealmEventsConfigDTO,
            await self._async_admin_request(
                "get_realm_events_config",
                "get",
                "/events/config",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_events_config(
        self,
        realm_name: str,
        config: KeycloakRealmEventsConfigRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update the event settings of a realm.

        Args:
            realm_name: Realm name.
            config: Event settings.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_events_config",
                "put",
                "/events/config",
                realm=realm_name,
                body=to_request_payload(config),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_client_policies(
        self,
        realm_name: str,
        include_global_policies: bool = False,
    ) -> KeycloakClientPoliciesDTO:
        """Get the client policies of a realm.

        Args:
            realm_name: Realm name.
            include_global_policies: Also return the built-in policies.

        Returns:
            The client policies.
        """
        return to_dto(
            KeycloakClientPoliciesDTO,
            await self._async_admin_request(
                "get_realm_client_policies",
                "get",
                "/client-policies/policies",
                realm=realm_name,
                params={"include-global-policies": include_global_policies},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_client_policies(
        self,
        realm_name: str,
        policies: KeycloakClientPoliciesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client policies of a realm.

        Args:
            realm_name: Realm name.
            policies: Client policies.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_client_policies",
                "put",
                "/client-policies/policies",
                realm=realm_name,
                body=to_request_payload(policies),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_client_profiles(
        self,
        realm_name: str,
        include_global_profiles: bool = False,
    ) -> KeycloakClientProfilesDTO:
        """Get the client profiles of a realm.

        Args:
            realm_name: Realm name.
            include_global_profiles: Also return the built-in profiles.

        Returns:
            The client profiles.
        """
        return to_dto(
            KeycloakClientProfilesDTO,
            await self._async_admin_request(
                "get_realm_client_profiles",
                "get",
                "/client-policies/profiles",
                realm=realm_name,
                params={"include-global-profiles": include_global_profiles},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_client_profiles(
        self,
        realm_name: str,
        profiles: KeycloakClientProfilesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client profiles of a realm.

        Args:
            realm_name: Realm name.
            profiles: Client profiles.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_client_profiles",
                "put",
                "/client-policies/profiles",
                realm=realm_name,
                body=to_request_payload(profiles),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_client_types(self, realm_name: str) -> KeycloakClientTypesDTO:
        """Get the client types of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The client types.
        """
        return to_dto(
            KeycloakClientTypesDTO,
            await self._async_admin_request(
                "get_realm_client_types",
                "get",
                "/client-types",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_client_types(
        self,
        realm_name: str,
        client_types: KeycloakClientTypesRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Replace the client types of a realm.

        Args:
            realm_name: Realm name.
            client_types: Client types.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_client_types",
                "put",
                "/client-types",
                realm=realm_name,
                body=to_request_payload(client_types),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_client_session_stats(self, realm_name: str) -> list[KeycloakClientSessionStatDTO]:
        """Get the session counts of every client of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The session counts per client.
        """
        return to_dto_list(
            KeycloakClientSessionStatDTO,
            await self._async_admin_request(
                "get_realm_client_session_stats",
                "get",
                "/client-session-stats",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_realm_credential_registrators(self, realm_name: str) -> list[str]:
        """List the required actions that register credentials.

        Args:
            realm_name: Realm name.

        Returns:
            The required action ids.
        """
        return await self._async_admin_request(
            "get_realm_credential_registrators",
            "get",
            "/credential-registrators",
            realm=realm_name,
            expected=(HTTPStatus.OK,),
        )

    async def get_realm_default_groups(self, realm_name: str) -> list[KeycloakGroupDTO]:
        """List the groups new users of a realm join by default.

        Args:
            realm_name: Realm name.

        Returns:
            The default groups.
        """
        return to_dto_list(
            KeycloakGroupDTO,
            await self._async_admin_request(
                "get_realm_default_groups",
                "get",
                "/default-groups",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def add_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakAssignResultDTO:
        """Make a group a default group of a realm.

        Args:
            realm_name: Realm name.
            group_id: Group identifier.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "add_realm_default_group",
                "put",
                f"/default-groups/{segment(group_id)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def remove_realm_default_group(self, realm_name: str, group_id: str) -> KeycloakDeleteResultDTO:
        """Remove a group from the default groups of a realm.

        Args:
            realm_name: Realm name.
            group_id: Group identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "remove_realm_default_group",
                "delete",
                f"/default-groups/{segment(group_id)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_localization_locales(self, realm_name: str) -> list[str]:
        """List the locales that have realm localization texts.

        Args:
            realm_name: Realm name.

        Returns:
            The locales.
        """
        return await self._async_admin_request(
            "get_realm_localization_locales",
            "get",
            "/localization",
            realm=realm_name,
            expected=(HTTPStatus.OK,),
        )

    async def get_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        use_realm_default_locale_fallback: bool = False,
    ) -> dict[str, str]:
        """Get the localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            use_realm_default_locale_fallback: Fall back to the realm default locale.

        Returns:
            The texts by key.
        """
        return await self._async_admin_request(
            "get_realm_localization_texts",
            "get",
            f"/localization/{segment(locale)}",
            realm=realm_name,
            params={"useRealmDefaultLocaleFallback": use_realm_default_locale_fallback},
            expected=(HTTPStatus.OK,),
        )

    async def update_realm_localization_texts(
        self,
        realm_name: str,
        locale: str,
        texts: dict[str, str],
    ) -> KeycloakUpdateResultDTO:
        """Add or replace localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            texts: Texts by key.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_realm_localization_texts",
                "post",
                f"/localization/{segment(locale)}",
                realm=realm_name,
                body=texts,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_realm_localization(self, realm_name: str, locale: str) -> KeycloakDeleteResultDTO:
        """Delete all localization texts of a locale.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_localization",
                "delete",
                f"/localization/{segment(locale)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_realm_localization_text(self, realm_name: str, locale: str, key: str) -> KeycloakDeleteResultDTO:
        """Delete one localization text.

        Args:
            realm_name: Realm name.
            locale: Locale, such as ``en``.
            key: Text key.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_localization_text",
                "delete",
                f"/localization/{segment(locale)}/{segment(key)}",
                realm=realm_name,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def logout_all_realm_sessions(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Log out every user of a realm.

        Args:
            realm_name: Realm name.

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            await self._async_admin_request(
                "logout_all_realm_sessions",
                "post",
                "/logout-all",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def push_realm_revocation(self, realm_name: str) -> KeycloakGlobalRequestResultDTO:
        """Push the realm's revocation policy to the registered client nodes.

        Args:
            realm_name: Realm name.

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            await self._async_admin_request(
                "push_realm_revocation",
                "post",
                "/push-revocation",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def partial_export_realm(
        self,
        realm_name: str,
        export_clients: bool = False,
        export_groups_and_roles: bool = False,
    ) -> KeycloakRealmDTO:
        """Export a realm without secrets.

        Args:
            realm_name: Realm name.
            export_clients: Include clients.
            export_groups_and_roles: Include groups and roles.

        Returns:
            The exported realm.
        """
        return to_dto(
            KeycloakRealmDTO,
            await self._async_admin_request(
                "partial_export_realm",
                "post",
                "/partial-export",
                realm=realm_name,
                params={"exportClients": export_clients, "exportGroupsAndRoles": export_groups_and_roles},
                expected=(HTTPStatus.OK,),
            ),
        )

    async def partial_import_realm(
        self,
        realm_name: str,
        payload: KeycloakPartialImportRequestDTO | dict[str, Any],
    ) -> KeycloakPartialImportResultDTO:
        """Import users, clients, groups, roles and identity providers into a realm.

        Args:
            realm_name: Realm name.
            payload: What to import and how to treat duplicates.

        Returns:
            Counts and one entry per resource.
        """
        return to_dto(
            KeycloakPartialImportResultDTO,
            await self._async_admin_request(
                "partial_import_realm",
                "post",
                "/partialImport",
                realm=realm_name,
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_realm_session(
        self,
        realm_name: str,
        session_id: str,
        is_offline: bool = False,
    ) -> KeycloakDeleteResultDTO:
        """Delete one user session of a realm.

        Args:
            realm_name: Realm name.
            session_id: Session identifier.
            is_offline: The session is an offline session.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_realm_session",
                "delete",
                f"/sessions/{segment(session_id)}",
                realm=realm_name,
                params={"isOffline": is_offline},
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def test_realm_smtp_connection(self, realm_name: str, settings: dict[str, str]) -> KeycloakUpdateResultDTO:
        """Test the SMTP settings of a realm by sending a test email.

        Args:
            realm_name: Realm name.
            settings: SMTP settings, such as ``host``, ``port`` and ``from``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "test_realm_smtp_connection",
                "post",
                "/testSMTPConnection",
                realm=realm_name,
                body=settings,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_realm_users_management_permissions(self, realm_name: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of the realm's users.

        Args:
            realm_name: Realm name.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_realm_users_management_permissions",
                "get",
                "/users-management-permissions",
                realm=realm_name,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_realm_users_management_permissions(
        self,
        realm_name: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of the realm's users.

        Args:
            realm_name: Realm name.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_realm_users_management_permissions",
                "put",
                "/users-management-permissions",
                realm=realm_name,
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )
