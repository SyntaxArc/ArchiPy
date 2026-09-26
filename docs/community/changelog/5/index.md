---
title: "5.x Changelog"
description: "Release history for ArchiPy 5.x series"
---

# 5.x Changelog

[↑ All versions](../index.md)


| Version           | Date       | Summary                                                                              |
|-------------------|------------|--------------------------------------------------------------------------------------|
| [5.5.0](5.5.0.md) | 2026-09-26 | httpx2 OTel auto-instrumentation; drop `otel-elasticsearch` extra; `JsonValue` RediSearch payloads |
| [5.4.1](5.4.1.md) | 2026-09-20 | Raise extras floors to lock; Redis range BDD FLAT; Keycloak 26.7.4 and ES 9.5.4 |
| [5.4.0](5.4.0.md) | 2026-09-14 | Prometheus Pushgateway metrics exporter; scrape bind no longer kills traces/logs |
| [5.3.0](5.3.0.md) | 2026-09-14 | BaseConfig `APP_NAME` with OTEL / FastAPI / Auth / Temporal identity sync            |
| [5.2.4](5.2.4.md) | 2026-09-13 | MySQL session manager 3.14 DI wire NameError; Keycloak userinfo cache maxsize 200    |
| [5.2.3](5.2.3.md) | 2026-09-13 | Python 3.14 `inspect.signature` / DI wire NameError on TYPE_CHECKING annotations     |
| [5.2.2](5.2.2.md) | 2026-09-07 | Explicit W3C TraceContext propagator; async gRPC metrics and log↔trace BDD           |
| [5.2.1](5.2.1.md) | 2026-09-07 | Fix OTel BDD exporter config leak across scenarios                                   |
| [5.2.0](5.2.0.md) | 2026-09-07 | OTel metrics pull scrape (`METRICS_EXPORTER`), gRPC RPC metrics, system-metrics flag |
| [5.1.0](5.1.0.md) | 2026-09-05 | Native FakeAsyncRedis mock; Cursor agent rule ownership; lockfile refresh            |
| [5.0.7](5.0.7.md) | 2026-09-01 | StarRocks real SQLAlchemy BEGIN/ROLLBACK; expand atomic BDD coverage                 |
| [5.0.6](5.0.6.md) | 2026-09-01 | Clear global Ruff ignores; narrow adapter exceptions; cap ES testcontainer heap      |
| [5.0.5](5.0.5.md) | 2026-08-31 | Raise dep floors to lock; bump Vault 2.0.4 and Keycloak 26.7.3 test images           |
| [5.0.4](5.0.4.md) | 2026-08-31 | OTel: atomic lifecycle, signal gates, FastAPI/gRPC wiring, fork/ownership safety     |
| [5.0.3](5.0.3.md) | 2026-08-31 | OTel: fix duplicate exceptions, metric cache, HTTP endpoints, distributed BDD        |
| [5.0.2](5.0.2.md) | 2026-08-31 | Docs: OTel initialization order before DI adapter construction                       |
| [5.0.1](5.0.1.md) | 2026-08-29 | OTel: threading context propagation and system metrics in default `otel` extra       |
| [5.0.0](5.0.0.md) | 2026-08-29 | OpenTelemetry migration: replace Sentry, Elastic APM, and Prometheus with OTel/OTLP |
