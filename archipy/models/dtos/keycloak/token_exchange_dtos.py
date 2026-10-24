"""Keycloak token exchange and JWT grant DTOs (RFC 8693 and RFC 7523)."""

from typing import Any

from pydantic import ConfigDict, Field

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO
from archipy.models.dtos.keycloak.token_dtos import KeycloakTokenDTO
from archipy.models.types.keycloak_token_types import TokenExchangeTokenType


class KeycloakTokenExchangeRequestDTO(KeycloakRequestDTO):
    """Parameters of a token exchange request to the token endpoint.

    Standard token exchange (V2) uses ``subject_token``, ``subject_token_type``, ``requested_token_type``,
    ``audience`` and ``scope``. ``actor_token`` and ``actor_token_type`` select the delegation preview. The legacy
    V1 flow also uses ``subject_issuer``, ``requested_issuer`` and ``requested_subject``.

    Attributes:
        subject_token: The token being exchanged.
        subject_token_type: Type of ``subject_token``; V2 only accepts an access token.
        requested_token_type: Type of the token to issue; defaults to an access token on the server.
        audience: One client ID or several, to filter the audience and client roles of the new token.
        scope: Extra optional client scopes to request.
        actor_token: Access token of the acting party (delegation preview).
        actor_token_type: Type of ``actor_token``.
        subject_issuer: Identity provider alias or issuer of an external subject token (legacy V1).
        requested_issuer: Identity provider alias to obtain an external token for (legacy V1).
        requested_subject: User to impersonate (legacy V1).
    """

    model_config = ConfigDict(alias_generator=None)

    subject_token: str
    subject_token_type: TokenExchangeTokenType = TokenExchangeTokenType.ACCESS_TOKEN
    requested_token_type: TokenExchangeTokenType | None = None
    audience: str | list[str] | None = None
    scope: str | None = None
    actor_token: str | None = None
    actor_token_type: TokenExchangeTokenType | None = None
    subject_issuer: str | None = None
    requested_issuer: str | None = None
    requested_subject: str | None = None

    def to_form(self) -> dict[str, Any]:
        """Return the set parameters as token endpoint form fields; a list value repeats its field."""
        return self.model_dump(exclude_none=True, mode="json")


class KeycloakTokenExchangeResponseDTO(KeycloakTokenDTO):
    """Token exchange response: the issued token and which kind of token it is.

    Attributes:
        issued_token_type: Type URN of the issued token; ``access_token`` holds it whatever the type.
        account_link_url: Where to link the account when an external token needs a linked identity (legacy V1).
    """

    issued_token_type: str | None = None
    account_link_url: str | None = Field(default=None, alias="account-link-url")
