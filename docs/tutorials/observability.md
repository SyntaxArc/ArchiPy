---
title: Observability
description: Adding metrics and tracing to ArchiPy applications using Prometheus interceptors, Sentry, Elastic APM interceptors, and the @capture_transaction / @capture_span decorators.
---

# Observability

ArchiPy provides built-in observability through interceptors and configuration — no manual metric registration
or APM client wiring required. Enable the relevant extras and flip the config flags.

## Installation

=== "Prometheus"

    ```bash
    uv add "archipy[prometheus]"
    ```

=== "Sentry"

    ```bash
    uv add "archipy[sentry]"
    ```

=== "Elastic APM"

    ```bash
    uv add "archipy[elastic-apm]"
    ```

=== "All three"

    ```bash
    uv add "archipy[prometheus,sentry,elastic-apm]"
    ```

---

## Prometheus

### Configuration

Enable Prometheus via `BaseConfig`:

```bash
# .env
PROMETHEUS__IS_ENABLED=true
PROMETHEUS__SERVER_PORT=8200
```

```python
from archipy.configs.base_config import BaseConfig


class AppConfig(BaseConfig):
    """Application configuration with Prometheus enabled."""


config = AppConfig()
BaseConfig.set_global(config)
```

### Starting the Metrics Server

Use `start_prometheus_server_if_needed` to start the Prometheus HTTP scrape endpoint once at application
startup — it is safe to call multiple times (no-op if already running):

```python
import logging
from archipy.helpers.utils.prometheus_utils import start_prometheus_server_if_needed
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
if config.PROMETHEUS.IS_ENABLED:
    start_prometheus_server_if_needed(config.PROMETHEUS.SERVER_PORT)
    logger.info("Prometheus metrics available on port %d", config.PROMETHEUS.SERVER_PORT)
```

### FastAPI Metrics Middleware

`FastAPIMetricInterceptor` automatically tracks every HTTP request — response time (histogram) and active
request count (gauge) — with no additional code:

```python
import logging
from fastapi import FastAPI
from archipy.helpers.interceptors.fastapi.metric.interceptor import FastAPIMetricInterceptor
from archipy.helpers.utils.app_utils import AppUtils
from archipy.helpers.utils.prometheus_utils import start_prometheus_server_if_needed
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
app = AppUtils.create_fastapi_app()

if config.PROMETHEUS.IS_ENABLED:
    app.add_middleware(FastAPIMetricInterceptor)
    start_prometheus_server_if_needed(config.PROMETHEUS.SERVER_PORT)
    logger.info("Prometheus middleware registered")
```

The middleware records these metrics automatically for every request:

| Metric                          | Type      | Labels                                   |
|---------------------------------|-----------|------------------------------------------|
| `fastapi_response_time_seconds` | Histogram | `method`, `status_code`, `path_template` |
| `fastapi_active_requests`       | Gauge     | `method`, `path_template`                |

The middleware respects `config.PROMETHEUS.IS_ENABLED` — if disabled, requests pass through unchanged.

---

## gRPC Metrics

`GrpcServerMetricInterceptor` (sync) and `AsyncGrpcServerMetricInterceptor` (async) record response time
and active request counts per gRPC method:

```python
import logging
import grpc
from archipy.helpers.interceptors.grpc.metric.server_interceptor import (
    GrpcServerMetricInterceptor,
    AsyncGrpcServerMetricInterceptor,
)
from archipy.helpers.utils.prometheus_utils import start_prometheus_server_if_needed
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


def create_sync_grpc_server() -> grpc.Server:
    """Create a synchronous gRPC server with Prometheus metrics.

    Returns:
        A configured gRPC server instance.
    """
    config = BaseConfig.global_config()
    if config.PROMETHEUS.IS_ENABLED:
        start_prometheus_server_if_needed(config.PROMETHEUS.SERVER_PORT)

    server = grpc.server(
        thread_pool=None,
        interceptors=[GrpcServerMetricInterceptor()],
    )
    logger.info("Sync gRPC server created with Prometheus metrics interceptor")
    return server


async def create_async_grpc_server() -> grpc.aio.Server:
    """Create an async gRPC server with Prometheus metrics.

    Returns:
        A configured async gRPC server instance.
    """
    config = BaseConfig.global_config()
    if config.PROMETHEUS.IS_ENABLED:
        start_prometheus_server_if_needed(config.PROMETHEUS.SERVER_PORT)

    server = grpc.aio.server(interceptors=[AsyncGrpcServerMetricInterceptor()])
    logger.info("Async gRPC server created with Prometheus metrics interceptor")
    return server
```

