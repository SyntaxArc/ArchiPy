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
