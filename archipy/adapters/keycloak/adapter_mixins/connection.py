"""Keycloak adapter mixins for connection/init operations."""

from __future__ import annotations

import logging
import time

from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakUMA
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
)
from keycloak.openid_connection import KeycloakOpenIDConnection

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import KeycloakConfig
from archipy.models.errors import (
    ConnectionTimeoutError,
    UnauthenticatedError,
    UnavailableError,
)

logger = logging.getLogger(__name__)


class KeycloakConnectionMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for connection/init operations."""

    def __init__(self, keycloak_configs: KeycloakConfig | None = None) -> None:
        """Initialize KeycloakAdapter with configuration.

        Args:
            keycloak_configs: Optional Keycloak configuration. If None, global config is used.
        """
        self.configs: KeycloakConfig = (
            BaseConfig.global_config().KEYCLOAK if keycloak_configs is None else keycloak_configs
        )

        # Initialize the OpenID client for authentication
        self._openid_adapter = self._get_openid_client(self.configs)

        # Cache for admin client to avoid unnecessary re-authentication
        self._admin_adapter: KeycloakAdmin | None = None
        self._admin_token_expiry: float = 0.0
        self._uma_adapter: KeycloakUMA | None = None

        # Initialize admin client if admin mode is enabled and credentials are provided
        if self.configs.IS_ADMIN_MODE_ENABLED and (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            self._initialize_admin_client()

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "clear_cache"):
                attr.clear_cache()

    @staticmethod
    def _get_openid_client(configs: KeycloakConfig) -> KeycloakOpenID:
        """Create and configure a KeycloakOpenID instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakOpenID client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakOpenID(
            server_url=server_url,
            client_id=client_id,
            realm_name=configs.REALM_NAME,
            client_secret_key=configs.CLIENT_SECRET_KEY,
            verify=configs.VERIFY_SSL,
            timeout=configs.TIMEOUT,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    username=self.configs.ADMIN_USERNAME,
                    password=self.configs.ADMIN_PASSWORD,
                    realm_name=self.configs.REALM_NAME,
                    user_realm_name=self.configs.ADMIN_REALM_NAME,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                # Since we're using direct credentials, set a long expiry time
                self._admin_token_expiry = time.time() + 3600  # 1 hour
                logger.debug("Admin client initialized with admin credentials")

            elif self.configs.CLIENT_SECRET_KEY:
                # Get token using client credentials
                token = self._openid_adapter.token(grant_type="client_credentials")

                # Set token expiry time (current time + expires_in - buffer)
                # Using a 30-second buffer to ensure we refresh before expiration
                self._admin_token_expiry = time.time() + token.get("expires_in", 60) - 30

                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    realm_name=self.configs.REALM_NAME,
                    token=token,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                logger.debug("Admin client initialized with client credentials")

            else:
                raise UnauthenticatedError(
                    additional_data={"detail": "Neither admin credentials nor client secret provided"},
                )

        except KeycloakAuthenticationError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise UnauthenticatedError(
                additional_data={"detail": "Failed to authenticate with Keycloak service account"},
            ) from e
        except KeycloakConnectionError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise ConnectionTimeoutError("Failed to connect to Keycloak server") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_initialize_admin_client")

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary.

        Returns:
            KeycloakAdmin instance

        Raises:
            UnauthenticatedError: If admin client is not available due to authentication issues
            UnavailableError: If Keycloak service is unavailable
        """
        if not self.configs.IS_ADMIN_MODE_ENABLED or not (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            raise UnauthenticatedError(
                additional_data={
                    "data": "Admin mode is disabled or neither admin credentials nor client secret provided",
                },
            )

        # Check if token is about to expire and refresh if needed
        if self._admin_adapter is None or time.time() >= self._admin_token_expiry:
            self._initialize_admin_client()

        if self._admin_adapter is None:
            raise UnavailableError("Keycloak admin client is not available")

        return self._admin_adapter

    @staticmethod
    def _get_uma_client(configs: KeycloakConfig) -> KeycloakUMA:
        """Create and configure a KeycloakUMA instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakUMA client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakUMA(
            KeycloakOpenIDConnection(
                server_url=server_url,
                realm_name=configs.REALM_NAME,
                client_id=client_id,
                client_secret_key=configs.CLIENT_SECRET_KEY,
                verify=configs.VERIFY_SSL,
                timeout=configs.TIMEOUT,
            ),
        )

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access.

        Returns:
            KeycloakUMA instance
        """
        if self._uma_adapter is None:
            self._uma_adapter = self._get_uma_client(self.configs)
        return self._uma_adapter


class AsyncKeycloakConnectionMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for connection/init operations."""

    def __init__(self, keycloak_configs: KeycloakConfig | None = None) -> None:
        """Initialize KeycloakAdapter with configuration.

        Args:
            keycloak_configs: Optional Keycloak configuration. If None, global config is used.
        """
        self.configs: KeycloakConfig = (
            BaseConfig.global_config().KEYCLOAK if keycloak_configs is None else keycloak_configs
        )

        # Initialize the OpenID client for authentication
        self.openid_adapter = self._get_openid_client(self.configs)

        # Cache for admin client to avoid unnecessary re-authentication
        self._admin_adapter: KeycloakAdmin | None = None
        self._admin_token_expiry: float = 0.0
        self._uma_adapter: KeycloakUMA | None = None

        # Initialize admin client if admin mode is enabled and credentials are provided
        if self.configs.IS_ADMIN_MODE_ENABLED and (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            self._initialize_admin_client()

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "cache_clear"):
                attr.cache_clear()

    @staticmethod
    def _get_openid_client(configs: KeycloakConfig) -> KeycloakOpenID:
        """Create and configure a KeycloakOpenID instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakOpenID client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakOpenID(
            server_url=server_url,
            client_id=client_id,
            realm_name=configs.REALM_NAME,
            client_secret_key=configs.CLIENT_SECRET_KEY,
            verify=configs.VERIFY_SSL,
            timeout=configs.TIMEOUT,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    username=self.configs.ADMIN_USERNAME,
                    password=self.configs.ADMIN_PASSWORD,
                    realm_name=self.configs.REALM_NAME,
                    user_realm_name=self.configs.ADMIN_REALM_NAME,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                # Since we're using direct credentials, set a long expiry time
                self._admin_token_expiry = time.time() + 3600  # 1 hour
                logger.debug("Admin client initialized with admin credentials")
            elif self.configs.CLIENT_SECRET_KEY:
                # Get token using client credentials
                token = self.openid_adapter.token(grant_type="client_credentials")

                # Set token expiry time (current time + expires_in - buffer)
                # Using a 30-second buffer to ensure we refresh before expiration
                self._admin_token_expiry = time.time() + token.get("expires_in", 60) - 30

                # Create admin client with the token
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    realm_name=self.configs.REALM_NAME,
                    token=token,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                logger.debug("Admin client initialized with client credentials")
            else:
                raise UnauthenticatedError(
                    additional_data={"detail": "Neither admin credentials nor client secret provided"},
                )

        except KeycloakAuthenticationError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise UnauthenticatedError(
                additional_data={"detail": "Failed to authenticate with Keycloak service account"},
            ) from e
        except KeycloakConnectionError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise ConnectionTimeoutError("Failed to connect to Keycloak server") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_initialize_admin_client")

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary.

        Returns:
            KeycloakAdmin instance

        Raises:
            UnauthenticatedError: If admin client is not available due to authentication issues
            UnavailableError: If Keycloak service is unavailable
        """
        if not self.configs.IS_ADMIN_MODE_ENABLED or not (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            raise UnauthenticatedError(
                additional_data={
                    "detail": "Admin mode is disabled or neither admin credentials nor client secret provided",
                },
            )

        # Check if token is about to expire and refresh if needed
        if self._admin_adapter is None or time.time() >= self._admin_token_expiry:
            self._initialize_admin_client()

        if self._admin_adapter is None:
            raise UnavailableError("Keycloak admin client is not available")

        return self._admin_adapter

    @staticmethod
    def _get_uma_client(configs: KeycloakConfig) -> KeycloakUMA:
        """Create and configure a KeycloakUMA instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakUMA client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakUMA(
            KeycloakOpenIDConnection(
                server_url=server_url,
                realm_name=configs.REALM_NAME,
                client_id=client_id,
                client_secret_key=configs.CLIENT_SECRET_KEY,
                verify=configs.VERIFY_SSL,
                timeout=configs.TIMEOUT,
            ),
        )

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access.

        Returns:
            KeycloakUMA instance
        """
        if self._uma_adapter is None:
            self._uma_adapter = self._get_uma_client(self.configs)
        return self._uma_adapter
