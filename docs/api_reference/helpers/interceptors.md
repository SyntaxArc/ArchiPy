# Interceptors

The `helpers/interceptors` subpackage provides request/response interceptors for FastAPI and gRPC, covering rate limiting, metrics collection, exception handling, and distributed tracing.

## FastAPI

### metric

FastAPI middleware interceptor for collecting Prometheus metrics on HTTP requests.

::: archipy.helpers.interceptors.fastapi.metric.interceptor
    options:
      show_root_heading: true
      show_source: true

### rate_limit

FastAPI interceptor that enforces configurable rate limits on HTTP endpoints using Redis as a backend.

::: archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler
    options:
      show_root_heading: true
      show_source: true

## gRPC

### base

Abstract base classes for gRPC client and server interceptors.

::: archipy.helpers.interceptors.grpc.base.client_interceptor
    options:
      show_root_heading: true
      show_source: true

::: archipy.helpers.interceptors.grpc.base.server_interceptor
    options:
      show_root_heading: true
      show_source: true

### exception

gRPC server interceptor that catches exceptions and converts them to gRPC status codes.

::: archipy.helpers.interceptors.grpc.exception.server_interceptor
    options:
      show_root_heading: true
      show_source: true

### metric

gRPC server interceptor for collecting Prometheus metrics on RPC calls.

::: archipy.helpers.interceptors.grpc.metric.server_interceptor
    options:
      show_root_heading: true
      show_source: true

### trace

gRPC interceptors for propagating distributed tracing context across client and server.

::: archipy.helpers.interceptors.grpc.trace.client_interceptor
    options:
      show_root_heading: true
      show_source: true

::: archipy.helpers.interceptors.grpc.trace.server_interceptor
    options:
      show_root_heading: true
      show_source: true
