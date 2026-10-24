"""Keycloak client representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzSettingsDTO, KeycloakAuthzSettingsRequestDTO
from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.protocol_mapper_dtos import (
    KeycloakProtocolMapperDTO,
    KeycloakProtocolMapperRequestDTO,
)


class KeycloakClientDTO(KeycloakResponseDTO):
    """Keycloak ``ClientRepresentation`` as returned by the admin API."""

    id: str | None = None
    client_id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    root_url: str | None = None
    admin_url: str | None = None
    base_url: str | None = None
    surrogate_auth_required: bool | None = None
    enabled: bool | None = None
    always_display_in_console: bool | None = None
    client_authenticator_type: str | None = None
    secret: str | None = None
    registration_access_token: str | None = None
    default_roles: list[str] | None = None
    redirect_uris: list[str] | None = None
    web_origins: list[str] | None = None
    not_before: int | None = None
    bearer_only: bool | None = None
    consent_required: bool | None = None
    standard_flow_enabled: bool | None = None
    implicit_flow_enabled: bool | None = None
    direct_access_grants_enabled: bool | None = None
    service_accounts_enabled: bool | None = None
    authorization_services_enabled: bool | None = None
    direct_grants_only: bool | None = None
    public_client: bool | None = None
    frontchannel_logout: bool | None = None
    protocol: str | None = None
    attributes: dict[str, str] | None = None
    authentication_flow_binding_overrides: dict[str, str] | None = None
    full_scope_allowed: bool | None = None
    node_re_registration_timeout: int | None = None
    registered_nodes: dict[str, int] | None = None
    protocol_mappers: list[KeycloakProtocolMapperDTO] | None = None
    client_template: str | None = None
    use_template_config: bool | None = None
    use_template_scope: bool | None = None
    use_template_mappers: bool | None = None
    default_client_scopes: list[str] | None = None
    optional_client_scopes: list[str] | None = None
    authorization_settings: KeycloakAuthzSettingsDTO | None = None
    access: dict[str, bool] | None = None
    origin: str | None = None


class KeycloakClientRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientRepresentation`` payload sent to the admin API."""

    id: str | None = None
    client_id: str | None = None
    name: str | None = None
    description: str | None = None
    type: str | None = None
    root_url: str | None = None
    admin_url: str | None = None
    base_url: str | None = None
    surrogate_auth_required: bool | None = None
    enabled: bool | None = None
    always_display_in_console: bool | None = None
    client_authenticator_type: str | None = None
    secret: str | None = None
    registration_access_token: str | None = None
    default_roles: list[str] | None = None
    redirect_uris: list[str] | None = None
    web_origins: list[str] | None = None
    not_before: int | None = None
    bearer_only: bool | None = None
    consent_required: bool | None = None
    standard_flow_enabled: bool | None = None
    implicit_flow_enabled: bool | None = None
    direct_access_grants_enabled: bool | None = None
    service_accounts_enabled: bool | None = None
    authorization_services_enabled: bool | None = None
    direct_grants_only: bool | None = None
    public_client: bool | None = None
    frontchannel_logout: bool | None = None
    protocol: str | None = None
    attributes: dict[str, str] | None = None
    authentication_flow_binding_overrides: dict[str, str] | None = None
    full_scope_allowed: bool | None = None
    node_re_registration_timeout: int | None = None
    registered_nodes: dict[str, int] | None = None
    protocol_mappers: list[KeycloakProtocolMapperRequestDTO] | None = None
    client_template: str | None = None
    use_template_config: bool | None = None
    use_template_scope: bool | None = None
    use_template_mappers: bool | None = None
    default_client_scopes: list[str] | None = None
    optional_client_scopes: list[str] | None = None
    authorization_settings: KeycloakAuthzSettingsRequestDTO | None = None
    access: dict[str, bool] | None = None
    origin: str | None = None
