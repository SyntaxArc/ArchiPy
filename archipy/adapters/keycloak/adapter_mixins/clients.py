"""Keycloak adapter mixins for client operations."""

from __future__ import annotations

import logging
from typing import Any

from async_lru import alru_cache
from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.helpers.utils.string_utils import StringUtils

logger = logging.getLogger(__name__)


class KeycloakClientsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client operations."""

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = self.get_client_id(self.configs.CLIENT_ID)
            return self.admin_adapter.get_client_service_account_user(str(client_id)).get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = self.admin_adapter.get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return self.admin_adapter.get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            kwargs: Additional optional configurations for the client

        Returns:
            Client details
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            internal_client_id = None
            try:
                internal_client_id = self.admin_adapter.create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug(f"Failed to create client: {e!s}")

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return {
                            "client_id": client_id,
                            "status": "already_exists",
                            "realm": self.admin_adapter.connection.realm_name,
                        }

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return {
                "client_id": client_id,
                "internal_client_id": internal_client_id,
                "realm": self.admin_adapter.connection.realm_name,
                "status": "created",
            }

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm


class AsyncKeycloakClientsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client operations."""

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = await self.get_client_id(self.configs.CLIENT_ID)
            if client_id is None:
                return None
            service_account = await self.admin_adapter.a_get_client_service_account_user(client_id)
            return service_account.get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = await self.admin_adapter.a_get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return await self.admin_adapter.a_get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            kwargs: Additional optional configurations for the client

        Returns:
            Dictionary with client information

        Raises:
            InternalError: If client creation fails
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            internal_client_id = None
            try:
                internal_client_id = await self.admin_adapter.a_create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug(f"Failed to create client: {e!s}")

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return {
                            "client_id": client_id,
                            "status": "already_exists",
                            "realm": self.admin_adapter.connection.realm_name,
                        }

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return {
                "client_id": client_id,
                "internal_client_id": internal_client_id,
                "realm": self.admin_adapter.connection.realm_name,
                "status": "created",
            }

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm
