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
    uv add "archipy[postgres,sqlalchemy,starrocks,redis,keycloak,minio,kafka]"
    ```

=== "pip"

    ```bash
    pip install "archipy[postgres,sqlalchemy,starrocks,redis,keycloak,minio,kafka]"
    ```

## Optional Dependencies

ArchiPy supports modular features through optional extras — install only what you need:

| Category      | Extra                           | Description                                       |
|---------------|---------------------------------|---------------------------------------------------|
| Database      | `archipy[postgres]`             | PostgreSQL adapter with SQLAlchemy integration    |
| Database      | `archipy[aiosqlite]`            | SQLite async adapter with SQLAlchemy integration  |
| Database      | `archipy[starrocks]`            | StarRocks adapter with SQLAlchemy integration     |
| Database      | `archipy[starrocks-async]`      | StarRocks async adapter                           |
| Database      | `archipy[sqlalchemy]`           | SQLAlchemy core integration                       |
| Database      | `archipy[sqlalchemy-async]`     | SQLAlchemy async integration                      |
| Database      | `archipy[elasticsearch]`        | Elasticsearch integration                         |
| Database      | `archipy[elasticsearch-async]`  | Elasticsearch async integration                   |
| Database      | `archipy[scylladb]`             | ScyllaDB integration                              |
| Service       | `archipy[redis]`                | Redis caching and key-value storage               |
| Service       | `archipy[keycloak]`             | Authentication and authorization services         |
| Service       | `archipy[minio]`                | S3-compatible object storage                      |
| Service       | `archipy[kafka]`                | Message streaming and event processing            |
| Service       | `archipy[temporalio]`           | Temporal workflow engine                          |
| Service       | `archipy[parsian-ipg]`          | Payment gateway (Parsian)                         |
| Web           | `archipy[fastapi]`              | FastAPI integration with middleware and utilities |
| Web           | `archipy[grpc]`                 | gRPC integration with interceptors                |
| Observability | `archipy[prometheus]`           | Metrics and monitoring                            |
| Observability | `archipy[sentry]`               | Error tracking and monitoring                     |
| Observability | `archipy[elastic-apm]`          | Elastic APM tracing                               |
| Utilities     | `archipy[jwt]`                  | JSON Web Token utilities                          |
| Utilities     | `archipy[scheduler]`            | Task scheduling utilities                         |
| Utilities     | `archipy[cache]`                | TTL and async caching utilities                   |
| Utilities     | `archipy[dependency-injection]` | Dependency injector support                       |
| Testing       | `archipy[fakeredis]`            | In-memory Redis mock for testing                  |
| Testing       | `archipy[testcontainers]`       | Testcontainers integration                        |
| Testing       | `archipy[behave]`               | BDD testing framework                             |

## Troubleshooting

If issues arise, verify:

1. Python version is 3.14+
2. `uv` is updated (`uv self update`)
3. Build tools are available (UV handles this automatically)
4. Database-specific dependencies are installed if using database adapters

> **Warning:** ArchiPy uses `X | Y` union syntax, lowercase generics (`list[str]`), and other modern features that
> require Python 3.14 or later. Using an older Python will result in `SyntaxError` at import time.

> **Tip:** For the best development experience, use an IDE that supports Python type hints, such as PyCharm or VS Code
> with the Python extension. The project uses modern Python type hints and benefits from IDE support for type checking and
> autocompletion.

## See Also

- [Get Started](../index.md) — overview of ArchiPy and a quick example
- [Concepts](concepts.md) — Clean Architecture layers and design philosophy
- [Tutorials](../tutorials/index.md) — complete guides for every adapter and helper
