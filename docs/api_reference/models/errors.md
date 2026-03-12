# Errors

The `models/errors` subpackage defines the custom exception hierarchy for ArchiPy. All errors subclass `BaseError` and are organized by domain: authentication, authorization, validation, resource management, networking, database, system, Keycloak, and Temporal.

## base_error

The root `BaseError` class that all ArchiPy exceptions inherit from, providing structured error codes and context.

::: archipy.models.errors.base_error
    options:
      show_root_heading: true
      show_source: true

## auth_errors

Exceptions for authentication and authorization failures.

::: archipy.models.errors.auth_errors
    options:
      show_root_heading: true
      show_source: true

## validation_errors

Exceptions for input validation and data integrity failures.

::: archipy.models.errors.validation_errors
    options:
      show_root_heading: true
      show_source: true

## resource_errors

Exceptions for resource lifecycle issues such as not found, already exists, and conflict.

::: archipy.models.errors.resource_errors
    options:
      show_root_heading: true
      show_source: true

## business_errors

Exceptions representing violations of business rules and domain constraints.

::: archipy.models.errors.business_errors
    options:
      show_root_heading: true
      show_source: true

## network_errors

Exceptions for network communication failures including timeouts and connectivity issues.

::: archipy.models.errors.network_errors
    options:
      show_root_heading: true
      show_source: true

## database_errors

Exceptions for database-level failures including connection errors, constraint violations, and transaction failures.

::: archipy.models.errors.database_errors
    options:
      show_root_heading: true
      show_source: true

## system_errors

Exceptions for system-level failures including configuration errors and unexpected runtime conditions.

::: archipy.models.errors.system_errors
    options:
      show_root_heading: true
      show_source: true

## keycloak_errors

Exceptions specific to Keycloak integration failures, such as token validation errors and realm configuration issues.

::: archipy.models.errors.keycloak_errors
    options:
      show_root_heading: true
      show_source: true

## temporal_errors

Exceptions specific to Temporal workflow orchestration failures, such as workflow execution errors and activity timeouts.

::: archipy.models.errors.temporal_errors
    options:
      show_root_heading: true
      show_source: true
