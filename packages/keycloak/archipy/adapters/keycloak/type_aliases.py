"""Shared Keycloak port type aliases."""

from __future__ import annotations

from typing import Any

from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeDTO, KeycloakProtocolMapperDTO
from archipy.models.dtos.keycloak.component_dtos import KeycloakComponentDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupDTO
from archipy.models.dtos.keycloak.organization_dtos import KeycloakOrganizationDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO

# Define type aliases for better type hinting
KeycloakResponseType = dict[str, Any]
KeycloakTokenType = dict[str, Any]

KeycloakUserType = dict[str, Any]

# Deprecated aliases of the pydantic DTOs that replaced the TypedDicts; removed in 6.0.0.
KeycloakRoleType = KeycloakRoleDTO
KeycloakGroupType = KeycloakGroupDTO
KeycloakOrganizationType = KeycloakOrganizationDTO
KeycloakClientScopeType = KeycloakClientScopeDTO
KeycloakProtocolMapperType = KeycloakProtocolMapperDTO
KeycloakComponentType = KeycloakComponentDTO

# Define a type for the public key return type
# Using Any for JWK.JWK object, since we don't want to depend on jwcrypto types
PublicKeyType = Any
