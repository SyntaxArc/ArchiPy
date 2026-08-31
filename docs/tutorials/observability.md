---
title: Observability
description: OpenTelemetry traces, metrics, and logs in ArchiPy via BaseConfig.OTEL, AppUtils auto-instrumentation, and tracing/metrics decorators.
---

# Observability

ArchiPy uses **OpenTelemetry** for traces, metrics, and logs. Providers are built from
`BaseConfig.OTEL` (pydantic-settings) — not from `OTEL_*` environment-variable autoconfiguration.

Enable the relevant extras, set `OTEL__IS_ENABLED=true`, and call `AppUtils.create_fastapi_app` /
`create_grpc_app` (or use the tracing/metrics decorators in workers and business logic).

## Installation

| Extra                     | Purpose                                              |
|---------------------------|------------------------------------------------------|
| `archipy[otel]`           | SDK, OTLP exporters, httpx/requests, threading, system metrics |
| `archipy[otel-fastapi]`   | FastAPI auto-instrumentation                         |
| `archipy[otel-grpc]`      | gRPC server/client contrib interceptors              |
| `archipy[otel-sqlalchemy]`| SQLAlchemy instrumentation (covers Postgres/MySQL/SQLite via ORM) |
| `archipy[otel-redis]`     | Redis instrumentation                                |
| `archipy[otel-elasticsearch]` | Elasticsearch instrumentation                    |
| `archipy[otel-kafka]`     | Confluent Kafka instrumentation                      |
| `archipy[otel-scylladb]`  | Cassandra/ScyllaDB driver instrumentation            |
| `archipy[otel-minio]`     | Botocore (MinIO/S3) instrumentation                  |

=== "Core"

    ```bash
    uv add "archipy[otel]"
    ```

=== "FastAPI + gRPC"

    ```bash
    uv add "archipy[otel-fastapi,otel-grpc]"
    ```

=== "Adapters"

    ```bash
    uv add "archipy[otel,otel-sqlalchemy,otel-redis,otel-elasticsearch,otel-kafka,otel-scylladb,otel-minio]"
    ```

---

## Configuration

Configure OpenTelemetry through `BaseConfig.OTEL` (env prefix `OTEL__`):

```bash
# .env
OTEL__IS_ENABLED=true
OTEL__SERVICE_NAME=my-service
OTEL__OTLP_ENDPOINT=http://localhost:4317
OTEL__PROTOCOL=grpc
OTEL__TRACES_ENABLED=true
OTEL__METRICS_ENABLED=true
OTEL__LOGS_ENABLED=true
OTEL__TRACES_SAMPLE_RATIO=0.1
OTEL__FASTAPI_EXCLUDED_URLS=health,docs,redoc,openapi.json
```

```python
import logging

from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    """Application configuration with OpenTelemetry enabled."""


config = AppConfig()
BaseConfig.set_global(config)
logger.info("OTel enabled=%s endpoint=%s", config.OTEL.IS_ENABLED, config.OTEL.OTLP_ENDPOINT)
```

> **Note:** Do not rely on `OTEL_*` SDK autoconfiguration. ArchiPy builds
> `TracerProvider` / `MeterProvider` / `LoggerProvider` programmatically from
> `OpentelemetryConfig` only.

### Key fields

| Field                     | Default                     | Description                                      |
|---------------------------|-----------------------------|--------------------------------------------------|
| `IS_ENABLED`              | `false`                     | Master switch                                    |
| `OTLP_ENDPOINT`           | `http://localhost:4317`     | OTLP collector URL                               |
| `PROTOCOL`                | `grpc`                      | `grpc` or `http/protobuf`                        |
| `TRACES_SAMPLE_RATIO`     | `0.1`                       | Parent-based trace ID ratio sampler              |
| `METRIC_EXPORT_INTERVAL_MS` | `60000`                   | Periodic metric export interval                  |
| `FASTAPI_EXCLUDED_URLS`   | `None`                      | Comma-separated URL patterns skipped by FastAPI  |
| `RESOURCE_ATTRIBUTES`     | `{}`                        | Extra OTel resource attributes                   |

