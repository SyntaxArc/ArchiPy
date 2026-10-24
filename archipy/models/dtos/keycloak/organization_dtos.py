"""Keycloak organization representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import Field, JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO, KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import (
    KeycloakIdentityProviderDTO,
    KeycloakIdentityProviderRequestDTO,
)
from archipy.models.dtos.keycloak.user_dtos import (
    KeycloakCredentialDTO,
    KeycloakCredentialRequestDTO,
    KeycloakFederatedIdentityDTO,
    KeycloakFederatedIdentityRequestDTO,
)


class KeycloakOrganizationDomainDTO(KeycloakResponseDTO):
    """Keycloak ``OrganizationDomainRepresentation`` as returned by the admin API."""

    name: str | None = None
    verified: bool | None = None
    identity_provider_alias: str | None = None
    auto_redirect: bool | None = None


class KeycloakOrganizationDomainRequestDTO(KeycloakRequestDTO):
    """Keycloak ``OrganizationDomainRepresentation`` payload sent to the admin API."""

    name: str | None = None
    verified: bool | None = None
    identity_provider_alias: str | None = None
    auto_redirect: bool | None = None


class KeycloakOrganizationMemberDTO(KeycloakResponseDTO):
    """Keycloak ``MemberRepresentation`` as returned by the admin API."""

    id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    attributes: dict[str, list[str]] | None = None
    user_profile_metadata: dict[str, JsonValue] | None = None
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
    client_consents: list[dict[str, JsonValue]] | None = None
    not_before: int | None = None
    verifiable_credentials: list[dict[str, JsonValue]] | None = None
    issued_verifiable_credentials: list[dict[str, JsonValue]] | None = None
    application_roles: dict[str, list[str]] | None = None
    social_links: list[dict[str, JsonValue]] | None = None
    groups: list[str] | None = None
    access: dict[str, bool] | None = None
    membership_type: str | None = None


class KeycloakOrganizationMemberRequestDTO(KeycloakRequestDTO):
    """Keycloak ``MemberRepresentation`` payload sent to the admin API."""

    id: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    attributes: dict[str, list[str]] | None = None
    user_profile_metadata: dict[str, JsonValue] | None = None
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
    client_consents: list[dict[str, JsonValue]] | None = None
    not_before: int | None = None
    verifiable_credentials: list[dict[str, JsonValue]] | None = None
    issued_verifiable_credentials: list[dict[str, JsonValue]] | None = None
    application_roles: dict[str, list[str]] | None = None
    social_links: list[dict[str, JsonValue]] | None = None
    groups: list[str] | None = None
    access: dict[str, bool] | None = None
    membership_type: str | None = None


class KeycloakOrganizationDTO(KeycloakResponseDTO):
    """Keycloak ``OrganizationRepresentation`` as returned by the admin API."""

    id: str | None = None
    name: str | None = None
    alias: str | None = None
    enabled: bool | None = None
    description: str | None = None
    redirect_url: str | None = None
    attributes: dict[str, list[str]] | None = None
    domains: list[KeycloakOrganizationDomainDTO] | None = None
    members: list[KeycloakOrganizationMemberDTO] | None = None
    identity_providers: list[KeycloakIdentityProviderDTO] | None = None
    groups: list[KeycloakGroupDTO] | None = None


class KeycloakOrganizationRequestDTO(KeycloakRequestDTO):
    """Keycloak ``OrganizationRepresentation`` payload sent to the admin API."""

    id: str | None = None
    name: str | None = None
    alias: str | None = None
    enabled: bool | None = None
    description: str | None = None
    redirect_url: str | None = None
    attributes: dict[str, list[str]] | None = None
    domains: list[KeycloakOrganizationDomainRequestDTO] | None = None
    members: list[KeycloakOrganizationMemberRequestDTO] | None = None
    identity_providers: list[KeycloakIdentityProviderRequestDTO] | None = None
    groups: list[KeycloakGroupRequestDTO] | None = None


class KeycloakOrganizationInvitationDTO(KeycloakResponseDTO):
    """Keycloak ``OrganizationInvitationRepresentation`` as returned by the admin API."""

    id: str | None = None
    organization_id: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    sent_date: int | None = None
    expires_at: int | None = None
    status: str | None = None
    invite_link: str | None = None


class KeycloakOrganizationInvitationRequestDTO(KeycloakRequestDTO):
    """Keycloak ``OrganizationInvitationRepresentation`` payload sent to the admin API."""

    id: str | None = None
    organization_id: str | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    sent_date: int | None = None
    expires_at: int | None = None
    status: str | None = None
    invite_link: str | None = None
