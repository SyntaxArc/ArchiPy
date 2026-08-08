---
title: Interceptor Tutorials
description: Practical tutorials for using ArchiPy helper interceptors.
---

# Interceptor Tutorials

This page demonstrates how to use ArchiPy's interceptors for cross-cutting concerns like tracing, metrics, and error
handling.

## Deprecations

The following APIs are **deprecated** and will be removed in a future major release. They are no longer
maintained and emit a runtime signal when used.

| Deprecated API                                                                            | Kind         | Runtime signal                   | Replacement                                   |
|-------------------------------------------------------------------------------------------|--------------|----------------------------------|-----------------------------------------------|
| `FastAPIRestRateLimitHandler`                                                             | class        | `DeprecationError` on instantiation | `rate_limit()` from `fastapi-redis-sdk`    |
| `extract_bearer_token` / `resolve_jwt_access_token_sub` (`fastapi.rate_limit.identifiers`) | functions    | `DeprecationError` on call       | Your own auth `Depends`                       |
| `FastAPIRateLimitConfig`                                                                  | config class | `DeprecationWarning` on instantiation | `fastapi-redis-sdk` + `REDIS_*` env vars |
| `BaseConfig.FASTAPI_RATE_LIMIT`                                                           | config field | —                                | `fastapi-redis-sdk` + `REDIS_*` env vars |
| `FASTAPI_RATE_LIMIT__*` environment variables                                             | env vars     | —                                | `REDIS_*` environment variables                |

**Not affected:** the gRPC rate-limit interceptor (`GrpcServerRateLimitInterceptor`,
`AsyncGrpcServerRateLimitInterceptor`) and `grpc_rate_limit_decorator` remain fully supported, as do
`GrpcRateLimitConfig`, `RateLimitUtils`, and `RateLimitWindowDTO`.

See [Migrating to `fastapi-redis-sdk`](#migrating-to-fastapi-redis-sdk) below for the step-by-step replacement.

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

### Rate Limiting Interceptor

Per-RPC gRPC rate limits use two pieces:

1. **`grpc_rate_limit_decorator`** — declares limits on servicer methods (see
   [Decorator Tutorials — gRPC Rate Limit](decorators.md#grpc-rate-limit-decorator))
2. **`GrpcServerRateLimitInterceptor` / `AsyncGrpcServerRateLimitInterceptor`** — enforces decorated limits via Redis
   `INCREX`

Limits use the Redis 8.8 `INCREX` command, the same atomic counter primitive as the FastAPI handler.

Install the required extras:

```bash
uv add "archipy[redis,grpc]"
```

> **Note:** Redis **8.8+** is required. The interceptor depends on the `INCREX` command.

Register the interceptor on the server (automatically via config or manually) and declare limits on individual RPC
methods.

Enable automatic registration:

```bash
GRPC_RATE_LIMIT__IS_ENABLED=true
```

With ``IS_ENABLED``, ``AppUtils.create_grpc_app`` / ``create_async_grpc_app`` append the matching interceptor (same
pattern as Prometheus metrics). Per-RPC limits still come only from ``grpc_rate_limit_decorator``.

**Sync:**

```python
from archipy.helpers.decorators import grpc_rate_limit_decorator
from archipy.helpers.utils.app_utils import AppUtils
from archipy.configs.base_config import BaseConfig


class MySyncServiceServicer(pb2_grpc.MyServiceServicer):
    @grpc_rate_limit_decorator(calls_count=100, minutes=1)
    def Cheap(self, request, context):
        return pb2.CheapResponse()

    @grpc_rate_limit_decorator(calls_count=10, seconds=1)
    @grpc_rate_limit_decorator(calls_count=1000, days=1)
    def Expensive(self, request, context):
        return pb2.ExpensiveResponse()


config = BaseConfig.global_config()
server = AppUtils.create_grpc_app(config)
```

**Async:**

```python
from archipy.helpers.decorators import grpc_rate_limit_decorator
from archipy.helpers.utils.app_utils import AppUtils
from archipy.configs.base_config import BaseConfig


class MyAsyncServiceServicer(pb2_grpc.MyServiceServicer):
    @grpc_rate_limit_decorator(calls_count=100, minutes=1)
    async def Cheap(self, request, context):
        return pb2.CheapResponse()

    @grpc_rate_limit_decorator(calls_count=10, seconds=1)
    @grpc_rate_limit_decorator(calls_count=1000, days=1)
    async def Expensive(self, request, context):
        return pb2.ExpensiveResponse()


config = BaseConfig.global_config()
server = AppUtils.create_async_grpc_app(config)
```

Manual registration (when ``IS_ENABLED`` is false) via ``customized_interceptors`` is still supported; pass
``GrpcServerRateLimitInterceptor`` or ``AsyncGrpcServerRateLimitInterceptor`` explicitly.

#### Configuration

Global defaults load from ``GRPC_RATE_LIMIT`` on ``BaseConfig.global_config()`` (env prefix
``GRPC_RATE_LIMIT__``). Per-RPC limits are set only on ``grpc_rate_limit_decorator``; the interceptor
constructor controls shared behavior such as Redis key prefix, fail-closed mode, and JWT identity.

```bash
GRPC_RATE_LIMIT__IS_ENABLED=true
GRPC_RATE_LIMIT__FAIL_CLOSED=true
GRPC_RATE_LIMIT__IDENTITY_FROM_ACCESS_TOKEN=true
```

#### Client identification

By default the interceptor buckets authenticated callers by verified JWT access token ``sub`` from
gRPC invocation metadata (`authorization: Bearer ...`). Missing or invalid tokens fall back to
``context.peer()`` (for example `ipv4:1.2.3.4:5678`).

> **Warning:** ``context.peer()`` reflects the immediate TCP peer. Behind an L7 proxy that
> reconnects upstream, the peer is often the proxy address. Pass ``identifier_fn`` to the interceptor
> when you need a custom server-resolved identity.

Undecorated servicer methods are never rate-limited. Stacked decorators add multiple windows; all
windows must pass before the RPC handler runs.

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

> **Deprecated:** The FastAPI rate-limit interceptor — `FastAPIRestRateLimitHandler`, its
> `FastAPIRateLimitConfig` settings, and the `fastapi.rate_limit.identifiers` helpers — is
> **deprecated** and will be removed in a future major release. Instantiating the handler or
> calling the identity helpers raises `DeprecationError`. It is no longer maintained.

The FastAPI rate limiter in ArchiPy has been superseded by the official
[`fastapi-redis-sdk`](https://github.com/redis/fastapi-redis-sdk), which provides the same
distributed per-client counters with `X-RateLimit-*` / `Retry-After` headers and a fluent rate
language (`"10/second"`). The gRPC rate-limit interceptor is **not** affected by this
deprecation.

#### Migrating to `fastapi-redis-sdk`

Install the SDK and configure Redis via environment variables (`REDIS_URL`, or `REDIS_HOST` /
`REDIS_PORT` / `REDIS_PASSWORD`):

```bash
uv add fastapi-redis-sdk
export REDIS_URL=redis://user:pass@host:6379/0
```

Replace the handler dependency with the `rate_limit()` dependency:

```python
from fastapi import Depends, FastAPI
from redis_fastapi import FastAPIRedis, rate_limit

app = FastAPI()
FastAPIRedis(app).lifespan().rate_limiting()


@app.get(
    "/search",
    dependencies=[
        Depends(rate_limit("10/second", scope="search:burst")),  # burst
        Depends(rate_limit("100/minute", scope="search:sustained")),  # sustained
    ],
)
async def search() -> dict[str, str]:
    return {"results": []}
```

Both limits count per client IP by default and a request must satisfy both; distinct `scope`
values keep the counters independent on the same route. When a limit is exceeded the request
gets a `429 Too Many Requests` with `Retry-After`, and every response carries
`X-RateLimit-Limit` / `-Remaining` / `-Reset`. Counters live in Redis, so limits hold across
every worker and pod. `fastapi-redis-sdk` requires Redis **7.4+** (no `INCREX` 8.8 dependency)
and supports Python 3.10–3.14 with FastAPI 0.115+.

| ArchiPy (deprecated)                            | `fastapi-redis-sdk`                          |
|-------------------------------------------------|----------------------------------------------|
| `Depends(FastAPIRestRateLimitHandler(calls_count=100, minutes=1))` | `Depends(rate_limit("100/minute"))` |
| `additional_windows` stacked tiers              | stack multiple `rate_limit()` dependencies   |
| `FASTAPI_RATE_LIMIT__*` environment variables   | `REDIS_*` environment variables              |

#### Client identification

`FastAPIRestRateLimitHandler` previously resolved the client identity from trusted proxy
headers (`CF-Connecting-IP`, `True-Client-IP`, `Forwarded`, `X-Forwarded-For`, `X-Real-IP`)
only when the immediate peer matched `FASTAPI_RATE_LIMIT.TRUSTED_PROXY_IPS` /
`FASTAPI.FORWARDED_ALLOW_IPS`. This behavior is deprecated along with the handler; in
`fastapi-redis-sdk` per-client counters default to the client IP. For per-user quotas, identify
the caller in your auth `Depends` and use a distinct `scope` per user instead.

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
