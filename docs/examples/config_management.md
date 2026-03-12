---
title: Configuration Management
description: Guide and examples for managing configuration in ArchiPy applications.
---

# Configuration Management

ArchiPy provides a robust configuration management system that ensures type safety, environment variable support, and
consistent access patterns across your application.

## Basic Configuration

### Defining a Configuration

Create a configuration class by inheriting from `BaseConfig`:

```python
from archipy.configs.base_config import BaseConfig
from archipy.configs.environment_type import EnvironmentType

class AppConfig(BaseConfig):
    # Application settings
    APP_NAME: str = "MyService"
    DEBUG: bool = False

    # Database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "myapp"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"  # noqa: S105

    # Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # Environment
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEV

    # API settings
    API_PREFIX: str = "/api/v1"

    # Logging
    LOG_LEVEL: str = "INFO"
```

### Using the Configuration

```python
# Create and set as global configuration
config = AppConfig()
BaseConfig.set_global(config)

# Access configuration values from anywhere in your code
from archipy.configs.base_config import BaseConfig

current_config = BaseConfig.global_config()
db_url = f"postgresql://{current_config.DB_USER}:{current_config.DB_PASSWORD}@{current_config.DB_HOST}:{current_config.DB_PORT}/{current_config.DB_NAME}"
```

## Environment Variables

ArchiPy configurations automatically load values from environment variables with the same name:

```bash
# .env file
# WARNING: Never commit this file to version control!
# Use environment-specific .env files and add .env to .gitignore
APP_NAME=ProductionService
DB_HOST=db.example.com
DB_PASSWORD=your-secure-password-here  # Replace with actual secure password
ENVIRONMENT=PRODUCTION
```

The environment variables override the default values in your configuration class:

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

config = AppConfig()  # Will have values from environment variables
logger.info(f"App name: {config.APP_NAME}")  # "ProductionService"
logger.info(f"Environment: {config.ENVIRONMENT}")  # EnvironmentType.PRODUCTION
```

## Environment-Specific Configurations

You can create environment-specific configurations:

```python
import logging
import os

from archipy.configs.base_config import BaseConfig
from archipy.configs.environment_type import EnvironmentType

# Configure logging
logger = logging.getLogger(__name__)


class BaseAppConfig(BaseConfig):
    APP_NAME: str = "MyService"
    DEBUG: bool = False
    # Common settings...

class DevelopmentConfig(BaseAppConfig):
    DEBUG: bool = True
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEV
    LOG_LEVEL: str = "DEBUG"

class ProductionConfig(BaseAppConfig):
    DEBUG: bool = False
    ENVIRONMENT: EnvironmentType = EnvironmentType.PRODUCTION
    LOG_LEVEL: str = "WARNING"

# Choose configuration based on environment
env: str = os.getenv("ENVIRONMENT", "development").lower()

config: BaseAppConfig
if env == "production":
    config = ProductionConfig()
else:
    config = DevelopmentConfig()

BaseConfig.set_global(config)
logger.info(f"Configuration loaded for environment: {env}")
```

## Nested Configurations

You can use nested Pydantic models for more complex configurations:

```python
import logging

from pydantic import BaseModel
from archipy.configs.base_config import BaseConfig

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    HOST: str = "localhost"
    PORT: int = 5432
    NAME: str = "myapp"
    USER: str = "postgres"
    PASSWORD: str = "password"  # noqa: S105

    def connection_string(self) -> str:
        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}/{self.NAME}"

class RedisConfig(BaseModel):
    HOST: str = "localhost"
    PORT: int = 6379
    DB: int = 0

class AppConfig(BaseConfig):
    APP_NAME: str = "MyService"
    DEBUG: bool = False
    DATABASE: DatabaseConfig = DatabaseConfig()
    REDIS: RedisConfig = RedisConfig()

# Usage
config = AppConfig()
logger.info(config.DATABASE.connection_string())
```

## Configuration Template

ArchiPy provides pre-configured templates for common configuration objects:

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.configs.environment_type import EnvironmentType

# Configure logging
logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    # Override only what you need
    APP_NAME: str = "MyCustomApp"

    # The BaseConfig provides default templates for common configurations like:
    # AUTH, DATETIME, ELASTIC, EMAIL, FASTAPI, KAFKA, REDIS, etc.

config = AppConfig()
logger.info(f"Environment: {config.ENVIRONMENT}")  # Default value from BaseConfig (EnvironmentType.LOCAL)
```

## Configuration in Different Components

### With FastAPI

```python
import logging
from fastapi import FastAPI

from archipy.helpers.utils.app_utils import AppUtils
from archipy.configs.base_config import BaseConfig
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Initialize your configuration
    config = BaseConfig()
    BaseConfig.set_global(config)
except Exception as e:
    raise ConfigurationError() from e
else:
    logger.info("Configuration initialized successfully")

# Create a FastAPI app with configuration
app = AppUtils.create_fastapi_app()  # Uses global config by default

# Or provide a specific configuration
# app = AppUtils.create_fastapi_app(config)

# Access config in endpoint
@app.get("/config")
def get_config_info() -> dict[str, str | bool]:
    """Get current configuration information."""
    try:
        config = BaseConfig.global_config()
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        raise ConfigurationError() from e
    else:
        return {
            "app_name": config.FASTAPI.PROJECT_NAME,
            "environment": config.ENVIRONMENT.value,
            "debug": config.FASTAPI.RELOAD
        }
```

### With Database Adapters

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.configs.base_config import BaseConfig

config = BaseConfig.global_config()

# Create PostgreSQL adapter with global config (reads from config.POSTGRES_SQLALCHEMY)
adapter = PostgresSQLAlchemyAdapter()
```

### With Redis Adapters

```python
from archipy.adapters.redis.adapters import RedisAdapter

# Create Redis adapter using global config (reads from config.REDIS automatically)
redis_adapter = RedisAdapter()
```

## Best Practices

1. **Use meaningful defaults**: Configure sensible defaults that work in local development

2. **Never hardcode secrets**: Always use environment variables for sensitive information

3. **Validate configurations**: Use Pydantic validators for complex validation rules

4. **Document configuration options**: Add clear docstrings to your configuration classes

5. **Keep configurations centralized**: Avoid creating multiple configuration sources


## See Also

- [API Reference - Configs](../api_reference/configs.md) - Full configuration API documentation
- [Examples Overview](index.md) - Overview of all examples