---

## Initialization Order

Call `OtelUtils.init_otel_if_needed(config)` at bootstrap — **before** your DI container builds
adapters — right after `BaseConfig.set_global(config)`:

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.otel_utils import OtelUtils

logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    """Application configuration with OpenTelemetry enabled."""


config = AppConfig()
BaseConfig.set_global(config)
OtelUtils.init_otel_if_needed(config)
logger.info("OTel initialized before adapter construction")

# Only now build the DI container / adapters
```

The call is idempotent and thread-safe — `AppUtils.create_fastapi_app` / `create_grpc_app`
invoke it again safely.

> **Warning:** If adapters are constructed before OTel initialization, some telemetry is lost
> permanently:
>
> - **SQLAlchemy** — engines created before `SQLAlchemyInstrumentor` runs are never traced
>   (only future `create_engine` calls are wrapped).
> - **Confluent Kafka** — producers/consumers instantiated before instrumentation stay unwrapped.
> - **Cassandra/ScyllaDB** — sessions created early miss span wrapping.
> - **Logs** — records emitted before init bypass the OTLP logging handler.
>
> Tracers and meters obtained via `OtelUtils.get_tracer` / `get_meter` before init recover
> automatically (the global proxy provider resolves once providers are set), as do Redis,
> requests, httpx, and Elasticsearch clients — their instrumentors patch at class level.

---

## Auto-instrumentation via AppUtils

### FastAPI

`AppUtils.create_fastapi_app` calls `FastAPIUtils.setup_otel` when `OTEL.IS_ENABLED` is true.
That initializes providers (idempotent) and instruments the app with
`FastAPIInstrumentor` (requires `archipy[otel-fastapi]`):

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
app = AppUtils.create_fastapi_app(config)
logger.info("FastAPI app created with OTel auto-instrumentation")
```

### gRPC

`AppUtils.create_grpc_app` / `create_async_grpc_app` insert the OpenTelemetry contrib server
interceptor at position 0 when OTel is enabled (requires `archipy[otel-grpc]`). Order becomes:
OTel → exception interceptor → rate-limit (if enabled) → custom interceptors.

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()
server = AppUtils.create_grpc_app(config)
logger.info("gRPC server created with OTel interceptor")
```

### Library instrumentors

On first `OtelUtils.init_otel_if_needed`, ArchiPy best-effort instruments installed contrib
packages (SQLAlchemy, Redis, Elasticsearch, Confluent Kafka, Cassandra, Botocore, httpx,
requests) when the matching `otel-*` extras are present.

### Client gRPC

For outbound gRPC clients, attach contrib interceptors explicitly:

```python
import logging

import grpc

from archipy.helpers.utils.otel_utils import OtelUtils

logger = logging.getLogger(__name__)

channel = grpc.intercept_channel(
    grpc.insecure_channel("localhost:50051"),
    *OtelUtils.grpc_client_interceptors(),
)
logger.info("gRPC client channel wrapped with OTel interceptors")
```

For async clients use `OtelUtils.async_grpc_client_interceptors()`.

---

## Tracing Decorators

For code outside FastAPI/gRPC — workers, schedulers, domain logic — use decorators from
`archipy.helpers.decorators`:

| Decorator            | Purpose                                      |
|----------------------|----------------------------------------------|
| `@trace_span`        | Sync child span                              |
| `@async_trace_span`  | Async child span                             |
| `@trace_root`        | Sync root span (entry point)                 |
| `@async_trace_root`  | Async root span                              |
| `@trace_class`       | Wrap public methods of a class with spans    |

```python
import logging

from archipy.helpers.decorators import async_trace_span, trace_root, trace_span

logger = logging.getLogger(__name__)


