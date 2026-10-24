"""Keycloak session representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakUserSessionDTO(KeycloakResponseDTO):
    """Keycloak ``UserSessionRepresentation`` as returned by the admin API."""

    id: str | None = None
    username: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    start: int | None = None
    last_access: int | None = None
    remember_me: bool | None = None
    clients: dict[str, str] | None = None
    transient_user: bool | None = None


class KeycloakUserSessionRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UserSessionRepresentation`` payload sent to the admin API."""

    id: str | None = None
    username: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    start: int | None = None
    last_access: int | None = None
    remember_me: bool | None = None
    clients: dict[str, str] | None = None
    transient_user: bool | None = None
