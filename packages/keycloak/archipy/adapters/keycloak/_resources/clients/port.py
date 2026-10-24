"""Keycloak port mixins for client operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.client_dtos import KeycloakClientDTO, KeycloakClientRequestDTO

if TYPE_CHECKING:
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


class KeycloakClientsPort:
    """Sync Keycloak port interface for client operations."""

    @abstractmethod
    def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    @abstractmethod
    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        config: KeycloakClientRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakClientDTO | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError

    @abstractmethod
    def get_clients(self, query: dict[str, Any] | None = None) -> list[KeycloakClientDTO]:
        """List clients, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    def get_client(self, client_uuid: str) -> KeycloakClientDTO:
        """Get a client by its UUID."""
        raise NotImplementedError

    @abstractmethod
    def update_client(
        self,
        client_uuid: str,
        payload: KeycloakClientRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client."""
        raise NotImplementedError

    @abstractmethod
    def delete_client(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Delete a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_secret_credential(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the secret credential of a client."""
        raise NotImplementedError

    @abstractmethod
    def regenerate_client_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Generate a new secret for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_rotated_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the rotated (previous) secret of a client."""
        raise NotImplementedError

    @abstractmethod
    def invalidate_client_rotated_secret(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Invalidate the rotated secret of a client."""
        raise NotImplementedError

    @abstractmethod
    def regenerate_client_registration_access_token(self, client_uuid: str) -> KeycloakClientDTO:
        """Generate a new registration access token for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_service_account_user(self, client_uuid: str) -> KeycloakUserDTO:
        """Get the service account user of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_example_access_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example access token for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_example_id_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example ID token for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_example_userinfo(self, client_uuid: str, query: dict[str, Any] | None = None) -> KeycloakUserInfoDTO:
        """Generate an example UserInfo response for a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_example_saml_response(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakSamlExampleResponseDTO:
        """Generate an example SAML response for a client."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_client_protocol_mappers(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakProtocolMapperEvaluationDTO]:
        """Evaluate which protocol mappers apply to a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container granted by the client's scopes."""
        raise NotImplementedError

    @abstractmethod
    def get_client_not_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container not granted by the client's scopes."""
        raise NotImplementedError

    @abstractmethod
    def get_client_installation_provider(self, client_uuid: str, provider_id: str) -> str:
        """Get the client adapter configuration for a provider, such as ``keycloak-oidc-keycloak-json``."""
        raise NotImplementedError

    @abstractmethod
    def get_client_management_permissions(self, client_uuid: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client."""
        raise NotImplementedError

    @abstractmethod
    def update_client_management_permissions(
        self,
        client_uuid: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client."""
        raise NotImplementedError

    @abstractmethod
    def register_client_node(self, client_uuid: str, node: str) -> KeycloakAssignResultDTO:
        """Register a cluster node with a client."""
        raise NotImplementedError

    @abstractmethod
    def unregister_client_node(self, client_uuid: str, node: str) -> KeycloakDeleteResultDTO:
        """Unregister a cluster node from a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the active user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_offline_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the offline user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_user_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the active user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    def get_client_offline_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the offline user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    def push_client_revocation(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Push the client's revocation policy to its registered nodes."""
        raise NotImplementedError

    @abstractmethod
    def test_client_nodes_available(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Test whether the client's registered nodes are reachable."""
        raise NotImplementedError


class AsyncKeycloakClientsPort:
    """Async Keycloak port interface for client operations."""

    @abstractmethod
    async def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret."""
        raise NotImplementedError

    @abstractmethod
    async def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client."""
        raise NotImplementedError

    @abstractmethod
    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        config: KeycloakClientRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakClientDTO | None:
        """Create a new client in the specified realm."""
        raise NotImplementedError

    @abstractmethod
    async def get_clients(self, query: dict[str, Any] | None = None) -> list[KeycloakClientDTO]:
        """List clients, filtered by the admin API query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def get_client(self, client_uuid: str) -> KeycloakClientDTO:
        """Get a client by its UUID."""
        raise NotImplementedError

    @abstractmethod
    async def update_client(
        self,
        client_uuid: str,
        payload: KeycloakClientRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update a client."""
        raise NotImplementedError

    @abstractmethod
    async def delete_client(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Delete a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_secret_credential(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the secret credential of a client."""
        raise NotImplementedError

    @abstractmethod
    async def regenerate_client_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Generate a new secret for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_rotated_secret(self, client_uuid: str) -> KeycloakCredentialDTO:
        """Get the rotated (previous) secret of a client."""
        raise NotImplementedError

    @abstractmethod
    async def invalidate_client_rotated_secret(self, client_uuid: str) -> KeycloakDeleteResultDTO:
        """Invalidate the rotated secret of a client."""
        raise NotImplementedError

    @abstractmethod
    async def regenerate_client_registration_access_token(self, client_uuid: str) -> KeycloakClientDTO:
        """Generate a new registration access token for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_service_account_user(self, client_uuid: str) -> KeycloakUserDTO:
        """Get the service account user of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_example_access_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example access token for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_example_id_token(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakTokenClaimsDTO:
        """Generate an example ID token for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_example_userinfo(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakUserInfoDTO:
        """Generate an example UserInfo response for a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_example_saml_response(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> KeycloakSamlExampleResponseDTO:
        """Generate an example SAML response for a client."""
        raise NotImplementedError

    @abstractmethod
    async def evaluate_client_protocol_mappers(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakProtocolMapperEvaluationDTO]:
        """Evaluate which protocol mappers apply to a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container granted by the client's scopes."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_not_granted_scope_roles(
        self,
        client_uuid: str,
        role_container_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakRoleDTO]:
        """List the roles of a role container not granted by the client's scopes."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_installation_provider(self, client_uuid: str, provider_id: str) -> str:
        """Get the client adapter configuration for a provider, such as ``keycloak-oidc-keycloak-json``."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_management_permissions(self, client_uuid: str) -> KeycloakManagementPermissionDTO:
        """Get the fine-grained permission setup of a client."""
        raise NotImplementedError

    @abstractmethod
    async def update_client_management_permissions(
        self,
        client_uuid: str,
        payload: KeycloakManagementPermissionRequestDTO | dict[str, Any],
    ) -> KeycloakManagementPermissionDTO:
        """Enable or disable the fine-grained permissions of a client."""
        raise NotImplementedError

    @abstractmethod
    async def register_client_node(self, client_uuid: str, node: str) -> KeycloakAssignResultDTO:
        """Register a cluster node with a client."""
        raise NotImplementedError

    @abstractmethod
    async def unregister_client_node(self, client_uuid: str, node: str) -> KeycloakDeleteResultDTO:
        """Unregister a cluster node from a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the active user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_offline_session_count(self, client_uuid: str) -> KeycloakCountDTO:
        """Count the offline user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_user_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the active user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    async def get_client_offline_sessions(
        self,
        client_uuid: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakUserSessionDTO]:
        """List the offline user sessions of a client."""
        raise NotImplementedError

    @abstractmethod
    async def push_client_revocation(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Push the client's revocation policy to its registered nodes."""
        raise NotImplementedError

    @abstractmethod
    async def test_client_nodes_available(self, client_uuid: str) -> KeycloakGlobalRequestResultDTO:
        """Test whether the client's registered nodes are reachable."""
        raise NotImplementedError
