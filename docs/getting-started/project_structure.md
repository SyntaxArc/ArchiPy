---
title: Project Structure
description: Recommended folder layout for an ArchiPy application, with per-layer responsibilities and naming conventions.
---

# Project Structure

ArchiPy encourages a domain-driven folder layout where each domain (e.g. `user`, `order`) owns its own DTOs,
entities, errors, adapters, repository, and logic classes. This scales naturally as the project grows.

## Reference Layout

```
my_app/
├── configs/
│   ├── app_config.py               # AppConfig(BaseConfig) — set_global called here
│   └── containers.py               # DI container — wires adapters, repos, logic
│
├── models/
│   ├── dtos/
│   │   ├── user/
│   │   │   ├── domain/             # Versioned DTOs that cross the service boundary
│   │   │   │   ├── v1/
│   │   │   │   │   └── user_dtos.py
│   │   │   │   └── v2/             # Breaking domain DTO changes live here
│   │   │   │       └── user_dtos.py
│   │   │   └── repository/         # Internal DTOs — never versioned
│   │   │       └── user_dtos.py
│   │   └── order/
│   │       ├── domain/
│   │       │   └── v1/
│   │       │       └── order_dtos.py
│   │       └── repository/
│   │           └── order_dtos.py
│   ├── entities/
│   │   ├── user.py                 # User(BaseEntity)
│   │   └── order.py
│   └── errors/
│       ├── user_errors.py          # UserAlreadyExistsError(AlreadyExistsError)
│       └── order_errors.py
│
├── repositories/
│   ├── user/
│   │   ├── adapters/
│   │   │   ├── user_db_adapter.py   # Wraps PostgresSQLAlchemyAdapter
│   │   │   └── user_cache_adapter.py # Wraps RedisAdapter
│   │   └── user_repository.py
│   └── order/
│       ├── adapters/
│       │   ├── order_db_adapter.py
│       │   └── order_payment_adapter.py
│       └── order_repository.py
│
├── logics/
│   ├── user/
│   │   ├── user_registration_logic.py  # @atomic — unit of work boundary
│   │   └── user_query_logic.py
│   └── order/
│       ├── order_creation_logic.py
│       └── order_payment_logic.py
│
├── services/
│   ├── user/
│   │   ├── v1/
│   │   │   └── user_service.py     # FastAPI router for API v1
│   │   └── v2/                     # Breaking API changes go here
│   │       └── user_service.py
│   └── order/
│       └── v1/
│           └── order_service.py
│
├── tests/
│   ├── unit/                       # Uses mock adapters — no Docker
│   │   ├── test_user_registration_logic.py
│   │   └── test_order_creation_logic.py
│   ├── integration/                # Uses testcontainers — requires Docker
│   │   ├── test_postgres_adapter.py
│   │   └── test_redis_adapter.py
│   └── features/                   # BDD acceptance tests
│       ├── user_registration.feature
│       └── steps/
│           └── user_steps.py
│
└── main.py                         # Bootstraps the container and creates the FastAPI app
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

!!! tip "DTO naming conventions"

- **Domain input**: `UserRegistrationInputDTO` — data arriving from the client
- **Domain output**: `UserRegistrationOutputDTO` — data returned to the client
- **Repository command**: `CreateUserCommandDTO` — a write operation
- **Repository query**: `GetUserByIdQueryDTO` — a read operation
- **Repository response**: `UserResponseDTO` — result from an adapter or repository

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

### `tests/`

| Folder         | Tool                        | Scope                                     |
|----------------|-----------------------------|-------------------------------------------|
| `unit/`        | `pytest` + mock adapters    | Single logic class or utility — no Docker |
| `integration/` | `pytest` + `testcontainers` | Adapter against a real service in Docker  |
| `features/`    | `behave`                    | Full-stack acceptance scenarios           |

---

## Entry Point: `main.py`

```python
# main.py
from archipy.helpers.utils.app_utils import AppUtils

import configs.app_config  # noqa: F401 — triggers BaseConfig.set_global
from configs.containers import UserContainer
from services.user.v1.user_service import create_router as create_user_v1_router

user_container = UserContainer()

app = AppUtils.create_fastapi_app()
app.include_router(create_user_v1_router(user_container))

if __name__ == "__main__":
    import uvicorn
    from archipy.configs.base_config import BaseConfig

    config = BaseConfig.global_config()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
```

!!! note "Container import side-effect"
Importing `configs.app_config` is enough to call `BaseConfig.set_global`. The DI container in
`containers.py` imports `app_config` at the top, so importing the container module is sufficient for
a fully bootstrapped application.

---

## See Also

- [Quickstart](quickstart.md) — five-minute getting-started example
- [Concepts](concepts.md) — four-layer architecture and import rules
- [Dependency Injection](../examples/dependency_injection.md) — container wiring in detail
- [Testing Strategy](../examples/testing_strategy.md) — unit, integration, and BDD test layout
- [Configuration Management](../examples/config_management.md) — environment-specific configs
