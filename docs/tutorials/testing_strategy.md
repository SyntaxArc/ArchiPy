---
title: BDD Testing
description: BDD testing patterns for ArchiPy applications — Gherkin features, mock adapters, testcontainers, and the Ports & Adapters pattern.
---

# BDD Testing

ArchiPy's layered architecture makes testing straightforward. Each layer can be tested in isolation, and the
Ports & Adapters pattern ensures business logic never depends on real infrastructure.

## Overview

ArchiPy uses **BDD (Behave)** as its sole test framework. All scenarios — including those that use mock
adapters and in-memory fakes — are written as Gherkin features with Behave step definitions.

| Level               | Tool                        | Scope                             | Speed | Requires infrastructure |
|---------------------|-----------------------------|-----------------------------------|-------|-------------------------|
| BDD (mock adapters) | `behave` + mocks            | Single adapter / helper behaviour | Fast  | No                      |
| BDD (integration)   | `behave` + `testcontainers` | Adapter against real service      | Slow  | Yes (Docker)            |

> **Tip:** Features that require a running service are tagged with `@needs-*`. Skip infrastructure-heavy scenarios when
> Docker is not available:

```bash
uv run behave --tags=~@needs-redis         # skip Redis scenarios
uv run behave --tags=@needs-postgres       # run only Postgres scenarios
uv run behave --tags=~@needs-redis,~@needs-postgres,~@needs-kafka  # skip all infra tags
```

---

## Testing with Mock Adapters

### The Mock Adapter Pattern

Every ArchiPy adapter provides a `ports.py` abstract interface. Your business logic depends only on the
abstract port — not on the concrete adapter. This means you can swap the real adapter for an in-memory mock
in Behave step definitions:

```
Production:  YourLogic → RedisAdapter (real Redis)
Test:        YourLogic → RedisMock (in-memory dict)
```

### Using the Built-in `RedisMock`

Redis is the only adapter that ships a built-in `mocks.py`. Use it directly in Behave step definitions:

```python
# features/steps/session_steps.py
import logging
from behave import given, then, when
from archipy.adapters.redis.mocks import RedisMock

logger = logging.getLogger(__name__)


@given("an empty session cache")
def step_empty_cache(context) -> None:
    context.cache = RedisMock()


@when('a session "{session_id}" is stored with value "{value}"')
def step_store_session(context, session_id: str, value: str) -> None:
    context.cache.set(f"session:{session_id}", value, ttl=300)


@then('retrieving session "{session_id}" returns "{expected}"')
def step_get_session(context, session_id: str, expected: str) -> None:
    result = context.cache.get(f"session:{session_id}")
    assert result == expected
    logger.info("Session %s retrieved correctly", session_id)
```

### Using `fakeredis` for a More Complete Redis Mock

For scenarios that need pipeline support or Lua scripts, use `fakeredis`:

```bash
uv add "archipy[fakeredis]"
```

```python
# features/steps/counter_steps.py
import logging
import fakeredis
from behave import given, then, when
from archipy.adapters.redis.ports import RedisPort

logger = logging.getLogger(__name__)


def make_fake_redis() -> RedisPort:
    """Create a fake Redis client that satisfies the RedisPort interface."""
    return fakeredis.FakeRedis(decode_responses=True)  # type: ignore[return-value]


@given("a fresh Redis counter at zero")
def step_fresh_counter(context) -> None:
    context.client = make_fake_redis()
    context.client.set("counter", "0")


@when("the counter is incremented")
def step_increment_counter(context) -> None:
    context.client.incr("counter")


@then("the counter value is 1")
def step_assert_counter(context) -> None:
    assert context.client.get("counter") == "1"
    logger.info("Counter increment scenario passed")
```

### Writing a Custom Mock for Other Adapters

For adapters without a built-in mock, implement the port interface yourself:

