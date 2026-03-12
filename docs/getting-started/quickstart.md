---
title: Quickstart
description: Get an ArchiPy application running in under five minutes with a config, a Redis adapter, and a caching decorator.
---

# Quickstart

This guide walks you through creating a minimal ArchiPy application from scratch. You will have a running service
with a typed config, a Redis adapter, and a TTL cache decorator in under five minutes.

## Prerequisites

- Python 3.14 or later
- `uv` package manager ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

!!! tip "Check your Python version"

```bash
python --version  # must be 3.14+
```

## Step 1 — Create the Project

```bash
mkdir my_service && cd my_service
uv init
```

## Step 2 — Install ArchiPy

```bash
uv add "archipy[redis,cache]"
```

## Step 3 — Define the Configuration

Create a configuration class that extends `BaseConfig`. Add only the fields your service needs:

```python
# configs/app_config.py
import logging
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    """Service-level configuration.

    All ArchiPy config sections (REDIS, FASTAPI, etc.) are inherited.
    Add custom fields below.
    """

    APP_NAME: str = "my-service"
    DEBUG: bool = False


config = AppConfig()
BaseConfig.set_global(config)
logger.info("Config loaded for environment: %s", config.ENVIRONMENT)
```

## Step 4 — Connect to Redis

Create a Redis adapter using the global config:

```python
# adapters/cache_adapter.py
import logging
from archipy.adapters.redis.adapters import RedisAdapter

logger = logging.getLogger(__name__)

redis = RedisAdapter()  # reads config.REDIS automatically
logger.info("Redis adapter ready")
```

## Step 5 — Add a Caching Decorator

Use `@ttl_cache` to cache any function result in Redis:

```python
# logics/user_logic.py
import logging
from archipy.helpers.decorators.cache import ttl_cache

logger = logging.getLogger(__name__)


@ttl_cache(ttl=60)
def get_user_name(user_id: str) -> str:
    """Fetch a user name from the database (simulated).

    Args:
        user_id: Unique user identifier.

    Returns:
        The user's display name.
    """
    logger.info("Cache miss — fetching user %s from database", user_id)
    return f"User-{user_id}"  # replace with a real DB call


# First call: cache miss — hits the database
name = get_user_name("42")

# Second call within 60 seconds: cache hit — returns instantly
name = get_user_name("42")
```

## Step 6 — Run the App

```python
# main.py
import logging
import configs.app_config  # noqa: F401 — triggers BaseConfig.set_global
from logics.user_logic import get_user_name

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(get_user_name("42"))
    logger.info(get_user_name("42"))  # returns from cache
```

```bash
uv run main.py
```

You should see:

```
INFO  Cache miss — fetching user 42 from database
INFO  User-42
INFO  User-42
```

The second call is served from Redis without hitting the database.

---

## What's Next

Now that the basics work, explore the full feature set:

- [Concepts](concepts.md) — understand the four-layer architecture and import rules
- [Project Structure](project_structure.md) — recommended folder layout for a full service
- [Configuration Management](../examples/config_management.md) — environment variables, `.env` files, nested config
- [Dependency Injection](../examples/dependency_injection.md) — wire adapters and logic with a DI container
- [Tutorials](../examples/index.md) — guides for every adapter (PostgreSQL, Kafka, Keycloak, …)
