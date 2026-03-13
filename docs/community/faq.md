---
title: FAQ
description: Answers to frequently asked questions about ArchiPy's architecture, adapters, testing, and configuration.
---

# FAQ

## Architecture

### Why Clean Architecture instead of plain FastAPI or Django?

Plain FastAPI and Django encourage mixing I/O, business logic, and configuration in the same layer. This makes
unit testing hard (you can't call a function without a live database), and it makes changing infrastructure
expensive (swapping PostgreSQL for ScyllaDB requires touching business logic).

ArchiPy enforces a strict four-layer boundary:

```
configs ← models ← helpers ← adapters
```

Business logic (in your `logics/` layer) depends only on abstract ports — never on concrete database drivers.
Swapping the implementation means changing a single adapter class, not rewriting business code.

### What is the difference between `ports.py` and `adapters.py`?

- **`ports.py`** — defines an abstract interface (`ABC`) that describes *what* the adapter can do. Your business
  logic and repositories import only from `ports.py`. This makes them testable in isolation.
- **`adapters.py`** — provides the concrete implementation that talks to the real external service (Redis, Postgres,
  etc.). It implements the interface defined in `ports.py`.

```python
# ports.py defines the contract
class RedisPort(ABC):
    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl: int | None = None) -> None: ...


# adapters.py fulfils the contract against a real Redis server
class RedisAdapter(RedisPort):
    def get(self, key: str) -> str | None:
        return self._client.get(key)
```

Your business logic only sees `RedisPort`. In production you inject `RedisAdapter`; in tests you inject
`RedisMock` (or `FakeRedis`).

### Can I use ArchiPy without FastAPI?

Yes. FastAPI is an optional extra (`archipy[fastapi]`). The core library — configs, models, helpers, and adapters —
has no dependency on FastAPI. You can use ArchiPy with any Python framework (Flask, gRPC, CLI scripts, Celery
workers) or with no web framework at all.

### Can I use ArchiPy with an existing project?

Yes. ArchiPy components are designed to be adopted incrementally. You can:

1. Start by using only `BaseConfig` for configuration management.
2. Add individual adapters one at a time (e.g., the Redis adapter).
3. Gradually move business logic behind ports as you refactor.

There is no requirement to adopt the full four-layer structure immediately.

### Why does ArchiPy require Python 3.14+?

ArchiPy targets the latest stable Python release to stay lean and forward-looking. Requiring 3.14+
ensures access to the full set of current runtime improvements, performance gains, and security patches,
while dropping legacy compatibility shims like `typing.Optional`, `typing.Union`, and
`from __future__ import annotations`.

Using the latest stable Python keeps dependencies minimal and the code idiomatic.

---

## Adapters

### How do I use multiple databases at the same time?

Each adapter is independently configured. Instantiate them separately and inject them where needed:

```python
import logging

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.adapters.redis.adapters import RedisAdapter
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)

config = BaseConfig.global_config()

pg = PostgresSQLAlchemyAdapter()  # uses config.POSTGRES_SQLALCHEMY
cache = RedisAdapter()  # uses config.REDIS
search = ElasticsearchAdapter()  # uses config.ELASTIC

logger.info("All three adapters ready")
```

Each adapter reads its own nested config section from `BaseConfig`, so there are no naming conflicts.

### How do I connect to two separate PostgreSQL databases?

Pass explicit config objects instead of relying on the global config:

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.configs.base_config import BaseConfig, PostgresSQLAlchemyConfig

primary_cfg = PostgresSQLAlchemyConfig(HOST="primary.db", DB_NAME="main_db")
replica_cfg = PostgresSQLAlchemyConfig(HOST="replica.db", DB_NAME="main_db")

primary = PostgresSQLAlchemyAdapter(config=primary_cfg)
replica = PostgresSQLAlchemyAdapter(config=replica_cfg)
```

### Why does my adapter raise an ImportError?

ArchiPy uses optional extras to keep the base install lightweight. If you get an `ImportError` when importing an
adapter, install the corresponding extra:

```bash
# Example: ImportError for Redis
uv add "archipy[redis]"

# Example: ImportError for PostgreSQL
uv add "archipy[postgres,sqlalchemy]"
```

See the [Installation](../getting-started/installation.md) page for the full extras table.

### What is the `mocks.py` file in adapters?

`mocks.py` provides a **test double** — an in-memory implementation of the adapter's port that behaves like the
real adapter but requires no external service. Use it in unit tests to avoid spinning up Redis, Postgres, or
Kafka:

```python
from archipy.adapters.redis.mocks import RedisMock


def test_user_cache():
    cache = RedisMock()  # no Redis server needed
    cache.set("user:1", "Alice")
    assert cache.get("user:1") == "Alice"
```

---

## Testing

### How do I write unit tests without a real database or Redis?

Use the mock adapters provided in each adapter's `mocks.py`. For adapters that don't ship a `mocks.py` yet,
use `fakeredis` (for Redis) or `testcontainers` (for databases):

```bash
uv add "archipy[fakeredis]"     # in-memory Redis for tests
uv add "archipy[testcontainers]" # Docker-backed real DBs for integration tests
```

See the [Testing Strategy](../tutorials/testing_strategy.md) guide for full patterns.

### How do I run BDD tests?

```bash
make behave
```

Or target a single feature file:

```bash
uv run behave features/my_feature.feature
```

See the [BDD Testing](../tutorials/testing_strategy.md) guide for Gherkin syntax and step definitions.

### What is the difference between unit tests and integration tests in ArchiPy?

- **Unit tests** — test a single component (a logic class, a utility function) in complete isolation using mock
  adapters. They run instantly without Docker or external services.
- **Integration tests** — test your adapters against real services (started via `testcontainers`). They verify
  that SQL queries, cache keys, and Kafka messages actually work end-to-end.
- **BDD tests** — describe system behaviour in Gherkin, implemented with Behave. They sit at the acceptance level
  and can use either mocks or real services depending on the scenario.

---

## Configuration

### How do I load configuration from a `.env` file?

`BaseConfig` inherits from `pydantic_settings.BaseSettings`, which automatically reads from a `.env` file in the
working directory (or from environment variables). No extra setup is needed:

```bash
# .env
REDIS__HOST=localhost
REDIS__PORT=6379
ENVIRONMENT=DEV
```

> **Warning:** Add `.env` to your `.gitignore`. Use `.env.example` to document the required variables without real
> values.

### Can I override configuration at runtime?

Yes. Call `BaseConfig.set_global(config_instance)` at application start-up. Any code that calls
`BaseConfig.global_config()` afterwards will see the new values:

```python
from archipy.configs.base_config import BaseConfig

config = BaseConfig(ENVIRONMENT="PRODUCTION")
BaseConfig.set_global(config)
```

### How do I validate custom configuration fields?

Use Pydantic field validators:

```python
from pydantic import field_validator
from archipy.configs.base_config import BaseConfig


class AppConfig(BaseConfig):
    MAX_CONNECTIONS: int = 10

    @field_validator("MAX_CONNECTIONS")
    @classmethod
    def connections_must_be_positive(cls, v: int) -> int:
        """Validate that MAX_CONNECTIONS is positive."""
        if v <= 0:
            raise ValueError("MAX_CONNECTIONS must be greater than 0")
        return v
```

---

## Helpers & Utilities

### What decorators does ArchiPy provide?

| Decorator     | Module                                    | Purpose                         |
|---------------|-------------------------------------------|---------------------------------|
| `@ttl_cache`  | `helpers.decorators.cache`                | In-memory TTL cache             |
| `@retry`      | `helpers.decorators.retry`                | Automatic retry with back-off   |
| `@atomic`     | `helpers.decorators.sqlalchemy_atomic`    | SQLAlchemy transaction wrapping |
| `@singleton`  | `helpers.decorators.singleton`            | Singleton pattern enforcement   |
| `@timeout`    | `helpers.decorators.timeout`              | Function execution timeout      |
| `@timing`     | `helpers.decorators.timing`               | Execution time logging          |
| `@deprecated` | `helpers.decorators.deprecation_warnings` | Deprecation warning             |

See the [Decorators tutorial](../tutorials/helpers/decorators.md) for examples.

### What is the difference between `@singleton` decorator and `SingletonMeta` metaclass?

Both enforce the singleton pattern but suit different use cases:

- **`@singleton` decorator** — wraps any callable; simpler to apply to a standalone function or an existing class.
- **`SingletonMeta` metaclass** — used as `metaclass=SingletonMeta` on a class definition; integrates more
  naturally into class hierarchies and works with inheritance.

---

## See Also

- [Concepts](../getting-started/concepts.md) — Clean Architecture layers and import rules
- [Installation](../getting-started/installation.md) — optional extras and prerequisites
- [Testing Strategy](../tutorials/testing_strategy.md) — unit, integration, and BDD test patterns
- [Configuration Management](../tutorials/config_management.md) — environment variables, `.env` files, nested config
- [Error Handling](../tutorials/error_handling.md) — domain exceptions and chaining