Recorded metrics per gRPC method:

| Metric                       | Type      | Labels                                        |
|------------------------------|-----------|-----------------------------------------------|
| `grpc_response_time_seconds` | Histogram | `package`, `service`, `method`, `status_code` |
| `grpc_active_requests`       | Gauge     | `package`, `service`, `method`                |

---

## Distributed Tracing (Sentry + Elastic APM)

ArchiPy integrates Sentry and Elastic APM directly inside the gRPC trace interceptors. Both systems are
controlled exclusively through `BaseConfig` — no manual SDK initialisation required.

### Configuration

```bash
# .env — Sentry
SENTRY__IS_ENABLED=true
SENTRY__DSN=https://your-key@sentry.io/your-project-id
SENTRY__TRACES_SAMPLE_RATE=0.1
SENTRY__SAMPLE_RATE=1.0

# .env — Elastic APM
ELASTIC_APM__IS_ENABLED=true
ELASTIC_APM__SERVER_URL=https://apm.example.com:8200
ELASTIC_APM__SECRET_TOKEN=your-secret-token
ELASTIC_APM__SERVICE_NAME=my-grpc-service
ELASTIC_APM__TRANSACTION_SAMPLE_RATE=0.01
```

### gRPC Trace Interceptors

`GrpcServerTraceInterceptor` (sync) and `AsyncGrpcServerTraceInterceptor` (async) handle both Sentry and
Elastic APM automatically:

- If `config.SENTRY.IS_ENABLED` is true, a Sentry transaction is started for each gRPC call and marked
  `ok` or `internal_error` on completion.
- If `config.ELASTIC_APM.IS_ENABLED` is true, an Elastic APM transaction is started, with support for
  distributed trace parent propagation via gRPC metadata headers.
- If both are disabled, the interceptor is a zero-overhead pass-through.

```python
import logging
import grpc
from archipy.helpers.interceptors.grpc.trace.server_interceptor import (
    GrpcServerTraceInterceptor,
    AsyncGrpcServerTraceInterceptor,
)

logger = logging.getLogger(__name__)


def create_sync_grpc_server() -> grpc.Server:
    """Create a synchronous gRPC server with distributed tracing.

    Returns:
        A configured gRPC server instance.
    """
    server = grpc.server(
        thread_pool=None,
        interceptors=[GrpcServerTraceInterceptor()],
    )
    logger.info("Sync gRPC server created with trace interceptor")
    return server


async def create_async_grpc_server() -> grpc.aio.Server:
    """Create an async gRPC server with distributed tracing.

    Returns:
        A configured async gRPC server instance.
    """
    server = grpc.aio.server(interceptors=[AsyncGrpcServerTraceInterceptor()])
    logger.info("Async gRPC server created with trace interceptor")
    return server
```

### Combined Metrics + Tracing

Stack multiple interceptors to get both Prometheus metrics and APM tracing on every gRPC call:

```python
import logging
import grpc
from archipy.helpers.interceptors.grpc.metric.server_interceptor import GrpcServerMetricInterceptor
from archipy.helpers.interceptors.grpc.trace.server_interceptor import GrpcServerTraceInterceptor
from archipy.helpers.utils.prometheus_utils import start_prometheus_server_if_needed
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


def create_grpc_server() -> grpc.Server:
    """Create a gRPC server with Prometheus metrics and APM tracing.

    Returns:
        A configured gRPC server instance.
    """
    config = BaseConfig.global_config()
    if config.PROMETHEUS.IS_ENABLED:
        start_prometheus_server_if_needed(config.PROMETHEUS.SERVER_PORT)

    server = grpc.server(
        thread_pool=None,
        interceptors=[
            GrpcServerMetricInterceptor(),
            GrpcServerTraceInterceptor(),
        ],
    )
    logger.info("gRPC server ready with metrics + tracing interceptors")
    return server
```

!!! note "FastAPI + APM"
ArchiPy does not ship a FastAPI APM middleware. For FastAPI Elastic APM or Sentry integration,
use the official SDKs directly (`elasticapm.contrib.starlette.ElasticAPM` or
`sentry_sdk.integrations.fastapi.FastApiIntegration`). ArchiPy's APM interceptors cover gRPC only.

---

## Tracing Decorators (Pure Python)

