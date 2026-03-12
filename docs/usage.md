---
title: Getting Started
description: Quick-start guide to get up and running with ArchiPy.
---

# Getting Started

This is a quick-start guide to get you up and running with ArchiPy in minutes. For comprehensive architectural patterns, detailed code examples, and production-ready project structure, see the **[Architecture Guide](architecture.md)**.

## Installation

```bash
# Recommended
uv add archipy

# With specific adapters
uv add "archipy[postgres,redis,fastapi]"

# Or using pip
pip install archipy
pip install archipy[postgres,redis,fastapi]
```

!!! tip "Optional Extras"
    ArchiPy uses optional extras to keep the base install lightweight. Only install the extras you need — for example, `archipy[postgres,redis]` for database and cache support. See [Installation](installation.md) for the full list of available extras.

## Quick Start: 5-Minute API

Here's a minimal example to create a working FastAPI application:

### 1. Setup Configuration

```python
# config.py
from archipy.configs.base_config import BaseConfig

config = BaseConfig()
BaseConfig.set_global(config)
```

### 2. Define Your Model

```python
# models.py
from sqlalchemy import Column, String
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity

class User(BaseEntity):
    __tablename__ = "users"
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)
```

### 3. Create Your API

```python
# main.py
from fastapi import FastAPI
from archipy.helpers.utils.app_utils import AppUtils
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from config import config
from models import User

# Create app
app = AppUtils.create_fastapi_app()

# Initialize database
db = PostgresSQLAlchemyAdapter()
BaseEntity.metadata.create_all(db.session_manager.engine)

@app.get("/users")
def list_users():
    return {"message": "List users"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 4. Run Your API

```bash
python main.py
```

Visit `http://localhost:8000/docs` to see your API documentation!

## Next Steps

### Learn the Recommended Architecture

The quick start above is minimal. For production applications, we recommend:

- **[Architecture Guide](architecture.md)** - Complete project structure with:
  - Domain-driven organization (models, repositories, logic, services)
  - API versioning (`/api/v1/`, `/api/v2/`)
  - Command/Query/Response DTO patterns
  - Domain-specific adapters
  - Complete working code examples

### Explore Specific Features

- **[Configuration Management](examples/config_management.md)** - Environment variables, Pydantic settings
- **[Database Adapters](examples/adapters/postgres.md)** - PostgreSQL, SQLite, StarRocks
- **[Caching with Redis](examples/adapters/redis.md)** - Redis patterns and examples
- **[Authentication](examples/adapters/keycloak.md)** - Keycloak integration
- **[Object Storage](examples/adapters/minio.md)** - MinIO/S3 compatible storage
- **[Message Streaming](examples/adapters/kafka.md)** - Kafka producers and consumers
- **[Error Handling](examples/error_handling.md)** - Custom exceptions and patterns
- **[BDD Testing](examples/bdd_testing.md)** - Behavior-driven development with Behave

## Key Concepts

### Adapters

ArchiPy provides pre-built adapters for common services. Each adapter:

- Uses global configuration automatically
- Includes both sync and async versions
- Has comprehensive error handling
- Comes with testing mocks

**Example:**
```python
from archipy.adapters.redis.adapters import RedisAdapter

redis = RedisAdapter()  # Uses global config
redis.set("key", "value", ex=3600)
```

**📖 See:** [All Available Adapters](examples/index.md#adapters)

### Configuration

Centralized, type-safe configuration with environment variable support:

```python
from archipy.configs.base_config import BaseConfig

class AppConfig(BaseConfig):
    # Override defaults as needed
    pass

config = AppConfig()
BaseConfig.set_global(config)
```

**📖 See:** [Configuration Examples](examples/config_management.md)

### Error Handling

Domain-specific exceptions with proper error chaining:

```python
from archipy.models.errors import NotFoundError, AlreadyExistsError

raise NotFoundError(
    resource_type="user",
    additional_data={"user_id": user_id}
)
```

**📖 See:** [Error Handling Guide](examples/error_handling.md)

## Production-Ready Structure

For production applications, use our recommended architecture:

```
my_app/
├── configs/            # Configuration
├── models/             # DTOs, Entities, Errors
├── repositories/       # Data access with domain-specific adapters
│   └── user/
│       ├── adapters/   # UserDBAdapter, UserCacheAdapter
│       └── user_repository.py
├── logic/              # Business rules
│   └── user/
│       ├── user_registration_logic.py
│       └── user_query_logic.py
├── services/           # FastAPI endpoints
│   └── user/
│       └── v1/
│           └── user_service.py
└── main.py             # Application entry point
```

**📖 Complete guide:** [Architecture Document](architecture.md)

## Best Practices

1. **Start with the Architecture Guide** - Don't reinvent the wheel
2. **Use global configuration** - Set it once at startup
3. **Follow DTO patterns** - InputDTO, CommandDTO, QueryDTO, ResponseDTO, OutputDTO
4. **Organize by domain** - Keep related code together
5. **Version your APIs** - Use `/api/v1/`, `/api/v2/`
6. **Test with BDD** - Use Behave for behavior-driven testing

## Need Help?

- **Architecture questions?** → [Architecture Guide](architecture.md)
- **Adapter usage?** → [Examples](examples/index.md)
- **API reference?** → [API Documentation](api_reference/index.md)
- **Contributing?** → [Contributing Guide](contributing.md)

Happy coding!
