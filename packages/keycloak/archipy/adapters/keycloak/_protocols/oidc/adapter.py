"""Keycloak adapter mixins for auth/token operations."""

from __future__ import annotations

import base64
import json
import logging
import time
from typing import TYPE_CHECKING, Any

from async_lru import alru_cache
from jwcrypto import jwk
from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_or_none,
)
from archipy.helpers.decorators import ttl_cache
from archipy.models.dtos.keycloak.token_dtos import (
    KeycloakCertsDTO,
    KeycloakTokenClaimsDTO,
    KeycloakTokenDTO,
    KeycloakUserInfoDTO,
    KeycloakWellKnownDTO,
)
from archipy.models.dtos.keycloak.token_exchange_dtos import (
    KeycloakTokenExchangeRequestDTO,
    KeycloakTokenExchangeResponseDTO,
)
from archipy.models.errors import (
    InternalError,
)

if TYPE_CHECKING:
    from archipy.adapters.keycloak.ports import (
        KeycloakUserType,
        PublicKeyType,
    )

logger = logging.getLogger(__name__)

TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"  # noqa: S105 # nosec B105
JWT_BEARER_GRANT = "urn:ietf:params:oauth:grant-type:jwt-bearer"
UMA_TICKET_GRANT = "urn:ietf:params:oauth:grant-type:uma-ticket"

JWKS_TTL_SECONDS = 3600.0
JWKS_UNKNOWN_KID_REFRESH_INTERVAL_SECONDS = 10.0


def _token_kid(token: str) -> str | None:
    """Read the ``kid`` header of a JWT without verifying it.

    Args:
        token: Compact JWT.

    Returns:
        The key id, or None when the token header is missing, malformed or has no ``kid``.
    """
    try:
        segment_b64 = token.split(".", 1)[0]
        header = json.loads(base64.urlsafe_b64decode(segment_b64 + "=" * (-len(segment_b64) % 4)))
    except ValueError:
        return None
    kid = header.get("kid") if isinstance(header, dict) else None
    return kid if isinstance(kid, str) else None


def _jwks_needs_refresh(raw: dict[str, Any] | None, fetched_at: float, kid: str | None, now: float) -> bool:
    """Decide whether the cached realm JWKS must be fetched again.

    The set is refreshed when it is missing or older than ``JWKS_TTL_SECONDS``, or (rate limited) when the token
    names a ``kid`` the cached set does not contain, which is how a rotated signing key shows up.
    """
    if raw is None or now - fetched_at >= JWKS_TTL_SECONDS:
        return True
    if kid is None or now - fetched_at < JWKS_UNKNOWN_KID_REFRESH_INTERVAL_SECONDS:
        return False
    return all(key.get("kid") != kid for key in raw.get("keys", []))


