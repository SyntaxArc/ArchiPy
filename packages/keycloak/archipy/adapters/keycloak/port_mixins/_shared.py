"""Shared Keycloak port type aliases."""

from __future__ import annotations

from typing import Any, TypedDict

# Define type aliases for better type hinting
KeycloakResponseType = dict[str, Any]
KeycloakUserType = dict[str, Any]
KeycloakTokenType = dict[str, Any]


class KeycloakRoleType(TypedDict, total=False):
    """Keycloak ``RoleRepresentation`` as returned by the admin API."""

    id: str
    name: str
    description: str
    composite: bool
    clientRole: bool
    containerId: str
    attributes: dict[str, list[str]]


class KeycloakGroupType(TypedDict, total=False):
    """Keycloak ``GroupRepresentation`` as returned by the admin API."""

    id: str
    name: str
    path: str
    parentId: str
    subGroupCount: int
    subGroups: list[KeycloakGroupType]
    attributes: dict[str, list[str]]
    realmRoles: list[str]
    clientRoles: dict[str, list[str]]
    access: dict[str, bool]


class KeycloakOrganizationType(TypedDict, total=False):
    """Keycloak ``OrganizationRepresentation`` as returned by the admin API."""

    id: str
    name: str
    alias: str
    enabled: bool
    description: str
    redirectUrl: str
    attributes: dict[str, list[str]]
    domains: list[dict[str, Any]]


class KeycloakClientScopeType(TypedDict, total=False):
    """Keycloak ``ClientScopeRepresentation`` as returned by the admin API."""

    id: str
    name: str
    description: str
    protocol: str
    attributes: dict[str, str]
    protocolMappers: list[KeycloakProtocolMapperType]


class KeycloakProtocolMapperType(TypedDict, total=False):
    """Keycloak ``ProtocolMapperRepresentation`` as returned by the admin API."""

    id: str
    name: str
    protocol: str
    protocolMapper: str
    consentRequired: bool
    config: dict[str, str]


class KeycloakComponentType(TypedDict, total=False):
    """Keycloak ``ComponentRepresentation`` as returned by the admin API."""

    id: str
    name: str
    providerId: str
    providerType: str
    parentId: str
    subType: str
    config: dict[str, list[str]]


# Define a type for the public key return type
# Using Any for JWK.JWK object, since we don't want to depend on jwcrypto types
PublicKeyType = Any
