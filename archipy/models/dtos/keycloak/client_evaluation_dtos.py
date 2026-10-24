"""Keycloak client evaluation representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakSamlExampleResponseDTO(KeycloakResponseDTO):
    """Keycloak ``SamlExampleResponse`` as returned by the admin API."""

    saml_response: str | None = None


class KeycloakSamlExampleResponseRequestDTO(KeycloakRequestDTO):
    """Keycloak ``SamlExampleResponse`` payload sent to the admin API."""

    saml_response: str | None = None


class KeycloakProtocolMapperEvaluationDTO(KeycloakResponseDTO):
    """Keycloak ``ProtocolMapperEvaluationRepresentation`` as returned by the admin API."""

    mapper_id: str | None = None
    mapper_name: str | None = None
    container_id: str | None = None
    container_name: str | None = None
    container_type: str | None = None
    protocol_mapper: str | None = None


class KeycloakProtocolMapperEvaluationRequestDTO(KeycloakRequestDTO):
    """Keycloak ``ProtocolMapperEvaluationRepresentation`` payload sent to the admin API."""

    mapper_id: str | None = None
    mapper_name: str | None = None
    container_id: str | None = None
    container_name: str | None = None
    container_type: str | None = None
    protocol_mapper: str | None = None


class KeycloakGlobalRequestResultDTO(KeycloakResponseDTO):
    """Keycloak ``GlobalRequestResult`` as returned by the admin API."""

    success_requests: list[str] | None = None
    failed_requests: list[str] | None = None


class KeycloakGlobalRequestResultRequestDTO(KeycloakRequestDTO):
    """Keycloak ``GlobalRequestResult`` payload sent to the admin API."""

    success_requests: list[str] | None = None
    failed_requests: list[str] | None = None
