"""Typed ``config`` DTOs for Keycloak protocol mappers.

Source: https://www.keycloak.org/admin-api/protocol-mappers. Each DTO models the ``config`` map of one protocol
mapper type. The wire map is ``dict[str, str]``: booleans travel as ``"true"``/``"false"``. Every property in the
documentation is a single value (``List``, ``ClientList``, ``Role`` and ``UserProfileAttributeList`` select a single
entry), so no list fields exist and no multi-value separator is used. Unset (``None``) properties are omitted.
"""

from typing import Any, ClassVar, Self

from pydantic import ConfigDict, Field

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO
from archipy.models.dtos.keycloak.protocol_mapper_dtos import KeycloakProtocolMapperRequestDTO


class KeycloakProtocolMapperConfigDTO(KeycloakRequestDTO):
    """Base for the typed ``config`` of one protocol mapper type.

    Subclasses set ``protocol`` and ``protocol_mapper`` and declare one field per documented config property,
    aliased to the dotted Keycloak property name.

    Attributes:
        protocol: Keycloak protocol of the mapper (``openid-connect``, ``saml``, ``oid4vc`` or ``docker-v2``).
        protocol_mapper: Keycloak mapper id, for example ``oidc-audience-mapper``.
    """

    model_config = ConfigDict(alias_generator=None, validate_by_name=True, validate_by_alias=True, extra="forbid")

    protocol: ClassVar[str]
    protocol_mapper: ClassVar[str]

    def to_config(self) -> dict[str, str]:
        """Serialize to the ``dict[str, str]`` config map Keycloak expects.

        Booleans become ``"true"``/``"false"`` and unset properties are omitted.

        Returns:
            dict[str, str]: The wire config map keyed by the dotted Keycloak property names.
        """
        values = self.model_dump(by_alias=True, exclude_none=True)
        return {key: str(value).lower() if isinstance(value, bool) else str(value) for key, value in values.items()}

    def to_mapper(self, name: str) -> KeycloakProtocolMapperRequestDTO:
        """Build the protocol mapper request carrying this config.

        Args:
            name: Name of the mapper.

        Returns:
            KeycloakProtocolMapperRequestDTO: Request with name, protocol, protocol mapper and config set.
        """
        return KeycloakProtocolMapperRequestDTO(
            name=name,
            protocol=self.protocol,
            protocol_mapper=self.protocol_mapper,
            config=self.to_config(),
        )

    @classmethod
    def from_config(cls, config: dict[str, str]) -> Self:
        """Build the DTO from a wire config map, ignoring keys this mapper type does not define.

        Args:
            config: Wire config map as returned by Keycloak.

        Returns:
            Self: The typed config.
        """
        known = {field.alias for field in cls.model_fields.values()}
        data: dict[str, Any] = {key: value for key, value in config.items() if key in known}
        return cls.model_validate(data)


class KeycloakOidcAllowedOriginsMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-allowed-origins-mapper`` mapper (openid-connect).

    Attributes:
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-allowed-origins-mapper"

    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcAudienceMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-audience-mapper`` mapper (openid-connect).

    Attributes:
        included_client_audience: Value of the ``included.client.audience`` property.
        included_custom_audience: Value of the ``included.custom.audience`` property.
        id_token_claim: Add the claim to the ID token. Defaults to ``false``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-audience-mapper"

    included_client_audience: str | None = Field(default=None, alias="included.client.audience")
    included_custom_audience: str | None = Field(default=None, alias="included.custom.audience")
    id_token_claim: bool = Field(default=False, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcAudienceResolveMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-audience-resolve-mapper`` mapper (openid-connect).

    Attributes:
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-audience-resolve-mapper"

    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcAcrMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-acr-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-acr-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcAmrMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-amr-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-amr-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")


class KeycloakOidcClaimsParamTokenMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-claims-param-token-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-claims-param-token-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")


class KeycloakOidcClaimsParamValueIdtokenMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-claims-param-value-idtoken-mapper`` mapper (openid-connect).

    Attributes:
        claim_name: Name of the claim in the token.
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-claims-param-value-idtoken-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")


class KeycloakOidcGroupMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-group-membership-mapper`` mapper (openid-connect).

    Attributes:
        claim_name: Name of the claim in the token.
        full_path: Use the full group path instead of the group name. Defaults to ``true``.
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-group-membership-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    full_path: bool = Field(default=True, alias="full.path")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcHardcodedRoleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-hardcoded-role-mapper`` mapper (openid-connect).

    Attributes:
        role: Value of the ``role`` property.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-hardcoded-role-mapper"

    role: str | None = Field(default=None, alias="role")


class KeycloakOidcHardcodedClaimMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-hardcoded-claim-mapper`` mapper (openid-connect).

    Attributes:
        claim_name: Name of the claim in the token.
        claim_value: Value of the ``claim.value`` property.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        access_token_response_claim: Value of the ``access.tokenResponse.claim`` property. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-hardcoded-claim-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    claim_value: str | None = Field(default=None, alias="claim.value")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    access_token_response_claim: bool = Field(default=False, alias="access.tokenResponse.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcNonceBackwardsCompatibleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-nonce-backwards-compatible-mapper`` mapper (openid-connect).

    This mapper type has no config properties.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-nonce-backwards-compatible-mapper"


class KeycloakOidcOrganizationGroupMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-organization-group-membership-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
        add_group_role_mappings: Value of the ``addGroupRoleMappings`` property. Defaults to ``false``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-organization-group-membership-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")
    add_group_role_mappings: bool = Field(default=False, alias="addGroupRoleMappings")


class KeycloakOidcOrganizationMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-organization-membership-mapper`` mapper (openid-connect).

    Attributes:
        claim_name: Name of the claim in the token.
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON). Defaults to ``String``.
        multivalued: Emit the claim as a multivalued array. Defaults to ``true``.
        add_organization_attributes: Value of the ``addOrganizationAttributes`` property. Defaults to ``false``.
        add_organization_id: Value of the ``addOrganizationId`` property. Defaults to ``false``.
        add_organization_domain: Value of the ``addOrganizationDomain`` property. Defaults to ``false``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-organization-membership-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")
    json_type_label: str = Field(default="String", alias="jsonType.label")
    multivalued: bool = Field(default=True, alias="multivalued")
    add_organization_attributes: bool = Field(default=False, alias="addOrganizationAttributes")
    add_organization_id: bool = Field(default=False, alias="addOrganizationId")
    add_organization_domain: bool = Field(default=False, alias="addOrganizationDomain")


class KeycloakOidcSha256PairwiseSubMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-sha256-pairwise-sub-mapper`` mapper (openid-connect).

    Attributes:
        sector_identifier_uri: Value of the ``sectorIdentifierUri`` property.
        pairwise_sub_algorithm_salt: Value of the ``pairwiseSubAlgorithmSalt`` property.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-sha256-pairwise-sub-mapper"

    sector_identifier_uri: str | None = Field(default=None, alias="sectorIdentifierUri")
    pairwise_sub_algorithm_salt: str | None = Field(default=None, alias="pairwiseSubAlgorithmSalt")


class KeycloakOidcParameterizedScopeAudienceMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-parameterized-scope-audience-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-parameterized-scope-audience-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcParameterizedScopeClientSubMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-parameterized-scope-client-sub-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-parameterized-scope-client-sub-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcParameterizedScopeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-parameterized-scope-mapper`` mapper (openid-connect).

    Attributes:
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-parameterized-scope-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcParameterizedScopeUserPropertyMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-parameterized-scope-user-property-mapper`` mapper (openid-connect).

    Attributes:
        user_attribute: Value of the ``user.attribute`` property.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-parameterized-scope-user-property-mapper"

    user_attribute: str | None = Field(default=None, alias="user.attribute")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcRoleNameMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-role-name-mapper`` mapper (openid-connect).

    Attributes:
        role: Value of the ``role`` property.
        new_role_name: Value of the ``new.role.name`` property.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-role-name-mapper"

    role: str | None = Field(default=None, alias="role")
    new_role_name: str | None = Field(default=None, alias="new.role.name")


class KeycloakOidcSessionStateMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-session-state-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-session-state-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcSubMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-sub-mapper`` mapper (openid-connect).

    Attributes:
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-sub-mapper"

    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcAddressMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-address-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
        user_attribute_street: Value of the ``user.attribute.street`` property. Defaults to ``street``.
        user_attribute_locality: Value of the ``user.attribute.locality`` property. Defaults to ``locality``.
        user_attribute_region: Value of the ``user.attribute.region`` property. Defaults to ``region``.
        user_attribute_postal_code: Value of the ``user.attribute.postal_code`` property. Defaults to ``postal_code``.
        user_attribute_country: Value of the ``user.attribute.country`` property. Defaults to ``country``.
        user_attribute_formatted: Value of the ``user.attribute.formatted`` property. Defaults to ``formatted``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-address-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")
    user_attribute_street: str = Field(default="street", alias="user.attribute.street")
    user_attribute_locality: str = Field(default="locality", alias="user.attribute.locality")
    user_attribute_region: str = Field(default="region", alias="user.attribute.region")
    user_attribute_postal_code: str = Field(default="postal_code", alias="user.attribute.postal_code")
    user_attribute_country: str = Field(default="country", alias="user.attribute.country")
    user_attribute_formatted: str = Field(default="formatted", alias="user.attribute.formatted")


class KeycloakOidcUsermodelAttributeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-usermodel-attribute-mapper`` mapper (openid-connect).

    Attributes:
        user_attribute: Value of the ``user.attribute`` property.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
        multivalued: Emit the claim as a multivalued array.
        aggregate_attrs: Value of the ``aggregate.attrs`` property.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-usermodel-attribute-mapper"

    user_attribute: str | None = Field(default=None, alias="user.attribute")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")
    multivalued: bool | None = Field(default=None, alias="multivalued")
    aggregate_attrs: bool | None = Field(default=None, alias="aggregate.attrs")


class KeycloakOidcUsermodelClientRoleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-usermodel-client-role-mapper`` mapper (openid-connect).

    Attributes:
        usermodel_client_role_mapping_client_id: Value of the ``usermodel.clientRoleMapping.clientId`` property.
        usermodel_client_role_mapping_role_prefix: Value of the ``usermodel.clientRoleMapping.rolePrefix`` property.
        multivalued: Emit the claim as a multivalued array. Defaults to ``true``.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-usermodel-client-role-mapper"

    usermodel_client_role_mapping_client_id: str | None = Field(
        default=None,
        alias="usermodel.clientRoleMapping.clientId",
    )
    usermodel_client_role_mapping_role_prefix: str | None = Field(
        default=None,
        alias="usermodel.clientRoleMapping.rolePrefix",
    )
    multivalued: bool = Field(default=True, alias="multivalued")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcUsermodelPropertyMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-usermodel-property-mapper`` mapper (openid-connect).

    Attributes:
        user_attribute: Value of the ``user.attribute`` property.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-usermodel-property-mapper"

    user_attribute: str | None = Field(default=None, alias="user.attribute")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcUsermodelRealmRoleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-usermodel-realm-role-mapper`` mapper (openid-connect).

    Attributes:
        usermodel_realm_role_mapping_role_prefix: Value of the ``usermodel.realmRoleMapping.rolePrefix`` property.
        multivalued: Emit the claim as a multivalued array. Defaults to ``true``.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-usermodel-realm-role-mapper"

    usermodel_realm_role_mapping_role_prefix: str | None = Field(
        default=None,
        alias="usermodel.realmRoleMapping.rolePrefix",
    )
    multivalued: bool = Field(default=True, alias="multivalued")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcUsersessionmodelNoteMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-usersessionmodel-note-mapper`` mapper (openid-connect).

    Attributes:
        user_session_note: Value of the ``user.session.note`` property.
        claim_name: Name of the claim in the token.
        json_type_label: JSON type of the claim value (String, long, int, boolean, JSON).
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        access_token_response_claim: Value of the ``access.tokenResponse.claim`` property. Defaults to ``false``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-usersessionmodel-note-mapper"

    user_session_note: str | None = Field(default=None, alias="user.session.note")
    claim_name: str | None = Field(default=None, alias="claim.name")
    json_type_label: str | None = Field(default=None, alias="jsonType.label")
    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    access_token_response_claim: bool = Field(default=False, alias="access.tokenResponse.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOidcFullNameMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oidc-full-name-mapper`` mapper (openid-connect).

    Attributes:
        id_token_claim: Add the claim to the ID token. Defaults to ``true``.
        access_token_claim: Add the claim to the access token. Defaults to ``true``.
        lightweight_claim: Add the claim to lightweight access tokens only. Defaults to ``false``.
        userinfo_token_claim: Add the claim to the userinfo response. Defaults to ``true``.
        introspection_token_claim: Add the claim to the token introspection response. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "openid-connect"
    protocol_mapper: ClassVar[str] = "oidc-full-name-mapper"

    id_token_claim: bool = Field(default=True, alias="id.token.claim")
    access_token_claim: bool = Field(default=True, alias="access.token.claim")
    lightweight_claim: bool = Field(default=False, alias="lightweight.claim")
    userinfo_token_claim: bool = Field(default=True, alias="userinfo.token.claim")
    introspection_token_claim: bool = Field(default=True, alias="introspection.token.claim")


class KeycloakOid4vcContextMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-context-mapper`` mapper (oid4vc).

    Attributes:
        context: Value of the ``context`` property. Defaults to ``https://www.w3.org/2018/credentials/v1``.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-context-mapper"

    context: str = Field(default="https://www.w3.org/2018/credentials/v1", alias="context")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcVcTypeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-vc-type-mapper`` mapper (oid4vc).

    Attributes:
        vc_type_property: Value of the ``vcTypeProperty`` property.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-vc-type-mapper"

    vc_type_property: str | None = Field(default=None, alias="vcTypeProperty")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcSubjectIdMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-subject-id-mapper`` mapper (oid4vc).

    Attributes:
        claim_name: Name of the claim in the token. Defaults to ``id``.
        user_attribute: Value of the ``userAttribute`` property. Defaults to ``username``.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-subject-id-mapper"

    claim_name: str = Field(default="id", alias="claim.name")
    user_attribute: str = Field(default="username", alias="userAttribute")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcGeneratedIdMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-generated-id-mapper`` mapper (oid4vc).

    Attributes:
        claim_name: Name of the claim in the token. Defaults to ``id``.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-generated-id-mapper"

    claim_name: str = Field(default="id", alias="claim.name")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcIssuedAtTimeClaimMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-issued-at-time-claim-mapper`` mapper (oid4vc).

    Attributes:
        claim_name: Name of the claim in the token. Defaults to ``iat``.
        truncate_to_time_unit: Value of the ``truncateToTimeUnit`` property.
        value_source: Value of the ``valueSource`` property. Defaults to ``COMPUTE``.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-issued-at-time-claim-mapper"

    claim_name: str = Field(default="iat", alias="claim.name")
    truncate_to_time_unit: str | None = Field(default=None, alias="truncateToTimeUnit")
    value_source: str = Field(default="COMPUTE", alias="valueSource")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcStaticClaimMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-static-claim-mapper`` mapper (oid4vc).

    Attributes:
        claim_name: Name of the claim in the token.
        static_value: Value of the ``staticValue`` property.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-static-claim-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    static_value: str | None = Field(default=None, alias="staticValue")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcTargetRoleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-target-role-mapper`` mapper (oid4vc).

    Attributes:
        client_id: Value of the ``clientId`` property. Defaults to ``roles``.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-target-role-mapper"

    client_id: str = Field(default="roles", alias="clientId")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakOid4vcUserAttributeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``oid4vc-user-attribute-mapper`` mapper (oid4vc).

    Attributes:
        claim_name: Name of the claim in the token.
        user_attribute: Value of the ``userAttribute`` property.
        aggregate_attributes: Value of the ``aggregateAttributes`` property.
        vc_mandatory: Value of the ``vc.mandatory`` property. Defaults to ``false``.
        vc_display: Value of the ``vc.display`` property.
        mdoc_namespace: Value of the ``mdoc.namespace`` property.
    """

    protocol: ClassVar[str] = "oid4vc"
    protocol_mapper: ClassVar[str] = "oid4vc-user-attribute-mapper"

    claim_name: str | None = Field(default=None, alias="claim.name")
    user_attribute: str | None = Field(default=None, alias="userAttribute")
    aggregate_attributes: bool | None = Field(default=None, alias="aggregateAttributes")
    vc_mandatory: bool = Field(default=False, alias="vc.mandatory")
    vc_display: str | None = Field(default=None, alias="vc.display")
    mdoc_namespace: str | None = Field(default=None, alias="mdoc.namespace")


class KeycloakSamlAudienceMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-audience-mapper`` mapper (saml).

    Attributes:
        included_client_audience: Value of the ``included.client.audience`` property.
        included_custom_audience: Value of the ``included.custom.audience`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-audience-mapper"

    included_client_audience: str | None = Field(default=None, alias="included.client.audience")
    included_custom_audience: str | None = Field(default=None, alias="included.custom.audience")


class KeycloakSamlAudienceResolveMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-audience-resolve-mapper`` mapper (saml).

    This mapper type has no config properties.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-audience-resolve-mapper"


class KeycloakSamlAuthnContextClassRefMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-authn-context-class-ref-mapper`` mapper (saml).

    This mapper type has no config properties.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-authn-context-class-ref-mapper"


class KeycloakSamlGroupMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-group-membership-mapper`` mapper (saml).

    Attributes:
        attribute_name: Value of the ``attribute.name`` property. Defaults to ``member``.
        friendly_name: Value of the ``friendly.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
        single: Value of the ``single`` property. Defaults to ``true``.
        full_path: Use the full group path instead of the group name. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-group-membership-mapper"

    attribute_name: str = Field(default="member", alias="attribute.name")
    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")
    single: bool = Field(default=True, alias="single")
    full_path: bool = Field(default=True, alias="full.path")


class KeycloakSamlHardcodeAttributeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-hardcode-attribute-mapper`` mapper (saml).

    Attributes:
        friendly_name: Value of the ``friendly.name`` property.
        attribute_name: Value of the ``attribute.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
        attribute_value: Value of the ``attribute.value`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-hardcode-attribute-mapper"

    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_name: str | None = Field(default=None, alias="attribute.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")
    attribute_value: str | None = Field(default=None, alias="attribute.value")


class KeycloakSamlHardcodeRoleMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-hardcode-role-mapper`` mapper (saml).

    Attributes:
        role: Value of the ``role`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-hardcode-role-mapper"

    role: str | None = Field(default=None, alias="role")


class KeycloakSamlOrganizationGroupMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-organization-group-membership-mapper`` mapper (saml).

    Attributes:
        add_group_role_mappings: Value of the ``addGroupRoleMappings`` property. Defaults to ``false``.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-organization-group-membership-mapper"

    add_group_role_mappings: bool = Field(default=False, alias="addGroupRoleMappings")


class KeycloakSamlOrganizationMembershipMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-organization-membership-mapper`` mapper (saml).

    This mapper type has no config properties.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-organization-membership-mapper"


class KeycloakSamlUserAttributeMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-user-attribute-mapper`` mapper (saml).

    Attributes:
        user_attribute: Value of the ``user.attribute`` property.
        friendly_name: Value of the ``friendly.name`` property.
        attribute_name: Value of the ``attribute.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
        aggregate_attrs: Value of the ``aggregate.attrs`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-user-attribute-mapper"

    user_attribute: str | None = Field(default=None, alias="user.attribute")
    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_name: str | None = Field(default=None, alias="attribute.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")
    aggregate_attrs: bool | None = Field(default=None, alias="aggregate.attrs")


class KeycloakSamlUserPropertyMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-user-property-mapper`` mapper (saml).

    Attributes:
        user_attribute: Value of the ``user.attribute`` property.
        friendly_name: Value of the ``friendly.name`` property.
        attribute_name: Value of the ``attribute.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-user-property-mapper"

    user_attribute: str | None = Field(default=None, alias="user.attribute")
    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_name: str | None = Field(default=None, alias="attribute.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")


class KeycloakSamlUserSessionNoteMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-user-session-note-mapper`` mapper (saml).

    Attributes:
        note: Value of the ``note`` property.
        friendly_name: Value of the ``friendly.name`` property.
        attribute_name: Value of the ``attribute.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-user-session-note-mapper"

    note: str | None = Field(default=None, alias="note")
    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_name: str | None = Field(default=None, alias="attribute.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")


class KeycloakSamlRoleNameMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-role-name-mapper`` mapper (saml).

    Attributes:
        role: Value of the ``role`` property.
        new_role_name: Value of the ``new.role.name`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-role-name-mapper"

    role: str | None = Field(default=None, alias="role")
    new_role_name: str | None = Field(default=None, alias="new.role.name")


class KeycloakSamlRoleListMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-role-list-mapper`` mapper (saml).

    Attributes:
        attribute_name: Value of the ``attribute.name`` property. Defaults to ``Role``.
        friendly_name: Value of the ``friendly.name`` property.
        attribute_nameformat: Value of the ``attribute.nameformat`` property.
        single: Value of the ``single`` property. Defaults to ``true``.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-role-list-mapper"

    attribute_name: str = Field(default="Role", alias="attribute.name")
    friendly_name: str | None = Field(default=None, alias="friendly.name")
    attribute_nameformat: str | None = Field(default=None, alias="attribute.nameformat")
    single: bool = Field(default=True, alias="single")


class KeycloakSamlUserAttributeNameidMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``saml-user-attribute-nameid-mapper`` mapper (saml).

    Attributes:
        mapper_nameid_format: Value of the ``mapper.nameid.format`` property.
        user_attribute: Value of the ``user.attribute`` property.
    """

    protocol: ClassVar[str] = "saml"
    protocol_mapper: ClassVar[str] = "saml-user-attribute-nameid-mapper"

    mapper_nameid_format: str | None = Field(default=None, alias="mapper.nameid.format")
    user_attribute: str | None = Field(default=None, alias="user.attribute")


class KeycloakDockerV2AllowAllMapperConfigDTO(KeycloakProtocolMapperConfigDTO):
    """Config of the ``docker-v2-allow-all-mapper`` mapper (docker-v2).

    This mapper type has no config properties.
    """

    protocol: ClassVar[str] = "docker-v2"
    protocol_mapper: ClassVar[str] = "docker-v2-allow-all-mapper"


PROTOCOL_MAPPER_CONFIGS: dict[str, type[KeycloakProtocolMapperConfigDTO]] = {
    "oidc-allowed-origins-mapper": KeycloakOidcAllowedOriginsMapperConfigDTO,
    "oidc-audience-mapper": KeycloakOidcAudienceMapperConfigDTO,
    "oidc-audience-resolve-mapper": KeycloakOidcAudienceResolveMapperConfigDTO,
    "oidc-acr-mapper": KeycloakOidcAcrMapperConfigDTO,
    "oidc-amr-mapper": KeycloakOidcAmrMapperConfigDTO,
    "oidc-claims-param-token-mapper": KeycloakOidcClaimsParamTokenMapperConfigDTO,
    "oidc-claims-param-value-idtoken-mapper": KeycloakOidcClaimsParamValueIdtokenMapperConfigDTO,
    "oidc-group-membership-mapper": KeycloakOidcGroupMembershipMapperConfigDTO,
    "oidc-hardcoded-role-mapper": KeycloakOidcHardcodedRoleMapperConfigDTO,
    "oidc-hardcoded-claim-mapper": KeycloakOidcHardcodedClaimMapperConfigDTO,
    "oidc-nonce-backwards-compatible-mapper": KeycloakOidcNonceBackwardsCompatibleMapperConfigDTO,
    "oidc-organization-group-membership-mapper": KeycloakOidcOrganizationGroupMembershipMapperConfigDTO,
    "oidc-organization-membership-mapper": KeycloakOidcOrganizationMembershipMapperConfigDTO,
    "oidc-sha256-pairwise-sub-mapper": KeycloakOidcSha256PairwiseSubMapperConfigDTO,
    "oidc-parameterized-scope-audience-mapper": KeycloakOidcParameterizedScopeAudienceMapperConfigDTO,
    "oidc-parameterized-scope-client-sub-mapper": KeycloakOidcParameterizedScopeClientSubMapperConfigDTO,
    "oidc-parameterized-scope-mapper": KeycloakOidcParameterizedScopeMapperConfigDTO,
    "oidc-parameterized-scope-user-property-mapper": KeycloakOidcParameterizedScopeUserPropertyMapperConfigDTO,
    "oidc-role-name-mapper": KeycloakOidcRoleNameMapperConfigDTO,
    "oidc-session-state-mapper": KeycloakOidcSessionStateMapperConfigDTO,
    "oidc-sub-mapper": KeycloakOidcSubMapperConfigDTO,
    "oidc-address-mapper": KeycloakOidcAddressMapperConfigDTO,
    "oidc-usermodel-attribute-mapper": KeycloakOidcUsermodelAttributeMapperConfigDTO,
    "oidc-usermodel-client-role-mapper": KeycloakOidcUsermodelClientRoleMapperConfigDTO,
    "oidc-usermodel-property-mapper": KeycloakOidcUsermodelPropertyMapperConfigDTO,
    "oidc-usermodel-realm-role-mapper": KeycloakOidcUsermodelRealmRoleMapperConfigDTO,
    "oidc-usersessionmodel-note-mapper": KeycloakOidcUsersessionmodelNoteMapperConfigDTO,
    "oidc-full-name-mapper": KeycloakOidcFullNameMapperConfigDTO,
    "oid4vc-context-mapper": KeycloakOid4vcContextMapperConfigDTO,
    "oid4vc-vc-type-mapper": KeycloakOid4vcVcTypeMapperConfigDTO,
    "oid4vc-subject-id-mapper": KeycloakOid4vcSubjectIdMapperConfigDTO,
    "oid4vc-generated-id-mapper": KeycloakOid4vcGeneratedIdMapperConfigDTO,
    "oid4vc-issued-at-time-claim-mapper": KeycloakOid4vcIssuedAtTimeClaimMapperConfigDTO,
    "oid4vc-static-claim-mapper": KeycloakOid4vcStaticClaimMapperConfigDTO,
    "oid4vc-target-role-mapper": KeycloakOid4vcTargetRoleMapperConfigDTO,
    "oid4vc-user-attribute-mapper": KeycloakOid4vcUserAttributeMapperConfigDTO,
    "saml-audience-mapper": KeycloakSamlAudienceMapperConfigDTO,
    "saml-audience-resolve-mapper": KeycloakSamlAudienceResolveMapperConfigDTO,
    "saml-authn-context-class-ref-mapper": KeycloakSamlAuthnContextClassRefMapperConfigDTO,
    "saml-group-membership-mapper": KeycloakSamlGroupMembershipMapperConfigDTO,
    "saml-hardcode-attribute-mapper": KeycloakSamlHardcodeAttributeMapperConfigDTO,
    "saml-hardcode-role-mapper": KeycloakSamlHardcodeRoleMapperConfigDTO,
    "saml-organization-group-membership-mapper": KeycloakSamlOrganizationGroupMembershipMapperConfigDTO,
    "saml-organization-membership-mapper": KeycloakSamlOrganizationMembershipMapperConfigDTO,
    "saml-user-attribute-mapper": KeycloakSamlUserAttributeMapperConfigDTO,
    "saml-user-property-mapper": KeycloakSamlUserPropertyMapperConfigDTO,
    "saml-user-session-note-mapper": KeycloakSamlUserSessionNoteMapperConfigDTO,
    "saml-role-name-mapper": KeycloakSamlRoleNameMapperConfigDTO,
    "saml-role-list-mapper": KeycloakSamlRoleListMapperConfigDTO,
    "saml-user-attribute-nameid-mapper": KeycloakSamlUserAttributeNameidMapperConfigDTO,
    "docker-v2-allow-all-mapper": KeycloakDockerV2AllowAllMapperConfigDTO,
}


def parse_protocol_mapper_config(
    protocol_mapper: str,
    config: dict[str, str],
) -> KeycloakProtocolMapperConfigDTO | None:
    """Parse a wire config map into the typed DTO of its mapper type.

    Args:
        protocol_mapper: Keycloak mapper id, for example ``oidc-audience-mapper``.
        config: Wire config map as returned by Keycloak. Unknown keys are ignored.

    Returns:
        KeycloakProtocolMapperConfigDTO | None: The typed config, or None for an unknown mapper id.
    """
    dto_class = PROTOCOL_MAPPER_CONFIGS.get(protocol_mapper)
    if dto_class is None:
        return None
    return dto_class.from_config(config)
