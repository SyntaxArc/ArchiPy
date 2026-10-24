"""Keycloak required action representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.component_dtos import KeycloakConfigPropertyDTO, KeycloakConfigPropertyRequestDTO


class KeycloakRequiredActionProviderDTO(KeycloakResponseDTO):
    """Keycloak ``RequiredActionProviderRepresentation`` as returned by the admin API."""

    alias: str | None = None
    name: str | None = None
    provider_id: str | None = None
    enabled: bool | None = None
    default_action: bool | None = None
    priority: int | None = None
    config: dict[str, str] | None = None


class KeycloakRequiredActionProviderRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RequiredActionProviderRepresentation`` payload sent to the admin API."""

    alias: str | None = None
    name: str | None = None
    provider_id: str | None = None
    enabled: bool | None = None
    default_action: bool | None = None
    priority: int | None = None
    config: dict[str, str] | None = None


class KeycloakRequiredActionConfigDTO(KeycloakResponseDTO):
    """Keycloak ``RequiredActionConfigRepresentation`` as returned by the admin API."""

    config: dict[str, str] | None = None


class KeycloakRequiredActionConfigRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RequiredActionConfigRepresentation`` payload sent to the admin API."""

    config: dict[str, str] | None = None


class KeycloakRequiredActionConfigInfoDTO(KeycloakResponseDTO):
    """Keycloak ``RequiredActionConfigInfoRepresentation`` as returned by the admin API."""

    properties: list[KeycloakConfigPropertyDTO] | None = None


class KeycloakRequiredActionConfigInfoRequestDTO(KeycloakRequestDTO):
    """Keycloak ``RequiredActionConfigInfoRepresentation`` payload sent to the admin API."""

    properties: list[KeycloakConfigPropertyRequestDTO] | None = None
