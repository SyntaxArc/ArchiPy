---
title: Decorators
description: API reference for ArchiPy helper decorators.
---

# Decorators

The `helpers/decorators` subpackage provides function and class decorators for cross-cutting concerns including caching,
retry logic, deprecation, timing, tracing, and transaction management.

Import general-purpose decorators from `archipy.helpers.decorators`. The tracing and metrics decorators accept
both synchronous and asynchronous functions.

## Cache

Decorator for caching function return values to avoid redundant computation or I/O.

::: archipy.helpers.decorators.ttl_caching
options:
show_root_toc_entry: false
heading_level: 3

## Retry

Decorator that automatically retries a failing function call with configurable backoff strategies.

::: archipy.helpers.decorators.retry_policy
options:
show_root_toc_entry: false
heading_level: 3

## Timeout

Decorator that enforces a maximum execution time on a function call.

::: archipy.helpers.decorators.timeout_limit
options:
show_root_toc_entry: false
heading_level: 3

## Timing

Decorator that measures and records the execution time of a function.

::: archipy.helpers.decorators.timing_log
options:
show_root_toc_entry: false
heading_level: 3

## Tracing

OpenTelemetry span decorators for functions and classes (`trace_span`, `trace_root`, `trace_class`).

::: archipy.helpers.decorators.tracing
options:
show_root_toc_entry: false
heading_level: 3

## Metrics

OpenTelemetry metrics decorators for duration histograms and call counters (`measure_duration`, `count_calls`). Both
accept synchronous and asynchronous functions.

::: archipy.helpers.decorators.metrics
options:
show_root_toc_entry: false
heading_level: 3

## Singleton

Decorator that ensures a class is instantiated only once throughout the application lifecycle.

::: archipy.helpers.decorators.singleton_class
options:
show_root_toc_entry: false
heading_level: 3

## SQLAlchemy Atomic


Import the atomic decorators from `archipy.adapters.base.sqlalchemy.atomic`.
[Base SQLAlchemy](../adapters/base.md#atomic-transaction-decorators) documents the database-specific variants.

## Deprecation Warnings

Decorator that emits a deprecation warning when a decorated function or class is used.

::: archipy.helpers.decorators.deprecation_warnings
options:
show_root_toc_entry: false
heading_level: 3

## Deprecation Exception

Decorator that raises an exception when a deprecated function or class is called.

::: archipy.helpers.decorators.deprecation_exception
options:
show_root_toc_entry: false
heading_level: 3

## gRPC Rate Limit

Decorator that declares per-RPC rate-limit windows on gRPC servicer methods. Read by
`GrpcServerRateLimitInterceptor` and `AsyncGrpcServerRateLimitInterceptor`.

::: archipy.helpers.decorators.grpc_rate_limit_window
options:
show_root_toc_entry: false
heading_level: 3
