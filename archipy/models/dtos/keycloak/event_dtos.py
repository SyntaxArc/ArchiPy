"""Keycloak event representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthDetailsDTO(KeycloakResponseDTO):
    """Keycloak ``AuthDetailsRepresentation`` as returned by the admin API."""

    realm_id: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    ip_address: str | None = None


class KeycloakAuthDetailsRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthDetailsRepresentation`` payload sent to the admin API."""

    realm_id: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    ip_address: str | None = None


class KeycloakEventDTO(KeycloakResponseDTO):
    """Keycloak ``EventRepresentation`` as returned by the admin API."""

    id: str | None = None
    time: int | None = None
    type: str | None = None
    realm_id: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    error: str | None = None
    details: dict[str, str] | None = None


class KeycloakEventRequestDTO(KeycloakRequestDTO):
    """Keycloak ``EventRepresentation`` payload sent to the admin API."""

    id: str | None = None
    time: int | None = None
    type: str | None = None
    realm_id: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    ip_address: str | None = None
    error: str | None = None
    details: dict[str, str] | None = None


class KeycloakAdminEventDTO(KeycloakResponseDTO):
    """Keycloak ``AdminEventRepresentation`` as returned by the admin API."""

    id: str | None = None
    time: int | None = None
    realm_id: str | None = None
    auth_details: KeycloakAuthDetailsDTO | None = None
    operation_type: str | None = None
    resource_type: str | None = None
    resource_path: str | None = None
    representation: str | None = None
    error: str | None = None
    details: dict[str, str] | None = None


class KeycloakAdminEventRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AdminEventRepresentation`` payload sent to the admin API."""

    id: str | None = None
    time: int | None = None
    realm_id: str | None = None
    auth_details: KeycloakAuthDetailsRequestDTO | None = None
    operation_type: str | None = None
    resource_type: str | None = None
    resource_path: str | None = None
    representation: str | None = None
    error: str | None = None
    details: dict[str, str] | None = None


class KeycloakRealmEventsConfigDTO(KeycloakResponseDTO):
    """Keycloak ``RealmEventsConfigRepresentation`` as returned by the admin API."""

    events_enabled: bool | None = None
    events_expiration: int | None = None
    events_listeners: list[str] | None = None
    enabled_event_types: list[str] | None = None
    admin_events_enabled: bool | None = None
    admin_events_details_enabled: bool | None = None


class KeycloakRealmEventsConfigRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RealmEventsConfigRepresentation`` payload sent to the admin API."""

    events_enabled: bool | None = None
    events_expiration: int | None = None
    events_listeners: list[str] | None = None
    enabled_event_types: list[str] | None = None
    admin_events_enabled: bool | None = None
    admin_events_details_enabled: bool | None = None
