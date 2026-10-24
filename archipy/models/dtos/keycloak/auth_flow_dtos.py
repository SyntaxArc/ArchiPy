"""Keycloak auth flow representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthenticationFlowDTO(KeycloakResponseDTO):
    """Keycloak ``AuthenticationFlowRepresentation`` as returned by the admin API."""

    id: str | None = None
    alias: str | None = None
    description: str | None = None
    provider_id: str | None = None
    top_level: bool | None = None
    built_in: bool | None = None
    authentication_executions: list[dict[str, JsonValue]] | None = None


class KeycloakAuthenticationFlowRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthenticationFlowRepresentation`` payload sent to the admin API."""

    id: str | None = None
    alias: str | None = None
    description: str | None = None
    provider_id: str | None = None
    top_level: bool | None = None
    built_in: bool | None = None
    authentication_executions: list[dict[str, JsonValue]] | None = None


class KeycloakAuthenticationExecutionDTO(KeycloakResponseDTO):
    """Keycloak ``AuthenticationExecutionRepresentation`` as returned by the admin API."""

    authenticator_config: str | None = None
    authenticator: str | None = None
    authenticator_flow: bool | None = None
    requirement: str | None = None
    priority: int | None = None
    autheticator_flow: bool | None = None
    id: str | None = None
    flow_id: str | None = None
    parent_flow: str | None = None


class KeycloakAuthenticationExecutionRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthenticationExecutionRepresentation`` payload sent to the admin API."""

    authenticator_config: str | None = None
    authenticator: str | None = None
    authenticator_flow: bool | None = None
    requirement: str | None = None
    priority: int | None = None
    autheticator_flow: bool | None = None
    id: str | None = None
    flow_id: str | None = None
    parent_flow: str | None = None


class KeycloakAuthenticationExecutionInfoDTO(KeycloakResponseDTO):
    """Keycloak ``AuthenticationExecutionInfoRepresentation`` as returned by the admin API."""

    id: str | None = None
    requirement: str | None = None
    display_name: str | None = None
    alias: str | None = None
    description: str | None = None
    requirement_choices: list[str] | None = None
    configurable: bool | None = None
    authentication_flow: bool | None = None
    provider_id: str | None = None
    authentication_config: str | None = None
    flow_id: str | None = None
    level: int | None = None
    index: int | None = None
    priority: int | None = None


class KeycloakAuthenticationExecutionInfoRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthenticationExecutionInfoRepresentation`` payload sent to the admin API."""

    id: str | None = None
    requirement: str | None = None
    display_name: str | None = None
    alias: str | None = None
    description: str | None = None
    requirement_choices: list[str] | None = None
    configurable: bool | None = None
    authentication_flow: bool | None = None
    provider_id: str | None = None
    authentication_config: str | None = None
    flow_id: str | None = None
    level: int | None = None
    index: int | None = None
    priority: int | None = None


class KeycloakAuthenticatorConfigDTO(KeycloakResponseDTO):
    """Keycloak ``AuthenticatorConfigRepresentation`` as returned by the admin API."""

    id: str | None = None
    alias: str | None = None
    config: dict[str, str] | None = None


class KeycloakAuthenticatorConfigRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthenticatorConfigRepresentation`` payload sent to the admin API."""

    id: str | None = None
    alias: str | None = None
    config: dict[str, str] | None = None


class KeycloakAuthenticatorConfigInfoDTO(KeycloakResponseDTO):
    """Keycloak ``AuthenticatorConfigInfoRepresentation`` as returned by the admin API."""

    name: str | None = None
    provider_id: str | None = None
    help_text: str | None = None
    properties: list[dict[str, JsonValue]] | None = None


class KeycloakAuthenticatorConfigInfoRequestDTO(KeycloakRequestDTO):
    """Keycloak ``AuthenticatorConfigInfoRepresentation`` payload sent to the admin API."""

    name: str | None = None
    provider_id: str | None = None
    help_text: str | None = None
    properties: list[dict[str, JsonValue]] | None = None
