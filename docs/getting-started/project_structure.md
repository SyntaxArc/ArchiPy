---
title: Project Structure
description: Recommended folder layout for an ArchiPy application, with per-layer responsibilities and naming conventions.
---

# Project Structure

ArchiPy encourages a domain-driven folder layout where each domain (e.g. `user`, `order`) owns its own DTOs,
entities, errors, adapters, repository, and logic classes. This scales naturally as the project grows.

## Reference Layout

```
project-root/
├── my_app/                             # Application package
│   ├── configs/
│   │   ├── app_config.py               # AppConfig(BaseConfig) — set_global called here
│   │   └── containers.py               # DI container — wires adapters, repos, logic
│   │
│   ├── models/
│   │   ├── dtos/
│   │   │   ├── user/
│   │   │   │   ├── domain/             # Versioned DTOs that cross the service boundary
│   │   │   │   │   ├── v1/
│   │   │   │   │   │   └── user_dtos.py
│   │   │   │   │   └── v2/             # Breaking domain DTO changes live here
│   │   │   │   │       └── user_dtos.py
│   │   │   │   └── repository/         # Internal DTOs — never versioned
│   │   │   │       └── user_dtos.py
│   │   │   └── order/
│   │   │       ├── domain/
│   │   │       │   └── v1/
│   │   │       │       └── order_dtos.py
│   │   │       └── repository/
│   │   │           └── order_dtos.py
│   │   ├── entities/
│   │   │   ├── user.py                 # User(BaseEntity)
│   │   │   └── order.py
│   │   └── errors/
│   │       ├── user_errors.py          # UserAlreadyExistsError(AlreadyExistsError)
│   │       └── order_errors.py
│   │
│   ├── repositories/
│   │   ├── user/
│   │   │   ├── adapters/
│   │   │   │   ├── user_db_adapter.py   # Wraps PostgresSQLAlchemyAdapter
│   │   │   │   └── user_cache_adapter.py # Wraps RedisAdapter
│   │   │   └── user_repository.py
│   │   └── order/
│   │       ├── adapters/
│   │       │   ├── order_db_adapter.py
│   │       │   └── order_payment_adapter.py
│   │       └── order_repository.py
│   │
│   ├── logics/
│   │   ├── user/
│   │   │   ├── user_registration_logic.py  # @atomic — unit of work boundary
│   │   │   └── user_query_logic.py
│   │   └── order/
│   │       ├── order_creation_logic.py
│   │       └── order_payment_logic.py
│   │
│   └── services/
│       ├── user/
│       │   ├── v1/
│       │   │   └── user_service.py     # FastAPI router for API v1
│       │   └── v2/                     # Breaking API changes go here
│       │       └── user_service.py
│       └── order/
│           └── v1/
│               └── order_service.py
│
├── features/                           # BDD acceptance tests (behave)
│   ├── user_registration.feature
│   ├── steps/
│   │   └── user_steps.py
│   ├── scenario_context.py             # Per-scenario isolated storage (adapter, entities, etc.)
│   ├── scenario_context_pool_manager.py # Singleton pool — maps scenario ID → ScenarioContext
│   └── environment.py                  # behave hooks — container setup/teardown
│
└── manage.py                           # CLI entry point — click commands (run, migrate, etc.)
```

---

## Layer Responsibilities

### `configs/`

| File            | Responsibility                                                                                                                                                                      |
|-----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `app_config.py` | Defines `AppConfig(BaseConfig)`. Calling `BaseConfig.set_global(config)` at module level means any other file that imports this module triggers config bootstrapping automatically. |
| `containers.py` | Imports `app_config` (to trigger `set_global`), then wires all adapters, repositories, and logic classes as thread-safe singletons using `dependency-injector`.                     |

### `models/`

| Sub-folder                   | Contents                                                        | Rule                            |
|------------------------------|-----------------------------------------------------------------|---------------------------------|
| `dtos/{domain}/domain/v{n}/` | `{Operation}InputDTO`, `{Operation}OutputDTO`                   | Versioned — public API contract |
| `dtos/{domain}/repository/`  | `{Action}CommandDTO`, `{Action}QueryDTO`, `{Domain}ResponseDTO` | Internal — never versioned      |
| `entities/`                  | SQLAlchemy `BaseEntity` subclasses                              | Data structure only — no logic  |
| `errors/`                    | Domain-specific exceptions extending ArchiPy base errors        | Raise with `raise ... from e`   |

> **Tip:** DTO naming conventions:
>
> - **Domain input**: `UserRegistrationInputDTO` — data arriving from the client
> - **Domain output**: `UserRegistrationOutputDTO` — data returned to the client
> - **Repository command**: `CreateUserCommandDTO` — a write operation
> - **Repository query**: `GetUserByIdQueryDTO` — a read operation
> - **Repository response**: `UserResponseDTO` — result from an adapter or repository

