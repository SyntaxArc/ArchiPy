"""Keycloak OpenID Connect (token, userinfo, claims, discovery) response DTOs.

OIDC payloads use snake_case on the wire, unlike the admin API representations.
"""

from typing import Any

from pydantic import ConfigDict, Field

from archipy.models.dtos.keycloak.base import KeycloakResponseDTO


class KeycloakOidcResponseDTO(KeycloakResponseDTO):
    """Base for OIDC responses: snake_case wire names and a falsy value when no claim is set."""

    model_config = ConfigDict(alias_generator=None)

    def __bool__(self) -> bool:
        """Return False when the response carries no values, like the empty dict it replaced."""
        return bool(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Return the set claims as a plain dict with their wire names, including unknown ones."""
        return self.model_dump(by_alias=True, exclude_none=True, mode="json")


class KeycloakTokenDTO(KeycloakOidcResponseDTO):
    """OAuth 2.0 token endpoint response."""

    access_token: str | None = None
    refresh_token: str | None = None
    id_token: str | None = None
    token_type: str | None = None
    expires_in: int | None = None
    refresh_expires_in: int | None = None
    not_before_policy: int | None = Field(default=None, alias="not-before-policy")
    session_state: str | None = None
    scope: str | None = None


class KeycloakRoleAccessDTO(KeycloakOidcResponseDTO):
    """Roles granted in a ``realm_access`` or ``resource_access`` claim."""

    roles: list[str] | None = None


class KeycloakUserInfoDTO(KeycloakOidcResponseDTO):
    """OIDC UserInfo endpoint response.

    ``realm_access`` and ``resource_access`` are only present when the Keycloak role mappers have
    "Add to userinfo" enabled. Other custom claims are kept in ``model_extra``.
    """

    sub: str | None = None
    preferred_username: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    groups: list[str] | None = None
    realm_access: KeycloakRoleAccessDTO | None = None
    resource_access: dict[str, KeycloakRoleAccessDTO] | None = None


class KeycloakActClaimDTO(KeycloakOidcResponseDTO):
    """RFC 8693 ``act`` claim: the acting party, with earlier actors nested under ``act``."""

    sub: str | None = None
    client_id: str | None = None
    azp: str | None = None
    act: "KeycloakActClaimDTO | None" = None


class KeycloakTokenClaimsDTO(KeycloakOidcResponseDTO):
    """Claims of a decoded access token or of a token introspection response (``active`` is set only there)."""

    iss: str | None = None
    sub: str | None = None
    aud: str | list[str] | None = None
    exp: int | None = None
    iat: int | None = None
    nbf: int | None = None
    auth_time: int | None = None
    jti: str | None = None
    typ: str | None = None
    azp: str | None = None
    sid: str | None = None
    session_state: str | None = None
    acr: str | None = None
    scope: str | None = None
    active: bool | None = None
    client_id: str | None = None
    username: str | None = None
    token_type: str | None = None
    preferred_username: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    act: KeycloakActClaimDTO | None = None
    realm_access: KeycloakRoleAccessDTO | None = None
    resource_access: dict[str, KeycloakRoleAccessDTO] | None = None


class KeycloakWellKnownDTO(KeycloakOidcResponseDTO):
    """OpenID Connect discovery document (``.well-known/openid-configuration``)."""

    issuer: str | None = None
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    jwks_uri: str | None = None
    end_session_endpoint: str | None = None
    introspection_endpoint: str | None = None
    registration_endpoint: str | None = None
    revocation_endpoint: str | None = None
    device_authorization_endpoint: str | None = None
    grant_types_supported: list[str] | None = None
    response_types_supported: list[str] | None = None
    response_modes_supported: list[str] | None = None
    scopes_supported: list[str] | None = None
    claims_supported: list[str] | None = None
    subject_types_supported: list[str] | None = None
    token_endpoint_auth_methods_supported: list[str] | None = None
    id_token_signing_alg_values_supported: list[str] | None = None
    code_challenge_methods_supported: list[str] | None = None


class KeycloakJwkDTO(KeycloakOidcResponseDTO):
    """One JSON Web Key from the realm certificate endpoint."""

    kid: str | None = None
    kty: str | None = None
    alg: str | None = None
    use: str | None = None
    n: str | None = None
    e: str | None = None
    x: str | None = None
    y: str | None = None
    crv: str | None = None
    x5c: list[str] | None = None
    x5t: str | None = None
    x5t_s256: str | None = Field(default=None, alias="x5t#S256")


class KeycloakCertsDTO(KeycloakOidcResponseDTO):
    """Realm JSON Web Key Set."""

    jwks: list[KeycloakJwkDTO] | None = Field(default=None, alias="keys")
