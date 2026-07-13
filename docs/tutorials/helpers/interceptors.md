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

#### Configuration

Global defaults load from ``FASTAPI_RATE_LIMIT`` on ``BaseConfig.global_config()`` (env prefix
``FASTAPI_RATE_LIMIT__``). Per-route limits still pass ``calls_count`` and the time window to the
handler constructor; optional kwargs override config fields for that handler instance only.

```bash
# .env — trusted proxies fall back to FASTAPI__FORWARDED_ALLOW_IPS when unset
FASTAPI_RATE_LIMIT__FAIL_CLOSED=true
FASTAPI_RATE_LIMIT__REJECT_UNKNOWN_CLIENT=true
FASTAPI_RATE_LIMIT__RATE_LIMIT_HEADERS=true
```

```python
from archipy.configs.base_config import BaseConfig

config = BaseConfig.global_config()
config.FASTAPI_RATE_LIMIT.TRUSTED_PROXY_IPS = ["10.0.0.0/8"]
```

#### How it works

On each request the handler:

1. Builds a Redis key from the client identifier, path, HTTP method, and optional query parameters.
2. Calls `INCREX` with `ubound=calls_count`, `saturate=True`, `enx=True`, and a millisecond window (`px`).
3. Allows the request when the increment is applied; otherwise raises HTTP **429 Too Many Requests** with
   `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining` headers.

`enx=True` sets the window expiry only when the key is first created, so subsequent requests within the window
preserve the original TTL.

#### Client identification

Forwarded headers (`CF-Connecting-IP`, `True-Client-IP`, `Forwarded`, `X-Forwarded-For`) are
honored **only** when the immediate peer (`request.client.host`) matches
`FASTAPI_RATE_LIMIT.TRUSTED_PROXY_IPS`, `FASTAPI.FORWARDED_ALLOW_IPS`, or an explicit
`trusted_proxy_ips` constructor override. Without trusted proxies, only `request.client.host` is
used, which prevents clients from spoofing their identity.

When trusted proxies are configured:

1. `CF-Connecting-IP`
2. `True-Client-IP`
3. `Forwarded` (`for=` directives, recursive trusted-proxy walk)
4. `X-Forwarded-For` — all header fields are combined (RFC 9110), port suffixes stripped,
   then resolved with a recursive trusted-proxy walk (nginx `real_ip_recursive` semantics)
5. `X-Real-IP` — only when `X-Forwarded-For` is absent (avoids nginx mis-identifying the proxy as the client)

Private, loopback, link-local, and multicast addresses are rejected unless `allow_private_ips=True`.

The literal `"*"` in `FASTAPI_RATE_LIMIT.TRUSTED_PROXY_IPS` or `FASTAPI.FORWARDED_ALLOW_IPS` trusts
all peers (matches Uvicorn) but is unsafe for rate limiting — prefer explicit CIDRs.

When running behind Uvicorn with `proxy_headers=True` and `forwarded_allow_ips` configured (see
[Project Structure](../../getting-started/project_structure.md)), `request.client.host` is already
rewritten to the real client before the handler runs. The logic above remains defense-in-depth for
deployments that bypass Uvicorn's `ProxyHeadersMiddleware` (Hypercorn, custom ASGI servers, etc.).

> **Warning:** In Python 3.14, documentation-range IPs such as `203.0.113.x` are classified as private. When
> testing `X-Real-IP` behaviour locally, use globally routable addresses (for example `8.8.8.8`) and configure
> `trusted_proxy_ips` to include your test peer (for example `127.0.0.1`).

For authenticated APIs, rate limiting buckets by verified JWT access token ``sub`` by default
(``identity_from_access_token=True``). Anonymous or invalid tokens fall back to the secure client IP.

```python
handler = FastAPIRestRateLimitHandler(calls_count=50, minutes=1)
```

Disable JWT identity when you need IP-only buckets:

```python
handler = FastAPIRestRateLimitHandler(calls_count=50, minutes=1, identity_from_access_token=False)
```

Or set ``FASTAPI_RATE_LIMIT__IDENTITY_FROM_ACCESS_TOKEN=false`` in the environment.

For custom identity resolution (for example Keycloak ``request.state.user_info["sub"]`` after an auth
``Depends``), pass ``identifier_fn``:

```python
def current_user_id(request: Request) -> str:
    return str(request.state.user_info["sub"])


handler = FastAPIRestRateLimitHandler(calls_count=50, minutes=1, identifier_fn=current_user_id)
```

For manual JWT extraction in a custom ``identifier_fn``:

```python
from archipy.helpers.interceptors.fastapi.rate_limit.identifiers import resolve_jwt_access_token_sub


def jwt_or_ip_identifier(request: Request) -> str:
    return resolve_jwt_access_token_sub(request) or handler._extract_client_ip(request)
```

#### Multiple windows

Pass ``additional_windows`` to enforce burst and sustained tiers on the same endpoint. All windows
must pass; successful responses report the most constrained remaining quota in ``X-RateLimit-*``
headers.

```python
from archipy.models.dtos.rate_limit_window_dto import RateLimitWindowDTO

handler = FastAPIRestRateLimitHandler(
    calls_count=10,
    seconds=1,
    additional_windows=[RateLimitWindowDTO(calls_count=1000, window_ms=86_400_000)],
)
```

#### Per-query-parameter buckets

Pass ``query_params`` together with server-resolved identity (``identity_from_access_token=True`` by default,
or ``identifier_fn``). Values are hashed by default to keep Redis keys bounded:

```python
handler = FastAPIRestRateLimitHandler(
    calls_count=50,
    minutes=1,
    query_params={"action"},
)

@app.get("/api/action", dependencies=[Depends(handler)])
async def action() -> dict[str, str]:
    return {"status": "ok"}
```

> **Warning:** Do not rely on client-controlled query parameters alone to identify users. Use
> ``identity_from_access_token`` or ``identifier_fn`` for per-user quotas. Set
> ``require_identifier_for_query_params=False`` only when query parameters are not used for user identity.

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
