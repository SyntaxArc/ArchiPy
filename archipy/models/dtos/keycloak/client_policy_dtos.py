"""Keycloak client policy representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import Field, JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakClientPolicyDTO(KeycloakResponseDTO):
    """Keycloak ``ClientPolicyRepresentation`` as returned by the admin API."""

    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    mode: str | None = None
    conditions: list[dict[str, JsonValue]] | None = None
    profiles: list[str] | None = None


class KeycloakClientPolicyRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientPolicyRepresentation`` payload sent to the admin API."""

    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    mode: str | None = None
    conditions: list[dict[str, JsonValue]] | None = None
    profiles: list[str] | None = None


class KeycloakClientProfileDTO(KeycloakResponseDTO):
    """Keycloak ``ClientProfileRepresentation`` as returned by the admin API."""

    name: str | None = None
    description: str | None = None
    executors: list[dict[str, JsonValue]] | None = None


class KeycloakClientProfileRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientProfileRepresentation`` payload sent to the admin API."""

    name: str | None = None
    description: str | None = None
    executors: list[dict[str, JsonValue]] | None = None


class KeycloakClientTypeDTO(KeycloakResponseDTO):
    """Keycloak ``ClientTypeRepresentation`` as returned by the admin API."""

    name: str | None = None
    provider: str | None = None
    parent: str | None = None
    config: dict[str, dict[str, JsonValue]] | None = None


class KeycloakClientTypeRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientTypeRepresentation`` payload sent to the admin API."""

    name: str | None = None
    provider: str | None = None
    parent: str | None = None
    config: dict[str, dict[str, JsonValue]] | None = None


class KeycloakClientPoliciesDTO(KeycloakResponseDTO):
    """Keycloak ``ClientPoliciesRepresentation`` as returned by the admin API."""

    policies: list[KeycloakClientPolicyDTO] | None = None
    global_policies: list[KeycloakClientPolicyDTO] | None = None


class KeycloakClientPoliciesRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientPoliciesRepresentation`` payload sent to the admin API."""

    policies: list[KeycloakClientPolicyRequestDTO] | None = None
    global_policies: list[KeycloakClientPolicyRequestDTO] | None = None


class KeycloakClientProfilesDTO(KeycloakResponseDTO):
    """Keycloak ``ClientProfilesRepresentation`` as returned by the admin API."""

    profiles: list[KeycloakClientProfileDTO] | None = None
    global_profiles: list[KeycloakClientProfileDTO] | None = None


class KeycloakClientProfilesRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientProfilesRepresentation`` payload sent to the admin API."""

    profiles: list[KeycloakClientProfileRequestDTO] | None = None
    global_profiles: list[KeycloakClientProfileRequestDTO] | None = None


class KeycloakClientTypesDTO(KeycloakResponseDTO):
    """Keycloak ``ClientTypesRepresentation`` as returned by the admin API."""

    client_types: list[KeycloakClientTypeDTO] | None = Field(default=None, alias="client-types")
    global_client_types: list[KeycloakClientTypeDTO] | None = Field(default=None, alias="global-client-types")


class KeycloakClientTypesRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ClientTypesRepresentation`` payload sent to the admin API."""

    client_types: list[KeycloakClientTypeRequestDTO] | None = Field(default=None, alias="client-types")
    global_client_types: list[KeycloakClientTypeRequestDTO] | None = Field(default=None, alias="global-client-types")
