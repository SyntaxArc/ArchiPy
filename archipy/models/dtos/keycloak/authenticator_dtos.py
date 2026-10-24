"""Hand-written Keycloak authentication DTOs for payloads the admin OpenAPI spec leaves untyped."""

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthenticatorProviderDTO(KeycloakResponseDTO):
    """One authenticator provider as listed by ``GET authentication/authenticator-providers``."""

    id: str | None = None
    display_name: str | None = None
    description: str | None = None


class KeycloakAuthenticationFlowCopyRequestDTO(KeycloakRequestDTO):
    """Payload of ``POST authentication/flows/{alias}/copy``."""

    new_name: str


class KeycloakAuthenticationFlowExecutionCreateRequestDTO(KeycloakRequestDTO):
    """Payload of ``POST authentication/flows/{alias}/executions/execution``."""

    provider: str


class KeycloakAuthenticationSubflowCreateRequestDTO(KeycloakRequestDTO):
    """Payload of ``POST authentication/flows/{alias}/executions/flow``."""

    alias: str
    type: str | None = None
    provider: str | None = None
    description: str | None = None


class KeycloakUnregisteredRequiredActionDTO(KeycloakResponseDTO):
    """A required action provider that exists on the server but is not registered in the realm."""

    name: str | None = None
    provider_id: str | None = None
