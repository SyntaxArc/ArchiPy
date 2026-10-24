"""Keycloak port mixins for identity providers and their mappers."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakCreateResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.identity_provider_dtos import (
        KeycloakIdentityProviderDTO,
        KeycloakIdentityProviderMapperDTO,
        KeycloakIdentityProviderMapperRequestDTO,
        KeycloakIdentityProviderRequestDTO,
    )
    from archipy.models.dtos.keycloak.management_permission_dtos import (
        KeycloakManagementPermissionDTO,
        KeycloakManagementPermissionRequestDTO,
    )


class KeycloakIdentityProvidersPort:
    """Sync Keycloak port interface for identity providers and their mappers."""

    @abstractmethod
    def get_identity_providers(self, query: dict[str, Any] | None = None) -> list[KeycloakIdentityProviderDTO]:
        """List the identity providers of the realm."""
        raise NotImplementedError

    @abstractmethod
    def create_identity_provider(
        self,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider(self, alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider by alias."""
        raise NotImplementedError

    @abstractmethod
    def update_identity_provider(
        self,
        alias: str,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def delete_identity_provider(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def export_identity_provider(self, alias: str, export_format: str | None = None) -> str:
        """Export the broker configuration of an identity provider, for example as SAML metadata."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider_management_permissions(self, alias: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def update_identity_provider_management_permissions(
        self,
        alias: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider_mapper_types(self, alias: str) -> dict[str, Any]:
        """List the mapper types an identity provider supports."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider_mappers(self, alias: str) -> list[KeycloakIdentityProviderMapperDTO]:
        """List the mappers of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def create_identity_provider_mapper(
        self,
        alias: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakIdentityProviderMapperDTO:
        """Get a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def update_identity_provider_mapper(
        self,
        alias: str,
        mapper_id: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def delete_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakDeleteResultDTO:
        """Delete a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    def reload_identity_provider_keys(self, alias: str) -> bool:
        """Reload the keys of an identity provider from its JWKS URL."""
        raise NotImplementedError

    @abstractmethod
    def get_identity_provider_factory(self, provider_id: str) -> dict[str, Any]:
        """Get the description of an identity provider type, such as ``oidc`` or ``saml``."""
        raise NotImplementedError

    @abstractmethod
    def import_identity_provider_config(self, payload: dict[str, Any]) -> dict[str, str]:
        """Read identity provider settings from a metadata URL or file content."""
        raise NotImplementedError


class AsyncKeycloakIdentityProvidersPort:
    """Async Keycloak port interface for identity providers and their mappers."""

    @abstractmethod
    async def get_identity_providers(self, query: dict[str, Any] | None = None) -> list[KeycloakIdentityProviderDTO]:
        """List the identity providers of the realm."""
        raise NotImplementedError

    @abstractmethod
    async def create_identity_provider(
        self,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider(self, alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider by alias."""
        raise NotImplementedError

    @abstractmethod
    async def update_identity_provider(
        self,
        alias: str,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def delete_identity_provider(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def export_identity_provider(self, alias: str, export_format: str | None = None) -> str:
        """Export the broker configuration of an identity provider, for example as SAML metadata."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider_management_permissions(self, alias: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def update_identity_provider_management_permissions(
        self,
        alias: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider_mapper_types(self, alias: str) -> dict[str, Any]:
        """List the mapper types an identity provider supports."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider_mappers(self, alias: str) -> list[KeycloakIdentityProviderMapperDTO]:
        """List the mappers of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def create_identity_provider_mapper(
        self,
        alias: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakIdentityProviderMapperDTO:
        """Get a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def update_identity_provider_mapper(
        self,
        alias: str,
        mapper_id: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def delete_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakDeleteResultDTO:
        """Delete a mapper of an identity provider."""
        raise NotImplementedError

    @abstractmethod
    async def reload_identity_provider_keys(self, alias: str) -> bool:
        """Reload the keys of an identity provider from its JWKS URL."""
        raise NotImplementedError

    @abstractmethod
    async def get_identity_provider_factory(self, provider_id: str) -> dict[str, Any]:
        """Get the description of an identity provider type, such as ``oidc`` or ``saml``."""
        raise NotImplementedError

    @abstractmethod
    async def import_identity_provider_config(self, payload: dict[str, Any]) -> dict[str, str]:
        """Read identity provider settings from a metadata URL or file content."""
        raise NotImplementedError
