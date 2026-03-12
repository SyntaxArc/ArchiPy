---
title: Keycloak
description: API reference for the Keycloak adapter ports, adapters, and mocks.
---

# Keycloak

The `keycloak` adapter provides integration with Keycloak for identity and access management, including token validation, user management, and role-based access control.

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
