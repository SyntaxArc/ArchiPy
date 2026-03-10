# Helpers

The `helpers` module provides utility functions, decorators, interceptors, and metaclasses to support common development
tasks and patterns.

## Overview

The `helpers` module provides utility functions and classes to simplify common development tasks.

## Installation

This module is included in the base ArchiPy installation:

```bash
# Add ArchiPy to your project
uv add archipy
```

For development features:

```bash
# Add ArchiPy with development extras
uv add archipy[dev]
```

## Source Code

📁 Location: `archipy/helpers/`

🔗 [Browse Source](https://github.com/SyntaxArc/ArchiPy/tree/master/archipy/helpers)

## API Stability

| Component    | Status    | Notes            |
|--------------|-----------|------------------|
| Decorators   | 🟢 Stable | Production-ready |
| Utils        | 🟢 Stable | Production-ready |
| Interceptors | 🟡 Beta   | API may change   |
| Metaclasses  | 🟢 Stable | Production-ready |

## Submodules

### Utils

*See [Utils Documentation](../examples/helpers/utils.md) for full documentation.*

General utility functions for common operations:

- String manipulation
- Date and time handling
- Error utilities
- File operations
- Password utilities
- JWT token handling
- TOTP generation

### Decorators

*See [Decorators Documentation](../examples/helpers/decorators.md) for full documentation.*

Function and class decorators for:

- Method deprecation
- Class deprecation
- Timing operations
- Retry logic

### Interceptors

*See [Interceptors Documentation](../examples/helpers/interceptors.md) for full documentation.*

Classes for cross-cutting concerns:

- Logging
- Performance monitoring
- Request/response tracking

**See Examples**: [Examples Helpers](../examples/helpers/index.md)

## Decorators

> **Tip**: See [Examples Helpers Decorators](../examples/helpers/decorators.md) for practical examples of decorators.

### Retry Decorator

The retry decorator provides a mechanism to automatically retry failed operations with configurable backoff strategies.

```python
from archipy.helpers.decorators.retry import retry

@retry(max_attempts=3, delay=1, backoff=2)
def risky_operation():
    # Operation that might fail
    result = some_unreliable_function()
    return result

# Will retry up to 3 times with exponential backoff
result = risky_operation()
```

::: archipy.helpers.decorators.retry
    options:
      show_root_heading: true
      show_source: true

### Singleton Decorator

The singleton decorator ensures that a class has only one instance throughout the application lifecycle.

```python
from archipy.helpers.decorators.singleton import singleton

@singleton
class DatabaseConnection:
    def __init__(self):
        self.connection = create_connection()

# Both instances will be the same
db1 = DatabaseConnection()
db2 = DatabaseConnection()
assert db1 is db2
```

::: archipy.helpers.decorators.singleton
    options:
      show_root_heading: true
      show_source: true

### SQLAlchemy Atomic Decorator

The SQLAlchemy atomic decorator provides transaction management for database operations.

```python
from archipy.helpers.decorators.sqlalchemy_atomic import sqlalchemy_atomic

@sqlalchemy_atomic
def create_user(username: str, email: str):
    user = User(username=username, email=email)
    db.session.add(user)
    # If any operation fails, the entire transaction is rolled back
    db.session.commit()
```

::: archipy.helpers.decorators.sqlalchemy_atomic
    options:
      show_root_heading: true
      show_source: true

## Interceptors

### FastAPI Interceptors

#### FastAPI Rest Rate Limit Handler

Provides rate limiting functionality for FastAPI endpoints.

```python
from archipy.helpers.interceptors.fastapi.rate_limit import FastAPIRestRateLimitHandler
from fastapi import FastAPI

app = FastAPI()
rate_limit_handler = FastAPIRestRateLimitHandler(
    redis_client=redis_client,
    rate_limit=100,  # requests per minute
    rate_limit_period=60
)

@app.get("/api/data")
@rate_limit_handler
async def get_data():
    return {"data": "protected by rate limit"}
```

::: archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler
    options:
      show_root_heading: true
      show_source: true

### gRPC Interceptors

gRPC interceptors for tracing and monitoring:

::: archipy.helpers.interceptors.grpc.trace.client_interceptor
    options:
      show_root_heading: true
      show_source: true

::: archipy.helpers.interceptors.grpc.trace.server_interceptor
    options:
      show_root_heading: true
      show_source: true

## Metaclasses

### Singleton Metaclass

A metaclass implementation of the singleton pattern.

```python
from archipy.helpers.metaclasses.singleton import Singleton

class DatabaseConnection(metaclass=Singleton):
    def __init__(self):
        self.connection = create_connection()

# Both instances will be the same
db1 = DatabaseConnection()
db2 = DatabaseConnection()
assert db1 is db2
```

::: archipy.helpers.metaclasses.singleton
    options:
      show_root_heading: true
      show_source: true

## Key Classes

### Retry Decorator

Function: `archipy.helpers.decorators.retry.retry`

A decorator that retries a function call when it fails, with configurable:

- Maximum number of attempts
- Delay between attempts
- Backoff strategy
- Exception types to catch

### Singleton

Class: `archipy.helpers.metaclasses.singleton.Singleton`

A metaclass that ensures a class has only one instance. Features:

- Thread-safe implementation
- Lazy initialization
- Support for inheritance
- Clear instance access

### FastAPIRestRateLimitHandler

Class: `archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler.FastAPIRestRateLimitHandler`

A rate limiting handler for FastAPI applications that:

- Supports Redis-based rate limiting
- Configurable rate limits and periods
- Customizable response handling
- Support for multiple rate limit rules
