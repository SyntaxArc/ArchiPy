"""Keycloak adapter mixins for group operations."""

from __future__ import annotations

from typing import Any

from archipy.adapters.keycloak.adapter_mixins._shared import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
)


class KeycloakGroupsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for group operations."""

    def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        return self._call_keycloak(
            "create_group",
            lambda: self.admin_adapter.create_group(payload=payload, parent=parent, skip_exists=skip_exists),
        )

    def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        return self._call_keycloak(
            "update_group",
            lambda: self.admin_adapter.update_group(group_id=group_id, payload=payload),
        )

    def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        return self._call_keycloak(
            "delete_group",
            lambda: self.admin_adapter.delete_group(group_id=group_id),
        )

    def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        return self._call_keycloak(
            "get_group",
            lambda: self.admin_adapter.get_group(group_id=group_id, full_hierarchy=full_hierarchy, query=query),
        )

    def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        return self._call_keycloak(
            "get_group_by_path",
            lambda: self.admin_adapter.get_group_by_path(path=path),
        )

    def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        return self._call_keycloak(
            "get_group_children",
            lambda: self.admin_adapter.get_group_children(
                group_id=group_id,
                query=query,
                full_hierarchy=full_hierarchy,
            ),
        )

    def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        return self._call_keycloak(
            "get_groups",
            lambda: self.admin_adapter.get_groups(query=query, full_hierarchy=full_hierarchy),
        )

    def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        return self._call_keycloak(
            "get_subgroups",
            lambda: self.admin_adapter.get_subgroups(group=group, path=path),
        )

    def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        return self._call_keycloak(
            "groups_count",
            lambda: self.admin_adapter.groups_count(query=query),
        )

    def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        return self._call_keycloak(
            "group_user_add",
            lambda: self.admin_adapter.group_user_add(user_id=user_id, group_id=group_id),
        )

    def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        return self._call_keycloak(
            "group_user_remove",
            lambda: self.admin_adapter.group_user_remove(user_id=user_id, group_id=group_id),
        )

    def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        return self._call_keycloak(
            "group_set_permissions",
            lambda: self.admin_adapter.group_set_permissions(group_id=group_id, enabled=enabled),
        )

    def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        return self._call_keycloak(
            "get_group_members",
            lambda: self.admin_adapter.get_group_members(group_id=group_id, query=query),
        )

    def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        return self._call_keycloak(
            "get_group_client_roles",
            lambda: self.admin_adapter.get_group_client_roles(group_id=group_id, client_id=client_id),
        )

    def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        return self._call_keycloak(
            "get_group_realm_roles",
            lambda: self.admin_adapter.get_group_realm_roles(
                group_id=group_id,
                brief_representation=brief_representation,
            ),
        )

    def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        return self._call_keycloak(
            "assign_group_client_roles",
            lambda: self.admin_adapter.assign_group_client_roles(group_id=group_id, client_id=client_id, roles=roles),
        )

    def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        return self._call_keycloak(
            "assign_group_realm_roles",
            lambda: self.admin_adapter.assign_group_realm_roles(group_id=group_id, roles=roles),
        )

    def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        return self._call_keycloak(
            "delete_group_client_roles",
            lambda: self.admin_adapter.delete_group_client_roles(group_id=group_id, client_id=client_id, roles=roles),
        )

    def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        return self._call_keycloak(
            "delete_group_realm_roles",
            lambda: self.admin_adapter.delete_group_realm_roles(group_id=group_id, roles=roles),
        )

    def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        return self._call_keycloak(
            "get_composite_client_roles_of_group",
            lambda: self.admin_adapter.get_composite_client_roles_of_group(
                client_id=client_id,
                group_id=group_id,
                brief_representation=brief_representation,
            ),
        )

    def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        return self._call_keycloak(
            "get_client_role_groups",
            lambda: self.admin_adapter.get_client_role_groups(client_id=client_id, role_name=role_name, **query),
        )

    def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        return self._call_keycloak(
            "get_realm_role_groups",
            lambda: self.admin_adapter.get_realm_role_groups(
                role_name=role_name,
                query=query,
                brief_representation=brief_representation,
            ),
        )


class AsyncKeycloakGroupsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for group operations."""

    async def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        return await self._async_call_keycloak(
            "create_group",
            lambda: self.admin_adapter.a_create_group(payload=payload, parent=parent, skip_exists=skip_exists),
        )

    async def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        return await self._async_call_keycloak(
            "update_group",
            lambda: self.admin_adapter.a_update_group(group_id=group_id, payload=payload),
        )

    async def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        return await self._async_call_keycloak(
            "delete_group",
            lambda: self.admin_adapter.a_delete_group(group_id=group_id),
        )

    async def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        return await self._async_call_keycloak(
            "get_group",
            lambda: self.admin_adapter.a_get_group(group_id=group_id, full_hierarchy=full_hierarchy, query=query),
        )

    async def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        return await self._async_call_keycloak(
            "get_group_by_path",
            lambda: self.admin_adapter.a_get_group_by_path(path=path),
        )

    async def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        return await self._async_call_keycloak(
            "get_group_children",
            lambda: self.admin_adapter.a_get_group_children(
                group_id=group_id,
                query=query,
                full_hierarchy=full_hierarchy,
            ),
        )

    async def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        return await self._async_call_keycloak(
            "get_groups",
            lambda: self.admin_adapter.a_get_groups(query=query, full_hierarchy=full_hierarchy),
        )

    async def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        return await self._async_call_keycloak(
            "get_subgroups",
            lambda: self.admin_adapter.a_get_subgroups(group=group, path=path),
        )

    async def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        return await self._async_call_keycloak(
            "groups_count",
            lambda: self.admin_adapter.a_groups_count(query=query),
        )

    async def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        return await self._async_call_keycloak(
            "group_user_add",
            lambda: self.admin_adapter.a_group_user_add(user_id=user_id, group_id=group_id),
        )

    async def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        return await self._async_call_keycloak(
            "group_user_remove",
            lambda: self.admin_adapter.a_group_user_remove(user_id=user_id, group_id=group_id),
        )

    async def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        return await self._async_call_keycloak(
            "group_set_permissions",
            lambda: self.admin_adapter.a_group_set_permissions(group_id=group_id, enabled=enabled),
        )

    async def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        return await self._async_call_keycloak(
            "get_group_members",
            lambda: self.admin_adapter.a_get_group_members(group_id=group_id, query=query),
        )

    async def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        return await self._async_call_keycloak(
            "get_group_client_roles",
            lambda: self.admin_adapter.a_get_group_client_roles(group_id=group_id, client_id=client_id),
        )

    async def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        return await self._async_call_keycloak(
            "get_group_realm_roles",
            lambda: self.admin_adapter.a_get_group_realm_roles(
                group_id=group_id,
                brief_representation=brief_representation,
            ),
        )

    async def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        return await self._async_call_keycloak(
            "assign_group_client_roles",
            lambda: self.admin_adapter.a_assign_group_client_roles(
                group_id=group_id,
                client_id=client_id,
                roles=roles,
            ),
        )

    async def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        return await self._async_call_keycloak(
            "assign_group_realm_roles",
            lambda: self.admin_adapter.a_assign_group_realm_roles(group_id=group_id, roles=roles),
        )

    async def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        return await self._async_call_keycloak(
            "delete_group_client_roles",
            lambda: self.admin_adapter.a_delete_group_client_roles(
                group_id=group_id,
                client_id=client_id,
                roles=roles,
            ),
        )

    async def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        return await self._async_call_keycloak(
            "delete_group_realm_roles",
            lambda: self.admin_adapter.a_delete_group_realm_roles(group_id=group_id, roles=roles),
        )

    async def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        return await self._async_call_keycloak(
            "get_composite_client_roles_of_group",
            lambda: self.admin_adapter.a_get_composite_client_roles_of_group(
                client_id=client_id,
                group_id=group_id,
                brief_representation=brief_representation,
            ),
        )

    async def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        return await self._async_call_keycloak(
            "get_client_role_groups",
            lambda: self.admin_adapter.a_get_client_role_groups(client_id=client_id, role_name=role_name, **query),
        )

    async def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        return await self._async_call_keycloak(
            "get_realm_role_groups",
            lambda: self.admin_adapter.a_get_realm_role_groups(
                role_name=role_name,
                query=query,
                brief_representation=brief_representation,
            ),
        )
