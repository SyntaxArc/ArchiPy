---
title: Interceptor Tutorials
description: Practical tutorials for ArchiPy gRPC interceptors and OpenTelemetry contrib wiring.
---

# Interceptor Tutorials

This page covers ArchiPy's remaining interceptors (gRPC exception handling and rate limiting)
and how OpenTelemetry is wired through AppUtils rather than custom metric/trace interceptors.

## OpenTelemetry (replaces metric/trace interceptors)

FastAPI metric middleware and gRPC metric/trace interceptors were removed in 5.0.0. Traces and
metrics come from OpenTelemetry contrib instrumentors configured via `BaseConfig.OTEL`.

| Stack       | Wiring                                                                                                |
|-------------|-------------------------------------------------------------------------------------------------------|
| FastAPI     | `AppUtils.create_fastapi_app` → `FastAPIUtils.build_otel_telemetry_config` (native FastAPI telemetry) |
| gRPC        | `AppUtils.create_grpc_app` / `create_async_grpc_app` → contrib server interceptor at index 0          |
| Client gRPC | `OtelUtils.grpc_client_interceptors()` / `async_grpc_client_interceptors()`                           |

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
app = AppUtils.create_fastapi_app(config)
grpc_server = AppUtils.create_grpc_app(config)
logger.info("Apps created with OTel auto-instrumentation")
```

Install `archipy[otel,fastapi]` and/or `archipy[otel-grpc]` as needed. Full config and decorator
reference: [Observability](../observability.md).

## gRPC Interceptors

### Exception Interceptor

`GrpcExceptionInterceptor` converts domain errors to gRPC status codes and calls
`archipy.helpers.errors.capture_exception` (records on the current OTel span). `GrpcExceptionInterceptor()` creates
the sync interceptor and `GrpcExceptionInterceptor(aio=True)` the one for `grpc.aio` servers.
`AppUtils.create_grpc_app` / `create_async_grpc_app` always register the matching interceptor.

```python
import logging
from concurrent import futures

import grpc

from archipy.helpers.errors.grpc import GrpcExceptionInterceptor
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)


def create_grpc_server(max_workers: int = 10) -> grpc.Server:
    """Create a gRPC server with the exception interceptor.

    Args:
        max_workers: Maximum worker threads for the server.

    Returns:
        Configured gRPC server instance.

    Raises:
        InternalError: If server creation fails.
    """
    try:
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=max_workers),
            interceptors=[GrpcExceptionInterceptor()],
        )
        logger.info("gRPC server created with exception interceptor")
        return server
    except OSError as e:
        raise InternalError(additional_data={"detail": "Failed to create gRPC server"}) from e
```

A Pydantic `ValidationError` that escapes a handler is reported as `INVALID_ARGUMENT` with the field errors, the
gRPC counterpart of the HTTP 422 that the FastAPI handlers return. `request_validation()` marks the code that parses
the **client's request** explicitly:

```python
from archipy.helpers.errors.grpc import request_validation


def Create(self, request, context):
    with request_validation():
        dto = CreateUserDTO(name=request.name, email=request.email)
    ...
```

A `ValidationError` raised while building DTOs from database rows or upstream responses is a server fault. To report
every `ValidationError` as `INTERNAL` instead (the 5.10 to 5.14 default), pass
`validation_errors_as_internal=True` to `GrpcExceptionInterceptor` or to `AppUtils.create_grpc_app` /
`create_async_grpc_app`.

To abort a call yourself with a `BaseError`, use `abort_grpc(error, context)` from `archipy.helpers.errors.grpc`. It
detects a sync or `grpc.aio` context; on an async context write `await abort_grpc(error, context)`.

### Rate Limiting Interceptor

Per-RPC gRPC rate limits use two pieces:

1. **`grpc_rate_limit`** — declares limits on servicer methods (see
   [Decorator Tutorials — gRPC Rate Limit](decorators.md#grpc-rate-limit-decorator))
2. **`GrpcServerRateLimitInterceptor` / `AsyncGrpcServerRateLimitInterceptor`** — enforces decorated limits via Redis
   `INCREX`

Install the required extras:

```bash
uv add "archipy[redis,grpc]"
```

> **Note:** Redis **8.8+** is required. The interceptor depends on the `INCREX` command.

Enable automatic registration:

```bash
GRPC_RATE_LIMIT__IS_ENABLED=true
```

With `IS_ENABLED`, `AppUtils.create_grpc_app` / `create_async_grpc_app` append the matching
interceptor. Per-RPC limits still come only from `grpc_rate_limit`.

**Sync:**

```python
from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import grpc_rate_limit
from archipy.helpers.utils.app_utils import AppUtils


class MySyncServiceServicer(pb2_grpc.MyServiceServicer):
    @grpc_rate_limit(calls_count=100, minutes=1)
    def Cheap(self, request, context):
        return pb2.CheapResponse()

    @grpc_rate_limit(calls_count=10, seconds=1)
    @grpc_rate_limit(calls_count=1000, days=1)
    def Expensive(self, request, context):
        return pb2.ExpensiveResponse()


