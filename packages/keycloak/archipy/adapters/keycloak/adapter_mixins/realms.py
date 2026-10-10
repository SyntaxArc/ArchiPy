"""Keycloak adapter mixins for realm operations."""

from __future__ import annotations

import logging
from typing import Any

from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.helpers.utils.string_utils import StringUtils

logger = logging.getLogger(__name__)


class KeycloakRealmsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for realm operations."""

    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
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

        try:
            self.admin_adapter.create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug("Failed to create realm: %s", e)

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return {"realm": realm_name, "status": "already_exists", "config": payload}

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return {"realm": realm_name, "status": "created", "config": payload}

    def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details
        """
        try:
            return self.admin_adapter.get_realm(realm_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation.

        Args:
            realm_name: Realm name (not the realm id).
            **kwargs: RealmRepresentation attributes to update (e.g. displayName).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return self.admin_adapter.update_realm(realm_name, dict(kwargs))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")


class AsyncKeycloakRealmsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for realm operations."""

    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
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

        try:
            await self.admin_adapter.a_create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug("Failed to create realm: %s", e)

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return {"realm": realm_name, "status": "already_exists", "config": payload}

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return {"realm": realm_name, "status": "created", "config": payload}

    async def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details

        Raises:
            InternalError: If getting realm fails
        """
        try:
            return await self.admin_adapter.a_get_realm(realm_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    async def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).

        Args:
            realm_name: Realm name (not the realm id).
            **kwargs: RealmRepresentation attributes to update (e.g. displayName, organizationsEnabled).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return await self.admin_adapter.a_update_realm(realm_name, dict(kwargs))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")
