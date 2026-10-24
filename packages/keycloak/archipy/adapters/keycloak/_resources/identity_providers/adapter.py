"""Keycloak adapter mixins for identity providers and their mappers."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    payload_value,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
    to_text,
    with_created_id,
    with_created_id_async,
)
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


class KeycloakIdentityProvidersMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for identity providers and their mappers."""

    def _find_identity_provider_internal_id(self, alias: str) -> str | None:
        """Return the internal id of the identity provider ``alias``."""
        return self.get_identity_provider(alias).internal_id

    def _find_identity_provider_mapper_id(self, alias: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of an identity provider."""
        return next((mapper.id for mapper in self.get_identity_provider_mappers(alias) if mapper.name == name), None)

    def get_identity_providers(self, query: dict[str, Any] | None = None) -> list[KeycloakIdentityProviderDTO]:
        """List the identity providers of the realm.

        Args:
            query: Optional query parameters: ``search``, ``type``, ``capability``, ``realmOnly``, ``first``,
                ``max`` and ``briefRepresentation``.

        Returns:
            The identity providers.
        """
        return to_dto_list(
            KeycloakIdentityProviderDTO,
            self._admin_request(
                "get_identity_providers",
                "get",
                "/identity-provider/instances",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def create_identity_provider(
        self,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create an identity provider.

        Args:
            payload: Identity provider representation.

        Returns:
            The create result, with the internal id of the new provider.
        """
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._admin_request(
                    "create_identity_provider",
                    "post",
                    "/identity-provider/instances",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.OK,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_identity_provider_internal_id(payload_value(payload, "alias", "alias") or ""),
        )

    def get_identity_provider(self, alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider by alias.

        Args:
            alias: Identity provider alias.

        Returns:
            The identity provider.
        """
        return to_dto(
            KeycloakIdentityProviderDTO,
            self._admin_request(
                "get_identity_provider",
                "get",
                f"/identity-provider/instances/{segment(alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_identity_provider(
        self,
        alias: str,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Identity provider representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_identity_provider",
                "put",
                f"/identity-provider/instances/{segment(alias)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_identity_provider(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_identity_provider",
                "delete",
                f"/identity-provider/instances/{segment(alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def export_identity_provider(self, alias: str, export_format: str | None = None) -> str:
        """Export the broker configuration of an identity provider, for example as SAML metadata.

        Args:
            alias: Identity provider alias.
            export_format: Export format understood by the provider.

        Returns:
            The exported configuration.
        """
        return to_text(
            self._admin_request(
                "export_identity_provider",
                "get",
                f"/identity-provider/instances/{segment(alias)}/export",
                params={"format": export_format} if export_format else None,
                expected=(HTTPStatus.OK, HTTPStatus.NO_CONTENT),
            ),
        )

    def get_identity_provider_management_permissions(self, alias: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_identity_provider_management_permissions",
                "get",
                f"/identity-provider/instances/{segment(alias)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_identity_provider_management_permissions(
        self,
        alias: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_identity_provider_management_permissions",
                "put",
                f"/identity-provider/instances/{segment(alias)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_identity_provider_mapper_types(self, alias: str) -> dict[str, Any]:
        """List the mapper types an identity provider supports.

        Args:
            alias: Identity provider alias.

        Returns:
            The mapper types by id.
        """
        return self._admin_request(
            "get_identity_provider_mapper_types",
            "get",
            f"/identity-provider/instances/{segment(alias)}/mapper-types",
            expected=(HTTPStatus.OK,),
        )

    def get_identity_provider_mappers(self, alias: str) -> list[KeycloakIdentityProviderMapperDTO]:
        """List the mappers of an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakIdentityProviderMapperDTO,
            self._admin_request(
                "get_identity_provider_mappers",
                "get",
                f"/identity-provider/instances/{segment(alias)}/mappers",
                expected=(HTTPStatus.OK,),
            ),
        )

    def create_identity_provider_mapper(
        self,
        alias: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Mapper representation.

        Returns:
            The create result, with the id of the new mapper.
        """
        return with_created_id(
            to_mutation_result(
                KeycloakCreateResultDTO,
                self._admin_request(
                    "create_identity_provider_mapper",
                    "post",
                    f"/identity-provider/instances/{segment(alias)}/mappers",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.OK,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_identity_provider_mapper_id(alias, payload_value(payload, "name", "name")),
        )

    def get_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakIdentityProviderMapperDTO:
        """Get a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakIdentityProviderMapperDTO,
            self._admin_request(
                "get_identity_provider_mapper",
                "get",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_identity_provider_mapper(
        self,
        alias: str,
        mapper_id: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.
            payload: Mapper representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_identity_provider_mapper",
                "put",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakDeleteResultDTO:
        """Delete a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_identity_provider_mapper",
                "delete",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def reload_identity_provider_keys(self, alias: str) -> bool:
        """Reload the keys of an identity provider from its JWKS URL.

        Args:
            alias: Identity provider alias.

        Returns:
            Whether the keys were reloaded.
        """
        return self._admin_request(
            "reload_identity_provider_keys",
            "get",
            f"/identity-provider/instances/{segment(alias)}/reload-keys",
            expected=(HTTPStatus.OK,),
        )

    def get_identity_provider_factory(self, provider_id: str) -> dict[str, Any]:
        """Get the description of an identity provider type, such as ``oidc`` or ``saml``.

        Args:
            provider_id: Provider type id.

        Returns:
            The provider description.
        """
        return self._admin_request(
            "get_identity_provider_factory",
            "get",
            f"/identity-provider/providers/{segment(provider_id)}",
            expected=(HTTPStatus.OK,),
        )

    def import_identity_provider_config(self, payload: dict[str, Any]) -> dict[str, str]:
        """Read identity provider settings from a metadata URL or file content.

        Args:
            payload: ``{"fromUrl": ..., "providerId": ...}``.

        Returns:
            The identity provider config.
        """
        return self._admin_request(
            "import_identity_provider_config",
            "post",
            "/identity-provider/import-config",
            body=payload,
            expected=(HTTPStatus.OK,),
        )


class AsyncKeycloakIdentityProvidersMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for identity providers and their mappers."""

    async def _find_identity_provider_internal_id(self, alias: str) -> str | None:
        """Return the internal id of the identity provider ``alias``."""
        return (await self.get_identity_provider(alias)).internal_id

    async def _find_identity_provider_mapper_id(self, alias: str, name: str | None) -> str | None:
        """Return the id of the mapper ``name`` of an identity provider."""
        mappers = await self.get_identity_provider_mappers(alias)
        return next((mapper.id for mapper in mappers if mapper.name == name), None)

    async def get_identity_providers(self, query: dict[str, Any] | None = None) -> list[KeycloakIdentityProviderDTO]:
        """List the identity providers of the realm.

        Args:
            query: Optional query parameters: ``search``, ``type``, ``capability``, ``realmOnly``, ``first``,
                ``max`` and ``briefRepresentation``.

        Returns:
            The identity providers.
        """
        return to_dto_list(
            KeycloakIdentityProviderDTO,
            await self._async_admin_request(
                "get_identity_providers",
                "get",
                "/identity-provider/instances",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def create_identity_provider(
        self,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create an identity provider.

        Args:
            payload: Identity provider representation.

        Returns:
            The create result, with the internal id of the new provider.
        """
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_admin_request(
                    "create_identity_provider",
                    "post",
                    "/identity-provider/instances",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.OK,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_identity_provider_internal_id(payload_value(payload, "alias", "alias") or ""),
        )

    async def get_identity_provider(self, alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider by alias.

        Args:
            alias: Identity provider alias.

        Returns:
            The identity provider.
        """
        return to_dto(
            KeycloakIdentityProviderDTO,
            await self._async_admin_request(
                "get_identity_provider",
                "get",
                f"/identity-provider/instances/{segment(alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_identity_provider(
        self,
        alias: str,
        payload: KeycloakIdentityProviderRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Identity provider representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_identity_provider",
                "put",
                f"/identity-provider/instances/{segment(alias)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_identity_provider(self, alias: str) -> KeycloakDeleteResultDTO:
        """Delete an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_identity_provider",
                "delete",
                f"/identity-provider/instances/{segment(alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def export_identity_provider(self, alias: str, export_format: str | None = None) -> str:
        """Export the broker configuration of an identity provider, for example as SAML metadata.

        Args:
            alias: Identity provider alias.
            export_format: Export format understood by the provider.

        Returns:
            The exported configuration.
        """
        return to_text(
            await self._async_admin_request(
                "export_identity_provider",
                "get",
                f"/identity-provider/instances/{segment(alias)}/export",
                params={"format": export_format} if export_format else None,
                expected=(HTTPStatus.OK, HTTPStatus.NO_CONTENT),
            ),
        )

    async def get_identity_provider_management_permissions(self, alias: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_identity_provider_management_permissions",
                "get",
                f"/identity-provider/instances/{segment(alias)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_identity_provider_management_permissions(
        self,
        alias: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_identity_provider_management_permissions",
                "put",
                f"/identity-provider/instances/{segment(alias)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_identity_provider_mapper_types(self, alias: str) -> dict[str, Any]:
        """List the mapper types an identity provider supports.

        Args:
            alias: Identity provider alias.

        Returns:
            The mapper types by id.
        """
        return await self._async_admin_request(
            "get_identity_provider_mapper_types",
            "get",
            f"/identity-provider/instances/{segment(alias)}/mapper-types",
            expected=(HTTPStatus.OK,),
        )

    async def get_identity_provider_mappers(self, alias: str) -> list[KeycloakIdentityProviderMapperDTO]:
        """List the mappers of an identity provider.

        Args:
            alias: Identity provider alias.

        Returns:
            The mappers.
        """
        return to_dto_list(
            KeycloakIdentityProviderMapperDTO,
            await self._async_admin_request(
                "get_identity_provider_mappers",
                "get",
                f"/identity-provider/instances/{segment(alias)}/mappers",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def create_identity_provider_mapper(
        self,
        alias: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakCreateResultDTO:
        """Create a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            payload: Mapper representation.

        Returns:
            The create result, with the id of the new mapper.
        """
        return await with_created_id_async(
            to_mutation_result(
                KeycloakCreateResultDTO,
                await self._async_admin_request(
                    "create_identity_provider_mapper",
                    "post",
                    f"/identity-provider/instances/{segment(alias)}/mappers",
                    body=to_request_payload(payload),
                    expected=(
                        HTTPStatus.CREATED,
                        HTTPStatus.OK,
                        HTTPStatus.NO_CONTENT,
                    ),
                ),
            ),
            lambda: self._find_identity_provider_mapper_id(alias, payload_value(payload, "name", "name")),
        )

    async def get_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakIdentityProviderMapperDTO:
        """Get a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.

        Returns:
            The mapper.
        """
        return to_dto(
            KeycloakIdentityProviderMapperDTO,
            await self._async_admin_request(
                "get_identity_provider_mapper",
                "get",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_identity_provider_mapper(
        self,
        alias: str,
        mapper_id: str,
        payload: KeycloakIdentityProviderMapperRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.
            payload: Mapper representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_identity_provider_mapper",
                "put",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_identity_provider_mapper(self, alias: str, mapper_id: str) -> KeycloakDeleteResultDTO:
        """Delete a mapper of an identity provider.

        Args:
            alias: Identity provider alias.
            mapper_id: Mapper identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_identity_provider_mapper",
                "delete",
                f"/identity-provider/instances/{segment(alias)}/mappers/{segment(mapper_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def reload_identity_provider_keys(self, alias: str) -> bool:
        """Reload the keys of an identity provider from its JWKS URL.

        Args:
            alias: Identity provider alias.

        Returns:
            Whether the keys were reloaded.
        """
        return await self._async_admin_request(
            "reload_identity_provider_keys",
            "get",
            f"/identity-provider/instances/{segment(alias)}/reload-keys",
            expected=(HTTPStatus.OK,),
        )

    async def get_identity_provider_factory(self, provider_id: str) -> dict[str, Any]:
        """Get the description of an identity provider type, such as ``oidc`` or ``saml``.

        Args:
            provider_id: Provider type id.

        Returns:
            The provider description.
        """
        return await self._async_admin_request(
            "get_identity_provider_factory",
            "get",
            f"/identity-provider/providers/{segment(provider_id)}",
            expected=(HTTPStatus.OK,),
        )

    async def import_identity_provider_config(self, payload: dict[str, Any]) -> dict[str, str]:
        """Read identity provider settings from a metadata URL or file content.

        Args:
            payload: ``{"fromUrl": ..., "providerId": ...}``.

        Returns:
            The identity provider config.
        """
        return await self._async_admin_request(
            "import_identity_provider_config",
            "post",
            "/identity-provider/import-config",
            body=payload,
            expected=(HTTPStatus.OK,),
        )
