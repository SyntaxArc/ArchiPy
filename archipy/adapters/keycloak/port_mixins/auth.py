"""Keycloak port mixins for auth/token operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from archipy.adapters.keycloak.port_mixins._shared import (
    KeycloakTokenType,
    KeycloakUserType,
    PublicKeyType,
)


class KeycloakAuthPort:
    """Sync Keycloak port interface for auth/token operations."""

    @abstractmethod
    def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials."""
        raise NotImplementedError

    @abstractmethod
    def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token."""
        raise NotImplementedError

    @abstractmethod
    def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens."""
        raise NotImplementedError

    @abstractmethod
    def get_well_known_config(self) -> dict[str, Any]:
        """Get the well-known OpenID configuration."""
        raise NotImplementedError

    @abstractmethod
    def get_certs(self) -> dict[str, Any]:
        """Get the JWT verification certificates."""
        raise NotImplementedError

    @abstractmethod
    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call."""
        raise NotImplementedError


class AsyncKeycloakAuthPort:
    """Async Keycloak port interface for auth/token operations."""

    @abstractmethod
    async def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password."""
        raise NotImplementedError

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token."""
        raise NotImplementedError

    @abstractmethod
    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid."""
        raise NotImplementedError

    @abstractmethod
    async def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token."""
        raise NotImplementedError

    @abstractmethod
    async def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims."""
        raise NotImplementedError

    @abstractmethod
    async def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials."""
        raise NotImplementedError

    @abstractmethod
    async def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token."""
        raise NotImplementedError

    @abstractmethod
    async def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens."""
        raise NotImplementedError

    @abstractmethod
    async def get_well_known_config(self) -> dict[str, Any]:
        """Get the well-known OpenID configuration."""
        raise NotImplementedError

    @abstractmethod
    async def get_certs(self) -> dict[str, Any]:
        """Get the JWT verification certificates."""
        raise NotImplementedError

    @abstractmethod
    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token."""
        raise NotImplementedError

    @abstractmethod
    async def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope."""
        raise NotImplementedError

    @abstractmethod
    async def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call."""
        raise NotImplementedError