@trace_root(name="process_order")
def process_order(order_id: int) -> dict[str, int | float]:
    """Process a single order end-to-end.

    Args:
        order_id: The order to process.

    Returns:
        A summary of the processing result.
    """
    items = fetch_order_items(order_id)
    total = calculate_total(items)
    return {"order_id": order_id, "total": total}


@trace_span(name="fetch_order_items", capture_args=["order_id"])
def fetch_order_items(order_id: int) -> list[dict[str, float]]:
    """Load order items from the database.

    Args:
        order_id: The order to load items for.

    Returns:
        List of order item dicts.
    """
    logger.debug("Fetching items for order %d", order_id)
    return [{"price": 10.0}]


@trace_span(name="calculate_total")
def calculate_total(items: list[dict[str, float]]) -> float:
    """Sum item prices.

    Args:
        items: List of order item dicts.

    Returns:
        Total order value.
    """
    return sum(item["price"] for item in items)
```

Decorators no-op when `OTEL.IS_ENABLED` is false. On exceptions they set span status via
`OtelUtils.status_for_exception` (`BaseError` with HTTP status below 500 stays OK).

---

## Metrics Decorators

| Decorator                 | Purpose                                |
|---------------------------|----------------------------------------|
| `@measure_duration`       | Sync duration histogram                |
| `@async_measure_duration` | Async duration histogram               |
| `@count_calls`            | Sync call counter                      |
| `@async_count_calls`      | Async call counter                     |

```python
from archipy.helpers.decorators import count_calls, measure_duration


@measure_duration(attributes={"layer": "logic"})
@count_calls()
def process_payment(amount: float) -> None:
    """Charge a payment amount.

    Args:
        amount: Amount to charge.
    """
    ...
```

Instruments default to `{module}.{qualname}.duration` / `.calls` and record a `status`
attribute (`ok` / `error`). No-op when OTel or `METRICS_ENABLED` is off.

---

## Exception Capture

`BaseUtils.capture_exception` always logs locally. When OTel is enabled and a recording span
is active, it records the exception on the **current span** and sets span status — it does not
send to Sentry or Elastic APM:

```python
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import InternalError


try:
    raise InternalError()
except InternalError as exc:
    BaseUtils.capture_exception(exc)
    raise
```

---

## Temporal

Temporal metrics and traces reuse the global OTel config:

- **Metrics:** set `TEMPORAL__ENABLE_METRICS=true` **and** `OTEL__IS_ENABLED=true` with
  `OTEL__METRICS_ENABLED=true`. The adapter builds a Temporal `Runtime` with
  `OpenTelemetryConfig` pointing at `OTEL.OTLP_ENDPOINT` / `PROTOCOL` / `OTLP_HEADERS`.
- **Traces:** when `OTEL.IS_ENABLED` and `TRACES_ENABLED`, the Temporal client attaches
  `temporalio.contrib.opentelemetry.TracingInterceptor` after `OtelUtils.init_otel_if_needed`.

See [Temporal adapter](adapters/temporal.md) for a full example.

---

## Known Gaps

| Area              | Status                                                                 |
|-------------------|------------------------------------------------------------------------|
| **httpx2**        | Core HTTP client is `httpx2`; OTel ships `httpx`/`requests` instrumentors only — outbound httpx2 calls are not auto-instrumented |
| **Kafka aio**     | `otel-kafka` covers Confluent Kafka sync instrumentation; async Kafka paths may not be instrumented |
| **SMTP / email**  | No OpenTelemetry instrumentation for `smtplib` / the email adapter     |

---

## See Also

- [Interceptors](helpers/interceptors.md) — gRPC exception and rate-limit interceptors; OTel via AppUtils
- [Error Handling](error_handling.md) — recording exceptions on the current span
- [Temporal](adapters/temporal.md) — OTLP metrics and `TracingInterceptor`
- [Installation](../getting-started/installation.md) — `otel` and `otel-*` extras
- [Configuration Management](config_management.md) — nested env vars (`OTEL__*`)
