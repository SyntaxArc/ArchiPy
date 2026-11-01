"""Keycloak adapter mixins for connection/init operations."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import TYPE_CHECKING

from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakUMA
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
)
from keycloak.openid_connection import KeycloakOpenIDConnection

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    client_options,
    with_sync_proxies,
)
from archipy.configs.base_config import BaseConfig
from archipy.models.errors import (
    ConfigurationError,
    ConnectionTimeoutError,
    UnauthenticatedError,
    UnavailableError,
)

if TYPE_CHECKING:
    from archipy.configs.config_template import KeycloakConfig

logger = logging.getLogger(__name__)

_CACHE_CLEAR_NAMES = ("clear_cache", "cache_clear")


def _clear_cached_callables(adapter: object) -> None:
    """Clear every cached method of an adapter, whichever clear method its cache decorator offers.

    Names come from the class and the instance dict and are read with ``inspect.getattr_static``, so properties such
    as ``admin_adapter`` and ``uma_adapter`` are never evaluated (they could raise or log in to Keycloak).
    """
    names = set(dir(type(adapter))) | set(vars(adapter))
    for name in names:
        static_attr = inspect.getattr_static(adapter, name, None)
        if static_attr is None or isinstance(static_attr, property):
            continue
        attr = getattr(adapter, name, None)
        for clear_name in _CACHE_CLEAR_NAMES:
            clear = getattr(attr, clear_name, None)
            if callable(clear):
                clear()
                break


class KeycloakConnectionMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for connection/init operations."""

    def __init__(self, keycloak_configs: KeycloakConfig | None = None) -> None:
        """Initialize KeycloakAdapter with configuration.

        Args:
            keycloak_configs: Optional Keycloak configuration. If None, global config is used.
        """
        self.configs: KeycloakConfig = keycloak_configs or BaseConfig.global_config().KEYCLOAK

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
        _clear_cached_callables(self)

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
            raise ConfigurationError(operation="keycloak_connect", reason="server_url_and_client_id_required")
        return with_sync_proxies(
            KeycloakOpenID(
                server_url=server_url,
                client_id=client_id,
                realm_name=configs.REALM_NAME,
                client_secret_key=configs.CLIENT_SECRET_KEY,
                **client_options(configs),
            ),
            configs,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = with_sync_proxies(
                    KeycloakAdmin(
                        server_url=self.configs.SERVER_URL,
                        username=self.configs.ADMIN_USERNAME,
                        password=self.configs.ADMIN_PASSWORD,
                        realm_name=self.configs.REALM_NAME,
                        user_realm_name=self.configs.ADMIN_REALM_NAME,
                        **client_options(self.configs, with_proxies=False),
                    ),
                    self.configs,
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

                self._admin_adapter = with_sync_proxies(
                    KeycloakAdmin(
                        server_url=self.configs.SERVER_URL,
                        realm_name=self.configs.REALM_NAME,
                        token=token,
                        **client_options(self.configs, with_proxies=False),
                    ),
                    self.configs,
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
            raise ConnectionTimeoutError(service="keycloak") from e
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
            raise UnavailableError(resource_type="keycloak_admin_client")

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
            raise ConfigurationError(operation="keycloak_connect", reason="server_url_and_client_id_required")
        return with_sync_proxies(
            KeycloakUMA(
                KeycloakOpenIDConnection(
                    server_url=server_url,
                    realm_name=configs.REALM_NAME,
                    client_id=client_id,
                    client_secret_key=configs.CLIENT_SECRET_KEY,
                    **client_options(configs, with_proxies=False),
                ),
            ),
            configs,
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
        self.configs: KeycloakConfig = keycloak_configs or BaseConfig.global_config().KEYCLOAK

        # Initialize the OpenID client for authentication
        self.openid_adapter = self._get_openid_client(self.configs)

        # Cache for admin client to avoid unnecessary re-authentication
        self._admin_adapter: KeycloakAdmin | None = None
        self._admin_token_expiry: float = 0.0
        self._uma_adapter: KeycloakUMA | None = None
        # Serializes admin token refreshes so concurrent coroutines trigger a single login.
        self._admin_lock = asyncio.Lock()

        # Initialize admin client if admin mode is enabled and credentials are provided
        if self.configs.IS_ADMIN_MODE_ENABLED and (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            self._initialize_admin_client()

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        _clear_cached_callables(self)

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
            raise ConfigurationError(operation="keycloak_connect", reason="server_url_and_client_id_required")
        return with_sync_proxies(
            KeycloakOpenID(
                server_url=server_url,
                client_id=client_id,
                realm_name=configs.REALM_NAME,
                client_secret_key=configs.CLIENT_SECRET_KEY,
                **client_options(configs),
            ),
            configs,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = with_sync_proxies(
                    KeycloakAdmin(
                        server_url=self.configs.SERVER_URL,
                        username=self.configs.ADMIN_USERNAME,
                        password=self.configs.ADMIN_PASSWORD,
                        realm_name=self.configs.REALM_NAME,
                        user_realm_name=self.configs.ADMIN_REALM_NAME,
                        **client_options(self.configs, with_proxies=False),
                    ),
                    self.configs,
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
                self._admin_adapter = with_sync_proxies(
                    KeycloakAdmin(
                        server_url=self.configs.SERVER_URL,
                        realm_name=self.configs.REALM_NAME,
                        token=token,
                        **client_options(self.configs, with_proxies=False),
                    ),
                    self.configs,
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
            raise ConnectionTimeoutError(service="keycloak") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_initialize_admin_client")

    def _admin_credentials_configured(self) -> bool:
        """Tell whether admin mode is on and credentials exist for an admin client."""
        return bool(
            self.configs.IS_ADMIN_MODE_ENABLED
            and (self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)),
        )

    def _admin_is_fresh(self) -> bool:
        return self._admin_adapter is not None and time.time() < self._admin_token_expiry

    async def _ensure_admin(self) -> None:
        """Refresh the admin client without blocking the event loop when its token is missing or about to expire.

        Concurrent callers wait on one lock, so only the first of them logs in. The sync ``admin_adapter`` property
        stays as it was and finds a fresh client afterwards.

        Raises:
            UnauthenticatedError: If the admin login is rejected.
            ConnectionTimeoutError: If Keycloak cannot be reached.
        """
        if not self._admin_credentials_configured() or self._admin_is_fresh():
            return
        async with self._admin_lock:
            if self._admin_is_fresh():
                return
            await self._a_initialize_admin_client()

    async def _a_initialize_admin_client(self) -> None:
        """Async variant of ``_initialize_admin_client``."""
        if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
            # KeycloakAdmin logs in while it is built, so build it in a worker thread.
            await asyncio.to_thread(self._initialize_admin_client)
            return
        try:
            token = await self.openid_adapter.a_token(grant_type="client_credentials")
            self._admin_token_expiry = time.time() + token.get("expires_in", 60) - 30
            self._admin_adapter = with_sync_proxies(
                KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    realm_name=self.configs.REALM_NAME,
                    token=token,
                    **client_options(self.configs, with_proxies=False),
                ),
                self.configs,
            )
            logger.debug("Admin client initialized with client credentials")
        except KeycloakAuthenticationError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise UnauthenticatedError(
                additional_data={"detail": "Failed to authenticate with Keycloak service account"},
            ) from e
        except KeycloakConnectionError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise ConnectionTimeoutError(service="keycloak") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_a_initialize_admin_client")

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
            raise UnavailableError(resource_type="keycloak_admin_client")

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
            raise ConfigurationError(operation="keycloak_connect", reason="server_url_and_client_id_required")
        return with_sync_proxies(
            KeycloakUMA(
                KeycloakOpenIDConnection(
                    server_url=server_url,
                    realm_name=configs.REALM_NAME,
                    client_id=client_id,
                    client_secret_key=configs.CLIENT_SECRET_KEY,
                    **client_options(configs, with_proxies=False),
                ),
            ),
            configs,
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
