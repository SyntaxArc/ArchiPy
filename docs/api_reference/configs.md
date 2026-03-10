# Configs

## Overview

The configs module provides tools for standardised configuration management and injection, supporting consistent setup
across services like databases, Redis, and email.

## Quick Start

```python
from archipy.configs.base_config import BaseConfig

class AppConfig(BaseConfig):
    APP_NAME: str = "MyService"
    DEBUG: bool = False
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
```

## API Stability

| Component         | Status    | Notes            |
|-------------------|-----------|------------------|
| BaseConfig        | 🟢 Stable | Production-ready |
| Config Templates  | 🟢 Stable | Production-ready |
| Environment Types | 🟢 Stable | Production-ready |

## Core Classes

### BaseConfig {#base-config}

The main configuration class that provides environment variable support, type validation, and global configuration
access.

**Key Features:**

- Environment variable support
- Type validation
- Global configuration access
- Nested configuration support

::: archipy.configs.base_config
    options:
      show_root_heading: true
      show_source: true
      members_order: alphabetical

## Config Templates {#config-templates}

For practical examples, see the [Configuration Management Guide](../examples/config_management.md).

### Database Configs

::: archipy.configs.config_template.SQLAlchemyConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.PostgresSQLAlchemyConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.SQLiteSQLAlchemyConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.StarRocksSQLAlchemyConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.ScyllaDBConfig
    options:
      show_root_heading: true
      show_source: true

### Search & Analytics Configs

::: archipy.configs.config_template.ElasticsearchConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.ElasticsearchAPMConfig
    options:
      show_root_heading: true
      show_source: true

### Service Configs

::: archipy.configs.config_template.RedisConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.KafkaConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.EmailConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.MinioConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.KeycloakConfig
    options:
      show_root_heading: true
      show_source: true

### Web Framework Configs

::: archipy.configs.config_template.FastAPIConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.GrpcConfig
    options:
      show_root_heading: true
      show_source: true

### Observability Configs

::: archipy.configs.config_template.SentryConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.PrometheusConfig
    options:
      show_root_heading: true
      show_source: true

### Payment Configs

::: archipy.configs.config_template.ParsianShaparakConfig
    options:
      show_root_heading: true
      show_source: true

### Application Configs

::: archipy.configs.config_template.AuthConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.FileConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.DatetimeConfig
    options:
      show_root_heading: true
      show_source: true

::: archipy.configs.config_template.TemporalConfig
    options:
      show_root_heading: true
      show_source: true

## Environment Type

::: archipy.configs.environment_type
    options:
      show_root_heading: true
      show_source: true
      show_bases: true

## Source Code

📁 Location: `archipy/configs/`

🔗 [Browse Source](https://github.com/SyntaxArc/ArchiPy/tree/master/archipy/configs)
