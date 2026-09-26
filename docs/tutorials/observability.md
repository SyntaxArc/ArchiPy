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
    uv add "archipy[otel,otel-sqlalchemy,otel-redis,otel-kafka,otel-scylladb,otel-minio]"
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
OTEL__METRICS_EXPORTER=otlp
OTEL__METRICS_PULL_HOST=0.0.0.0
OTEL__METRICS_PULL_PORT=8200
OTEL__SYSTEM_METRICS_ENABLED=true
OTEL__LOGS_ENABLED=true
OTEL__LOGS_EXPORTER=console
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
| `OTLP_ENDPOINT`           | `http://localhost:4317`     | Default OTLP collector URL                       |
| `TRACES_ENDPOINT`         | `None`                      | Optional per-signal OTLP traces URL override     |
| `METRICS_ENDPOINT`        | `None`                      | Optional per-signal OTLP metrics URL override    |
| `LOGS_ENDPOINT`           | `None`                      | Optional per-signal OTLP logs URL override       |
| `PROTOCOL`                | `grpc`                      | `grpc` or `http/protobuf`                        |
| `TRACES_SAMPLE_RATIO`     | `0.1`                       | Parent-based trace ID ratio sampler              |
| `METRIC_EXPORT_INTERVAL_MS` | `60000`                   | Periodic OTLP metric export interval             |
| `METRICS_EXPORTER`        | `otlp`                      | Unique exporter: `otlp`, `pull`, or `pushgateway`|
| `METRICS_PULL_HOST`       | `0.0.0.0`                   | Pull scrape bind host (unauthenticated)          |
| `METRICS_PULL_PORT`       | `8200`                      | Pull scrape bind port (`/metrics`)               |
| `METRICS_PUSHGATEWAY_URL` | `None`                      | Pushgateway URL (required for `pushgateway`)     |
| `METRICS_PUSHGATEWAY_JOB` | `None`                      | Pushgateway job (defaults to `SERVICE_NAME`)     |
| `METRICS_PUSHGATEWAY_INTERVAL_SECONDS` | `60`           | Push interval when exporter is `pushgateway`     |
| `METRICS_PUSHGATEWAY_TIMEOUT_SECONDS` | `10`            | HTTP timeout for push/delete                     |
| `METRICS_PUSHGATEWAY_GROUPING_KEY` | `{}`               | Extra grouping labels (max 16 entries)           |
| `METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN` | `true`       | Delete grouping key on graceful shutdown         |
| `SYSTEM_METRICS_ENABLED`  | `true`                      | Process/system metrics instrumentor              |
| `LOGS_ENABLED`            | `true`                      | Enable log export when OTel is on                |
| `LOGS_EXPORTER`           | `console`                   | Unique logs exporter: `console` or `otlp`        |
| `FASTAPI_EXCLUDED_URLS`   | `None`                      | Comma-separated URL patterns skipped by FastAPI  |
| `RESOURCE_ATTRIBUTES`     | `{}`                        | Extra OTel resource attributes                   |
| `LOGS_LEVEL`              | `INFO`                      | Minimum level for the root-logger handler        |

### Metrics exporters

Exactly **one** metrics exporter when `METRICS_ENABLED` is true — set via
`METRICS_EXPORTER` (`otlp` | `pull` | `pushgateway`):

| Mode | `METRICS_EXPORTER` | Behavior |
|------|-------------------|----------|
| OTLP (default) | `otlp` | Periodic export to the OTLP collector |
| Pull scrape | `pull` | Dedicated HTTP server on `METRICS_PULL_HOST:METRICS_PULL_PORT/metrics` |
| Pushgateway | `pushgateway` | Daemon thread pushes Prometheus text to Pushgateway (no local scrape) |

`otlp` and `pushgateway` both *push* from the process, but to different wire
targets: OTLP collector vs Prometheus Pushgateway.

Pull scrape is a **standalone** process-wide HTTP server started from
`OtelUtils.init_otel_if_needed` — not a FastAPI `/metrics` route. Works for
FastAPI, gRPC, and workers. If the scrape port cannot bind, ArchiPy logs a
warning and keeps traces/logs/metrics providers running.

```bash
# Pull-only (no collector)
OTEL__METRICS_ENABLED=true
OTEL__METRICS_EXPORTER=pull
OTEL__METRICS_PULL_HOST=0.0.0.0
OTEL__METRICS_PULL_PORT=8200
```

```bash
# Prometheus Pushgateway (no local /metrics server)
OTEL__METRICS_ENABLED=true
OTEL__METRICS_EXPORTER=pushgateway
OTEL__METRICS_PUSHGATEWAY_URL=http://pushgateway.monitoring:9091
OTEL__METRICS_PUSHGATEWAY_JOB=my-service
OTEL__METRICS_PUSHGATEWAY_INTERVAL_SECONDS=60
```

`OtelUtils.metrics_registry()` returns the Prometheus `CollectorRegistry` when
exporter is `pull` or `pushgateway`.
### Logs exporters

Exactly **one** logs exporter when `LOGS_ENABLED` is true — set via
`LOGS_EXPORTER` (`console` | `otlp`):

| Mode | `LOGS_EXPORTER` | Behavior |
|------|-----------------|----------|
| Console (default) | `console` | INFO/DEBUG → stdout; WARNING+ → stderr |
| OTLP | `otlp` | Batch export to the OTLP collector |

