---
title: Installation
description: Prerequisites, installation methods, and optional extras for ArchiPy.
---

# Installation

## Prerequisites

Before starting, ensure you have:

- **Python 3.14 or higher**

  Check your version with:

  ```bash
  python --version
  ```

  If needed, [download Python 3.14+](https://www.python.org/downloads/).

- **uv** (recommended package manager)

  uv is a fast Python package installer and resolver. Install it via
  the [official guide](https://docs.astral.sh/uv/getting-started/installation/).

> **Tip:** ArchiPy recommends **`uv`** — it is significantly faster than `pip` and provides better dependency
> resolution.

## Install ArchiPy

Install the core library:

=== "uv"

    ```bash
    uv add archipy
    ```

=== "pip"

    ```bash
    pip install archipy
    ```

With optional extras (install only what you need):

=== "uv"

    ```bash
    uv add "archipy[postgres,mysql,sqlalchemy,starrocks,redis,keycloak,minio,kafka]"
    ```

=== "pip"

    ```bash
    pip install "archipy[postgres,mysql,sqlalchemy,starrocks,redis,keycloak,minio,kafka]"
    ```

## Optional Dependencies

ArchiPy supports modular features through optional extras — install only what you need.

### Extras reference

Every extra declared in `[project.optional-dependencies]` of `pyproject.toml`. The **Mode** column tells
whether the extra targets sync code, async code, or both/neither. Extras marked **workspace** pull a separate
package (see [Adapter extras and workspace packages](#adapter-extras-and-workspace-packages)).

| Extra                           | Installs / purpose                                                                   | Mode        |
|---------------------------------|--------------------------------------------------------------------------------------|-------------|
| `archipy[postgres]`             | PostgreSQL adapter (`archipy-postgres`: psycopg 3 with pool); workspace              | Sync, async |
| `archipy[mysql]`                | MySQL adapter (`archipy-mysql[sync]`: pymysql); workspace                            | Sync        |
| `archipy[mysql-async]`          | MySQL adapter (`archipy-mysql[async]`: asyncmy); workspace                           | Async       |
| `archipy[aiosqlite]`            | SQLite adapter (`archipy-sqlite`: aiosqlite); workspace                              | Async       |
| `archipy[starrocks]`            | StarRocks adapter (`archipy-starrocks[sync]`: starrocks, pymysql); workspace         | Sync        |
| `archipy[starrocks-async]`      | StarRocks adapter (`archipy-starrocks[async]`: starrocks, asyncmy); workspace        | Async       |
| `archipy[sqlalchemy]`           | SQLAlchemy core                                                                      | Sync        |
| `archipy[sqlalchemy-async]`     | SQLAlchemy with asyncio support                                                      | Async       |
| `archipy[elasticsearch]`        | Elasticsearch adapter (`archipy-elasticsearch`); workspace                           | Sync        |
| `archipy[elasticsearch-async]`  | Elasticsearch adapter plus `elasticsearch[async]`; workspace                         | Async       |
| `archipy[scylladb]`             | ScyllaDB adapter (`archipy-scylladb`: scylla-driver); workspace                      | Sync, async |
| `archipy[redis]`                | Redis adapter (`archipy-redis`: redis with hiredis); workspace                       | Sync, async |
| `archipy[keycloak]`             | Keycloak authentication adapter (`archipy-keycloak`); workspace                      | Sync, async |
| `archipy[minio]`                | S3-compatible object storage adapter (`archipy-minio`: boto3); workspace             | Sync        |
| `archipy[kafka]`                | Kafka producer/consumer adapter (`archipy-kafka`: confluent-kafka); workspace        | Sync, async |
| `archipy[vault]`                | HashiCorp Vault adapter (`archipy-vault`: hvac); workspace                           | Sync        |
| `archipy[temporalio]`           | Temporal workflow adapter (`archipy-temporal`: temporalio); workspace                | Async       |
| `archipy[parsian-ipg]`          | Parsian payment gateway (`archipy-parsian-ipg[sync]`: zeep, requests); workspace     | Sync        |
| `archipy[parsian-ipg-async]`    | Parsian payment gateway (`archipy-parsian-ipg[async]`: zeep, httpx2); workspace      | Async       |
| `archipy[saman-ipg]`            | Saman payment gateway (`archipy-saman-ipg`: httpx2); workspace                       | Sync, async |
| `archipy[fastapi]`              | FastAPI integration with middleware and utilities                                    | Async       |
| `archipy[grpc]`                 | gRPC, health checking and protobuf for interceptors                                  | Sync, async |
| `archipy[pydantic-ai]`          | Pydantic AI (`pydantic-ai-slim`) agent integration                                   | Async       |
| `archipy[otel]`                 | OpenTelemetry SDK, OTLP and Prometheus exporters, httpx/requests/threading/system metrics | Sync, async |
| `archipy[otel-grpc]`            | `otel` plus gRPC server/client instrumentation                                       | Sync, async |
| `archipy[otel-sqlalchemy]`      | `otel` plus SQLAlchemy instrumentation                                               | Sync, async |
| `archipy[otel-redis]`           | `otel` plus Redis instrumentation                                                    | Sync, async |
| `archipy[otel-kafka]`           | `otel` plus Confluent Kafka instrumentation                                          | Sync        |
| `archipy[otel-scylladb]`        | `otel` plus Cassandra/ScyllaDB instrumentation                                       | Sync, async |
| `archipy[otel-minio]`           | `otel` plus botocore (MinIO/S3) instrumentation                                      | Sync        |
| `archipy[otel-pydantic-ai]`     | `otel` plus `pydantic-ai`: agent, model and tool spans and token metrics             | Async       |
| `archipy[jwt]`                  | JSON Web Token utilities (PyJWT)                                                     | Sync        |
| `archipy[scheduler]`            | Task scheduling (APScheduler)                                                        | Sync, async |
| `archipy[cache]`                | TTL and async caching utilities (cachetools, async-lru)                              | Sync, async |
| `archipy[dependency-injection]` | Dependency injector support                                                          | Sync, async |
| `archipy[fakeredis]`            | In-memory Redis fake for tests                                                       | Sync, async |
| `archipy[testcontainers]`       | Testcontainers (Elasticsearch, MinIO, MySQL, Vault modules)                          | Sync        |
| `archipy[behave]`               | Behave BDD testing framework                                                         | Sync        |

> **Note:** Combine extras with commas, for example `archipy[otel,fastapi]` adds FastAPI auto-instrumentation.

> **Note:** Enable observability with `OTEL__IS_ENABLED=true` and install the matching `otel-*`
> extras for each stack you use. See [Observability](../tutorials/observability.md).
>
> **Note:** ArchiPy’s HTTP clients (for example payment IPG adapters) use **httpx2**. The
> `otel` extra instruments **httpx** and **requests**, not httpx2 — outbound httpx2 calls are a
> known auto-instrumentation gap.

### Adapter extras and workspace packages

Most adapter extras do not carry the adapter code inside the `archipy` wheel. Each one pulls a separate
workspace package that is published to PyPI on its own. For example, `archipy[redis]` installs `archipy-redis`,
and `archipy[postgres]` installs `archipy-postgres`.

- **Pinned versions:** the publish flow pins every `archipy-*` package in the extras to the core `archipy`
  version, so an extra always installs a matching release (the `==0.1.0` pins in the repository are placeholders).
- **Sources:** each package lives in its own directory under
  [`packages/`](https://github.com/SyntaxArc/ArchiPy/tree/master/packages) (for example `packages/redis/`).
- **Imports:** the import path does not change. Adapters are still imported from `archipy.adapters.*`.
- **Sync/async variants:** some packages split their dependencies into `sync` and `async` extras, for example
  `archipy[mysql]` installs `archipy-mysql[sync]` and `archipy[mysql-async]` installs `archipy-mysql[async]`.

## Troubleshooting

If issues arise, verify:

1. Python version is 3.14+
2. `uv` is updated (`uv self update`)
3. Build tools are available (UV handles this automatically)
4. Database-specific dependencies are installed if using database adapters

> **Warning:** ArchiPy uses `X | Y` union syntax, lowercase generics (`list[str]`), and other modern features that
> require Python 3.14 or later. Using an older Python will result in `SyntaxError` at import time.

> **Tip:** For the best development experience, use an IDE that supports Python type hints, such as PyCharm or VS Code
> with the Python extension. The project uses modern Python type hints and benefits from IDE support for type checking
> and
> autocompletion.

## See Also

- [Get Started](../index.md) — overview of ArchiPy and a quick example
- [Concepts](concepts.md) — Clean Architecture layers and design philosophy
- [Tutorials](../tutorials/index.md) — complete guides for every adapter and helper
