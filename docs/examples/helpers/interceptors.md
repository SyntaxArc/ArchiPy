---
title: Interceptor Examples
description: Practical examples for using ArchiPy helper interceptors.
---

# Interceptor Examples

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
- [Helper Examples](index.md) - Overview of all helper examples
