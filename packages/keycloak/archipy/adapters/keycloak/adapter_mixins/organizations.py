"""Keycloak adapter mixins for organization operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)
from archipy.helpers.utils.string_utils import StringUtils


def _organization_payload(name: str, alias: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Build organization create payload with snake_case kwargs mapped to camelCase."""
    payload: dict[str, Any] = {"name": name, "alias": alias}
    for key, value in kwargs.items():
        if key in {"name", "alias"}:
            continue
        payload[StringUtils.snake_to_camel_case(key)] = value
    return payload


def _organization_update_payload(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Build organization update payload with snake_case kwargs mapped to camelCase."""
    return {StringUtils.snake_to_camel_case(key): value for key, value in kwargs.items()}


class KeycloakOrganizationsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for organization operations."""

    def get_organizations(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch all organizations, optionally filtered by query parameters.

        Args:
            query: Optional filter query parameters.

        Returns:
            List of organization representations.
        """
        return self._call_keycloak(
            "get_organizations",
            lambda: self.admin_adapter.get_organizations(query=query),
        )

    def get_organization(self, organization_id: str) -> dict[str, Any]:
        """Get representation of the organization by ID.

        Args:
            organization_id: Organization identifier.

        Returns:
            Organization representation.
        """
        return self._call_keycloak(
            "get_organization",
            lambda: self.admin_adapter.get_organization(organization_id),
        )

    def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique.

        Args:
            name: Organization name.
            alias: Organization alias.
            **kwargs: Additional organization attributes (snake_case mapped to camelCase).

        Returns:
            Created organization ID, or None.
        """
        payload = _organization_payload(name, alias, kwargs)
        return self._call_keycloak(
            "create_organization",
            lambda: self.admin_adapter.create_organization(payload=payload),
        )

    def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization.

        Args:
            organization_id: Organization identifier.
            **kwargs: Organization attributes to update (snake_case mapped to camelCase).

        Returns:
            Update response payload.
        """
        payload = _organization_update_payload(kwargs)
        return self._call_keycloak(
            "update_organization",
            lambda: self.admin_adapter.update_organization(organization_id=organization_id, payload=payload),
        )

    def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Deletion response payload.
        """
        return self._call_keycloak(
            "delete_organization",
            lambda: self.admin_adapter.delete_organization(organization_id=organization_id),
        )

    def get_organization_idps(self, organization_id: str) -> list[dict[str, Any]]:
        """Get identity providers linked to an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            List of identity provider representations.
        """
        return self._call_keycloak(
            "get_organization_idps",
            lambda: self.admin_adapter.get_organization_idps(organization_id=organization_id),
        )

    def get_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        """Get organizations by user id.

        Args:
            user_id: User identifier.

        Returns:
            Organizations the user belongs to.
        """
        return self._call_keycloak(
            "get_user_organizations",
            lambda: self.admin_adapter.get_user_organizations(user_id=user_id),
        )

    def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters.

        Args:
            organization_id: Organization identifier.
            query: Optional filter query parameters.

        Returns:
            Member representations.
        """
        return self._call_keycloak(
            "get_organization_members",
            lambda: self.admin_adapter.get_organization_members(organization_id=organization_id, query=query),
        )

    def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Member count.
        """
        return self._call_keycloak(
            "get_organization_members_count",
            lambda: self.admin_adapter.get_organization_members_count(organization_id=organization_id),
        )

    def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Raw response bytes.
        """
        return self._call_keycloak(
            "organization_user_add",
            lambda: self.admin_adapter.organization_user_add(user_id=user_id, organization_id=organization_id),
        )

    def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Removal response payload.
        """
        return self._call_keycloak(
            "organization_user_remove",
            lambda: self.admin_adapter.organization_user_remove(user_id=user_id, organization_id=organization_id),
        )


class AsyncKeycloakOrganizationsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for organization operations."""

    async def get_organizations(self, query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Fetch all organizations, optionally filtered by query parameters.

        Args:
            query: Optional filter query parameters.

        Returns:
            List of organization representations.
        """
        return await self._async_call_keycloak(
            "get_organizations",
            lambda: self.admin_adapter.a_get_organizations(query=query),
        )

    async def get_organization(self, organization_id: str) -> dict[str, Any]:
        """Get representation of the organization by ID.

        Args:
            organization_id: Organization identifier.

        Returns:
            Organization representation.
        """
        return await self._async_call_keycloak(
            "get_organization",
            lambda: self.admin_adapter.a_get_organization(organization_id=organization_id),
        )

    async def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique.

        Args:
            name: Organization name.
            alias: Organization alias.
            **kwargs: Additional organization attributes (snake_case mapped to camelCase).

        Returns:
            Created organization ID, or None.
        """
        payload = _organization_payload(name, alias, kwargs)
        return await self._async_call_keycloak(
            "create_organization",
            lambda: self.admin_adapter.a_create_organization(payload=payload),
        )

    async def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization.

        Args:
            organization_id: Organization identifier.
            **kwargs: Organization attributes to update (snake_case mapped to camelCase).

        Returns:
            Update response payload.
        """
        payload = _organization_update_payload(kwargs)
        return await self._async_call_keycloak(
            "update_organization",
            lambda: self.admin_adapter.a_update_organization(organization_id=organization_id, payload=payload),
        )

    async def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Deletion response payload.
        """
        return await self._async_call_keycloak(
            "delete_organization",
            lambda: self.admin_adapter.a_delete_organization(organization_id=organization_id),
        )

    async def get_organization_idps(self, organization_id: str) -> list[dict[str, Any]]:
        """Get identity providers linked to an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            List of identity provider representations.
        """
        return await self._async_call_keycloak(
            "get_organization_idps",
            lambda: self.admin_adapter.a_get_organization_idps(organization_id=organization_id),
        )

    async def get_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        """Get organizations by user id.

        Args:
            user_id: User identifier.

        Returns:
            Organizations the user belongs to.
        """
        return await self._async_call_keycloak(
            "get_user_organizations",
            lambda: self.admin_adapter.a_get_user_organizations(user_id=user_id),
        )

    async def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters.

        Args:
            organization_id: Organization identifier.
            query: Optional filter query parameters.

        Returns:
            Member representations.
        """
        return await self._async_call_keycloak(
            "get_organization_members",
            lambda: self.admin_adapter.a_get_organization_members(organization_id=organization_id, query=query),
        )

    async def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Member count.
        """
        return await self._async_call_keycloak(
            "get_organization_members_count",
            lambda: self.admin_adapter.a_get_organization_members_count(organization_id=organization_id),
        )

    async def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Raw response bytes.
        """
        return await self._async_call_keycloak(
            "organization_user_add",
            lambda: self.admin_adapter.a_organization_user_add(user_id=user_id, organization_id=organization_id),
        )

    async def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Removal response payload.
        """
        return await self._async_call_keycloak(
            "organization_user_remove",
            lambda: self.admin_adapter.a_organization_user_remove(user_id=user_id, organization_id=organization_id),
        )
