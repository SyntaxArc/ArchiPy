"""Keycloak brute force detection DTOs (hand-written: the admin OpenAPI spec types the response as a plain object)."""

from pydantic import ConfigDict, Field

from archipy.models.dtos.keycloak.base import KeycloakResponseDTO


class KeycloakBruteForceStatusDTO(KeycloakResponseDTO):
    """Brute force detection status of one user.

    Attributes:
        num_failures: Failed logins counted so far.
        disabled: Whether the user is temporarily locked.
        last_ip_failure: IP address of the last failed login.
        last_failure: Time of the last failed login, in milliseconds since the epoch.
    """

    model_config = ConfigDict(alias_generator=None)

    num_failures: int | None = Field(default=None, alias="numFailures")
    disabled: bool | None = None
    last_ip_failure: str | None = Field(default=None, alias="lastIPFailure")
    last_failure: int | None = Field(default=None, alias="lastFailure")