```python
import logging
from collections.abc import Generator
from contextlib import contextmanager

from archipy.adapters.base.sqlalchemy.ports import BaseSQLAlchemyAdapterPort

logger = logging.getLogger(__name__)


class InMemorySQLAlchemyMock(BaseSQLAlchemyAdapterPort):
    """In-memory mock for SQLAlchemy adapters — no database required."""

    def __init__(self) -> None:
        self._store: dict[str, object] = {}
        self._committed = False

    @contextmanager
    def session_scope(self) -> Generator:
        """Yield a fake session context."""
        yield self
        self._committed = True

    def add(self, entity: object) -> None:
        """Store entity by its id attribute."""
        entity_id = getattr(entity, "id", id(entity))
        self._store[str(entity_id)] = entity
        logger.debug("Mock stored entity: %s", entity_id)

    def get(self, entity_type: type, entity_id: str) -> object | None:
        """Retrieve entity by id."""
        return self._store.get(str(entity_id))
```

> **Note:** Implement only the methods your tests actually call. An `NotImplementedError` on unused methods is better
> than a mock that silently returns wrong values.

---

## Integration Testing with `testcontainers`

Integration scenarios verify that adapters work correctly against real services. ArchiPy manages all
Docker containers through a centralised `ContainerManager` and a tag-driven startup mechanism — you never
start containers manually inside step definitions.

### Installation

```bash
uv add "archipy[testcontainers]"
```

### How it works

```
features/
├── environment.py                  # Behave hooks: TestConfig, ContainerManager, ScenarioContextPoolManager
├── test_containers.py              # ContainerManager + per-service container classes (Singleton)
├── scenario_context.py             # Per-scenario isolated storage + cleanup
├── scenario_context_pool_manager.py # Singleton pool of ScenarioContext objects, keyed by scenario ID
└── steps/
    └── *.py                        # Step definitions — access containers via context.scenario_context_pool
```

The lifecycle is:

1. `before_all` — initialises `TestConfig` (reads `.env.test`), sets global config, wires `ContainerManager` and
   `ScenarioContextPoolManager` onto `context`.
2. `before_feature` — reads `@needs-*` tags; calls `ContainerManager.start_containers()` for only the services required
   by that feature.
3. `before_scenario` — allocates an isolated `ScenarioContext` from the pool for the current scenario.
4. `after_scenario` — cleans up the `ScenarioContext` (closes DB sessions, disposes engines, resets
   `SessionManagerRegistry`).
5. `after_feature` / `after_all` — stops all started containers.

### `environment.py`

```python
# features/environment.py
import logging
import uuid

from behave.model import Feature, Scenario
from behave.runner import Context
from features.scenario_context_pool_manager import ScenarioContextPoolManager
from features.test_containers import ContainerManager
from pydantic_settings import SettingsConfigDict

from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.configs.base_config import BaseConfig


class TestConfig(BaseConfig):
    """Extends BaseConfig with Docker image references read from .env.test."""

    model_config = SettingsConfigDict(env_file=".env.test")

    REDIS__IMAGE: str
    POSTGRES__IMAGE: str
    KAFKA__IMAGE: str
    # ... add images for every service you test


config = TestConfig()
BaseConfig.set_global(config)


def before_all(context: Context) -> None:
    logging.basicConfig(level=logging.INFO)
    context.logger = logging.getLogger("behave.tests")
    context.scenario_context_pool = ScenarioContextPoolManager()
    context.test_containers = ContainerManager


def before_feature(context: Context, feature: Feature) -> None:
    """Start only the containers needed by this feature's @needs-* tags."""
    if hasattr(feature, "tags") and feature.tags:
        feature_tags = [str(tag) for tag in feature.tags]
        required = ContainerManager.extract_containers_from_tags(feature_tags)
        if required:
            ContainerManager.start_containers(list(required))


def before_scenario(context: Context, scenario: Scenario) -> None:
    if not hasattr(scenario, "id"):
        scenario.id = str(uuid.uuid4())
    scenario_context = context.scenario_context_pool.get_context(scenario.id)
    scenario_context.store("test_containers", context.test_containers)


def after_scenario(context: Context, scenario: Scenario) -> None:
    scenario_id = getattr(scenario, "id", "unknown")
    if hasattr(context, "scenario_context_pool"):
        context.scenario_context_pool.cleanup_context(scenario_id)
    SessionManagerRegistry.reset()


def after_feature(context: Context, feature: Feature) -> None:
    if hasattr(context, "test_containers"):
        context.test_containers.stop_all()


def after_all(context: Context) -> None:
    if hasattr(context, "test_containers"):
        context.test_containers.stop_all()
    if hasattr(context, "scenario_context_pool"):
        context.scenario_context_pool.cleanup_all()
```

