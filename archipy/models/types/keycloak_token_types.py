"""Token type identifiers used by OAuth 2.0 token exchange (RFC 8693)."""

from enum import StrEnum


class TokenExchangeTokenType(StrEnum):
    """Token type URNs accepted in ``subject_token_type``, ``actor_token_type`` and ``requested_token_type``."""

    ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"  # noqa: S105 # nosec B105
    REFRESH_TOKEN = "urn:ietf:params:oauth:token-type:refresh_token"  # noqa: S105 # nosec B105
    ID_TOKEN = "urn:ietf:params:oauth:token-type:id_token"  # noqa: S105 # nosec B105
    JWT = "urn:ietf:params:oauth:token-type:jwt"
    SAML2 = "urn:ietf:params:oauth:token-type:saml2"