def _build_jwk_set(raw: dict[str, Any]) -> jwk.JWKSet:
    """Build a jwcrypto key set from a raw JWKS document."""
    key_set = jwk.JWKSet()
    for cert in raw["keys"]:
        key_set.add(jwk.JWK(**cert))
    return key_set


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

    _jwks_raw: dict[str, Any] | None = None
    _jwks_fetched_at: float = 0.0

    def _decode_token_locally(self, token: str) -> dict[str, Any]:
        """Verify and decode a token against the cached realm JWKS (one JWKS fetch per TTL or key rotation)."""
        now = time.monotonic()
        if _jwks_needs_refresh(self._jwks_raw, self._jwks_fetched_at, _token_kid(token), now):
            self._jwks_raw = self._openid_adapter.certs()
            self._jwks_fetched_at = now
        return self._openid_adapter.decode_token(
            token,
            key=_build_jwk_set(self._jwks_raw or {"keys": []}),
            leeway=self.configs.TOKEN_LEEWAY_SECONDS,
        )

    @ttl_cache(ttl_seconds=3600, maxsize=1, per_instance=True)  # Cache for 1 hour, public key rarely changes
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

    def get_token(self, username: str, password: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(
                KeycloakTokenDTO,
                self._openid_adapter.token(grant_type="password", username=username, password=password),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    def refresh_token(self, refresh_token: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(KeycloakTokenDTO, self._openid_adapter.refresh_token(refresh_token))
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
            self._decode_token_locally(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "validate_token")
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Token validation failed: %s", e)
            return False
        else:
            return True

    def get_userinfo(self, token: str) -> KeycloakUserInfoDTO | None:
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
            result: KeycloakUserType = _normalize_userinfo(self._openid_adapter.userinfo(token))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")
            return None
        else:
            return to_dto(KeycloakUserInfoDTO, result)

    @ttl_cache(ttl_seconds=3600, maxsize=1, per_instance=True)  # Cache for 1 hour
    def get_well_known_config(self) -> KeycloakWellKnownDTO:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return to_dto(KeycloakWellKnownDTO, self._openid_adapter.well_known())
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @ttl_cache(ttl_seconds=3600, maxsize=1, per_instance=True)  # Cache for 1 hour
    def get_certs(self) -> KeycloakCertsDTO:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return to_dto(KeycloakCertsDTO, self._openid_adapter.certs())
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(
                KeycloakTokenDTO,
                self._openid_adapter.token(grant_type="authorization_code", code=code, redirect_uri=redirect_uri),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    def get_client_credentials_token(self) -> KeycloakTokenDTO | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return to_dto_or_none(KeycloakTokenDTO, self._openid_adapter.token(grant_type="client_credentials"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    def exchange_token(
        self,
        subject_token: str,
        requested_subject: str | None = None,
        audience: str | None = None,
        scope: str = "openid",
    ) -> KeycloakTokenDTO | None:
        """Exchange a token per RFC 8693, optionally impersonating another user.

        Args:
            subject_token: Access token of the caller (e.g. an admin or service account).
            requested_subject: User ID or username to impersonate. When set, Keycloak 26.8+
                adds the ``act`` claim to the issued token.
            audience: Target client for the new token.
            scope: Requested scope.

        Returns:
            Token response

        Raises:
            Various application errors mapped from the Keycloak response (e.g. when exchange is not permitted).
        """
        try:
            return to_dto_or_none(
                KeycloakTokenDTO,
                self._openid_adapter.exchange_token(
                    subject_token,
                    audience=audience,
                    subject=requested_subject,
                    requested_token_type="urn:ietf:params:oauth:token-type:access_token",  # noqa: S106 # nosec B106
                    scope=scope,
                ),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "exchange_token")

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

    def introspect_token(self, token: str) -> KeycloakTokenClaimsDTO | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return to_dto_or_none(KeycloakTokenClaimsDTO, self._openid_adapter.introspect(token))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    def get_token_info(self, token: str) -> KeycloakTokenClaimsDTO | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            return to_dto_or_none(KeycloakTokenClaimsDTO, self._decode_token_locally(token))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

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
            if self._is_uma_nothing_granted(e):
                return frozenset()
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

    def token_exchange(self, request: KeycloakTokenExchangeRequestDTO) -> KeycloakTokenExchangeResponseDTO:
        """Exchange a token (RFC 8693) with full control of the request parameters.

        Covers standard token exchange (V2), the delegation preview (``actor_token``), legacy exchange (V1) and
        exchanging a token for a JWT assertion in order to chain across domains.

        Args:
            request: The exchange parameters.

        Returns:
            The issued token and its type.

        Raises:
            Mapped application errors when the exchange is not permitted or the request is invalid.
        """
        return to_dto(
            KeycloakTokenExchangeResponseDTO,
            self._call_keycloak(
                "token_exchange",
                lambda: self._openid_adapter.token(grant_type=TOKEN_EXCHANGE_GRANT, **request.to_form()),
            ),
        )

    def jwt_bearer_grant(self, assertion: str, scope: str | None = None) -> KeycloakTokenDTO:
        """Trade a signed JWT assertion for an access token (RFC 7523 JWT authorization grant).

        The assertion is issued by an identity provider the client is allowed to use. The same call serves the
        identity assertion JWT authorization grant (ID-JAG) and the second step of chaining across domains.

        Args:
            assertion: The signed JWT.
            scope: Requested scope; defaults to ``openid``.

        Returns:
            The access token. Keycloak issues no refresh token for this grant.

        Raises:
            Mapped application errors when the assertion or the client setup is rejected.
        """
        return to_dto(
            KeycloakTokenDTO,
            self._call_keycloak(
                "jwt_bearer_grant",
                lambda: self._openid_adapter.token(
                    grant_type=JWT_BEARER_GRANT,
                    scope=scope or "openid",
                    assertion=assertion,
                ),
            ),
        )

    def request_rpt(self, token: str, audience: str, permissions: list[str] | None = None) -> KeycloakTokenDTO:
        """Exchange a user's access token for a requesting party token (RPT) carrying their permissions.

        This is the UMA ticket grant that the authz-client library performs: the user's access token goes in the
        ``Authorization`` header and the resource server client is the ``audience``.

        Args:
            token: The user's access token.
            audience: Client ID of the resource server whose permissions are requested.
            permissions: Permissions as ``resource`` or ``resource#scope``; all granted permissions when omitted.

        Returns:
            The RPT in ``access_token``.

        Raises:
            Mapped application errors; ``InsufficientPermissionsError`` when no requested permission is granted.
        """
        form: dict[str, Any] = {"grant_type": UMA_TICKET_GRANT, "audience": audience}
        if permissions:
            form["permission"] = permissions
        return to_dto(
            KeycloakTokenDTO,
            self._bearer_request(
                "request_rpt",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/protocol/openid-connect/token",
                token=token,
                form=form,
            ),
        )


class AsyncKeycloakAuthMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for auth/token operations."""

    _jwks_raw: dict[str, Any] | None = None
    _jwks_fetched_at: float = 0.0

    async def _decode_token_locally(self, token: str) -> dict[str, Any]:
        """Verify and decode a token against the cached realm JWKS (one JWKS fetch per TTL or key rotation)."""
        now = time.monotonic()
        if _jwks_needs_refresh(self._jwks_raw, self._jwks_fetched_at, _token_kid(token), now):
            self._jwks_raw = await self.openid_adapter.a_certs()
            self._jwks_fetched_at = now
        return await self.openid_adapter.a_decode_token(
            token,
            key=_build_jwk_set(self._jwks_raw or {"keys": []}),
            leeway=self.configs.TOKEN_LEEWAY_SECONDS,
        )

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

    async def get_token(self, username: str, password: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(
                KeycloakTokenDTO,
                await self.openid_adapter.a_token(grant_type="password", username=username, password=password),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    async def refresh_token(self, refresh_token: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(KeycloakTokenDTO, await self.openid_adapter.a_refresh_token(refresh_token))
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
            await self._decode_token_locally(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "validate_token")
        except Exception as e:  # noqa: BLE001  # soft-fail authz/role checks; JWT/Keycloak libs
            logger.debug("Token validation failed: %s", e)
            return False
        else:
            return True

    async def get_userinfo(self, token: str) -> KeycloakUserInfoDTO | None:
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
            return to_dto(KeycloakUserInfoDTO, _normalize_userinfo(await self.openid_adapter.a_userinfo(token)))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_well_known_config(self) -> KeycloakWellKnownDTO:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return to_dto(KeycloakWellKnownDTO, await self.openid_adapter.a_well_known())
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_certs(self) -> KeycloakCertsDTO:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return to_dto(KeycloakCertsDTO, await self.openid_adapter.a_certs())
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenDTO | None:
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
            return to_dto_or_none(
                KeycloakTokenDTO,
                await self.openid_adapter.a_token(
                    grant_type="authorization_code",
                    code=code,
                    redirect_uri=redirect_uri,
                ),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    async def get_client_credentials_token(self) -> KeycloakTokenDTO | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return to_dto_or_none(KeycloakTokenDTO, await self.openid_adapter.a_token(grant_type="client_credentials"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    async def exchange_token(
        self,
        subject_token: str,
        requested_subject: str | None = None,
        audience: str | None = None,
        scope: str = "openid",
    ) -> KeycloakTokenDTO | None:
        """Exchange a token per RFC 8693, optionally impersonating another user.

        Args:
            subject_token: Access token of the caller (e.g. an admin or service account).
            requested_subject: User ID or username to impersonate. When set, Keycloak 26.8+
                adds the ``act`` claim to the issued token.
            audience: Target client for the new token.
            scope: Requested scope.

        Returns:
            Token response

        Raises:
            Various application errors mapped from the Keycloak response (e.g. when exchange is not permitted).
        """
        try:
            return to_dto_or_none(
                KeycloakTokenDTO,
                await self.openid_adapter.a_exchange_token(
                    subject_token,
                    audience=audience,
                    subject=requested_subject,
                    requested_token_type="urn:ietf:params:oauth:token-type:access_token",  # noqa: S106 # nosec B106
                    scope=scope,
                ),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "exchange_token")

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

    async def introspect_token(self, token: str) -> KeycloakTokenClaimsDTO | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return to_dto_or_none(KeycloakTokenClaimsDTO, await self.openid_adapter.a_introspect(token))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    async def get_token_info(self, token: str) -> KeycloakTokenClaimsDTO | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            return to_dto_or_none(KeycloakTokenClaimsDTO, await self._decode_token_locally(token))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

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
            if self._is_uma_nothing_granted(e):
                return frozenset()
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

    async def token_exchange(self, request: KeycloakTokenExchangeRequestDTO) -> KeycloakTokenExchangeResponseDTO:
        """Exchange a token (RFC 8693) with full control of the request parameters.

        Covers standard token exchange (V2), the delegation preview (``actor_token``), legacy exchange (V1) and
        exchanging a token for a JWT assertion in order to chain across domains.

        Args:
            request: The exchange parameters.

        Returns:
            The issued token and its type.

        Raises:
            Mapped application errors when the exchange is not permitted or the request is invalid.
        """
        return to_dto(
            KeycloakTokenExchangeResponseDTO,
            await self._async_call_keycloak(
                "token_exchange",
                lambda: self.openid_adapter.a_token(grant_type=TOKEN_EXCHANGE_GRANT, **request.to_form()),
            ),
        )

    async def jwt_bearer_grant(self, assertion: str, scope: str | None = None) -> KeycloakTokenDTO:
        """Trade a signed JWT assertion for an access token (RFC 7523 JWT authorization grant).

        The assertion is issued by an identity provider the client is allowed to use. The same call serves the
        identity assertion JWT authorization grant (ID-JAG) and the second step of chaining across domains.

        Args:
            assertion: The signed JWT.
            scope: Requested scope; defaults to ``openid``.

        Returns:
            The access token. Keycloak issues no refresh token for this grant.

        Raises:
            Mapped application errors when the assertion or the client setup is rejected.
        """
        return to_dto(
            KeycloakTokenDTO,
            await self._async_call_keycloak(
                "jwt_bearer_grant",
                lambda: self.openid_adapter.a_token(
                    grant_type=JWT_BEARER_GRANT,
                    scope=scope or "openid",
                    assertion=assertion,
                ),
            ),
        )

    async def request_rpt(self, token: str, audience: str, permissions: list[str] | None = None) -> KeycloakTokenDTO:
        """Exchange a user's access token for a requesting party token (RPT) carrying their permissions.

        This is the UMA ticket grant that the authz-client library performs: the user's access token goes in the
        ``Authorization`` header and the resource server client is the ``audience``.

        Args:
            token: The user's access token.
            audience: Client ID of the resource server whose permissions are requested.
            permissions: Permissions as ``resource`` or ``resource#scope``; all granted permissions when omitted.

        Returns:
            The RPT in ``access_token``.

        Raises:
            Mapped application errors; ``InsufficientPermissionsError`` when no requested permission is granted.
        """
        form: dict[str, Any] = {"grant_type": UMA_TICKET_GRANT, "audience": audience}
        if permissions:
            form["permission"] = permissions
        return to_dto(
            KeycloakTokenDTO,
            await self._async_bearer_request(
                "request_rpt",
                "post",
                f"realms/{segment(self.configs.REALM_NAME)}/protocol/openid-connect/token",
                token=token,
                form=form,
            ),
        )