### Tagging features for container startup

Tag a feature file with `@needs-<service>` to have `ContainerManager` start the required container
before any scenario in that feature runs:

```gherkin
# features/redis_cache.feature
@needs-redis
Feature: Redis cache adapter

  Scenario: Store and retrieve a value
    Given the Redis adapter is initialised
    When I store "hello" under key "greeting"
    Then retrieving "greeting" returns "hello"
```

Available tags: `@needs-redis`, `@needs-postgres`, `@needs-kafka`, `@needs-keycloak`,
`@needs-minio`, `@needs-elasticsearch`, `@needs-scylladb`, `@needs-starrocks`, `@needs-temporal`.

### Using `ScenarioContext` in step definitions

`ScenarioContext` provides per-scenario isolated storage. Access it from the pool by scenario ID:

```python
# features/steps/redis_adapter_steps.py
import logging
from behave import given, then, when
from features.test_containers import ContainerManager
from archipy.adapters.redis.adapters import RedisAdapter

logger = logging.getLogger(__name__)


@given("the Redis adapter is initialised")
def step_redis_init(context):
    # ContainerManager already started the container via @needs-redis tag.
    # Global config was patched automatically when the container started.
    scenario_ctx = context.scenario_context_pool.get_context(context.scenario.id)
    scenario_ctx.adapter = RedisAdapter()   # uses patched global config


@when('I store "{value}" under key "{key}"')
def step_store(context, value, key):
    scenario_ctx = context.scenario_context_pool.get_context(context.scenario.id)
    scenario_ctx.adapter.set(key, value)


@then('retrieving "{key}" returns "{expected}"')
def step_retrieve(context, key, expected):
    scenario_ctx = context.scenario_context_pool.get_context(context.scenario.id)
    result = scenario_ctx.adapter.get(key)
    assert result == expected
    logger.info("Redis value for key '%s' matched expected '%s'", key, expected)
```

> **Tip:** Each `*TestContainer.start()` updates `BaseConfig.global_config()` with the live container host and port.
> Adapters constructed after container startup automatically connect to the right endpoint — no manual config wiring
> needed in step definitions.

> **Warning:** Each container start adds several seconds. Containers are started per-feature and stopped after
> each feature — `ContainerManager` skips already-running containers so sharing across features
> within a run is handled automatically.

### Skipping infrastructure-heavy scenarios

```bash
uv run behave --tags=~@needs-redis          # skip Redis scenarios
uv run behave --tags=@needs-postgres        # run only Postgres scenarios
uv run behave --tags=~@needs-redis,~@needs-kafka  # skip multiple services
```

---

## Testing with Ports & Adapters

The key benefit of the Ports & Adapters pattern is that business logic is **100% testable** without any
infrastructure.

### Structure: Logic Layer Depends on Ports

```python
import logging
from archipy.adapters.redis.ports import RedisPort
from archipy.models.errors import NotFoundError

logger = logging.getLogger(__name__)


class UserSessionService:
    """Manages user sessions backed by a cache.

    Args:
        cache: A Redis-compatible cache adapter (real or mock).
    """

    def __init__(self, cache: RedisPort) -> None:
        self._cache = cache

    def get_session(self, session_id: str) -> str:
        """Retrieve a user session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The session data string.

        Raises:
            NotFoundError: If the session does not exist.
        """
        value = self._cache.get(f"session:{session_id}")
        if value is None:
            raise NotFoundError(resource_type="session", additional_data={"session_id": session_id})
        logger.debug("Session retrieved: %s", session_id)
        return value
```

### BDD Scenario: Inject the Mock

```gherkin
# features/user_session.feature
Feature: User session management

  Scenario: Retrieve an existing session
    Given an empty session cache
    And session "xyz" is stored with value "user_id:7"
    When I retrieve session "xyz"
    Then the result is "user_id:7"

  Scenario: Session not found raises an error
    Given an empty session cache
    When I retrieve session "nonexistent"
    Then a NotFoundError is raised
```

