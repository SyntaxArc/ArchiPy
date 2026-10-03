"""Keycloak-related data transfer objects."""

from typing import Any

from pydantic import Field, SecretStr

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types.actor_type import ActorType


class ActorDTO(BaseDTO):
    """One actor from an RFC 8693 ``act`` claim (impersonator or delegated client)."""

    id: str
    type: ActorType


class AuthenticatedUserDTO(BaseDTO):
    """Authenticated caller (subject, roles, token, and acting parties) passed to business logic."""

    user_id: str
    username: str
    email: str
    roles: list[str]
    token: SecretStr
    raw_user_info: dict[str, Any]
    actor_chain: list[ActorDTO] = Field(default_factory=list)

    @property
    def is_impersonated(self) -> bool:
        """True when the token was issued on behalf of the user by another actor."""
        return bool(self.actor_chain)

    @property
    def current_actor(self) -> ActorDTO | None:
        """The current acting party (outermost ``act``: admin or delegated client), if any.

        Earlier actors in a delegation chain are available via :attr:`actor_chain`.
        """
        return self.actor_chain[0] if self.actor_chain else None

    def propagation_headers(self) -> dict[str, str]:
        """Headers for calling downstream services on behalf of the same subject.

        The bearer token itself carries the ``act`` claim, so downstream services
        that validate it see the same impersonation data. No separate impersonation
        header is emitted because it could be spoofed.
        """
        return {"Authorization": f"Bearer {self.token.get_secret_value()}"}