```bash
# OTLP log export
OTEL__LOGS_ENABLED=true
OTEL__LOGS_EXPORTER=otlp
```

> **Warning (scrape security):** The pull scrape endpoint is unauthenticated.
> Default bind `0.0.0.0` is for cluster scrape. Prefer `127.0.0.1` plus a
> sidecar/proxy when the network is not locked down. Do not expose scrape on
> the public internet.

> **Warning (prefork):** The parent process holds the scrape port. With
> gunicorn `preload` + fork, workers cannot share one scrape port — use a
> unique port per worker or disable preload.

> **Note (HTTP endpoints):** With `PROTOCOL=http/protobuf`, each signal needs its own
> path (`/v1/traces`, `/v1/metrics`, `/v1/logs`). When `OTLP_ENDPOINT` has no path
> (e.g. `http://localhost:4318`), ArchiPy appends the correct `/v1/{signal}` suffix
> automatically. Set `TRACES_ENDPOINT` / `METRICS_ENDPOINT` / `LOGS_ENDPOINT` to
> override a single signal. gRPC mode uses one shared endpoint and needs no path.

> **Warning (logs cost):** When `LOGS_ENABLED=true`, a `LoggingHandler` is attached to
> the **root** logger at `LOGS_LEVEL`. With `LOGS_EXPORTER=otlp`, every matching
> record from every library (httpx, sqlalchemy, urllib3, …) is exported to OTLP —
> prefer `WARNING` in production. `console` (default) writes locally only.
> Records from `opentelemetry.*` loggers are filtered out to avoid exporter
> feedback loops.

> **Note (provider globals):** ArchiPy sets the global tracer/meter provider once
> (`_globals_set`). If another library already installed a global provider first,
> FastAPI/gRPC/Temporal interceptors (global) and ArchiPy decorators (owned
> provider) may emit to different backends — and ArchiPy OTLP/pull exporter
> configuration is ignored for an adopted `MeterProvider`. Initialize ArchiPy
> OTel early via `AppUtils` or `OtelUtils.init_otel_if_needed`.

> **Note (instrument names):** The OTel SDK lowercases instrument names
> (`TestMethod` → `testmethod`). Prefer lowercase dotted names in dashboards.
---

## Initialization Order

Call `OtelUtils.init_otel_if_needed(config)` at bootstrap — **before** your DI container builds
adapters — right after `BaseConfig.set_global(config)`. Init also installs the W3C TraceContext +
Baggage textmap propagator (`traceparent` / `tracestate` / `baggage`) so another library cannot
silently replace the global propagator first.

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
> requests, httpx, and httpx2 clients — their instrumentors patch at class level.

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

`AppUtils.create_grpc_app` / `create_async_grpc_app` install OpenTelemetry server
interceptors when OTel is enabled (requires `archipy[otel-grpc]` for traces):

- **Traces** — contrib `server_interceptor` / `aio_server_interceptor` when
  `TRACES_ENABLED`
- **Metrics** — ArchiPy `rpc.server.duration` histogram interceptor when
  `METRICS_ENABLED` (works in metrics-only mode; no handler decorators required)

Order becomes: OTel traces (if any) → OTel metrics (if any) → exception interceptor
→ rate-limit (if enabled) → custom interceptors.

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
packages (SQLAlchemy, Redis, Confluent Kafka, Cassandra, Botocore, httpx, httpx2,
requests, threading) when the matching `otel-*` extras are present. Instrumentors whose
target library is not installed (e.g. `httpx` when only `httpx2` is present) are skipped
silently. Elasticsearch needs no instrumentor — the `elasticsearch` client emits OTel
spans natively.
`SystemMetricsInstrumentor` runs only when `METRICS_ENABLED` and
`SYSTEM_METRICS_ENABLED` are both true.
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
`OtelUtils.status_for_exception` (`BaseError` with HTTP status below 500 leaves status
**UNSET** per the OTel spec for handled client errors; other exceptions become ERROR).

> **Warning (`capture_args`):** Prefer non-sensitive identifiers (`user_id`,
> `order_id`). Names matching a denylist (`password`, `token`, `secret`,
> `authorization`, `api_key`, …) are recorded as `***`. The denylist is
> substring-based and case-insensitive — still avoid capturing free-form blobs
> that may embed secrets.

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
attribute (`ok` / `error` / `cancelled` for async cancel). Duration histograms use
explicit second buckets and a description. `status` aligns with tracing:
`BaseError` with HTTP status below 500 records as `ok` (handled client error), not
`error`. No-op when OTel or `METRICS_ENABLED` is off.

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
| **Kafka aio**     | `otel-kafka` covers Confluent Kafka sync instrumentation; async Kafka paths may not be instrumented |
| **SMTP / email**  | No OpenTelemetry instrumentation for `smtplib` / the email adapter     |

---

## See Also

- [Interceptors](helpers/interceptors.md) — gRPC exception and rate-limit interceptors; OTel via AppUtils
- [Error Handling](error_handling.md) — recording exceptions on the current span
- [Temporal](adapters/temporal.md) — OTLP metrics and `TracingInterceptor`
- [Installation](../getting-started/installation.md) — `otel` and `otel-*` extras
- [Configuration Management](config_management.md) — nested env vars (`OTEL__*`)