config = BaseConfig.global_config()
server = AppUtils.create_grpc_app(config)
```

**Async:**

```python
from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import grpc_rate_limit
from archipy.helpers.utils.app_utils import AppUtils


class MyAsyncServiceServicer(pb2_grpc.MyServiceServicer):
    @grpc_rate_limit(calls_count=100, minutes=1)
    async def Cheap(self, request, context):
        return pb2.CheapResponse()

    @grpc_rate_limit(calls_count=10, seconds=1)
    @grpc_rate_limit(calls_count=1000, days=1)
    async def Expensive(self, request, context):
        return pb2.ExpensiveResponse()


config = BaseConfig.global_config()
server = AppUtils.create_async_grpc_app(config)
```

Manual registration (when `IS_ENABLED` is false) via `customized_interceptors` is still supported;
pass `GrpcServerRateLimitInterceptor` or `AsyncGrpcServerRateLimitInterceptor` explicitly.

#### Configuration

```bash
GRPC_RATE_LIMIT__IS_ENABLED=true
GRPC_RATE_LIMIT__FAIL_CLOSED=true
GRPC_RATE_LIMIT__IDENTITY_FROM_ACCESS_TOKEN=true
```

#### Client identification

By default the interceptor buckets authenticated callers by verified JWT access token `sub` from
gRPC invocation metadata (`authorization: Bearer ...`). Missing or invalid tokens fall back to
`context.peer()` (for example `ipv4:1.2.3.4:5678`).

> **Warning:** `context.peer()` reflects the immediate TCP peer. Behind an L7 proxy that
> reconnects upstream, the peer is often the proxy address. Pass `trusted_proxy_hosts` (the proxy
> addresses) to the interceptor to take the client address from `x-forwarded-for`, or pass
> `identifier_fn` when you need a custom server-resolved identity. `x-forwarded-for` is only read
> when the direct peer is a trusted proxy, so callers cannot spoof it.

If `identifier_fn` raises, a fail-closed limiter aborts the call with `UNAVAILABLE`; a fail-open
limiter lets the call through without counting it.

A call rejected by one window gives its quota back to the windows it already passed, so a rejected
call does not eat into the burst budget.

When `GRPC_RATE_LIMIT__FAIL_CLOSED=true`, a rate limiter that cannot be created at startup stops
`AppUtils.create_grpc_app` / `create_async_grpc_app` instead of leaving the server unprotected.

`customized_interceptors` runs after the built-in interceptors, in the order of the sequence you pass
(a `list` or `tuple`; the iteration order of a `set` is arbitrary).

Undecorated servicer methods are never rate-limited. Stacked decorators add multiple windows; all
windows must pass before the RPC handler runs.

#### Counter store

By default the interceptors count in Redis through a `RedisAdapter` (or `AsyncRedisAdapter`) built from the global
config. Pass `store=` to count somewhere else, for example in memory in a test. A store only needs the two methods of
`RateLimitStore` (`AsyncRateLimitStore` for the async interceptor): `increx` and `pttl`, with the semantics of the Redis
`INCREX` and `PTTL` commands.

```python
from archipy.helpers.interceptors.grpc.rate_limit import GrpcServerRateLimitInterceptor

interceptor = GrpcServerRateLimitInterceptor(
    store=MyStore(),
    store_errors=(MyBackendError,),  # backend failures that follow GRPC_RATE_LIMIT__FAIL_CLOSED
)
```

Connection, OS and timeout errors always count as an unavailable backend. `store_errors` adds the error types your
store raises for the same case.

## FastAPI Rate Limiting

ArchiPy no longer ships a FastAPI rate-limit handler. Use the official
[`fastapi-redis-sdk`](https://github.com/redis/fastapi-redis-sdk):

```bash
uv add fastapi-redis-sdk
export REDIS_URL=redis://user:pass@host:6379/0
```

```python
from fastapi import Depends, FastAPI
from redis_fastapi import FastAPIRedis, rate_limit

app = FastAPI()
FastAPIRedis(app).lifespan().rate_limiting()


@app.get(
    "/search",
    dependencies=[
        Depends(rate_limit("10/second", scope="search:burst")),
        Depends(rate_limit("100/minute", scope="search:sustained")),
    ],
)
async def search() -> dict[str, str]:
    return {"results": []}
```

The gRPC rate-limit interceptor is unaffected.

## See Also

- [Observability](../observability.md) — OpenTelemetry config, AppUtils wiring, decorators
- [API Reference - Interceptors](../../api_reference/helpers/interceptors.md) — interceptor API docs
- [Redis Adapter - INCREX](../adapters/redis.md#increx-window-counter) — Redis `INCREX` window counter
- [Helper Tutorials](index.md) — overview of all helper tutorials
