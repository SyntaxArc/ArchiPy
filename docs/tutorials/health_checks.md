---
title: Health Checks and Shutdown
description: What ArchiPy provides for health checks and graceful shutdown in FastAPI and gRPC services, and how to build probes on top.
---

# Health Checks and Shutdown

ArchiPy has **no ready-made liveness or readiness endpoint, no gRPC health servicer and no signal handler**. It does
provide the building blocks below; the probe endpoints are plain FastAPI or gRPC code you write.

## What ArchiPy provides

| Piece                                                    | Where                                | Use                                              |
|----------------------------------------------------------|--------------------------------------|--------------------------------------------------|
| `validate_healthiness()`                                 | Kafka producer adapters (sync, async)| Raises `UnavailableError` when Kafka is down     |
| `health_check()`                                         | ScyllaDB adapters (sync, async)      | Returns `{"status", "latency_ms", "error"?}`     |
| `HEALTH_CHECK_INTERVAL`                                  | `REDIS` config                       | Redis client keep-alive health check interval    |
| `lifespan` argument                                      | `AppUtils.create_fastapi_app`        | Startup and shutdown hooks; OTel flush on exit   |
| `UVICORN.TIMEOUT_GRACEFUL_SHUTDOWN`                      | Uvicorn config                       | Value for Uvicorn's graceful shutdown timeout    |
| `GRPC.SERVER_OPTIONS_CONFIG_LIST` grace                     | gRPC config                          | 5 s drain for connections past their max age     |
| `SKIP_METHODS` default                                   | gRPC rate-limit config               | Excludes `/grpc.health.v1.Health/*` from limits  |
| `TemporalWorkerManager.shutdown_all_workers()`           | Temporal adapter                     | Drains workers within `WORKER_GRACEFUL_SHUTDOWN_SECONDS` |

## Liveness and Readiness in FastAPI

Liveness answers "is the process up", so it checks nothing external. Readiness checks dependencies and returns 503 when
one is down. `UnavailableError` is the ArchiPy error for that; raising it from a route maps to an HTTP error through
the handlers `create_fastapi_app` installs.

```python
import logging

from fastapi import FastAPI

from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils
from archipy.models.errors import UnavailableError

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
app: FastAPI = AppUtils.create_fastapi_app(config)
producer = KafkaProducerAdapter(topic_name="events")


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    """Report that the process is running."""
    return {"status": "alive"}


@app.get("/health/ready")
def readiness() -> dict[str, str]:
    """Report readiness; raise UnavailableError when a dependency is down."""
    try:
        producer.validate_healthiness()
    except UnavailableError:
        logger.exception("Readiness check failed: Kafka unavailable")
        raise
    else:
        return {"status": "ready"}
```

`validate_healthiness()` of the sync producer blocks (a one-second metadata call), so the route above is a plain `def`
that FastAPI runs in a thread. With the async adapter, `await producer.validate_healthiness()` from an `async def`
route.

### ScyllaDB

`health_check()` never raises; it returns a status dict. Map it to your own response:

```python
import logging

from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.models.errors import UnavailableError

logger = logging.getLogger(__name__)


def check_scylladb(adapter: ScyllaDBAdapter) -> None:
    """Raise UnavailableError when ScyllaDB reports unhealthy."""
    health = adapter.health_check()
    if health["status"] != "healthy":
        logger.error("ScyllaDB unhealthy: %s", health.get("error"))
        raise UnavailableError(resource_type="ScyllaDB")
```

## gRPC

ArchiPy does not register the standard `grpc.health.v1` servicer. Add it yourself from `grpcio-health-checking` if your
orchestrator probes gRPC. When you do, ArchiPy already keeps `/grpc.health.v1.Health/Check` and
`/grpc.health.v1.Health/Watch` out of the rate limiter (`SKIP_METHODS`), so probes are never throttled.

## Graceful Shutdown

### FastAPI

Put cleanup in the `lifespan` you pass to `create_fastapi_app`. ArchiPy wraps it so OpenTelemetry force-flushes after
your code finishes; the OTel provider itself shuts down at process exit.

```python
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Open resources on startup and release them on shutdown."""
    logger.info("Starting up")
    try:
        yield
    finally:
        logger.info("Shutting down")


app = AppUtils.create_fastapi_app(BaseConfig.global_config(), lifespan=lifespan)
```

`UVICORN.TIMEOUT_GRACEFUL_SHUTDOWN` is only a config field; ArchiPy does not start Uvicorn for you. `AppUtils.uvicorn_config` passes it, with the rest of the `UVICORN` section, when you do:

```python
import uvicorn

from archipy.helpers.utils.app_utils import AppUtils

uvicorn.run("manage:create_app", factory=True, **AppUtils.uvicorn_config())
```

Uvicorn handles SIGTERM and SIGINT, stops accepting connections, waits up to that timeout, then runs the lifespan
shutdown.

### Temporal workers

Call `shutdown_all_workers()` in a `finally` block; it waits for in-flight work up to `WORKER_GRACEFUL_SHUTDOWN_SECONDS`
and raises `WorkerShutdownError` on timeout. See the [Temporal tutorial](adapters/temporal.md) for a full worker loop.

### gRPC

ArchiPy returns the server object from `AppUtils.create_grpc_app` and `create_async_grpc_app`. Stopping it and handling
signals is your code: call the server's own `stop(grace)` and wait for termination.

## Limits

- No built-in `/health` route, gRPC health servicer, signal handling or readiness registry.
- ArchiPy has no BDD scenarios for probes; only the adapter methods above have their own scenarios.

## See Also

- [Kafka Adapter](adapters/kafka.md) - `validate_healthiness` in context
- [ScyllaDB Adapter](adapters/scylladb.md) - `health_check` in context
- [Temporal Adapter](adapters/temporal.md) - Worker lifecycle
- [Observability](observability.md) - What flushes on shutdown
- [Error Handling](error_handling.md) - `UnavailableError` and friends
