"""Rate-limit identity helpers for gRPC server RPCs."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Any

from archipy.configs.base_config import BaseConfig
from archipy.models.errors import InvalidTokenError, TokenExpiredError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from archipy.configs.config_template import AuthConfig


_METADATA_PAIR_MIN_LEN = 2

# (global config object, its AUTH section): re-resolved only when the global config object changes.
_auth_config_cache: tuple[object, AuthConfig] | None = None


@cache
def _jwt_utils() -> Any:  # noqa: ANN401
    """Import ``JWTUtils`` once (a module-level import would create an import cycle)."""
    from archipy.helpers.utils.jwt_utils import JWTUtils  # noqa: PLC0415

    return JWTUtils


def _resolve_auth_config() -> AuthConfig:
    """Return the global ``AUTH`` config, cached until ``BaseConfig.set_global`` swaps the config object."""
    global _auth_config_cache  # noqa: PLW0603
    config = BaseConfig.global_config()
    cached = _auth_config_cache
    if cached is not None and cached[0] is config and cached[1] is config.AUTH:
        return cached[1]
    auth_config = config.AUTH
    _auth_config_cache = (config, auth_config)
    return auth_config


def invocation_metadata_to_dict(metadata_items: Iterable[Any]) -> dict[str, str]:
    """Normalize gRPC invocation metadata to a string dict.

    Args:
        metadata_items: Items from ``ServicerContext.invocation_metadata()``.

    Returns:
        Metadata keys mapped to decoded string values.
    """
    metadata_dict: dict[str, str] = {}
    for item in metadata_items:
        if hasattr(item, "key") and hasattr(item, "value"):
            key, value = item.key, item.value
        elif isinstance(item, tuple) and len(item) >= _METADATA_PAIR_MIN_LEN:
            key, value = item[0], item[1]
        else:
            continue
        if isinstance(value, bytes):
            metadata_dict[str(key)] = value.decode("utf-8", errors="ignore")
        else:
            metadata_dict[str(key)] = str(value)
    return metadata_dict


def extract_bearer_token_from_metadata(metadata_items: Iterable[Any]) -> str | None:
    """Extract a Bearer token from gRPC invocation metadata.

    Args:
        metadata_items: Items from ``ServicerContext.invocation_metadata()``.

    Returns:
        The raw JWT string, or None when metadata is missing or not Bearer.
    """
    metadata_dict = invocation_metadata_to_dict(metadata_items)
    authorization = metadata_dict.get("authorization") or metadata_dict.get("Authorization")
    if not authorization:
        return None

    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials:
        return None

    return credentials.strip() or None


def resolve_jwt_access_token_sub_from_metadata(
    metadata_items: Iterable[Any],
    *,
    auth_config: AuthConfig | None = None,
) -> str | None:
    """Resolve the user identity from a verified JWT in gRPC invocation metadata.

    Args:
        metadata_items: Items from ``ServicerContext.invocation_metadata()``.
        auth_config: Optional auth configuration override. When None, uses global config.

    Returns:
        The token ``sub`` claim as a string, or None when no valid access token is present.
    """
    token = extract_bearer_token_from_metadata(metadata_items)
    if not token:
        return None

    try:
        payload = _jwt_utils().verify_access_token(token, auth_config=auth_config or _resolve_auth_config())
    except InvalidTokenError, TokenExpiredError:
        return None

    sub = payload.get("sub")
    if sub is None:
        return None

    return str(sub)
