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
permissions and resource ownership.

::: archipy.adapters.keycloak.auth
options:
show_root_toc_entry: false
heading_level: 3
