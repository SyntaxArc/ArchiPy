"""Keycloak DTOs shared by several admin operations."""

from archipy.models.dtos.keycloak.base import KeycloakResponseDTO


class KeycloakMutationResultDTO(KeycloakResponseDTO):
    """Base of the results of Keycloak create, update, delete and assign calls.

    Keycloak answers these with ``204 No Content``, which is an empty result. ``msg`` is set to
    ``"Already exists"`` when a create was skipped because the resource existed (``skip_exists``). Any other
    response fields are kept in ``model_extra``.
    """

    msg: str | None = None
    error_message: str | None = None


class KeycloakCreateResultDTO(KeycloakMutationResultDTO):
    """Result of a create or copy call; ``msg`` is ``"Already exists"`` when ``skip_exists`` skipped it."""


class KeycloakUpdateResultDTO(KeycloakMutationResultDTO):
    """Result of an update, import or settings call."""


class KeycloakDeleteResultDTO(KeycloakMutationResultDTO):
    """Result of a delete or remove call."""


class KeycloakAssignResultDTO(KeycloakMutationResultDTO):
    """Result of a call that adds or assigns one resource to another, such as a role to a group."""


class KeycloakGroupsCountDTO(KeycloakResponseDTO):
    """Response of the group count endpoint."""

    count: int | None = None