```python
# features/steps/session_service_steps.py
import logging
from behave import given, then, when
from archipy.adapters.redis.mocks import RedisMock
from archipy.models.errors import NotFoundError

logger = logging.getLogger(__name__)


@given("an empty session cache")
def step_empty_cache(context) -> None:
    context.cache = RedisMock()
    context.service = UserSessionService(cache=context.cache)
    context.error = None
    context.result = None


@given('session "{session_id}" is stored with value "{value}"')
def step_store_session(context, session_id: str, value: str) -> None:
    context.cache.set(f"session:{session_id}", value)


@when('I retrieve session "{session_id}"')
def step_retrieve_session(context, session_id: str) -> None:
    try:
        context.result = context.service.get_session(session_id)
    except NotFoundError as e:
        context.error = e


@then('the result is "{expected}"')
def step_assert_result(context, expected: str) -> None:
    assert context.result == expected
    logger.info("Session retrieved correctly")


@then("a NotFoundError is raised")
def step_assert_not_found(context) -> None:
    assert isinstance(context.error, NotFoundError)
    logger.info("NotFoundError raised as expected")
```

### Feature Directory Layout

```
your_app/
├── logics/
│   └── user_session_service.py
└── features/
    ├── environment.py                    # TestConfig, ContainerManager, ScenarioContextPoolManager hooks
    ├── test_containers.py                # ContainerManager + per-service Singleton container classes
    ├── scenario_context.py               # Per-scenario isolated storage + cleanup
    ├── scenario_context_pool_manager.py  # Singleton pool of ScenarioContext, keyed by scenario ID
    ├── user_session.feature              # @needs-redis — uses RedisMock (no Docker)
    ├── redis_integration.feature         # @needs-redis — uses real container
    └── steps/
        ├── session_service_steps.py
        └── redis_adapter_steps.py
```

---

## Advanced Gherkin Patterns

### Data Tables

Use Behave data tables to drive a single step with multiple rows:

```gherkin
# features/user_management.feature
Feature: User Management

  Scenario: Create multiple users
    Given I have admin privileges
    When I create the following users:
      | username | email             | role    |
      | john     | john@example.com  | user    |
      | alice    | alice@example.com | admin   |
      | bob      | bob@example.com   | support |
    Then all users should be saved in the database
```

```python
# features/steps/user_steps.py
import logging
from behave import given, when, then
from archipy.models.errors import DatabaseQueryError, NotFoundError

logger = logging.getLogger(__name__)


@given("I have admin privileges")
def step_admin(context):
    context.is_admin = True


@when("I create the following users")
def step_create_many(context):
    context.users = []
    for row in context.table:
        try:
            user = UserService().create_user(
                username=row["username"],
                email=row["email"],
                role=row["role"],
            )
        except Exception as e:
            logger.error("Failed to create user %s: %s", row["username"], e)
            raise DatabaseQueryError(
                additional_data={"username": row["username"]}
            ) from e
        else:
            context.users.append(user)
            logger.info("Created user: %s", row["username"])
    logger.info("Created %d users total", len(context.users))


@then("all users should be saved in the database")
def step_all_saved(context):
    for user in context.users:
        db_user = User.query.filter_by(username=user.username).first()
        if db_user is None:
            raise NotFoundError(resource_type="user", additional_data={"username": user.username})
    logger.info("All %d users verified in database", len(context.users))
```

### Running specific scenarios

```bash
# All BDD scenarios
make behave

# Single feature file
uv run behave features/user_management.feature

# Single scenario by line number
uv run behave features/user_management.feature:7

# By tag
uv run behave --tags=@smoke
```

## Running All Tests

```bash
# All BDD scenarios
make behave

# Full check: format + lint + security + BDD
make check
```

---

## See Also

- [Error Handling](error_handling.md) — testing that the right exceptions are raised
- [Redis](adapters/redis.md) — Redis adapter and `fakeredis` configuration
- [Installation](../getting-started/installation.md) — `fakeredis` and `testcontainers` extras
- [FAQ](../community/faq.md) — common testing questions
