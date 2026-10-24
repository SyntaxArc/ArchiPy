"""Keycloak adapter mixins for client operations."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from async_lru import alru_cache
from keycloak.exceptions import (
    KeycloakError,
)

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_list,
    to_dto_or_none,
    to_mutation_result,
    to_request_payload,
    to_text,
)
from archipy.helpers.decorators import ttl_cache
from archipy.helpers.utils.string_utils import StringUtils
from archipy.models.dtos.keycloak.client_dtos import KeycloakClientDTO, KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.client_evaluation_dtos import (
    KeycloakGlobalRequestResultDTO,
    KeycloakProtocolMapperEvaluationDTO,
    KeycloakSamlExampleResponseDTO,
)
from archipy.models.dtos.keycloak.common_dtos import (
    KeycloakAssignResultDTO,
    KeycloakCountDTO,
    KeycloakDeleteResultDTO,
    KeycloakUpdateResultDTO,
)
from archipy.models.dtos.keycloak.management_permission_dtos import (
    KeycloakManagementPermissionDTO,
    KeycloakManagementPermissionRequestDTO,
)
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO
from archipy.models.dtos.keycloak.session_dtos import KeycloakUserSessionDTO
from archipy.models.dtos.keycloak.token_dtos import KeycloakTokenClaimsDTO, KeycloakUserInfoDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakCredentialDTO, KeycloakUserDTO

logger = logging.getLogger(__name__)


class KeycloakClientsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for client operations."""

    @ttl_cache(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = self.get_client_id(self.configs.CLIENT_ID)
            return self.admin_adapter.get_client_service_account_user(str(client_id)).get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @ttl_cache(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = self.admin_adapter.get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @ttl_cache(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return self.admin_adapter.get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        config: KeycloakClientRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakClientDTO | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            config: Optional request DTO; keyword arguments override its values.
            kwargs: Additional optional configurations for the client

        Returns:
            Client details
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            if config is not None:
                payload = {**payload, **config.to_payload()}

            internal_client_id = None
            try:
                internal_client_id = self.admin_adapter.create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug("Failed to create client: %s", e)

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return to_dto_or_none(
                            KeycloakClientDTO,
                            {
                                "client_id": client_id,
                                "status": "already_exists",
                                "realm": self.admin_adapter.connection.realm_name,
                            },
                        )

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return to_dto_or_none(
                KeycloakClientDTO,
                {
                    "client_id": client_id,
                    "internal_client_id": internal_client_id,
                    "realm": self.admin_adapter.connection.realm_name,
                    "status": "created",
                },
            )

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm

    def get_clients(self, query: dict[str, Any] | None = None) -> list[KeycloakClientDTO]:
        """List clients, filtered by the admin API query parameters.

        Args:
            query: Optional query parameters such as ``clientId``, ``search``, ``first`` and ``max``.

        Returns:
            The clients.
        """
        return to_dto_list(
            KeycloakClientDTO,
            self._admin_request(
                "get_clients",
                "get",
                "/clients",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client(self, client_uuid: str) -> KeycloakClientDTO:
        """Get a client by its UUID.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The client.
        """
        return to_dto(
            KeycloakClientDTO,
            self._admin_request(
                "get_client",
                "get",
                f"/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_client(
        self,
        client_uuid: str,
        payload: KeycloakClientRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            payload: Client representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_client",
                "put",
                f"/clients/{segment(client_uuid)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def delete_client(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Delete a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_client",
                "delete",
                f"/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_secret_credential(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the secret credential of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            self._admin_request(
                "get_client_secret_credential",
                "get",
                f"/clients/{segment(client_uuid)}/client-secret",
                expected=(HTTPStatus.OK,),
            ),
        )

    def regenerate_client_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Generate a new secret for a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The new secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            self._admin_request(
                "regenerate_client_secret",
                "post",
                f"/clients/{segment(client_uuid)}/client-secret",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_rotated_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the rotated (previous) secret of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The rotated secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            self._admin_request(
                "get_client_rotated_secret",
                "get",
                f"/clients/{segment(client_uuid)}/client-secret/rotated",
                expected=(HTTPStatus.OK,),
            ),
        )

    def invalidate_client_rotated_secret(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Invalidate the rotated secret of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "invalidate_client_rotated_secret",
                "delete",
                f"/clients/{segment(client_uuid)}/client-secret/rotated",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def regenerate_client_registration_access_token(self, client_uuid: str) -> KeycloakClientDTO:
        """Generate a new registration access token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The client with its new ``registrationAccessToken``.
        """
        return to_dto(
            KeycloakClientDTO,
            self._admin_request(
                "regenerate_client_registration_access_token",
                "post",
                f"/clients/{segment(client_uuid)}/registration-access-token",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_service_account_user(self, client_uuid: str) -> KeycloakUserDTO:
        """Get the service account user of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The service account user.
        """
        return to_dto(
            KeycloakUserDTO,
            self._admin_request(
                "get_client_service_account_user",
                "get",
                f"/clients/{segment(client_uuid)}/service-account-user",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_example_access_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example access token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``, ``userId`` and ``audience``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakTokenClaimsDTO,
            self._admin_request(
                "get_client_example_access_token",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-access-token",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_example_id_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example ID token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``, ``userId`` and ``audience``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakTokenClaimsDTO,
            self._admin_request(
                "get_client_example_id_token",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-id-token",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_example_userinfo(self, client_uuid: str, query: dict[str, Any] | None = None) -> KeycloakUserInfoDTO:
        """Generate an example UserInfo response for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope`` and ``userId``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakUserInfoDTO,
            self._admin_request(
                "get_client_example_userinfo",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-userinfo",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_example_saml_response(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakSamlExampleResponseDTO:
        """Generate an example SAML response for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope`` and ``userId``.

        Returns:
            The example response.
        """
        return to_dto(
            KeycloakSamlExampleResponseDTO,
            self._admin_request(
                "get_client_example_saml_response",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-saml-response",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def evaluate_client_protocol_mappers(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakProtocolMapperEvaluationDTO]:
        """Evaluate which protocol mappers apply to a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``.

        Returns:
            The mappers that apply.
        """
        return to_dto_list(
            KeycloakProtocolMapperEvaluationDTO,
            self._admin_request(
                "evaluate_client_protocol_mappers",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/protocol-mappers",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container granted by the client's scopes.

        Args:
            client_uuid: Client UUID (not the client ID).
            role_container_id: UUID of the client that owns the roles (a realm id was rejected by Keycloak 26).
            query: Optional query parameters: ``scope``.

        Returns:
            The granted roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_granted_scope_roles",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/scope-mappings/{segment(role_container_id)}/granted",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_not_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container not granted by the client's scopes.

        Args:
            client_uuid: Client UUID (not the client ID).
            role_container_id: UUID of the client that owns the roles (a realm id was rejected by Keycloak 26).
            query: Optional query parameters: ``scope``.

        Returns:
            The roles not granted.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            self._admin_request(
                "get_client_not_granted_scope_roles",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/scope-mappings/{segment(role_container_id)}/not-granted",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_installation_provider(self, client_uuid: str, provider_id: str) -> str:
        """Get the client adapter configuration for a provider, such as ``keycloak-oidc-keycloak-json``.

        Args:
            client_uuid: Client UUID (not the client ID).
            provider_id: Installation provider id.

        Returns:
            The configuration text.
        """
        return to_text(
            self._admin_request(
                "get_client_installation_provider",
                "get",
                f"/clients/{segment(client_uuid)}/installation/providers/{segment(provider_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_management_permissions(self, client_uuid: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "get_client_management_permissions",
                "get",
                f"/clients/{segment(client_uuid)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_client_management_permissions(
        self,
        client_uuid: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            self._admin_request(
                "update_client_management_permissions",
                "put",
                f"/clients/{segment(client_uuid)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    def register_client_node(self, client_uuid: str, node: str) -> KeycloakAssignResultDTO:
        """Register a cluster node with a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            node: Host name of the node.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "register_client_node",
                "post",
                f"/clients/{segment(client_uuid)}/nodes",
                body={"node": node},
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def unregister_client_node(self, client_uuid: str, node: str) -> KeycloakDeleteResultDTO:
        """Unregister a cluster node from a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            node: Host name of the node.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "unregister_client_node",
                "delete",
                f"/clients/{segment(client_uuid)}/nodes/{segment(node)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_client_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the active user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The count.
        """
        return to_dto(
            KeycloakCountDTO,
            self._admin_request(
                "get_client_session_count",
                "get",
                f"/clients/{segment(client_uuid)}/session-count",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_offline_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the offline user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The count.
        """
        return to_dto(
            KeycloakCountDTO,
            self._admin_request(
                "get_client_offline_session_count",
                "get",
                f"/clients/{segment(client_uuid)}/offline-session-count",
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_user_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the active user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``first`` and ``max``.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            self._admin_request(
                "get_client_user_sessions",
                "get",
                f"/clients/{segment(client_uuid)}/user-sessions",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_client_offline_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the offline user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``first`` and ``max``.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            self._admin_request(
                "get_client_offline_sessions",
                "get",
                f"/clients/{segment(client_uuid)}/offline-sessions",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def push_client_revocation(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Push the client's revocation policy to its registered nodes.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            self._admin_request(
                "push_client_revocation",
                "post",
                f"/clients/{segment(client_uuid)}/push-revocation",
                expected=(HTTPStatus.OK,),
            ),
        )

    def test_client_nodes_available(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Test whether the client's registered nodes are reachable.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            self._admin_request(
                "test_client_nodes_available",
                "get",
                f"/clients/{segment(client_uuid)}/test-nodes-available",
                expected=(HTTPStatus.OK,),
            ),
        )


class AsyncKeycloakClientsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for client operations."""

    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = await self.get_client_id(self.configs.CLIENT_ID)
            if client_id is None:
                return None
            service_account = await self.admin_adapter.a_get_client_service_account_user(client_id)
            return service_account.get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = await self.admin_adapter.a_get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return await self.admin_adapter.a_get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        config: KeycloakClientRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakClientDTO | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            config: Optional request DTO; keyword arguments override its values.
            kwargs: Additional optional configurations for the client

        Returns:
            Dictionary with client information

        Raises:
            InternalError: If client creation fails
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            if config is not None:
                payload = {**payload, **config.to_payload()}

            internal_client_id = None
            try:
                internal_client_id = await self.admin_adapter.a_create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug("Failed to create client: %s", e)

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return to_dto_or_none(
                            KeycloakClientDTO,
                            {
                                "client_id": client_id,
                                "status": "already_exists",
                                "realm": self.admin_adapter.connection.realm_name,
                            },
                        )

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return to_dto_or_none(
                KeycloakClientDTO,
                {
                    "client_id": client_id,
                    "internal_client_id": internal_client_id,
                    "realm": self.admin_adapter.connection.realm_name,
                    "status": "created",
                },
            )

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm

    async def get_clients(self, query: dict[str, Any] | None = None) -> list[KeycloakClientDTO]:
        """List clients, filtered by the admin API query parameters.

        Args:
            query: Optional query parameters such as ``clientId``, ``search``, ``first`` and ``max``.

        Returns:
            The clients.
        """
        return to_dto_list(
            KeycloakClientDTO,
            await self._async_admin_request(
                "get_clients",
                "get",
                "/clients",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client(self, client_uuid: str) -> KeycloakClientDTO:
        """Get a client by its UUID.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The client.
        """
        return to_dto(
            KeycloakClientDTO,
            await self._async_admin_request(
                "get_client",
                "get",
                f"/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_client(
        self,
        client_uuid: str,
        payload: KeycloakClientRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            payload: Client representation.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_client",
                "put",
                f"/clients/{segment(client_uuid)}",
                body=to_request_payload(payload),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def delete_client(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Delete a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_client",
                "delete",
                f"/clients/{segment(client_uuid)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_secret_credential(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the secret credential of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            await self._async_admin_request(
                "get_client_secret_credential",
                "get",
                f"/clients/{segment(client_uuid)}/client-secret",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def regenerate_client_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Generate a new secret for a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The new secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            await self._async_admin_request(
                "regenerate_client_secret",
                "post",
                f"/clients/{segment(client_uuid)}/client-secret",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_rotated_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the rotated (previous) secret of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The rotated secret credential.
        """
        return to_dto(
            KeycloakCredentialDTO,
            await self._async_admin_request(
                "get_client_rotated_secret",
                "get",
                f"/clients/{segment(client_uuid)}/client-secret/rotated",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def invalidate_client_rotated_secret(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Invalidate the rotated secret of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "invalidate_client_rotated_secret",
                "delete",
                f"/clients/{segment(client_uuid)}/client-secret/rotated",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def regenerate_client_registration_access_token(self, client_uuid: str) -> KeycloakClientDTO:
        """Generate a new registration access token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The client with its new ``registrationAccessToken``.
        """
        return to_dto(
            KeycloakClientDTO,
            await self._async_admin_request(
                "regenerate_client_registration_access_token",
                "post",
                f"/clients/{segment(client_uuid)}/registration-access-token",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_service_account_user(self, client_uuid: str) -> KeycloakUserDTO:
        """Get the service account user of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The service account user.
        """
        return to_dto(
            KeycloakUserDTO,
            await self._async_admin_request(
                "get_client_service_account_user",
                "get",
                f"/clients/{segment(client_uuid)}/service-account-user",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_example_access_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example access token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``, ``userId`` and ``audience``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakTokenClaimsDTO,
            await self._async_admin_request(
                "get_client_example_access_token",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-access-token",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_example_id_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example ID token for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``, ``userId`` and ``audience``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakTokenClaimsDTO,
            await self._async_admin_request(
                "get_client_example_id_token",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-id-token",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_example_userinfo(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUserInfoDTO:
        """Generate an example UserInfo response for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope`` and ``userId``.

        Returns:
            The example claims.
        """
        return to_dto(
            KeycloakUserInfoDTO,
            await self._async_admin_request(
                "get_client_example_userinfo",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-userinfo",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_example_saml_response(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakSamlExampleResponseDTO:
        """Generate an example SAML response for a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope`` and ``userId``.

        Returns:
            The example response.
        """
        return to_dto(
            KeycloakSamlExampleResponseDTO,
            await self._async_admin_request(
                "get_client_example_saml_response",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/generate-example-saml-response",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def evaluate_client_protocol_mappers(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakProtocolMapperEvaluationDTO]:
        """Evaluate which protocol mappers apply to a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``scope``.

        Returns:
            The mappers that apply.
        """
        return to_dto_list(
            KeycloakProtocolMapperEvaluationDTO,
            await self._async_admin_request(
                "evaluate_client_protocol_mappers",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/protocol-mappers",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container granted by the client's scopes.

        Args:
            client_uuid: Client UUID (not the client ID).
            role_container_id: UUID of the client that owns the roles (a realm id was rejected by Keycloak 26).
            query: Optional query parameters: ``scope``.

        Returns:
            The granted roles.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_granted_scope_roles",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/scope-mappings/{segment(role_container_id)}/granted",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_not_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container not granted by the client's scopes.

        Args:
            client_uuid: Client UUID (not the client ID).
            role_container_id: UUID of the client that owns the roles (a realm id was rejected by Keycloak 26).
            query: Optional query parameters: ``scope``.

        Returns:
            The roles not granted.
        """
        return to_dto_list(
            KeycloakRoleDTO,
            await self._async_admin_request(
                "get_client_not_granted_scope_roles",
                "get",
                f"/clients/{segment(client_uuid)}/evaluate-scopes/scope-mappings/{segment(role_container_id)}/not-granted",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_installation_provider(self, client_uuid: str, provider_id: str) -> str:
        """Get the client adapter configuration for a provider, such as ``keycloak-oidc-keycloak-json``.

        Args:
            client_uuid: Client UUID (not the client ID).
            provider_id: Installation provider id.

        Returns:
            The configuration text.
        """
        return to_text(
            await self._async_admin_request(
                "get_client_installation_provider",
                "get",
                f"/clients/{segment(client_uuid)}/installation/providers/{segment(provider_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_management_permissions(self, client_uuid: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "get_client_management_permissions",
                "get",
                f"/clients/{segment(client_uuid)}/management/permissions",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_client_management_permissions(
        self,
        client_uuid: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            payload: Management permission reference.

        Returns:
            The management permission reference.
        """
        return to_dto(
            KeycloakManagementPermissionDTO,
            await self._async_admin_request(
                "update_client_management_permissions",
                "put",
                f"/clients/{segment(client_uuid)}/management/permissions",
                body=to_request_payload(payload),
                expected=(HTTPStatus.OK,),
            ),
        )

    async def register_client_node(self, client_uuid: str, node: str) -> KeycloakAssignResultDTO:
        """Register a cluster node with a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            node: Host name of the node.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "register_client_node",
                "post",
                f"/clients/{segment(client_uuid)}/nodes",
                body={"node": node},
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def unregister_client_node(self, client_uuid: str, node: str) -> KeycloakDeleteResultDTO:
        """Unregister a cluster node from a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            node: Host name of the node.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "unregister_client_node",
                "delete",
                f"/clients/{segment(client_uuid)}/nodes/{segment(node)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_client_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the active user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The count.
        """
        return to_dto(
            KeycloakCountDTO,
            await self._async_admin_request(
                "get_client_session_count",
                "get",
                f"/clients/{segment(client_uuid)}/session-count",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_offline_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the offline user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The count.
        """
        return to_dto(
            KeycloakCountDTO,
            await self._async_admin_request(
                "get_client_offline_session_count",
                "get",
                f"/clients/{segment(client_uuid)}/offline-session-count",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_user_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the active user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``first`` and ``max``.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            await self._async_admin_request(
                "get_client_user_sessions",
                "get",
                f"/clients/{segment(client_uuid)}/user-sessions",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_client_offline_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the offline user sessions of a client.

        Args:
            client_uuid: Client UUID (not the client ID).
            query: Optional query parameters: ``first`` and ``max``.

        Returns:
            The sessions.
        """
        return to_dto_list(
            KeycloakUserSessionDTO,
            await self._async_admin_request(
                "get_client_offline_sessions",
                "get",
                f"/clients/{segment(client_uuid)}/offline-sessions",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def push_client_revocation(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Push the client's revocation policy to its registered nodes.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            await self._async_admin_request(
                "push_client_revocation",
                "post",
                f"/clients/{segment(client_uuid)}/push-revocation",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def test_client_nodes_available(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Test whether the client's registered nodes are reachable.

        Args:
            client_uuid: Client UUID (not the client ID).

        Returns:
            The nodes that succeeded and failed.
        """
        return to_dto(
            KeycloakGlobalRequestResultDTO,
            await self._async_admin_request(
                "test_client_nodes_available",
                "get",
                f"/clients/{segment(client_uuid)}/test-nodes-available",
                expected=(HTTPStatus.OK,),
            ),
        )
