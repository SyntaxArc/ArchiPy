---
title: Interceptors
description: API reference for ArchiPy helper interceptors.
---

# Interceptors

The `helpers/interceptors` subpackage provides gRPC server interceptors for exception handling
and rate limiting. FastAPI metrics middleware and gRPC metric/trace interceptors were removed in
5.0.0 — use OpenTelemetry via `AppUtils` / `OtelUtils` instead (see
[Observability](../../tutorials/observability.md)).

## gRPC

### base

Abstract base classes for gRPC client and server interceptors.

::: archipy.helpers.interceptors.grpc.base.client_interceptor
options:
show_root_toc_entry: false
heading_level: 3

::: archipy.helpers.interceptors.grpc.base.server_interceptor
options:
show_root_toc_entry: false
heading_level: 3

### exception

gRPC server interceptor that catches exceptions and converts them to gRPC status codes.

::: archipy.helpers.interceptors.grpc.exception.server_interceptor
options:
show_root_toc_entry: false
heading_level: 3

### rate_limit

gRPC server interceptors that enforce decorator-declared Redis rate limits on servicer methods.

::: archipy.helpers.interceptors.grpc.rate_limit.grpc_rate_limit_interceptor
options:
show_root_toc_entry: false
heading_level: 3

::: archipy.helpers.interceptors.grpc.rate_limit.identifiers
options:
show_root_toc_entry: false
heading_level: 3
