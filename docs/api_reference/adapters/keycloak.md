---
title: Keycloak
description: API reference for the Keycloak adapter ports and adapters.
---

# Keycloak

The `keycloak` adapter provides integration with Keycloak for identity and access management, including token
validation, user management, and role-based access control.

!!! note "Private layout"
    Only `ports`, `adapters` and `auth` are public API. The per-resource mixins in `_resources/`, the protocol mixins
    in `_protocols/`, and the modules `_base`, `_connection` and `_type_aliases` are private and may change without
    notice. Every method they define is reachable through `KeycloakPort`, `AsyncKeycloakPort`, `KeycloakAdapter` and
    `AsyncKeycloakAdapter`.

## Ports

Abstract port interface defining the Keycloak adapter contract.

::: archipy.adapters.keycloak.ports
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete Keycloak adapter wrapping the Keycloak REST API for authentication and authorization operations.

::: archipy.adapters.keycloak.adapters
options:
show_root_toc_entry: false
heading_level: 3

## Auth Guards

FastAPI dependencies and gRPC decorators that authenticate a bearer token against Keycloak and check roles,
permissions and resource ownership. Both guards populate typed organization details from authenticated UserInfo in the auth context.
`require_organization` overrides `KeycloakConfig.REQUIRE_ORGANIZATION`, which defaults to False.

`resolve_owner(context)` returns an immutable `OwnerDTO` with `owner_uuid` and `OwnerType.USER` or `OwnerType.ORGANIZATION`.
Only the matching `user` (`KeycloakUserInfoDTO`) or `organization` (`KeycloakOrganizationClaimDTO`) field is populated.
`is_user` and `is_organization` are read-only convenience properties and do not appear in JSON output.
`get_authenticated_actor()` returns the current outermost actor, falling back to the authenticated user for direct requests.
It raises `UnauthenticatedError` when no request context exists.
`get_authenticated_actor_and_owner()` combines both helpers and returns `(ActorDTO, OwnerDTO)`, propagating their errors.
`get_authenticated_owner()` delegates using the current request context and raises `UnauthenticatedError` if absent.
Ambiguous organization ownership raises `PermissionDeniedError`; it never falls back to personal ownership.
See [resource ownership](../../tutorials/adapters/keycloak.md#resource-ownership) for the contract and UUID migration notes.

::: archipy.adapters.keycloak.auth
options:
show_root_toc_entry: false
heading_level: 3
