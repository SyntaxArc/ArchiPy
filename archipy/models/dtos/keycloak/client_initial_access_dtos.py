"""Keycloak client initial access representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakClientInitialAccessDTO(KeycloakResponseDTO):
    """Keycloak ``ClientInitialAccessPresentation`` as returned by the admin API."""

    id: str | None = None
    token: str | None = None
    timestamp: int | None = None
    expiration: int | None = None
    count: int | None = None
    remaining_count: int | None = None


class KeycloakClientInitialAccessRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientInitialAccessPresentation`` payload sent to the admin API."""

    id: str | None = None
    token: str | None = None
    timestamp: int | None = None
    expiration: int | None = None
    count: int | None = None
    remaining_count: int | None = None


class KeycloakClientInitialAccessCreateDTO(KeycloakResponseDTO):
    """Keycloak ``ClientInitialAccessCreatePresentation`` as returned by the admin API."""

    expiration: int | None = None
    count: int | None = None
    web_origins: list[str] | None = None


class KeycloakClientInitialAccessCreateRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientInitialAccessCreatePresentation`` payload sent to the admin API."""

    expiration: int | None = None
    count: int | None = None
    web_origins: list[str] | None = None
