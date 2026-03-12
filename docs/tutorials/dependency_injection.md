---
title: Dependency Injection
description: Wiring ArchiPy adapters and services using the dependency-injection extra and a DI container.
---

# Dependency Injection

ArchiPy includes first-class support for dependency injection (DI) via the `dependency-injection` extra, which
uses [dependency-injector](https://python-dependency-injector.ets-labs.org/) under the hood.

## Installation

```bash
uv add "archipy[dependency-injection]"
```

## Why Dependency Injection?

In a Clean Architecture application, each layer depends on **abstractions** (ports), not on concrete
implementations. DI wires those abstractions to concrete implementations at application start-up — in one place,
with no global singletons scattered across the codebase.

Benefits:

- **Testability** — swap any real adapter for a mock by overriding a single provider.
- **Single responsibility** — business logic classes receive their dependencies; they do not create them.
- **Centralized configuration** — all wiring lives in one `containers.py` file.

---

## Basic Container Setup

### Project Layout

```
your_app/
├── configs/
│   ├── app_config.py     # AppConfig(BaseConfig)
│   └── containers.py     # DI container wiring
├── logics/
│   └── user_logic.py     # business logic, depends on ports
├── repositories/
│   └── user_repository.py
└── main.py
```

### 1. Define Your Config

```python
# configs/app_config.py
import logging
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    """Application-level configuration.

    Inherits all ArchiPy default config sections (REDIS, POSTGRES_SQLALCHEMY, etc.).
    Override any field to customise for this service.
    """

    APP_NAME: str = "my-service"
    DEBUG: bool = False
```

### 2. Write the DI Container

```python
# containers.py
import logging
from dependency_injector import containers, providers

from archipy.adapters.redis.adapters import RedisAdapter
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from configs.app_config import AppConfig
from repositories.user_repository import UserRepository
from logics.user_logic import UserLogic

logger = logging.getLogger(__name__)


class ApplicationContainer(containers.DeclarativeContainer):
    """Central DI container for the application.

    Wire adapters → repositories → logic layers here.
    Override providers in tests to inject mocks.
    """

    # --- Configuration ---
    config = providers.Singleton(AppConfig)

    # --- Infrastructure adapters ---
    redis_adapter = providers.Singleton(RedisAdapter)

    postgres_adapter = providers.Singleton(PostgresSQLAlchemyAdapter)

    # --- Repositories ---
    user_repository = providers.Factory(
        UserRepository,
        db=postgres_adapter,
        cache=redis_adapter,
    )

    # --- Business logic ---
    user_logic = providers.Factory(
        UserLogic,
        repository=user_repository,
    )
```

### 3. Business Logic (Depends on Ports)

```python
# logics/user_logic.py
import logging
from typing import Protocol

from archipy.models.errors import NotFoundError

logger = logging.getLogger(__name__)


class UserRepositoryPort(Protocol):
    """Minimal port that any user repository must satisfy."""

    def find_by_id(self, user_id: str) -> dict | None:
        """Return user attributes by ID, or None if not found."""
        ...


class UserLogic:
    """User management business logic.

    Args:
        repository: Data access object for user persistence and caching.
    """

    def __init__(self, repository: UserRepositoryPort) -> None:
        self._repo = repository

    def get_user(self, user_id: str) -> dict:
        """Fetch a user by ID.

        Args:
            user_id: The unique user identifier.

        Returns:
            A dictionary of user attributes.

        Raises:
            NotFoundError: If the user does not exist.
        """
        user = self._repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(resource_type="user", additional_data={"user_id": user_id})

        logger.info("User %s loaded", user_id)
        return user
```

### 4. Bootstrap in `main.py`

```python
# main.py
import logging
from archipy.configs.base_config import BaseConfig
from containers import ApplicationContainer

logger = logging.getLogger(__name__)


def main() -> None:
    """Bootstrap the application container and set global config."""
    container = ApplicationContainer()

    # Initialise and register the global config
    config = container.config()
    BaseConfig.set_global(config)
    logger.info("Application started: %s (env=%s)", config.APP_NAME, config.ENVIRONMENT)

    # Wire the container into modules that use @inject
    container.wire(modules=["logics.user_logic", "repositories.user_repository"])

    # Example: resolve the full object graph
    logic = container.user_logic()
    user = logic.get_user("user-123")
    logger.info("User: %s", user)


if __name__ == "__main__":
    main()
```

---

## FastAPI Integration

Use `dependency-injector`'s `@inject` decorator with FastAPI's `Depends`:

```python
# services/user_service.py
import logging
from dependency_injector.wiring import inject, Provide
from fastapi import APIRouter, Depends
from containers import ApplicationContainer
from logics.user_logic import UserLogic
from archipy.models.errors import NotFoundError
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}")
@inject
async def get_user(
        user_id: str,
        logic: UserLogic = Depends(Provide[ApplicationContainer.user_logic]),
) -> dict:
    """Get a user by ID.

    Args:
        user_id: The user's unique identifier.
        logic: Injected user logic instance.

    Returns:
        A dictionary with user attributes.

    Raises:
        HTTPException: 404 if the user is not found.
    """
    try:
        return logic.get_user(user_id)
    except NotFoundError as e:
        logger.warning("User not found: %s", user_id)
        raise AppUtils.create_not_found_exception(detail=str(e)) from e
```

Wire the container in the FastAPI app factory:

```python
# app.py
import logging
from fastapi import FastAPI
from containers import ApplicationContainer
from services.user_service import router as user_router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        A configured FastAPI instance.
    """
    container = ApplicationContainer()
    container.wire(modules=["services.user_service"])

    app = FastAPI(title="My ArchiPy Service")
    app.container = container  # type: ignore[attr-defined]
    app.include_router(user_router)

    logger.info("FastAPI app created")
    return app
```

---

## Overriding Providers in Tests

The biggest advantage of DI is trivial mock injection in tests:

```python
# tests/unit/test_user_logic.py
import logging
import pytest
from unittest.mock import MagicMock
from containers import ApplicationContainer
from archipy.models.errors import NotFoundError

logger = logging.getLogger(__name__)


@pytest.fixture()
def container_with_mocks() -> ApplicationContainer:
    """Return a container with all adapters replaced by mocks."""
    container = ApplicationContainer()

    # Override the repository — cache is an internal detail of the repository layer
    mock_repo = MagicMock()
    container.user_repository.override(mock_repo)

    yield container

    container.unwire()


def test_get_user_returns_value(container_with_mocks: ApplicationContainer) -> None:
    """Logic returns the value provided by the repository."""
    repo_mock = container_with_mocks.user_repository()
    repo_mock.find_by_id.return_value = {"id": "42", "username": "Alice"}

    logic = container_with_mocks.user_logic()
    result = logic.get_user("42")

    assert result["username"] == "Alice"
    repo_mock.find_by_id.assert_called_once_with("42")
    logger.info("get_user test passed")


def test_get_user_raises_not_found(container_with_mocks: ApplicationContainer) -> None:
    """NotFoundError raised when the repository returns None."""
    repo_mock = container_with_mocks.user_repository()
    repo_mock.find_by_id.return_value = None

    logic = container_with_mocks.user_logic()
    with pytest.raises(NotFoundError):
        logic.get_user("nonexistent")
```

---

## See Also

- [Configuration Management](config_management.md) — `BaseConfig` and environment variables
- [Testing Strategy](testing_strategy.md) — mock adapters and testcontainers
- [Redis](adapters/redis.md) — Redis adapter configuration
- [PostgreSQL](adapters/postgres.md) — PostgreSQL adapter configuration
- [API Reference — Configs](../api_reference/configs.md) — full config API
