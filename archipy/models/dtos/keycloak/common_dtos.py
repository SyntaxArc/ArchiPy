"""Keycloak DTOs shared by several admin operations."""

from archipy.models.dtos.keycloak.base import KeycloakResponseDTO


class KeycloakMutationResultDTO(KeycloakResponseDTO):
    """Body of a Keycloak create, update, delete or assign call.

    Keycloak answers these with ``204 No Content``, which is an empty result. ``msg`` is set to
    ``"Already exists"`` when a create was skipped because the resource existed (``skip_exists``). Any other
    response fields are kept in ``model_extra``.
    """

    msg: str | None = None
    error_message: str | None = None


class KeycloakGroupsCountDTO(KeycloakResponseDTO):
    """Response of the group count endpoint."""

    count: int | None = None
