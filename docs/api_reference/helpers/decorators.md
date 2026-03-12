# Decorators

The `helpers/decorators` subpackage provides function and class decorators for cross-cutting concerns including caching, retry logic, deprecation, timing, tracing, and transaction management.

## cache

Decorator for caching function return values to avoid redundant computation or I/O.

::: archipy.helpers.decorators.cache
    options:
      show_root_heading: true
      show_source: true

## retry

Decorator that automatically retries a failing function call with configurable backoff strategies.

::: archipy.helpers.decorators.retry
    options:
      show_root_heading: true
      show_source: true

## timeout

Decorator that enforces a maximum execution time on a function call.

::: archipy.helpers.decorators.timeout
    options:
      show_root_heading: true
      show_source: true

## timing

Decorator that measures and records the execution time of a function.

::: archipy.helpers.decorators.timing
    options:
      show_root_heading: true
      show_source: true

## tracing

Decorator that adds distributed tracing instrumentation to a function.

::: archipy.helpers.decorators.tracing
    options:
      show_root_heading: true
      show_source: true

## singleton

Decorator that ensures a class is instantiated only once throughout the application lifecycle.

::: archipy.helpers.decorators.singleton
    options:
      show_root_heading: true
      show_source: true

## sqlalchemy_atomic

Decorator that wraps a function in a SQLAlchemy database transaction, rolling back on failure.

::: archipy.helpers.decorators.sqlalchemy_atomic
    options:
      show_root_heading: true
      show_source: true

## deprecation_warnings

Decorator that emits a deprecation warning when a decorated function or class is used.

::: archipy.helpers.decorators.deprecation_warnings
    options:
      show_root_heading: true
      show_source: true

## deprecation_exception

Decorator that raises an exception when a deprecated function or class is called.

::: archipy.helpers.decorators.deprecation_exception
    options:
      show_root_heading: true
      show_source: true
