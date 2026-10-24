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
    """Result of a create or copy call.

    Keycloak answers with an empty body, so the adapter looks the new resource up and sets ``id``. ``msg`` is
    ``"Already exists"`` and ``id`` stays ``None`` when ``skip_exists`` skipped the create.
    """

    id: str | None = None


class KeycloakUpdateResultDTO(KeycloakMutationResultDTO):
    """Result of an update, import or settings call."""


class KeycloakDeleteResultDTO(KeycloakMutationResultDTO):
    """Result of a delete or remove call."""


class KeycloakAssignResultDTO(KeycloakMutationResultDTO):
    """Result of a call that adds or assigns one resource to another, such as a role to a group."""


class KeycloakCountDTO(KeycloakResponseDTO):
    """Response of a count endpoint."""

    count: int | None = None


class KeycloakGroupsCountDTO(KeycloakCountDTO):
    """Response of the group count endpoint."""


class KeycloakImpersonationDTO(KeycloakResponseDTO):
    """Response of a user impersonation request.

    Attributes:
        same_realm: Whether the impersonated user belongs to the admin's realm.
        redirect: URL to open to continue as the impersonated user.
    """

    same_realm: bool | None = None
    redirect: str | None = None
