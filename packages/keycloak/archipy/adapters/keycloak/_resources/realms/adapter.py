"""Keycloak adapter mixins for realm operations."""

from __future__ import annotations

import logging
from typing import Any

from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    to_dto_or_none,
)
from archipy.helpers.utils.string_utils import StringUtils
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
