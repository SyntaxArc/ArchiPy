"""Keycloak adapter mixins for auth/token operations."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from async_lru import alru_cache
from jwcrypto import jwk
from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.models.errors import (
    InternalError,
)

if TYPE_CHECKING:
    from archipy.adapters.keycloak.ports import (
        KeycloakTokenType,
        KeycloakUserType,
        PublicKeyType,
    )

logger = logging.getLogger(__name__)


def _normalize_userinfo(raw: dict[str, Any] | bytes) -> KeycloakUserType:
    """Normalize a Keycloak userinfo response into a string-keyed dict.

    Args:
        raw: The userinfo payload as returned by python-keycloak (parsed dict or raw JSON bytes).

    Returns:
        User information with string keys.

    Raises:
        InternalError: If the payload is neither a JSON object nor a dict.
    """
    payload = json.loads(raw) if isinstance(raw, bytes) else raw
    if not isinstance(payload, dict):
        raise InternalError(additional_data={"operation": "userinfo", "error": "unexpected payload type"})
    return {str(key): value for key, value in payload.items()}


class KeycloakAuthMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for auth/token operations."""

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour, public key rarely changes
    def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens.

        Returns:
            JWK key object used to verify signatures

        Raises:
            ServiceUnavailableError: If Keycloak service is unavailable
            InternalError: If there's an internal error processing the public key
        """
        try:
            keys_info = self._openid_adapter.public_key()
            key = f"-----BEGIN PUBLIC KEY-----\n{keys_info}\n-----END PUBLIC KEY-----"
            return jwk.JWK.from_pem(key.encode("utf-8"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_public_key")
        except Exception as e:  # soft-fail authz/role checks; JWT/Keycloak libs
            raise InternalError(additional_data={"operation": "get_public_key", "error": str(e)}) from e

    def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password using the Resource Owner Password Credentials Grant.

        Warning:
            This method uses the direct password grant flow, which is less secure and not recommended
            for user login in production environments. Instead, prefer the web-based OAuth 2.0
            Authorization Code Flow (use `get_token_from_code`) for secure authentication.
            Use this method only for testing, administrative tasks, or specific service accounts
            where direct credential use is acceptable and properly secured.

        Args:
            username: User's username
            password: User's password

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            InvalidCredentialsError: If username or password is invalid
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return self._openid_adapter.token(grant_type="password", username=username, password=password)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New token response containing access_token, refresh_token, etc.

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return self._openid_adapter.refresh_token(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "refresh_token")

    def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Not caching validation results as tokens are time-sensitive
        try:
            # Let the underlying adapter handle key selection to align with expected types
            self._openid_adapter.decode_token(token)
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Token validation failed: %s", e)
            return False
        else:
            return True

    def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token via the UserInfo endpoint.

        The UserInfo endpoint validates the token server-side, so no local
        validation is needed here.

        Args:
            token: Access token

        Returns:
            User information

        Raises:
            ValueError: If getting user info fails
        """
        try:
            # _get_userinfo_cached returns KeycloakUserType (dict[str, Any])
            # The ttl_cache_decorator loses type info, but runtime behavior is correct
            # Access underlying function for proper typing
            cached_func = self._get_userinfo_cached
            underlying_func = getattr(cached_func, "__wrapped__", None)
            if underlying_func is not None:
                # Call underlying function directly for type checking
                result: KeycloakUserType = underlying_func(self, token)
            else:
                # Fallback to cached version if __wrapped__ not available
                result_raw = cached_func(token)
                if not isinstance(result_raw, dict):
                    return None
                # Type assertion: result_raw is a dict, which matches KeycloakUserType
                # Convert to proper type by creating a new dict with explicit typing
                result: KeycloakUserType = {str(k): v for k, v in result_raw.items()}
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")
            return None
        else:
            return result

    @ttl_cache_decorator(ttl_seconds=30, maxsize=100)  # Cache for 30 seconds
    def _get_userinfo_cached(self, token: str) -> KeycloakUserType:
        return _normalize_userinfo(self._openid_adapter.userinfo(token))

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_well_known_config(self) -> dict[str, Any] | None:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return self._openid_adapter.well_known()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_certs(self) -> dict[str, Any] | None:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return self._openid_adapter.certs()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token.

        Args:
            code: Authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Token response

        Raises:
            ValueError: If token exchange fails
        """
        # Authorization codes can only be used once, don't cache
        try:
            return self._openid_adapter.token(grant_type="authorization_code", code=code, redirect_uri=redirect_uri)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return self._openid_adapter.token(grant_type="client_credentials")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token.

        Args:
            refresh_token: Refresh token to invalidate

        Raises:
            ValueError: If logout fails
        """
        try:
            self._openid_adapter.logout(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "logout")

    def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return self._openid_adapter.introspect(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            # Let the underlying adapter handle key selection to align with expected types
            return self._openid_adapter.decode_token(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

    @ttl_cache_decorator(ttl_seconds=30, maxsize=200)
    def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call.

        Prefer this over :meth:`check_permissions` when multiple pairs must be checked per request.

        Args:
            token: Access token
            permissions: Tuple of (resource, scope) pairs to check

        Returns:
            Subset of ``permissions`` that are granted
        """
        if not permissions:
            return frozenset()
        perm_strs = [f"{resource}#{scope}" for resource, scope in permissions]
        try:
            results = self._openid_adapter.uma_permissions(token, permissions=perm_strs)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "check_permissions_batch")
        if not results or not isinstance(results, list):
            return frozenset()
        granted: set[tuple[str, str]] = set()
        requested = set(permissions)
        for perm in results:
            rsname = perm.get("rsname")
            for scope in perm.get("scopes", []) or []:
                pair = (rsname, scope)
                if pair in requested:
                    granted.add(pair)
        return frozenset(granted)

    def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope.

        Prefer :meth:`check_permissions_batch` when checking multiple pairs per request.

        Args:
            token: Access token
            resource: Resource name
            scope: Permission scope

        Returns:
            True if permission granted, False otherwise
        """
        try:
            # Use UMA permissions endpoint to check specific resource and scope
            permissions = self._openid_adapter.uma_permissions(token, permissions=f"{resource}#{scope}")

            # Check if the response indicates permission is granted
            if not permissions or not isinstance(permissions, list):
                logger.debug("No permissions returned or invalid response format")
                return False

            # Look for the specific permission in the response
            for perm in permissions:
                if perm.get("rsname") == resource and scope in perm.get("scopes", []):
                    return True

        except KeycloakError as e:
            logger.debug("Permission check failed with Keycloak error: %s", e)
            return False
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Permission check failed with unexpected error: %s", e)
            return False
        else:
            return False


class AsyncKeycloakAuthMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for auth/token operations."""

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour, public key rarely changes
    async def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens.

        Returns:
            JWK key object used to verify signatures

        Raises:
            ServiceUnavailableError: If Keycloak service is unavailable
            InternalError: If there's an internal error processing the public key
        """
        try:
            keys_info = await self.openid_adapter.a_public_key()
            key = f"-----BEGIN PUBLIC KEY-----\n{keys_info}\n-----END PUBLIC KEY-----"
            return jwk.JWK.from_pem(key.encode("utf-8"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_public_key")
        except Exception as e:  # soft-fail authz/role checks; JWT/Keycloak libs
            raise InternalError(additional_data={"operation": "get_public_key", "error": str(e)}) from e

    async def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password using the Resource Owner Password Credentials Grant.

        Warning:
            This method uses the direct password grant flow, which is less secure and not recommended
            for user login in production environments. Instead, prefer the web-based OAuth 2.0
            Authorization Code Flow (use `get_token_from_code`) for secure authentication.
            Use this method only for testing, administrative tasks, or specific service accounts
            where direct credential use is acceptable and properly secured.

        Args:
            username: User's username
            password: User's password

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            InvalidCredentialsError: If username or password is invalid
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return await self.openid_adapter.a_token(grant_type="password", username=username, password=password)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    async def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New token response containing access_token, refresh_token, etc.

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return await self.openid_adapter.a_refresh_token(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "refresh_token")

    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Not caching validation results as tokens are time-sensitive
        try:
            await self.openid_adapter.a_decode_token(
                token,
                key=await self.get_public_key(),
            )
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Token validation failed: %s", e)
            return False
        else:
            return True

    async def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token via the UserInfo endpoint.

        The UserInfo endpoint validates the token server-side, so no local
        validation is needed here.

        Args:
            token: Access token

        Returns:
            User information

        Raises:
            ValueError: If getting user info fails
        """
        try:
            return await self._get_userinfo_cached(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")

    @alru_cache(ttl=30, maxsize=100)  # Cache for 30 seconds
    async def _get_userinfo_cached(self, token: str) -> KeycloakUserType:
        return _normalize_userinfo(await self.openid_adapter.a_userinfo(token))

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_well_known_config(self) -> dict[str, Any] | None:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return await self.openid_adapter.a_well_known()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_certs(self) -> dict[str, Any] | None:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return await self.openid_adapter.a_certs()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token.

        Args:
            code: Authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Token response

        Raises:
            ValueError: If token exchange fails
        """
        # Authorization codes can only be used once, don't cache
        try:
            return await self.openid_adapter.a_token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=redirect_uri,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    async def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return await self.openid_adapter.a_token(grant_type="client_credentials")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    async def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token.

        Args:
            refresh_token: Refresh token to invalidate

        Raises:
            ValueError: If logout fails
        """
        try:
            await self.openid_adapter.a_logout(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "logout")

    async def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return await self.openid_adapter.a_introspect(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    async def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            return await self.openid_adapter.a_decode_token(
                token,
                key=await self.get_public_key(),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

    @alru_cache(ttl=30, maxsize=200)
    async def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call.

        Prefer this over :meth:`check_permissions` when multiple pairs must be checked per request.

        Args:
            token: Access token
            permissions: Tuple of (resource, scope) pairs to check

        Returns:
            Subset of ``permissions`` that are granted
        """
        if not permissions:
            return frozenset()
        perm_strs = [f"{resource}#{scope}" for resource, scope in permissions]
        try:
            results = await self.openid_adapter.a_uma_permissions(token, permissions=perm_strs)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "check_permissions_batch")
        if not results or not isinstance(results, list):
            return frozenset()
        granted: set[tuple[str, str]] = set()
        requested = set(permissions)
        for perm in results:
            rsname = perm.get("rsname")
            for scope in perm.get("scopes", []) or []:
                pair = (rsname, scope)
                if pair in requested:
                    granted.add(pair)
        return frozenset(granted)

    async def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope.

        Prefer :meth:`check_permissions_batch` when checking multiple pairs per request.

        Args:
            token: Access token
            resource: Resource name
            scope: Permission scope

        Returns:
            True if permission granted, False otherwise
        """
        try:
            # Use UMA permissions endpoint to check specific resource and scope
            permissions = await self.openid_adapter.a_uma_permissions(token, permissions=f"{resource}#{scope}")

            # Check if the response indicates permission is granted
            if not permissions or not isinstance(permissions, list):
                logger.debug("No permissions returned or invalid response format")
                return False

            # Look for the specific permission in the response
            for perm in permissions:
                if perm.get("rsname") == resource and scope in perm.get("scopes", []):
                    return True

        except KeycloakError as e:
            logger.debug("Permission check failed with Keycloak error: %s", e)
            return False
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Permission check failed with unexpected error: %s", e)
            return False
        else:
            return False
