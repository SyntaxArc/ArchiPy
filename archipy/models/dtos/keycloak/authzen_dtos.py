"""Keycloak AuthZEN (OpenID Authorization API) DTOs, an experimental feature behind the server's ``authzen`` flag."""

from typing import Literal

from pydantic import JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakAuthzenSubjectDTO(KeycloakRequestDTO):
    """Who asks for access.

    Attributes:
        type: ``user`` or ``client``.
        id: User ID, username (or an ``id:``, ``username:`` or ``email:`` prefixed value), or the client ID.
        properties: Extra attributes that policies can evaluate.
    """

    type: Literal["user", "client"]
    id: str
    properties: dict[str, JsonValue] | None = None


class KeycloakAuthzenResourceDTO(KeycloakRequestDTO):
    """What access is asked for: a resource name (``id``) and its type.

    The documentation lists ``type`` as optional, but Keycloak 26.8 rejects a request without it
    (``Cannot parse the JSON``), so the DTO requires it.

    Attributes:
        type: Resource type.
        id: Resource name.
        properties: Extra attributes that policies can evaluate.
    """

    type: str
    id: str
    properties: dict[str, JsonValue] | None = None


class KeycloakAuthzenActionDTO(KeycloakRequestDTO):
    """The action asked for; it maps to a scope name."""

    name: str


class KeycloakAuthzenEvaluationRequestDTO(KeycloakRequestDTO):
    """One access evaluation request.

    Attributes:
        subject: Who asks.
        resource: What for.
        action: Which action.
        context: Extra attributes that policies can evaluate.
    """

    subject: KeycloakAuthzenSubjectDTO
    resource: KeycloakAuthzenResourceDTO
    action: KeycloakAuthzenActionDTO
    context: dict[str, JsonValue] | None = None


class KeycloakAuthzenEvaluationDTO(KeycloakResponseDTO):
    """One access decision.

    Attributes:
        decision: Whether access is granted.
        context: Extra information about the decision.
    """

    decision: bool | None = None
    context: dict[str, JsonValue] | None = None


class KeycloakAuthzenEvaluationItemDTO(KeycloakRequestDTO):
    """One entry of a batch evaluation; fields left out fall back to the batch defaults."""

    subject: KeycloakAuthzenSubjectDTO | None = None
    resource: KeycloakAuthzenResourceDTO | None = None
    action: KeycloakAuthzenActionDTO | None = None
    context: dict[str, JsonValue] | None = None


class KeycloakAuthzenEvaluationOptionsDTO(KeycloakRequestDTO):
    """Options of a batch evaluation.

    Attributes:
        evaluations_semantic: ``execute_all`` (default), ``deny_on_first_deny`` or ``permit_on_first_permit``.
    """

    evaluations_semantic: Literal["execute_all", "deny_on_first_deny", "permit_on_first_permit"] | None = None


class KeycloakAuthzenEvaluationsRequestDTO(KeycloakRequestDTO):
    """A batch of access evaluations. Top-level ``subject``, ``resource``, ``action`` and ``context`` are defaults."""

    subject: KeycloakAuthzenSubjectDTO | None = None
    resource: KeycloakAuthzenResourceDTO | None = None
    action: KeycloakAuthzenActionDTO | None = None
    context: dict[str, JsonValue] | None = None
    evaluations: list[KeycloakAuthzenEvaluationItemDTO]
    options: KeycloakAuthzenEvaluationOptionsDTO | None = None


class KeycloakAuthzenEvaluationsDTO(KeycloakResponseDTO):
    """Decisions of a batch evaluation, in request order."""

    evaluations: list[KeycloakAuthzenEvaluationDTO] | None = None


class KeycloakAuthzenConfigurationDTO(KeycloakResponseDTO):
    """AuthZEN discovery document of a realm."""

    policy_decision_point: str | None = None
    access_evaluation_endpoint: str | None = None
    access_evaluations_endpoint: str | None = None
