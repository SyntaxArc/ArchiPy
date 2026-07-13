"""Rate-limit identity helpers for FastAPI REST endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

from archipy.models.errors import InvalidTokenError, TokenExpiredError

if TYPE_CHECKING:
    from archipy.configs.config_template import AuthConfig


def extract_bearer_token(request: Request) -> str | None:
    """Extract a Bearer token from the Authorization header.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The raw JWT string, or None when the header is missing or not Bearer.
    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        return None

    return credentials.strip() or None


def resolve_jwt_access_token_sub(request: Request, *, auth_config: AuthConfig | None = None) -> str | None:
    """Resolve the user identity from a verified JWT access token.

    Args:
        request: The incoming FastAPI request.
        auth_config: Optional auth configuration override. When None, uses global config.

    Returns:
        The token ``sub`` claim as a string, or None when no valid access token is present.
    """
    token = extract_bearer_token(request)
    if not token:
        return None

    from archipy.helpers.utils.jwt_utils import JWTUtils  # noqa: PLC0415

    try:
        payload = JWTUtils.verify_access_token(token, auth_config=auth_config)
    except InvalidTokenError, TokenExpiredError:
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    return str(sub)
