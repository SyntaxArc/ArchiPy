"""Deprecated import path; the Keycloak guards live in ``archipy.adapters.keycloak.auth``.

``KeycloakUtils.fastapi_auth`` and the other class methods are now plain functions of that module. Names are resolved
lazily on first access, so importing this module does not require the keycloak extra.
"""

from __future__ import annotations

from typing import Any

from archipy.helpers._deprecation import warn_deprecated_name

_MOVED_NAMES = frozenset({"AuthContextManager", "clear_keycloak_remote_cache"})
_LEGACY_CLASS_METHODS = ("fastapi_auth", "async_fastapi_auth", "grpc_auth", "async_grpc_auth")


def _legacy_keycloak_utils() -> type:
    """Build the ``KeycloakUtils`` namespace whose methods delegate to the functions of the new module."""
    from archipy.adapters.keycloak import auth  # noqa: PLC0415

    namespace: dict[str, Any] = {name: staticmethod(getattr(auth, name)) for name in _LEGACY_CLASS_METHODS}
    namespace["_get_keycloak_adapter"] = staticmethod(auth._get_keycloak_adapter)
    namespace["_get_async_keycloak_adapter"] = staticmethod(auth._get_async_keycloak_adapter)
    namespace["__doc__"] = "Deprecated namespace; use the functions of ``archipy.adapters.keycloak.auth``."
    return type("KeycloakUtils", (), namespace)


def __getattr__(name: str) -> Any:  # noqa: ANN401
    """Return ``name`` from ``archipy.adapters.keycloak.auth``, warning for the names that moved or were replaced."""
    if name.startswith("__"):
        raise AttributeError(name)
    if name == "KeycloakUtils":
        warn_deprecated_name(
            "archipy.helpers.utils.keycloak_utils.KeycloakUtils",
            "the functions of archipy.adapters.keycloak.auth",
        )
        return _legacy_keycloak_utils()
    from archipy.adapters.keycloak import auth  # noqa: PLC0415

    try:
        value = getattr(auth, name)
    except AttributeError as e:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from e
    if name in _MOVED_NAMES:
        warn_deprecated_name(
            f"archipy.helpers.utils.keycloak_utils.{name}",
            f"archipy.adapters.keycloak.auth.{name}",
        )
    return value
