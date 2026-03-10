# API Reference

Welcome to the ArchiPy API reference documentation. This section provides detailed information about all modules,
classes, and functions in ArchiPy.

## Core Modules

### Adapters

The adapters module provides standardized interfaces to external systems:

- [Adapters Documentation](adapters.md)
- [Database Adapters](adapters.md#database-adapters)
    - [PostgreSQL](adapters.md#postgresql)
    - [SQLite](adapters.md#sqlite)
    - [StarRocks](adapters.md#starrocks)
    - [ScyllaDB](adapters.md#scylladb)
- [Redis Adapters](adapters.md#redis)
- [Email Adapters](adapters.md#email)
- [Keycloak Adapters](adapters.md#keycloak)
- [MinIO Adapters](adapters.md#minio)
- [Kafka Adapters](adapters.md#kafka)
- [Temporal Adapters](adapters.md#temporal)
- [Payment Gateway Adapters](adapters.md#payment-gateways)
    - [Parsian Shaparak](adapters.md#parsian-shaparak)

### Configs

Configuration management and injection tools:

- [Configs Documentation](configs.md)
- [Base Config](configs.md#base-config)
- [Config Templates](configs.md#config-templates)

### Helpers

Utility functions and support classes:

- [Helpers Documentation](helpers.md)
- [Decorators](../examples/helpers/decorators.md)
- [Utils](../examples/helpers/utils.md)
- [Metaclasses](../examples/helpers/metaclasses.md)
- [Interceptors](../examples/helpers/interceptors.md)

### Models

Core data structures and types:

- [Models Documentation](models.md)
- [Entities](models.md#entities)
- [DTOs](models.md#dtos-data-transfer-objects)
- [Errors](models.md#errors)
- [Types](models.md#types)

## Source Code Organization

The ArchiPy source code is organized into the following structure:

```
archipy/
├── adapters/           # External system integrations
│   ├── base/          # Base adapter implementations
│   │   └── sqlalchemy/  # Base SQLAlchemy components
│   ├── email/         # Email service adapters
│   ├── internet_payment_gateways/ # Payment gateway adapters
│   │   └── ir/        # Country-specific implementations
│   │       └── parsian/  # Parsian Shaparak gateway adapter
│   ├── keycloak/      # Keycloak authentication adapters
│   ├── kafka/         # Kafka message streaming adapters
│   ├── minio/         # MinIO object storage adapters
│   ├── postgres/      # PostgreSQL database adapters
│   │   └── sqlalchemy/  # PostgreSQL SQLAlchemy components
│   ├── redis/         # Redis adapters
│   ├── scylladb/      # ScyllaDB/Cassandra adapters
│   ├── sqlite/        # SQLite database adapters
│   │   └── sqlalchemy/  # SQLite SQLAlchemy components
│   ├── starrocks/     # StarRocks database adapters
│   │   └── sqlalchemy/  # StarRocks SQLAlchemy components
│   └── temporal/      # Temporal workflow orchestration adapters
├── configs/           # Configuration management
│   ├── base_config.py
│   ├── config_template.py
│   └── environment_type.py
├── helpers/           # Utility functions
│   ├── decorators/
│   ├── interceptors/
│   ├── metaclasses/
│   └── utils/
└── models/            # Core data structures
    ├── dtos/
    ├── entities/
    ├── errors/
    └── types/
```

## API Stability

ArchiPy follows semantic versioning and marks API stability as follows:

- 🟢 **Stable**: Production-ready APIs, covered by semantic versioning
- 🟡 **Beta**: APIs that are stabilizing but may have breaking changes
- 🔴 **Alpha**: Experimental APIs that may change significantly

See the [Changelog](../changelog.md) for version history and breaking changes.

## Contributing

For information about contributing to ArchiPy's development, please see:

- [Contributing Guide](../contributing.md)
- [Development Guide](../development.md)
- [Documentation Guide](../contributing-docs.md)
