---
title: Interceptor Tutorials
description: Practical tutorials for using ArchiPy helper interceptors.
---

# Interceptor Tutorials

This page demonstrates how to use ArchiPy's interceptors for cross-cutting concerns like tracing, metrics, and error
handling.

## gRPC Interceptors

### Tracing Interceptor

The tracing interceptor adds request/response tracking to gRPC services:

```python
import grpc
from concurrent import futures

from archipy.helpers.interceptors.grpc.trace.server_interceptor import GrpcServerTraceInterceptor
from archipy.models.errors import InternalError


# Create a gRPC server with tracing
def create_grpc_server(max_workers: int = 10) -> grpc.Server:
    """Create a gRPC server with tracing interceptor.

    Args:
        max_workers: Maximum worker threads for the server

    Returns:
        Configured gRPC server instance
    """
    try:
        # Initialize the tracing interceptor
        trace_interceptor = GrpcServerTraceInterceptor()

        # Create the server with the interceptor
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers),
            interceptors=[trace_interceptor],
        )
        return server
    except Exception as e:
        raise InternalError(additional_data={"detail": "Failed to create gRPC server"}) from e


# Usage
server = create_grpc_server()
# Add your services to the server
# my_service.add_to_server(server)
# server.add_insecure_port('[::]:50051')
# server.start()
```

### Metrics Interceptor

The metrics interceptor records gRPC call durations and counts for Prometheus:

```python
import grpc
from concurrent import futures

from archipy.helpers.interceptors.grpc.metric.server_interceptor import GrpcServerMetricInterceptor
from archipy.helpers.interceptors.grpc.trace.server_interceptor import GrpcServerTraceInterceptor


def create_grpc_server_with_metrics(max_workers: int = 10) -> grpc.Server:
    """Create a gRPC server with both tracing and metrics interceptors.

    Args:
        max_workers: Maximum worker threads for the server

    Returns:
        Configured gRPC server instance
    """
    interceptors = [
        GrpcServerTraceInterceptor(),
        GrpcServerMetricInterceptor(),
    ]
    return grpc.server(
        futures.ThreadPoolExecutor(max_workers=max_workers),
        interceptors=interceptors,
    )
```

## FastAPI Interceptors

### Metrics Middleware

`FastAPIMetricInterceptor` records request durations and counts for Prometheus:

```python
from fastapi import FastAPI

from archipy.helpers.interceptors.fastapi.metric.interceptor import FastAPIMetricInterceptor
from archipy.helpers.utils.app_utils import AppUtils

# Create a FastAPI app
app = AppUtils.create_fastapi_app()

# Add the metrics middleware
app.add_middleware(FastAPIMetricInterceptor)


# Example endpoint — duration and status will be recorded automatically
@app.get("/process")
async def process_data(query: str) -> dict[str, str]:
    return {"query": query, "result": "processed"}
```

### Rate Limiting Dependency

`FastAPIRestRateLimitHandler` enforces per-client request limits on HTTP endpoints using Redis as the backend.
It uses the Redis 8.8 `INCREX` command for atomic counter increments with bounds and window expiry, avoiding
check-then-act races under concurrent requests.

Install the required extras:

```bash
uv add "archipy[redis,fastapi]"
```

> **Note:** Redis **8.8+** is required. The handler depends on the `INCREX` command, which is not available on
> earlier Redis versions.

Attach the handler as a route dependency with `Depends` — it is not registered as middleware:

```python
from fastapi import Depends

from archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler import (
    FastAPIRestRateLimitHandler,
)
from archipy.helpers.utils.app_utils import AppUtils

app = AppUtils.create_fastapi_app()


@app.get("/api/resource", dependencies=[Depends(FastAPIRestRateLimitHandler(calls_count=100, minutes=1))])
async def resource() -> dict[str, str]:
    return {"status": "ok"}
```

#### How it works

On each request the handler:

1. Builds a Redis key from the client identifier, path, HTTP method, and optional query parameters.
2. Calls `INCREX` with `ubound=calls_count`, `saturate=True`, `enx=True`, and a millisecond window (`px`).
3. Allows the request when the increment is applied; otherwise raises HTTP **429 Too Many Requests** with a
   `Retry-After` header (seconds, ceiling of the remaining TTL).

`enx=True` sets the window expiry only when the key is first created, so subsequent requests within the window
preserve the original TTL.

#### Client identification

The handler resolves the client in this order:

1. `X-Real-IP` header
2. `X-Forwarded-For` header (first non-private IP)
3. `request.client.host`

Private, loopback, link-local, and multicast addresses in headers are ignored and the next source is tried.

> **Warning:** In Python 3.14, documentation-range IPs such as `203.0.113.x` are classified as private. When
> testing `X-Real-IP` behaviour locally, use globally routable addresses (for example `8.8.8.8`).

#### Per-query-parameter buckets

Pass `query_params` to include specific query parameters in the rate-limit key:

```python
handler = FastAPIRestRateLimitHandler(
    calls_count=50,
    minutes=1,
    query_params={"user_id", "action"},
)

@app.get("/api/action", dependencies=[Depends(handler)])
async def action() -> dict[str, str]:
    return {"status": "ok"}
```

## Using Multiple Interceptors

Combining gRPC and FastAPI interceptors in an application:

```python
import grpc
from concurrent import futures
from fastapi import FastAPI

from archipy.helpers.interceptors.fastapi.metric.interceptor import FastAPIMetricInterceptor
from archipy.helpers.interceptors.grpc.trace.server_interceptor import GrpcServerTraceInterceptor
from archipy.helpers.utils.app_utils import AppUtils


# Create a FastAPI app with metrics middleware
def create_fastapi_app() -> FastAPI:
    app = AppUtils.create_fastapi_app()

    # Add metrics middleware
    app.add_middleware(FastAPIMetricInterceptor)

    return app


# Create a gRPC server with the tracing interceptor
def create_grpc_server() -> grpc.Server:
    return grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[GrpcServerTraceInterceptor()],
    )
```

## See Also

- [API Reference - Interceptors](../../api_reference/helpers/interceptors.md) - Full interceptors API documentation
- [Redis Adapter - INCREX](../adapters/redis.md#increx-window-counter) - Redis `INCREX` window counter usage
- [Helper Tutorials](index.md) - Overview of all helper tutorials
