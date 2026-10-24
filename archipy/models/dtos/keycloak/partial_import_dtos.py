"""Keycloak partial import DTOs (hand-written: the admin OpenAPI spec types the body as an opaque string)."""

from typing import Literal

from pydantic import JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.client_dtos import KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import KeycloakIdentityProviderRequestDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserRequestDTO


class KeycloakPartialImportRequestDTO(KeycloakRequestDTO):
    """Payload of ``POST partialImport``.

    Attributes:
        if_resource_exists: What to do with resources that already exist: ``FAIL``, ``SKIP`` or ``OVERWRITE``.
        users: Users to import.
        clients: Clients to import.
        groups: Groups to import.
        identity_providers: Identity providers to import.
        roles: Realm and client roles to import, as ``{"realm": [...], "client": {...}}``.
    """

    if_resource_exists: Literal["FAIL", "SKIP", "OVERWRITE"] | None = None
    users: list[KeycloakUserRequestDTO] | None = None
    clients: list[KeycloakClientRequestDTO] | None = None
    groups: list[KeycloakGroupRequestDTO] | None = None
    identity_providers: list[KeycloakIdentityProviderRequestDTO] | None = None
    roles: dict[str, JsonValue] | None = None


class KeycloakPartialImportResultDTO(KeycloakResponseDTO):
    """Outcome of a partial import: counts and one entry per imported resource."""

    added: int | None = None
    overwritten: int | None = None
    skipped: int | None = None
    results: list[dict[str, JsonValue]] | None = None
