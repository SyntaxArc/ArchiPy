"""Keycloak helpers.

``KeycloakUtils`` resolves the organization selected by an already-verified Keycloak access token.

The Keycloak guards live in ``archipy.adapters.keycloak.auth``: the legacy ``KeycloakUtils`` guard methods delegate to
the functions of that module, resolved lazily on first call, so importing this module does not require the keycloak
extra.
"""

from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import Any
from uuid import UUID

from archipy.helpers._deprecation import warn_deprecated_name
from archipy.models.errors import PermissionDeniedError

_MOVED_NAMES: frozenset[str] = frozenset({"AuthContextManager", "clear_keycloak_remote_cache"})


def _legacy_guard(old_name: str, new_name: str) -> staticmethod:
    """Build a ``KeycloakUtils`` method that warns, then calls the function ``new_name`` of the auth module."""

    def guard(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401 - forwards to the guard factories unchanged
        from archipy.adapters.keycloak import auth  # noqa: PLC0415

        warn_deprecated_name(f"KeycloakUtils.{old_name}", new_name)
        return getattr(auth, new_name)(*args, **kwargs)

    guard.__name__ = old_name
    guard.__qualname__ = f"KeycloakUtils.{old_name}"
    return staticmethod(guard)


class KeycloakUtils:
    """Keycloak helpers.

    The organization methods read the selected organization from Keycloak token claims. They take claims that a caller
    has already verified; no signature is checked here. Keycloak 26 emits ``{"<alias>": {"id": "<uuid>"}}`` in the
    ``organization`` claim when the organization scope and the id mapper are enabled.

    ``fastapi_auth``, ``async_fastapi_auth``, ``grpc_auth`` and ``async_grpc_auth`` are deprecated; use the functions
    of ``archipy.adapters.keycloak.auth``.
    """

    fastapi_auth: staticmethod = _legacy_guard("fastapi_auth", "fastapi_auth")
    async_fastapi_auth: staticmethod = _legacy_guard("async_fastapi_auth", "fastapi_auth")
    grpc_auth: staticmethod = _legacy_guard("grpc_auth", "grpc_auth")
    async_grpc_auth: staticmethod = _legacy_guard("async_grpc_auth", "grpc_auth")

    @staticmethod
    def _get_keycloak_adapter() -> object:
        """Return the shared sync adapter of ``archipy.adapters.keycloak.auth``."""
        from archipy.adapters.keycloak import auth  # noqa: PLC0415

        return auth._get_keycloak_adapter()

    @staticmethod
    def _get_async_keycloak_adapter() -> object:
        """Return the shared async adapter of ``archipy.adapters.keycloak.auth``."""
        from archipy.adapters.keycloak import auth  # noqa: PLC0415

        return auth._get_async_keycloak_adapter()

    @classmethod
    def parse_organization_uuids(cls, token_info: Mapping[str, Any] | None) -> set[UUID]:
        """Collect the organization UUIDs of the ``organization`` claim.

        Entries that are not mappings, have no ``id`` or carry an invalid UUID are skipped. This method never raises.

        Args:
            token_info: Verified token claims, or None.

        Returns:
            set[UUID]: The valid organization UUIDs, empty when the claim has none.
        """
        organization: object = cls._get_claim(token_info, "organization")
        if not isinstance(organization, Mapping):
            return set()
        parsed: Generator[UUID | None] = (cls._parse_organization_entry(entry) for entry in organization.values())
        return {organization_uuid for organization_uuid in parsed if organization_uuid is not None}

    @classmethod
    def resolve_selected_organization_uuid(cls, token_info: Mapping[str, Any] | None) -> UUID | None:
        """Return the organization the token selected, or None for the personal context.

        Args:
            token_info: Verified token claims, or None.

        Returns:
            UUID | None: The single selected organization, or None when no organization is selected.

        Raises:
            PermissionDeniedError: If the ``organization`` claim is present but yields no valid UUID, or if several
                organizations are present without the ``organization:*`` scope.
        """
        organization_uuids: set[UUID] = cls.parse_organization_uuids(token_info)
        if not organization_uuids and cls._has_claim(token_info, "organization"):
            raise PermissionDeniedError(
                additional_data={
                    "reason": ("invalid organization claim"),
                },
            )
        if cls._has_wildcard_scope(token_info) or not organization_uuids:
            return None
        if len(organization_uuids) > 1:
            raise PermissionDeniedError(
                additional_data={
                    "reason": ("multiple organizations selected"),
                    "organization_count": len(organization_uuids),
                },
            )
        return next(iter(organization_uuids))

    @classmethod
    def require_selected_organization_uuid(cls, token_info: Mapping[str, Any] | None) -> UUID:
        """Return the selected organization, failing when none is selected.

        Args:
            token_info: Verified token claims, or None.

        Returns:
            UUID: The selected organization.

        Raises:
            PermissionDeniedError: If no organization is selected, or if the claim is malformed or ambiguous.
        """
        organization_uuid: UUID | None = cls.resolve_selected_organization_uuid(token_info)
        if organization_uuid is None:
            raise PermissionDeniedError(
                additional_data={
                    "reason": "organization not selected",
                },
            )
        return organization_uuid

    @classmethod
    def _get_claim(cls, token_info: Mapping[str, Any] | None, name: str) -> object:
        """Return the claim ``name``, or None when the claims are missing."""
        if token_info is None:
            return None
        return token_info.get(name)

    @classmethod
    def _has_claim(cls, token_info: Mapping[str, Any] | None, name: str) -> bool:
        """Return whether the claim ``name`` is present and truthy."""
        return bool(cls._get_claim(token_info, name))

    @classmethod
    def _get_scopes(cls, token_info: Mapping[str, Any] | None) -> set[str]:
        """Return the scopes of the space-separated ``scope`` claim; a missing or non-string claim has none."""
        scope: object = cls._get_claim(token_info, "scope")
        return set(scope.split()) if isinstance(scope, str) else set()

    @classmethod
    def _has_wildcard_scope(cls, token_info: Mapping[str, Any] | None) -> bool:
        """Return whether the ``scope`` claim contains ``organization:*``."""
        return "organization:*" in cls._get_scopes(token_info)

    @classmethod
    def _parse_organization_entry(cls, entry: object) -> UUID | None:
        """Return the UUID of one organization entry, or None when the entry is malformed."""
        if not isinstance(entry, Mapping):
            return None
        organization_id: object = entry.get("id")
        if not isinstance(organization_id, str):
            return None
        try:
            return UUID(organization_id)
        except ValueError:
            return None


def __getattr__(name: str) -> Any:  # noqa: ANN401 - module __getattr__ forwards names of any type
    """Return ``name`` from ``archipy.adapters.keycloak.auth``, warning for the names that moved or were replaced."""
    if name.startswith("__"):
        raise AttributeError(name)
    from archipy.adapters.keycloak import auth  # noqa: PLC0415

    try:
        value: object = getattr(auth, name)
    except AttributeError as e:
        msg: str = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg) from e
    if name in _MOVED_NAMES:
        warn_deprecated_name(
            f"archipy.helpers.utils.keycloak_utils.{name}",
            f"archipy.adapters.keycloak.auth.{name}",
        )
    return value