For code that runs outside gRPC or FastAPI — background workers, scheduled tasks, business logic classes —
ArchiPy provides two decorators in `archipy.helpers.decorators.tracing`:

| Decorator              | Purpose                                                       |
|------------------------|---------------------------------------------------------------|
| `@capture_transaction` | Wraps an entire function as a top-level APM transaction       |
| `@capture_span`        | Wraps a function as a child span inside an active transaction |

Both decorators read `BaseConfig` at call time — no extra setup beyond the `.env` flags.

### Installation

```bash
uv add "archipy[sentry]"        # for Sentry tracing
uv add "archipy[elastic-apm]"   # for Elastic APM tracing
```

### `@capture_transaction`

Use on entry-point functions — the outermost call that defines the unit of work:

```python
from archipy.helpers.decorators.tracing import capture_transaction


@capture_transaction(name="process_order", op="business_logic")
def process_order(order_id: int) -> dict:
    """Process a single order.

    Args:
        order_id: The order to process.

    Returns:
        A summary of the processing result.
    """
    items = fetch_order_items(order_id)
    total = calculate_total(items)
    save_order_result(order_id, total)
    return {"order_id": order_id, "total": total}
```

When `SENTRY__IS_ENABLED=true`, a Sentry transaction named `process_order` is started and closed
automatically. When `ELASTIC_APM__IS_ENABLED=true`, an Elastic APM transaction is started similarly.
Both are marked `ok` on success or `internal_error` if the function raises.

### `@capture_span`

Use on inner functions to produce child spans within an active transaction. Spans give per-function
timing inside the parent transaction:

```python
from archipy.helpers.decorators.tracing import capture_transaction, capture_span


@capture_transaction(name="process_order", op="business_logic")
def process_order(order_id: int) -> dict:
    """Process a single order end-to-end."""
    items = fetch_order_items(order_id)
    total = calculate_total(items)
    save_order_result(order_id, total)
    return {"order_id": order_id, "total": total}


@capture_span(name="fetch_order_items", op="db")
def fetch_order_items(order_id: int) -> list:
    """Load order items from the database.

    Args:
        order_id: The order to load items for.

    Returns:
        List of order item dicts.
    """
    ...  # real DB call here


@capture_span(name="calculate_total", op="processing")
def calculate_total(items: list) -> float:
    """Sum item prices.

    Args:
        items: List of order item dicts.

    Returns:
        Total order value.
    """
    return sum(item["price"] for item in items)


@capture_span(name="save_order_result", op="db")
def save_order_result(order_id: int, total: float) -> None:
    """Persist the order total.

    Args:
        order_id: The order to update.
        total: Computed order total.
    """
    ...  # real DB call here
```

The resulting trace shows `process_order` as the transaction with three child spans —
`fetch_order_items`, `calculate_total`, and `save_order_result` — each with its own timing.

### Parameters

Both decorators accept the same parameters:

| Parameter     | Type          | Default       | Description                                              |
|---------------|---------------|---------------|----------------------------------------------------------|
| `name`        | `str \| None` | function name | Display name in the APM UI                               |
| `op`          | `str`         | `"function"`  | Operation category (`"db"`, `"http"`, `"processing"`, …) |
| `description` | `str \| None` | `None`        | Optional longer description shown in the APM UI          |

### Configuration Reference

```bash
# .env — Sentry
SENTRY__IS_ENABLED=true
SENTRY__DSN=https://your-key@sentry.io/your-project-id
SENTRY__TRACES_SAMPLE_RATE=0.1    # fraction of transactions sampled (0.0–1.0)
SENTRY__SAMPLE_RATE=1.0           # fraction of errors captured

# .env — Elastic APM
ELASTIC_APM__IS_ENABLED=true
ELASTIC_APM__SERVER_URL=https://apm.example.com:8200
ELASTIC_APM__SECRET_TOKEN=your-secret-token
ELASTIC_APM__SERVICE_NAME=my-service
ELASTIC_APM__TRANSACTION_SAMPLE_RATE=0.1
```

---

## See Also

- [Interceptors](helpers/interceptors.md) — FastAPI and gRPC interceptor reference (metrics, tracing, rate limiting)
- [Security](../community/security.md) — redacting sensitive data from error reports
- [Configuration Management](config_management.md) — loading APM and Prometheus settings from environment
- [Installation](../getting-started/installation.md) — `prometheus`, `sentry`, `elastic-apm` extras
