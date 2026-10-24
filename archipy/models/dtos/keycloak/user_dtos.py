"""Keycloak user representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import Field, JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.user_profile_dtos import (
    KeycloakUserProfileMetadataDTO,
    KeycloakUserProfileMetadataRequestDTO,
)


class KeycloakCredentialDTO(KeycloakResponseDTO):
    """Keycloak ``CredentialRepresentation`` as returned by the admin API."""

    id: str | None = None
    type: str | None = None
    user_label: str | None = None
    created_date: int | None = None
    secret_data: str | None = None
    credential_data: str | None = None
    priority: int | None = None
    value: str | None = None
    temporary: bool | None = None
    device: str | None = None
    hashed_salted_value: str | None = None
    salt: str | None = None
    hash_iterations: int | None = None
    counter: int | None = None
    algorithm: str | None = None
    digits: int | None = None
    period: int | None = None
    config: dict[str, JsonValue] | None = None
    federation_link: str | None = None


class KeycloakCredentialRequestDTO(KeycloakRequestDTO):
    """Keycloak ``CredentialRepresentation`` payload sent to the admin API."""

    id: str | None = None
    type: str | None = None
    user_label: str | None = None
    created_date: int | None = None
    secret_data: str | None = None
    credential_data: str | None = None
    priority: int | None = None
    value: str | None = None
    temporary: bool | None = None
    device: str | None = None
    hashed_salted_value: str | None = None
    salt: str | None = None
    hash_iterations: int | None = None
    counter: int | None = None
    algorithm: str | None = None
    digits: int | None = None
    period: int | None = None
    config: dict[str, JsonValue] | None = None
    federation_link: str | None = None


class KeycloakFederatedIdentityDTO(KeycloakResponseDTO):
    """Keycloak ``FederatedIdentityRepresentation`` as returned by the admin API."""

    identity_provider: str | None = None
    user_id: str | None = None
    user_name: str | None = None


class KeycloakFederatedIdentityRequestDTO(KeycloakRequestDTO):
    """Keycloak ``FederatedIdentityRepresentation`` payload sent to the admin API."""

    identity_provider: str | None = None
    user_id: str | None = None
    user_name: str | None = None


class KeycloakUserDTO(KeycloakResponseDTO):
    """Keycloak ``UserRepresentation`` as returned by the admin API."""

    id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    attributes: dict[str, list[str]] | None = None
    user_profile_metadata: KeycloakUserProfileMetadataDTO | None = None
    enabled: bool | None = None
    self_link: str | None = Field(default=None, alias="self")
    origin: str | None = None
    created_timestamp: int | None = None
    totp: bool | None = None
    federation_link: str | None = None
    service_account_client_id: str | None = None
    credentials: list[KeycloakCredentialDTO] | None = None
    disableable_credential_types: list[str] | None = None
    required_actions: list[str] | None = None
    federated_identities: list[KeycloakFederatedIdentityDTO] | None = None
    realm_roles: list[str] | None = None
    client_roles: dict[str, list[str]] | None = None
    client_consents: list[KeycloakUserConsentDTO] | None = None
    not_before: int | None = None
    verifiable_credentials: list[dict[str, JsonValue]] | None = None
    issued_verifiable_credentials: list[dict[str, JsonValue]] | None = None
    application_roles: dict[str, list[str]] | None = None
    social_links: list[dict[str, JsonValue]] | None = None
    groups: list[str] | None = None
    access: dict[str, bool] | None = None


class KeycloakUserRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UserRepresentation`` payload sent to the admin API."""

    id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    attributes: dict[str, list[str]] | None = None
    user_profile_metadata: KeycloakUserProfileMetadataRequestDTO | None = None
    enabled: bool | None = None
    self_link: str | None = Field(default=None, alias="self")
    origin: str | None = None
    created_timestamp: int | None = None
    totp: bool | None = None
    federation_link: str | None = None
    service_account_client_id: str | None = None
    credentials: list[KeycloakCredentialRequestDTO] | None = None
    disableable_credential_types: list[str] | None = None
    required_actions: list[str] | None = None
    federated_identities: list[KeycloakFederatedIdentityRequestDTO] | None = None
    realm_roles: list[str] | None = None
    client_roles: dict[str, list[str]] | None = None
    client_consents: list[KeycloakUserConsentRequestDTO] | None = None
    not_before: int | None = None
    verifiable_credentials: list[dict[str, JsonValue]] | None = None
    issued_verifiable_credentials: list[dict[str, JsonValue]] | None = None
    application_roles: dict[str, list[str]] | None = None
    social_links: list[dict[str, JsonValue]] | None = None
    groups: list[str] | None = None
    access: dict[str, bool] | None = None


class KeycloakUserConsentDTO(KeycloakResponseDTO):
    """Keycloak ``UserConsentRepresentation`` as returned by the admin API."""

    client_id: str | None = None
    granted_client_scopes: list[str] | None = None
    created_date: int | None = None
    last_updated_date: int | None = None
    granted_realm_roles: list[str] | None = None


class KeycloakUserConsentRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UserConsentRepresentation`` payload sent to the admin API."""

    client_id: str | None = None
    granted_client_scopes: list[str] | None = None
    created_date: int | None = None
    last_updated_date: int | None = None
    granted_realm_roles: list[str] | None = None
