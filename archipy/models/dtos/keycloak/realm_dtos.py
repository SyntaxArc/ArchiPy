"""Keycloak realm representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import JsonValue

from archipy.models.dtos.keycloak.auth_flow_dtos import (
    KeycloakAuthenticationFlowDTO,
    KeycloakAuthenticationFlowRequestDTO,
    KeycloakAuthenticatorConfigDTO,
    KeycloakAuthenticatorConfigRequestDTO,
)
from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.client_dtos import KeycloakClientDTO, KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.client_policy_dtos import (
    KeycloakClientPoliciesDTO,
    KeycloakClientPoliciesRequestDTO,
    KeycloakClientProfilesDTO,
    KeycloakClientProfilesRequestDTO,
)
from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeDTO, KeycloakClientScopeRequestDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO, KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import (
    KeycloakIdentityProviderDTO,
    KeycloakIdentityProviderMapperDTO,
    KeycloakIdentityProviderMapperRequestDTO,
    KeycloakIdentityProviderRequestDTO,
)
from archipy.models.dtos.keycloak.organization_dtos import KeycloakOrganizationDTO, KeycloakOrganizationRequestDTO
from archipy.models.dtos.keycloak.protocol_mapper_dtos import (
    KeycloakProtocolMapperDTO,
    KeycloakProtocolMapperRequestDTO,
)
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO, KeycloakRoleRequestDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserDTO, KeycloakUserRequestDTO


class KeycloakRealmDTO(KeycloakResponseDTO):
    """Keycloak ``RealmRepresentation`` as returned by the admin API."""

    id: str | None = None
    realm: str | None = None
    display_name: str | None = None
    display_name_html: str | None = None
    not_before: int | None = None
    default_signature_algorithm: str | None = None
    revoke_refresh_token: bool | None = None
    refresh_token_max_reuse: int | None = None
    access_token_lifespan: int | None = None
    access_token_lifespan_for_implicit_flow: int | None = None
    sso_session_idle_timeout: int | None = None
    sso_session_max_lifespan: int | None = None
    sso_session_idle_timeout_remember_me: int | None = None
    sso_session_max_lifespan_remember_me: int | None = None
    offline_session_idle_timeout: int | None = None
    offline_session_max_lifespan_enabled: bool | None = None
    offline_session_max_lifespan: int | None = None
    client_session_idle_timeout: int | None = None
    client_session_max_lifespan: int | None = None
    client_offline_session_idle_timeout: int | None = None
    client_offline_session_max_lifespan: int | None = None
    access_code_lifespan: int | None = None
    access_code_lifespan_user_action: int | None = None
    access_code_lifespan_login: int | None = None
    action_token_generated_by_admin_lifespan: int | None = None
    action_token_generated_by_user_lifespan: int | None = None
    oauth2_device_code_lifespan: int | None = None
    oauth2_device_polling_interval: int | None = None
    enabled: bool | None = None
    ssl_required: str | None = None
    password_credential_grant_allowed: bool | None = None
    registration_allowed: bool | None = None
    registration_email_as_username: bool | None = None
    remember_me: bool | None = None
    verify_email: bool | None = None
    login_with_email_allowed: bool | None = None
    duplicate_emails_allowed: bool | None = None
    reset_password_allowed: bool | None = None
    edit_username_allowed: bool | None = None
    user_cache_enabled: bool | None = None
    realm_cache_enabled: bool | None = None
    brute_force_protected: bool | None = None
    permanent_lockout: bool | None = None
    max_temporary_lockouts: int | None = None
    brute_force_strategy: str | None = None
    max_failure_wait_seconds: int | None = None
    minimum_quick_login_wait_seconds: int | None = None
    wait_increment_seconds: int | None = None
    quick_login_check_milli_seconds: int | None = None
    max_delta_time_seconds: int | None = None
    failure_factor: int | None = None
    max_secondary_auth_failures: int | None = None
    private_key: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    code_secret: str | None = None
    roles: dict[str, JsonValue] | None = None
    groups: list[KeycloakGroupDTO] | None = None
    default_roles: list[str] | None = None
    default_role: KeycloakRoleDTO | None = None
    admin_permissions_client: KeycloakClientDTO | None = None
    default_groups: list[str] | None = None
    required_credentials: list[str] | None = None
    password_policy: str | None = None
    otp_policy_type: str | None = None
    otp_policy_algorithm: str | None = None
    otp_policy_initial_counter: int | None = None
    otp_policy_digits: int | None = None
    otp_policy_look_ahead_window: int | None = None
    otp_policy_period: int | None = None
    otp_policy_code_reusable: bool | None = None
    otp_supported_applications: list[str] | None = None
    localization_texts: dict[str, dict[str, str]] | None = None
    web_authn_policy_rp_entity_name: str | None = None
    web_authn_policy_signature_algorithms: list[str] | None = None
    web_authn_policy_rp_id: str | None = None
    web_authn_policy_attestation_conveyance_preference: str | None = None
    web_authn_policy_authenticator_attachment: str | None = None
    web_authn_policy_require_resident_key: str | None = None
    web_authn_policy_resident_key: str | None = None
    web_authn_policy_user_verification_requirement: str | None = None
    web_authn_policy_create_timeout: int | None = None
    web_authn_policy_avoid_same_authenticator_register: bool | None = None
    web_authn_policy_acceptable_aaguids: list[str] | None = None
    web_authn_policy_extra_origins: list[str] | None = None
    web_authn_policy_passwordless_rp_entity_name: str | None = None
    web_authn_policy_passwordless_signature_algorithms: list[str] | None = None
    web_authn_policy_passwordless_rp_id: str | None = None
    web_authn_policy_passwordless_attestation_conveyance_preference: str | None = None
    web_authn_policy_passwordless_authenticator_attachment: str | None = None
    web_authn_policy_passwordless_require_resident_key: str | None = None
    web_authn_policy_passwordless_resident_key: str | None = None
    web_authn_policy_passwordless_user_verification_requirement: str | None = None
    web_authn_policy_passwordless_create_timeout: int | None = None
    web_authn_policy_passwordless_avoid_same_authenticator_register: bool | None = None
    web_authn_policy_passwordless_acceptable_aaguids: list[str] | None = None
    web_authn_policy_passwordless_extra_origins: list[str] | None = None
    web_authn_policy_passwordless_passkeys_enabled: bool | None = None
    web_authn_policy_passwordless_mediation: str | None = None
    client_profiles: KeycloakClientProfilesDTO | None = None
    client_policies: KeycloakClientPoliciesDTO | None = None
    users: list[KeycloakUserDTO] | None = None
    federated_users: list[KeycloakUserDTO] | None = None
    scope_mappings: list[dict[str, JsonValue]] | None = None
    client_scope_mappings: dict[str, list[dict[str, JsonValue]]] | None = None
    clients: list[KeycloakClientDTO] | None = None
    client_scopes: list[KeycloakClientScopeDTO] | None = None
    default_default_client_scopes: list[str] | None = None
    default_optional_client_scopes: list[str] | None = None
    browser_security_headers: dict[str, str] | None = None
    smtp_server: dict[str, str] | None = None
    user_federation_providers: list[dict[str, JsonValue]] | None = None
    user_federation_mappers: list[dict[str, JsonValue]] | None = None
    login_theme: str | None = None
    account_theme: str | None = None
    admin_theme: str | None = None
    email_theme: str | None = None
    events_enabled: bool | None = None
    events_expiration: int | None = None
    events_listeners: list[str] | None = None
    enabled_event_types: list[str] | None = None
    admin_events_enabled: bool | None = None
    admin_events_details_enabled: bool | None = None
    identity_providers: list[KeycloakIdentityProviderDTO] | None = None
    identity_provider_mappers: list[KeycloakIdentityProviderMapperDTO] | None = None
    protocol_mappers: list[KeycloakProtocolMapperDTO] | None = None
    components: dict[str, JsonValue] | None = None
    internationalization_enabled: bool | None = None
    supported_locales: list[str] | None = None
    default_locale: str | None = None
    authentication_flows: list[KeycloakAuthenticationFlowDTO] | None = None
    authenticator_config: list[KeycloakAuthenticatorConfigDTO] | None = None
    required_actions: list[dict[str, JsonValue]] | None = None
    browser_flow: str | None = None
    registration_flow: str | None = None
    direct_grant_flow: str | None = None
    reset_credentials_flow: str | None = None
    client_authentication_flow: str | None = None
    docker_authentication_flow: str | None = None
    first_broker_login_flow: str | None = None
    attributes: dict[str, str] | None = None
    keycloak_version: str | None = None
    user_managed_access_allowed: bool | None = None
    organizations_enabled: bool | None = None
    organizations: list[KeycloakOrganizationDTO] | None = None
    verifiable_credentials_enabled: bool | None = None
    admin_permissions_enabled: bool | None = None
    social: bool | None = None
    update_profile_on_initial_social_login: bool | None = None
    social_providers: dict[str, str] | None = None
    application_scope_mappings: dict[str, list[dict[str, JsonValue]]] | None = None
    applications: list[dict[str, JsonValue]] | None = None
    oauth_clients: list[dict[str, JsonValue]] | None = None
    client_templates: list[dict[str, JsonValue]] | None = None
    scim_api_enabled: bool | None = None


class KeycloakRealmRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RealmRepresentation`` payload sent to the admin API."""

    id: str | None = None
    realm: str | None = None
    display_name: str | None = None
    display_name_html: str | None = None
    not_before: int | None = None
    default_signature_algorithm: str | None = None
    revoke_refresh_token: bool | None = None
    refresh_token_max_reuse: int | None = None
    access_token_lifespan: int | None = None
    access_token_lifespan_for_implicit_flow: int | None = None
    sso_session_idle_timeout: int | None = None
    sso_session_max_lifespan: int | None = None
    sso_session_idle_timeout_remember_me: int | None = None
    sso_session_max_lifespan_remember_me: int | None = None
    offline_session_idle_timeout: int | None = None
    offline_session_max_lifespan_enabled: bool | None = None
    offline_session_max_lifespan: int | None = None
    client_session_idle_timeout: int | None = None
    client_session_max_lifespan: int | None = None
    client_offline_session_idle_timeout: int | None = None
    client_offline_session_max_lifespan: int | None = None
    access_code_lifespan: int | None = None
    access_code_lifespan_user_action: int | None = None
    access_code_lifespan_login: int | None = None
    action_token_generated_by_admin_lifespan: int | None = None
    action_token_generated_by_user_lifespan: int | None = None
    oauth2_device_code_lifespan: int | None = None
    oauth2_device_polling_interval: int | None = None
    enabled: bool | None = None
    ssl_required: str | None = None
    password_credential_grant_allowed: bool | None = None
    registration_allowed: bool | None = None
    registration_email_as_username: bool | None = None
    remember_me: bool | None = None
    verify_email: bool | None = None
    login_with_email_allowed: bool | None = None
    duplicate_emails_allowed: bool | None = None
    reset_password_allowed: bool | None = None
    edit_username_allowed: bool | None = None
    user_cache_enabled: bool | None = None
    realm_cache_enabled: bool | None = None
    brute_force_protected: bool | None = None
    permanent_lockout: bool | None = None
    max_temporary_lockouts: int | None = None
    brute_force_strategy: str | None = None
    max_failure_wait_seconds: int | None = None
    minimum_quick_login_wait_seconds: int | None = None
    wait_increment_seconds: int | None = None
    quick_login_check_milli_seconds: int | None = None
    max_delta_time_seconds: int | None = None
    failure_factor: int | None = None
    max_secondary_auth_failures: int | None = None
    private_key: str | None = None
    public_key: str | None = None
    certificate: str | None = None
    code_secret: str | None = None
    roles: dict[str, JsonValue] | None = None
    groups: list[KeycloakGroupRequestDTO] | None = None
    default_roles: list[str] | None = None
    default_role: KeycloakRoleRequestDTO | None = None
    admin_permissions_client: KeycloakClientRequestDTO | None = None
    default_groups: list[str] | None = None
    required_credentials: list[str] | None = None
    password_policy: str | None = None
    otp_policy_type: str | None = None
    otp_policy_algorithm: str | None = None
    otp_policy_initial_counter: int | None = None
    otp_policy_digits: int | None = None
    otp_policy_look_ahead_window: int | None = None
    otp_policy_period: int | None = None
    otp_policy_code_reusable: bool | None = None
    otp_supported_applications: list[str] | None = None
    localization_texts: dict[str, dict[str, str]] | None = None
    web_authn_policy_rp_entity_name: str | None = None
    web_authn_policy_signature_algorithms: list[str] | None = None
    web_authn_policy_rp_id: str | None = None
    web_authn_policy_attestation_conveyance_preference: str | None = None
    web_authn_policy_authenticator_attachment: str | None = None
    web_authn_policy_require_resident_key: str | None = None
    web_authn_policy_resident_key: str | None = None
    web_authn_policy_user_verification_requirement: str | None = None
    web_authn_policy_create_timeout: int | None = None
    web_authn_policy_avoid_same_authenticator_register: bool | None = None
    web_authn_policy_acceptable_aaguids: list[str] | None = None
    web_authn_policy_extra_origins: list[str] | None = None
    web_authn_policy_passwordless_rp_entity_name: str | None = None
    web_authn_policy_passwordless_signature_algorithms: list[str] | None = None
    web_authn_policy_passwordless_rp_id: str | None = None
    web_authn_policy_passwordless_attestation_conveyance_preference: str | None = None
    web_authn_policy_passwordless_authenticator_attachment: str | None = None
    web_authn_policy_passwordless_require_resident_key: str | None = None
    web_authn_policy_passwordless_resident_key: str | None = None
    web_authn_policy_passwordless_user_verification_requirement: str | None = None
    web_authn_policy_passwordless_create_timeout: int | None = None
    web_authn_policy_passwordless_avoid_same_authenticator_register: bool | None = None
    web_authn_policy_passwordless_acceptable_aaguids: list[str] | None = None
    web_authn_policy_passwordless_extra_origins: list[str] | None = None
    web_authn_policy_passwordless_passkeys_enabled: bool | None = None
    web_authn_policy_passwordless_mediation: str | None = None
    client_profiles: KeycloakClientProfilesRequestDTO | None = None
    client_policies: KeycloakClientPoliciesRequestDTO | None = None
    users: list[KeycloakUserRequestDTO] | None = None
    federated_users: list[KeycloakUserRequestDTO] | None = None
    scope_mappings: list[dict[str, JsonValue]] | None = None
    client_scope_mappings: dict[str, list[dict[str, JsonValue]]] | None = None
    clients: list[KeycloakClientRequestDTO] | None = None
    client_scopes: list[KeycloakClientScopeRequestDTO] | None = None
    default_default_client_scopes: list[str] | None = None
    default_optional_client_scopes: list[str] | None = None
    browser_security_headers: dict[str, str] | None = None
    smtp_server: dict[str, str] | None = None
    user_federation_providers: list[dict[str, JsonValue]] | None = None
    user_federation_mappers: list[dict[str, JsonValue]] | None = None
    login_theme: str | None = None
    account_theme: str | None = None
    admin_theme: str | None = None
    email_theme: str | None = None
    events_enabled: bool | None = None
    events_expiration: int | None = None
    events_listeners: list[str] | None = None
    enabled_event_types: list[str] | None = None
    admin_events_enabled: bool | None = None
    admin_events_details_enabled: bool | None = None
    identity_providers: list[KeycloakIdentityProviderRequestDTO] | None = None
    identity_provider_mappers: list[KeycloakIdentityProviderMapperRequestDTO] | None = None
    protocol_mappers: list[KeycloakProtocolMapperRequestDTO] | None = None
    components: dict[str, JsonValue] | None = None
    internationalization_enabled: bool | None = None
    supported_locales: list[str] | None = None
    default_locale: str | None = None
    authentication_flows: list[KeycloakAuthenticationFlowRequestDTO] | None = None
    authenticator_config: list[KeycloakAuthenticatorConfigRequestDTO] | None = None
    required_actions: list[dict[str, JsonValue]] | None = None
    browser_flow: str | None = None
    registration_flow: str | None = None
    direct_grant_flow: str | None = None
    reset_credentials_flow: str | None = None
    client_authentication_flow: str | None = None
    docker_authentication_flow: str | None = None
    first_broker_login_flow: str | None = None
    attributes: dict[str, str] | None = None
    keycloak_version: str | None = None
    user_managed_access_allowed: bool | None = None
    organizations_enabled: bool | None = None
    organizations: list[KeycloakOrganizationRequestDTO] | None = None
    verifiable_credentials_enabled: bool | None = None
    admin_permissions_enabled: bool | None = None
    social: bool | None = None
    update_profile_on_initial_social_login: bool | None = None
    social_providers: dict[str, str] | None = None
    application_scope_mappings: dict[str, list[dict[str, JsonValue]]] | None = None
    applications: list[dict[str, JsonValue]] | None = None
    oauth_clients: list[dict[str, JsonValue]] | None = None
    client_templates: list[dict[str, JsonValue]] | None = None
    scim_api_enabled: bool | None = None
