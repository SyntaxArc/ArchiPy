---
title: Errors
description: API reference for ArchiPy custom exception classes.
---

# Errors

The `models/errors` subpackage defines the custom exception hierarchy for ArchiPy. All errors subclass `BaseError` and are organized by domain: authentication, authorization, validation, resource management, networking, database, system, Keycloak, and Temporal.

## Base Error

The root `BaseError` class that all ArchiPy exceptions inherit from, providing structured error codes and context.

::: archipy.models.errors.base_error
    options:
      show_root_toc_entry: false
      heading_level: 3

## Auth Errors

Exceptions for authentication and authorization failures.

::: archipy.models.errors.auth_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Validation Errors

Exceptions for input validation and data integrity failures.

::: archipy.models.errors.validation_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Resource Errors

Exceptions for resource lifecycle issues such as not found, already exists, and conflict.

::: archipy.models.errors.resource_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Business Errors

Exceptions representing violations of business rules and domain constraints.

::: archipy.models.errors.business_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Network Errors

Exceptions for network communication failures including timeouts and connectivity issues.

::: archipy.models.errors.network_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Database Errors

Exceptions for database-level failures including connection errors, constraint violations, and transaction failures.

::: archipy.models.errors.database_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## System Errors

Exceptions for system-level failures including configuration errors and unexpected runtime conditions.

::: archipy.models.errors.system_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Keycloak Errors

Exceptions specific to Keycloak integration failures, such as token validation errors and realm configuration issues.

::: archipy.models.errors.keycloak_errors
    options:
      show_root_toc_entry: false
      heading_level: 3

## Temporal Errors

Exceptions specific to Temporal workflow orchestration failures, such as workflow execution errors and activity timeouts.

::: archipy.models.errors.temporal_errors
    options:
      show_root_toc_entry: false
      heading_level: 3
