---
title: "5.x Changelog"
description: "Release history for ArchiPy 5.x series"
---

# 5.x Changelog

[↑ All versions](../index.md)

| Version           | Date       | Summary                                                                                                                          |
|-------------------|------------|----------------------------------------------------------------------------------------------------------------------------------|
| [5.19.0](5.19.0.md) | 2026-10-21 | Temporal activity spans carry messaging attributes via `MessagingOpenTelemetryPlugin`, replay-safe tracer and meter providers; **behavior:** Temporal tracing is skipped when a plain tracer provider was registered first |
| [5.18.3](5.18.3.md) | 2026-10-20 | Email adapter imports without `jinja2`; template rendering raises `ConfigurationError` with an install hint |
| [5.18.2](5.18.2.md) | 2026-10-20 | Async SQLAlchemy count cache reports a missing `async-lru` as `ConfigurationError` |
| [5.18.1](5.18.1.md) | 2026-10-20 | `archipy.helpers.decorators` imports without the `cache` extra; `ttl_cache` raises `ConfigurationError` with an install hint |
| [5.18.0](5.18.0.md) | 2026-10-20 | Database errors classified by driver code, `DatabaseResourceExhaustedError`, `DatabaseUnknownOutcomeError` and a `retryable` flag; **behavior:** serialization failures and deadlocks from adapter methods now raise specific errors |
| [5.17.0](5.17.0.md) | 2026-10-20 | In-memory SQLite rate-limit stores for gRPC, a `UnavailableError` for unreachable Kafka brokers, ScyllaDB CQL and PostgreSQL DSN port fixes, and a split of the SQLAlchemy, config and OTel modules |
| [5.16.1](5.16.1.md) | 2026-10-18 | No-op OTel meter gains `create_gauge` and observable instruments |
| [5.16.0](5.16.0.md) | 2026-10-18 | Several SQLAlchemy databases of one type, `archipy.adapters.keycloak.auth`, configurable OTel SDK with B3 and `OtelRuntime`; **breaking:** `otel-fastapi` extra removed and gRPC metrics follow the stable RPC conventions |
| [5.15.0](5.15.0.md) | 2026-10-14 | `archipy.helpers.errors` package for FastAPI and gRPC error handling, `GrpcExceptionInterceptor`, `abort_grpc` (**behavior:** gRPC `ValidationError` is now `INVALID_ARGUMENT`) |
| [5.14.0](5.14.0.md) | 2026-10-14 | Search output DTOs with `total_count_estimated`, `PAGINATION.MAX_ITEMS` config that drives the pagination limit and the default `COUNT_THRESHOLD` (**behavior:** PostgreSQL totals above it are estimated) |
| [5.13.0](5.13.0.md) | 2026-10-14 | Cheaper search totals: `count_threshold` with a PostgreSQL estimate, opt-in count cache, skipped `COUNT` on short pages |
| [5.12.1](5.12.1.md) | 2026-10-14 | Kafka consume spans end when the message is committed instead of at the next poll |
| [5.12.0](5.12.0.md) | 2026-10-14 | SQLAlchemy, Kafka and Redis search tracing fixed; Temporal metrics scrape endpoint; `email.send` span; MinIO non-recursive listing returns folders |
| [5.11.0](5.11.0.md) | 2026-10-13 | Security and correctness fixes across TOTP, passwords, JWT and the gRPC interceptors; **breaking:** minimum HMAC key length and handler `ValidationError` maps to `INTERNAL` |
| [5.10.0](5.10.0.md) | 2026-10-12 | Decorators drop the `_decorator` suffix and detect async (old names deprecated); **breaking:** email send errors, Keycloak expired tokens and Saman 5xx now raise specific errors |
| [5.9.0](5.9.0.md) | 2026-10-11 | Opt-in FastAPI OTel logs; gRPC `rpc.server.active_requests`; **breaking:** `rpc.server.duration` → `rpc.server.request.duration` |
| [5.8.0](5.8.0.md) | 2026-10-10 | Adapters ship as per-extra packages (`archipy[redis]` → `archipy-redis`); async extras no longer pull sync drivers               |
| [5.7.1](5.7.1.md) | 2026-10-03 | Test container images bumped; dependency floors raised to locked versions                                                        |
| [5.7.0](5.7.0.md) | 2026-10-03 | Keycloak impersonation tracking via `act` claim; `exchange_token`; constrained Pydantic types in DTOs                            |
| [5.6.0](5.6.0.md) | 2026-09-30 | Native FastAPI OTel telemetry; `setup_otel` removed; `FASTAPI_OPERATION_SPANS_ENABLED`                                           |
| [5.5.2](5.5.2.md) | 2026-09-29 | Async gRPC streaming RPCs work with OTel interceptors; mid-stream errors and stream metrics                                      |
| [5.5.1](5.5.1.md) | 2026-09-26 | Sync SQLAlchemy path works without greenlet; SQLite driver and in-memory pool fixes                                              |
| [5.5.0](5.5.0.md) | 2026-09-26 | httpx2 OTel auto-instrumentation; drop `otel-elasticsearch` extra; `JsonValue` RediSearch payloads                               |
| [5.4.1](5.4.1.md) | 2026-09-20 | Raise extras floors to lock; Redis range BDD FLAT; Keycloak 26.7.4 and ES 9.5.4                                                  |
| [5.4.0](5.4.0.md) | 2026-09-14 | Prometheus Pushgateway metrics exporter; scrape bind no longer kills traces/logs                                                 |
| [5.3.0](5.3.0.md) | 2026-09-14 | BaseConfig `APP_NAME` with OTEL / FastAPI / Auth / Temporal identity sync                                                        |
| [5.2.4](5.2.4.md) | 2026-09-13 | MySQL session manager 3.14 DI wire NameError; Keycloak userinfo cache maxsize 200                                                |
| [5.2.3](5.2.3.md) | 2026-09-13 | Python 3.14 `inspect.signature` / DI wire NameError on TYPE_CHECKING annotations                                                 |
| [5.2.2](5.2.2.md) | 2026-09-07 | Explicit W3C TraceContext propagator; async gRPC metrics and log↔trace BDD                                                       |
| [5.2.1](5.2.1.md) | 2026-09-07 | Fix OTel BDD exporter config leak across scenarios                                                                               |
| [5.2.0](5.2.0.md) | 2026-09-07 | OTel metrics pull scrape (`METRICS_EXPORTER`), gRPC RPC metrics, system-metrics flag                                             |
| [5.1.0](5.1.0.md) | 2026-09-05 | Native FakeAsyncRedis mock; Cursor agent rule ownership; lockfile refresh                                                        |
| [5.0.7](5.0.7.md) | 2026-09-01 | StarRocks real SQLAlchemy BEGIN/ROLLBACK; expand atomic BDD coverage                                                             |
| [5.0.6](5.0.6.md) | 2026-09-01 | Clear global Ruff ignores; narrow adapter exceptions; cap ES testcontainer heap                                                  |
| [5.0.5](5.0.5.md) | 2026-08-31 | Raise dep floors to lock; bump Vault 2.0.4 and Keycloak 26.7.3 test images                                                       |
| [5.0.4](5.0.4.md) | 2026-08-31 | OTel: atomic lifecycle, signal gates, FastAPI/gRPC wiring, fork/ownership safety                                                 |
| [5.0.3](5.0.3.md) | 2026-08-31 | OTel: fix duplicate exceptions, metric cache, HTTP endpoints, distributed BDD                                                    |
| [5.0.2](5.0.2.md) | 2026-08-31 | Docs: OTel initialization order before DI adapter construction                                                                   |
| [5.0.1](5.0.1.md) | 2026-08-29 | OTel: threading context propagation and system metrics in default `otel` extra                                                   |
| [5.0.0](5.0.0.md) | 2026-08-29 | OpenTelemetry migration: replace Sentry, Elastic APM, and Prometheus with OTel/OTLP                                              |
