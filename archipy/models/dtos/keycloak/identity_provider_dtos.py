"""Keycloak identity provider representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakIdentityProviderDTO(KeycloakResponseDTO):
    """Keycloak ``IdentityProviderRepresentation`` as returned by the admin API."""

    alias: str | None = None
    display_name: str | None = None
    internal_id: str | None = None
    provider_id: str | None = None
    enabled: bool | None = None
    update_profile_first_login_mode: str | None = None
    trust_email: bool | None = None
    store_token: bool | None = None
    add_read_token_role_on_create: bool | None = None
    authenticate_by_default: bool | None = None
    link_only: bool | None = None
    hide_on_login: bool | None = None
    first_broker_login_flow_alias: str | None = None
    post_broker_login_flow_alias: str | None = None
    organization_links: list[KeycloakOrganizationIdentityProviderLinkDTO] | None = None
    config: dict[str, str] | None = None
    types: list[str] | None = None
    update_profile_first_login: bool | None = None
    organization_id: str | None = None


class KeycloakIdentityProviderRequestDTO(KeycloakRequestDTO):
    """Keycloak ``IdentityProviderRepresentation`` payload sent to the admin API."""

    alias: str | None = None
    display_name: str | None = None
    internal_id: str | None = None
    provider_id: str | None = None
    enabled: bool | None = None
    update_profile_first_login_mode: str | None = None
    trust_email: bool | None = None
    store_token: bool | None = None
    add_read_token_role_on_create: bool | None = None
    authenticate_by_default: bool | None = None
    link_only: bool | None = None
    hide_on_login: bool | None = None
    first_broker_login_flow_alias: str | None = None
    post_broker_login_flow_alias: str | None = None
    organization_links: list[KeycloakOrganizationIdentityProviderLinkRequestDTO] | None = None
    config: dict[str, str] | None = None
    types: list[str] | None = None
    update_profile_first_login: bool | None = None
    organization_id: str | None = None


class KeycloakOrganizationIdentityProviderLinkDTO(KeycloakResponseDTO):
    """Keycloak ``OrganizationIdentityProviderLinkRepresentation`` as returned by the admin API."""

    organization_id: str | None = None
    auto_membership: bool | None = None
    membership_type: str | None = None


class KeycloakOrganizationIdentityProviderLinkRequestDTO(KeycloakRequestDTO):
    """Keycloak ``OrganizationIdentityProviderLinkRepresentation`` payload sent to the admin API."""

    organization_id: str | None = None
    auto_membership: bool | None = None
    membership_type: str | None = None
