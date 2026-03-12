# Utils

The `helpers/utils` subpackage provides utility classes with static methods for common operations including date/time handling, string manipulation, file I/O, JWT tokens, passwords, TOTP, Keycloak integration, Prometheus metrics, and application-level utilities.

## base_utils

Base utility class providing foundational helpers shared across other utility classes.

::: archipy.helpers.utils.base_utils
    options:
      show_root_heading: true
      show_source: true

## app_utils

Application-level utilities for runtime environment inspection and process management.

::: archipy.helpers.utils.app_utils
    options:
      show_root_heading: true
      show_source: true

## datetime_utils

Utilities for timezone-aware date and time operations with microsecond precision.

::: archipy.helpers.utils.datetime_utils
    options:
      show_root_heading: true
      show_source: true

## string_utils

Utilities for string manipulation including slugification, truncation, random string generation, and HTML sanitization.

::: archipy.helpers.utils.string_utils
    options:
      show_root_heading: true
      show_source: true

## string_utils_constants

Constants used by `string_utils` for character sets, patterns, and limits.

::: archipy.helpers.utils.string_utils_constants
    options:
      show_root_heading: true
      show_source: true

## file_utils

Utilities for file operations including reading, writing, hashing, and type validation.

::: archipy.helpers.utils.file_utils
    options:
      show_root_heading: true
      show_source: true

## error_utils

Utilities for error formatting, context enrichment, and error chain inspection.

::: archipy.helpers.utils.error_utils
    options:
      show_root_heading: true
      show_source: true

## jwt_utils

Utilities for JWT generation, verification, and decoding with configurable signing algorithms and expiration.

::: archipy.helpers.utils.jwt_utils
    options:
      show_root_heading: true
      show_source: true

## password_utils

Utilities for secure password hashing, verification, generation, and strength validation with timing-attack protection.

::: archipy.helpers.utils.password_utils
    options:
      show_root_heading: true
      show_source: true

## totp_utils

Utilities for TOTP (Time-based One-Time Password) generation, verification, and QR code URI construction.

::: archipy.helpers.utils.totp_utils
    options:
      show_root_heading: true
      show_source: true

## keycloak_utils

Utilities for Keycloak token acquisition, validation, user info retrieval, and role checking.

::: archipy.helpers.utils.keycloak_utils
    options:
      show_root_heading: true
      show_source: true

## prometheus_utils

Utilities for registering and exposing Prometheus metrics within ArchiPy applications.

::: archipy.helpers.utils.prometheus_utils
    options:
      show_root_heading: true
      show_source: true
