"""Shared Keycloak port type aliases."""

from __future__ import annotations

from typing import Any

# Define type aliases for better type hinting
KeycloakResponseType = dict[str, Any]
KeycloakTokenType = dict[str, Any]

KeycloakUserType = dict[str, Any]


# Define a type for the public key return type
# Using Any for JWK.JWK object, since we don't want to depend on jwcrypto types
PublicKeyType = Any