### `repositories/`

Each domain repository owns its data access logic:

- `adapters/` — domain-specific wrappers around ArchiPy base adapters; own entity construction and query
  building
- `{domain}_repository.py` — orchestrates the adapters, handles cache-aside patterns, and maps results to
  response DTOs

### `logics/`

Logic classes are **pure business rules**. They:

- Accept domain DTOs as input; return domain DTOs as output
- Are framework-agnostic (no FastAPI/gRPC imports)
- Define the unit of work boundary via `@postgres_sqlalchemy_atomic_decorator`
- May call other logic classes within the same transaction (nested `@atomic` reuses the open session)
- Must never import or call repositories from a different domain

### `services/`

Services are thin FastAPI routers that:

- Validate and translate HTTP requests into domain input DTOs
- Call the appropriate logic class
- Map errors to HTTP status codes (404, 409, etc.)
- Return domain output DTOs as JSON responses

API versioning lives in the folder structure (`v1/`, `v2/`), not in the business logic.

### `features/`

BDD acceptance tests live at the **project root** in a `features/` directory, following the standard `behave` layout:

| Path                                        | Purpose                                                         |
|---------------------------------------------|-----------------------------------------------------------------|
| `features/*.feature`                        | Gherkin scenarios — the source of truth for behaviour           |
| `features/steps/`                           | Step definitions mapping Gherkin to Python                      |
| `features/scenario_context.py`              | Per-scenario storage: adapter, async_adapter, entities, db_file |
| `features/scenario_context_pool_manager.py` | Singleton pool mapping scenario ID → `ScenarioContext`          |
| `features/environment.py`                   | `behave` hooks — container setup and teardown                   |

`ScenarioContext` prevents cross-contamination between scenarios by giving each one its own isolated storage.
`ScenarioContextPoolManager` (a `Singleton`) creates or retrieves the context for a given scenario ID and disposes of it
after the scenario completes.

---

## Entry Point: `manage.py`

`manage.py` lives at the **project root** and exposes CLI commands via `click`:

```python
# manage.py
import click
import uvicorn

import configs.app_config  # noqa: F401 — triggers BaseConfig.set_global
from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils
from configs.containers import UserContainer
from services.user.v1.user_service import create_router as create_user_v1_router


def create_app():
    """Create and configure the FastAPI application."""
    user_container = UserContainer()
    app = AppUtils.create_fastapi_app()
    app.include_router(create_user_v1_router(user_container))
    return app


@click.group()
def cli():
    """Management commands for my_app."""


@cli.command()
@click.option("--host", default=None, show_default=True, help="Bind host (defaults to FAST_API.SERVE_HOST).")
@click.option("--port", default=None, type=int, show_default=True, help="Bind port (defaults to FAST_API.SERVE_PORT).")
@click.option("--reload/--no-reload", default=None, help="Enable auto-reload (defaults to FAST_API.RELOAD).")
def run(host: str | None, port: int | None, reload: bool | None) -> None:
    """Start the FastAPI development server."""
    config = BaseConfig.global_config()
    serve_host = host or config.FAST_API.SERVE_HOST
    serve_port = port or config.FAST_API.SERVE_PORT
    serve_reload = config.FAST_API.RELOAD if reload is None else reload
    uvicorn.run(
        "manage:create_app",
        factory=True,
        host=serve_host,
        port=serve_port,
        reload=serve_reload,
        proxy_headers=config.FASTAPI.PROXY_HEADERS,
        forwarded_allow_ips=config.FASTAPI.FORWARDED_ALLOW_IPS or "127.0.0.1",
    )


if __name__ == "__main__":
    cli()
```

Run the server with:

```bash
python manage.py run
python manage.py run --port 9000 --reload
```

> **Note:** `proxy_headers` and `forwarded_allow_ips` wire `FASTAPI.PROXY_HEADERS` and
> `FASTAPI.FORWARDED_ALLOW_IPS` into Uvicorn's `ProxyHeadersMiddleware`. When enabled, Uvicorn
> rewrites `request.client.host` from trusted `X-Forwarded-For` headers before your application
> runs. For HTTP rate limiting, use [fastapi-redis-sdk](https://github.com/redis/fastapi-redis-sdk)
> — see [Interceptors — FastAPI Rate Limiting](../tutorials/helpers/interceptors.md#fastapi-rate-limiting).

---

## See Also

- [Quickstart](quickstart.md) — five-minute getting-started example
- [Concepts](concepts.md) — four-layer architecture and import rules
- [Dependency Injection](../tutorials/dependency_injection.md) — container wiring in detail
- [Testing Strategy](../tutorials/testing_strategy.md) — BDD test layout with behave
- [Configuration Management](../tutorials/config_management.md) — environment-specific configs
