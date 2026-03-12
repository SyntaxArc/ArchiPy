---
title: Get Started
description: Introduction to ArchiPy and installation guide for the framework and its optional dependencies.
---

# Get Started

![ArchiPy Logo](assets/logo.jpg)

[![PyPI version](https://img.shields.io/pypi/v/archipy)](https://pypi.org/project/archipy/)
[![Python versions](https://img.shields.io/pypi/pyversions/archipy)](https://pypi.org/project/archipy/)
[![License](https://img.shields.io/pypi/l/archipy)](license.md)
[![Downloads](https://img.shields.io/pypi/dm/archipy)](https://pypi.org/project/archipy/)

ArchiPy is a Python framework that provides standardized, scalable building blocks for modern applications.
Built on Clean Architecture principles with Python 3.14+, it removes the boilerplate from wiring up databases,
caches, queues, and services — so you focus on business logic.

## Why Use ArchiPy?

- **Clean Architecture out of the box** — four strictly separated layers (configs, models, helpers, adapters) enforce
  dependency rules automatically
- **Type-safe everything** — configurations, entities, DTOs, and errors all use Pydantic or SQLAlchemy with full type
  hint support
- **Modular adapters** — install only what you need; each integration (PostgreSQL, Redis, Kafka, Keycloak…) is an
  optional extra
- **Testability first** — every adapter ships with a `ports.py` interface and a `mocks.py` test double, so unit tests
  never need a real database
- **One config system** — environment variables, `.env` files, and runtime overrides all flow through a single validated
  `BaseConfig`
- **Python 3.14+ native** — uses `X | Y` unions, `list[str]` generics, and modern syntax throughout; no legacy
  compatibility shims

## ArchiPy vs Others

| Feature                     | ArchiPy           | Plain FastAPI | Django        |
|-----------------------------|-------------------|---------------|---------------|
| Clean Architecture layers   | Built-in          | Manual        | Manual        |
| Type-safe config            | Pydantic Settings | Manual        | `settings.py` |
| Adapter mocks for testing   | Built-in          | Manual        | Manual        |
| Modular optional extras     | Yes               | N/A           | Via apps      |
| BDD testing support         | Built-in          | Manual        | Manual        |
| Multiple DB adapters        | Yes               | Manual        | ORM only      |
| gRPC + FastAPI interceptors | Built-in          | Manual        | No            |

## What ArchiPy Offers

ArchiPy is organized into four layers:

- **Configs** — Type-safe, environment-based configuration via `pydantic_settings.BaseSettings`
- **Models** — Entities (SQLAlchemy), DTOs (Pydantic), Errors, and Types — data structures only, no I/O
- **Helpers** — Pure utilities: decorators (retry, cache, atomic), interceptors (rate limiting, tracing), JWT, password,
  date utils
- **Adapters** — Plug-and-play integrations: PostgreSQL, SQLite, StarRocks, Redis, Kafka, Keycloak, MinIO, ScyllaDB,
  Elasticsearch, Temporal, Email, Payment Gateways

## Architecture Overview

Dependencies flow strictly inward — adapters may import from any inner layer, but inner layers never import outward:

```mermaid
graph LR
    Adapters -->|imports| Helpers
    Adapters -->|imports| Models
    Adapters -->|imports| Configs
    Helpers -->|imports| Models
    Helpers -->|imports| Configs
    Models -->|imports| Configs
```

See [Concepts](concepts.md) for the full architectural breakdown.

## Quick Example

A minimal ArchiPy setup — define a config, connect to Redis, and use a helper decorator:

```python
from archipy.configs.base_config import BaseConfig
from archipy.adapters.redis.adapters import RedisAdapter
from archipy.helpers.decorators.cache import ttl_cache

# Load config from environment variables or .env
config = BaseConfig()

# Create a Redis adapter using the config
redis = RedisAdapter(config.REDIS)


# Use a TTL cache decorator on any function
@ttl_cache(ttl=60)
def get_user(user_id: str) -> dict:
    return redis.get(f"user:{user_id}")
```

!!! tip "Full examples"
See the [Tutorials](examples/index.md) section for complete, runnable examples for every adapter and helper.

## Prerequisites

Before starting, ensure you have:

- **Python 3.14 or higher**

  Check your version with:

    ```bash
    python --version
    ```

  If needed, [download Python 3.14+](https://www.python.org/downloads/).

- **UV** (recommended package manager)

  UV is a fast Python package installer and resolver. Install it via
  the [official guide](https://docs.astral.sh/uv/getting-started/installation/).

!!! tip "Recommended Package Manager"
ArchiPy recommends **`uv`** — it is significantly faster than `pip` and provides better dependency resolution.

## Installation Methods

### Using UV

Add the core library:

```bash
uv add archipy
```

With optional dependencies:

```bash
uv add "archipy[postgres,sqlalchemy,starrocks,redis,keycloak,minio,kafka]"
```

### Using pip

Install the core library:

```bash
pip install archipy
```

With optional dependencies:

```bash
pip install archipy[postgres,sqlalchemy,starrocks,redis,keycloak,minio,kafka]
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

!!! tip "IDE Integration"
For the best development experience, use an IDE that supports Python type hints, such as PyCharm or VS Code with the
Python extension. The project uses modern Python type hints and benefits from IDE support for type checking and
autocompletion.

## Next Steps

- [Concepts](concepts.md) — understand the Clean Architecture layers and design philosophy
- [Tutorials](examples/index.md) — step-by-step guides for every adapter, helper, and feature
- [API Reference](api_reference/index.md) — full reference for all public classes and functions
- [Contributing](contributing.md) — set up a dev environment and contribute to ArchiPy
