"""Shared helpers and attribute bases for Keycloak adapter mixins."""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, NoReturn, TypeVar

from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakUMA
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
)

from archipy.configs.config_template import KeycloakConfig
from archipy.models.errors import (
    ClientAlreadyExistsError,
    InsufficientPermissionsError,
    InternalError,
    InvalidCredentialsError,
    KeycloakConnectionTimeoutError,
    KeycloakServiceUnavailableError,
    PasswordPolicyError,
    RealmAlreadyExistsError,
    ResourceNotFoundError,
    RoleAlreadyExistsError,
    UserAlreadyExistsError,
    ValidationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class KeycloakExceptionHandlerMixin:
    """Mixin class to handle Keycloak exceptions in a consistent way."""

    @classmethod
    def _extract_error_message(cls, exception: KeycloakError) -> str:
        """Extract the actual error message from Keycloak error response.

        Args:
            exception: The Keycloak exception

        Returns:
            str: The extracted error message
        """
        error_message = str(exception)

        # Try to parse JSON response body
        if hasattr(exception, "response_body") and exception.response_body:
            try:
                body = exception.response_body
                if isinstance(body, bytes):
                    body_str = body.decode("utf-8")
                elif isinstance(body, str):
                    body_str = body
                else:
                    body_str = str(body)

                parsed = json.loads(body_str)
                if isinstance(parsed, dict):
                    error_message = (
                        parsed.get("errorMessage")
                        or parsed.get("error_description")
                        or parsed.get("error")
                        or error_message
                    )
            except json.JSONDecodeError, UnicodeDecodeError:
                pass

        return error_message

    @classmethod
    def _handle_keycloak_exception(cls, exception: KeycloakError, operation: str) -> NoReturn:
        """Handle Keycloak exceptions and map them to appropriate application errors.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_message = cls._extract_error_message(exception)
        response_code = getattr(exception, "response_code", None)
        error_lower = error_message.lower()

        # Common context data
        additional_data = {
            "operation": operation,
            "original_error": error_message,
            "response_code": response_code,
            "keycloak_error_type": type(exception).__name__,
        }

        # Connection and network errors
        if isinstance(exception, KeycloakConnectionError):
            if "timeout" in error_lower:
                raise KeycloakConnectionTimeoutError(additional_data=additional_data) from exception
            raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

        # Authentication errors
        if isinstance(exception, KeycloakAuthenticationError) or any(
            phrase in error_lower
            for phrase in ["invalid user credentials", "invalid credentials", "authentication failed", "unauthorized"]
        ):
            raise InvalidCredentialsError(additional_data=additional_data) from exception

        # Resource already exists errors
        if "already exists" in error_lower:
            if "realm" in error_lower:
                raise RealmAlreadyExistsError(additional_data=additional_data) from exception
            elif "user exists with same" in error_lower:
                raise UserAlreadyExistsError(additional_data=additional_data) from exception
            elif "client" in error_lower:
                raise ClientAlreadyExistsError(additional_data=additional_data) from exception
            elif "role" in error_lower:
                raise RoleAlreadyExistsError(additional_data=additional_data) from exception

        # Not found errors
        if "not found" in error_lower:
            raise ResourceNotFoundError(additional_data=additional_data) from exception

        # Permission errors
        if any(
            phrase in error_lower
            for phrase in ["forbidden", "access denied", "insufficient permissions", "insufficient scope"]
        ):
            raise InsufficientPermissionsError(additional_data=additional_data) from exception

        # Password policy errors
        if any(
            phrase in error_lower
            for phrase in ["invalid password", "password policy", "minimum length", "password must"]
        ):
            raise PasswordPolicyError(additional_data=additional_data) from exception

        # Validation errors (400 status codes that don't match above)
        if response_code == 400 or any(
            phrase in error_lower for phrase in ["validation", "invalid", "required field", "bad request"]
        ):
            raise ValidationError(additional_data=additional_data) from exception

        # Service unavailable
        if response_code in [503, 504] or "unavailable" in error_lower:
            raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

        # Default to InternalError for unrecognized errors
        raise InternalError(additional_data=additional_data) from exception

    @classmethod
    def _handle_realm_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        realm_name: str | None = None,
    ) -> NoReturn:
        """Handle realm-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            realm_name: The realm name involved in the operation

        Raises:
            RealmAlreadyExistsError: If realm already exists
            Various other errors from _handle_keycloak_exception
        """
        # Add realm-specific context
        error_message = cls._extract_error_message(exception)

        # Realm-specific error handling
        if realm_name and "already exists" in error_message.lower():
            additional_data = {
                "operation": operation,
                "realm_name": realm_name,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            raise RealmAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)

    @classmethod
    def _handle_user_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        user_data: dict | None = None,
    ) -> NoReturn:
        """Handle user-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            user_data: The user data involved in the operation

        Raises:
            UserAlreadyExistsError: If user already exists
            Various other errors from _handle_keycloak_exception
        """
        error_message = cls._extract_error_message(exception)

        # User-specific error handling
        if "user exists with same" in error_message.lower():
            additional_data = {
                "operation": operation,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            if user_data:
                additional_data.update(
                    {
                        "username": user_data.get("username"),
                        "email": user_data.get("email"),
                    },
                )
            raise UserAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)

    @classmethod
    def _handle_client_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        client_data: dict | None = None,
    ) -> None:
        """Handle client-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            client_data: The client data involved in the operation

        Raises:
            ClientAlreadyExistsError: If client already exists
            Various other errors from _handle_keycloak_exception
        """
        error_message = cls._extract_error_message(exception)

        # Client-specific error handling
        if "client" in error_message.lower() and "already exists" in error_message.lower():
            additional_data = {
                "operation": operation,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            if client_data:
                additional_data.update(
                    {
                        "client_id": client_data.get("clientId"),
                        "client_name": client_data.get("name"),
                    },
                )
            raise ClientAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)


class SyncKeycloakMixinBase(KeycloakExceptionHandlerMixin):
    """Shared attribute declarations for sync Keycloak adapter mixins."""

    configs: KeycloakConfig
    _openid_adapter: KeycloakOpenID
    _admin_adapter: KeycloakAdmin | None
    _admin_token_expiry: float
    _uma_adapter: KeycloakUMA | None

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary."""
        raise NotImplementedError

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access."""
        raise NotImplementedError

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        raise NotImplementedError

    def get_userinfo(self, token: str) -> dict[str, Any] | None:
        """Get user information from a token."""
        raise NotImplementedError

    def _call_keycloak(self, operation: str, fn: Callable[[], T]) -> T:
        """Run a sync Keycloak call and map KeycloakError to app errors.

        Args:
            operation: Name of the adapter operation for error context.
            fn: Zero-arg callable performing the Keycloak client call.

        Returns:
            Result of ``fn``.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """
        try:
            return fn()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, operation)


class AsyncKeycloakMixinBase(KeycloakExceptionHandlerMixin):
    """Shared attribute declarations for async Keycloak adapter mixins."""

    configs: KeycloakConfig
    openid_adapter: KeycloakOpenID
    _admin_adapter: KeycloakAdmin | None
    _admin_token_expiry: float
    _uma_adapter: KeycloakUMA | None

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary."""
        raise NotImplementedError

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access."""
        raise NotImplementedError

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        raise NotImplementedError

    async def get_userinfo(self, token: str) -> dict[str, Any] | None:
        """Get user information from a token."""
        raise NotImplementedError

    async def _async_call_keycloak(self, operation: str, fn: Callable[[], Awaitable[T]]) -> T:
        """Run an async Keycloak call and map KeycloakError to app errors.

        Args:
            operation: Name of the adapter operation for error context.
            fn: Zero-arg async callable performing the Keycloak client call.

        Returns:
            Result of ``fn``.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """
        try:
            return await fn()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, operation)
