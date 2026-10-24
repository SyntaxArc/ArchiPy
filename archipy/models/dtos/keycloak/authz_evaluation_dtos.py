"""Keycloak authz evaluation representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import JsonValue

from archipy.models.dtos.keycloak.authz_dtos import (
    KeycloakAuthzPolicyDTO,
    KeycloakAuthzPolicyRequestDTO,
    KeycloakAuthzResourceDTO,
    KeycloakAuthzResourceRequestDTO,
    KeycloakAuthzScopeDTO,
    KeycloakAuthzScopeRequestDTO,
)
from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthzPolicyEvaluationRequestDTO(KeycloakResponseDTO):
    """Keycloak ``PolicyEvaluationRequest`` as returned by the admin API."""

    context: dict[str, dict[str, str]] | None = None
    resources: list[KeycloakAuthzResourceDTO] | None = None
    resource_type: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    role_ids: list[str] | None = None
    entitlements: bool | None = None


class KeycloakAuthzPolicyEvaluationRequestRequestDTO(KeycloakRequestDTO):
    """Keycloak ``PolicyEvaluationRequest`` payload sent to the admin API."""

    context: dict[str, dict[str, str]] | None = None
    resources: list[KeycloakAuthzResourceRequestDTO] | None = None
    resource_type: str | None = None
    client_id: str | None = None
    user_id: str | None = None
    role_ids: list[str] | None = None
    entitlements: bool | None = None


class KeycloakAuthzPolicyEvaluationResponseDTO(KeycloakResponseDTO):
    """Keycloak ``PolicyEvaluationResponse`` as returned by the admin API."""

    results: list[KeycloakAuthzEvaluationResultDTO] | None = None
    entitlements: bool | None = None
    status: str | None = None
    rpt: dict[str, JsonValue] | None = None


class KeycloakAuthzPolicyEvaluationResponseRequestDTO(KeycloakRequestDTO):
    """Keycloak ``PolicyEvaluationResponse`` payload sent to the admin API."""

    results: list[KeycloakAuthzEvaluationResultRequestDTO] | None = None
    entitlements: bool | None = None
    status: str | None = None
    rpt: dict[str, JsonValue] | None = None


class KeycloakAuthzEvaluationResultDTO(KeycloakResponseDTO):
    """Keycloak ``EvaluationResultRepresentation`` as returned by the admin API."""

    resource: KeycloakAuthzResourceDTO | None = None
    scopes: list[KeycloakAuthzScopeDTO] | None = None
    policies: list[KeycloakAuthzPolicyResultDTO] | None = None
    status: str | None = None
    allowed_scopes: list[KeycloakAuthzScopeDTO] | None = None
    denied_scopes: list[KeycloakAuthzScopeDTO] | None = None


class KeycloakAuthzEvaluationResultRequestDTO(KeycloakRequestDTO):
    """Keycloak ``EvaluationResultRepresentation`` payload sent to the admin API."""

    resource: KeycloakAuthzResourceRequestDTO | None = None
    scopes: list[KeycloakAuthzScopeRequestDTO] | None = None
    policies: list[KeycloakAuthzPolicyResultRequestDTO] | None = None
    status: str | None = None
    allowed_scopes: list[KeycloakAuthzScopeRequestDTO] | None = None
    denied_scopes: list[KeycloakAuthzScopeRequestDTO] | None = None


class KeycloakAuthzPolicyResultDTO(KeycloakResponseDTO):
    """Keycloak ``PolicyResultRepresentation`` as returned by the admin API."""

    policy: KeycloakAuthzPolicyDTO | None = None
    status: str | None = None
    associated_policies: list[KeycloakAuthzPolicyResultDTO] | None = None
    scopes: list[str] | None = None
    resource_type: str | None = None


class KeycloakAuthzPolicyResultRequestDTO(KeycloakRequestDTO):
    """Keycloak ``PolicyResultRepresentation`` payload sent to the admin API."""

    policy: KeycloakAuthzPolicyRequestDTO | None = None
    status: str | None = None
    associated_policies: list[KeycloakAuthzPolicyResultRequestDTO] | None = None
    scopes: list[str] | None = None
    resource_type: str | None = None


class KeycloakAuthzPolicyProviderDTO(KeycloakResponseDTO):
    """Keycloak ``PolicyProviderRepresentation`` as returned by the admin API."""

    type: str | None = None
    name: str | None = None
    group: str | None = None
    description: str | None = None
    code: str | None = None


class KeycloakAuthzPolicyProviderRequestDTO(KeycloakRequestDTO):
    """Keycloak ``PolicyProviderRepresentation`` payload sent to the admin API."""

    type: str | None = None
    name: str | None = None
    group: str | None = None
    description: str | None = None
    code: str | None = None
