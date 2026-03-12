# Keycloak

The `keycloak` adapter provides integration with Keycloak for identity and access management, including token validation, user management, and role-based access control.

## ports

Abstract port interface defining the Keycloak adapter contract.

::: archipy.adapters.keycloak.ports
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete Keycloak adapter wrapping the Keycloak REST API for authentication and authorization operations.

::: archipy.adapters.keycloak.adapters
    options:
      show_root_heading: true
      show_source: true
