---
title: API Reference
description: Complete API reference for all ArchiPy modules and packages.
---

# API Reference

Welcome to the ArchiPy API reference documentation. This section provides detailed information about all modules,
classes, and functions in ArchiPy.

## Core Modules

### Adapters

The adapters module provides standardized interfaces to external systems:

- [Adapters Overview](adapters/index.md)
- [Base SQLAlchemy](adapters/base.md)
- [Redis](adapters/redis.md)
- [PostgreSQL](adapters/postgres.md)
- [SQLite](adapters/sqlite.md)
- [StarRocks](adapters/starrocks.md)
- [Kafka](adapters/kafka.md)
- [Keycloak](adapters/keycloak.md)
- [MinIO](adapters/minio.md)
- [ScyllaDB](adapters/scylladb.md)
- [Elasticsearch](adapters/elasticsearch.md)
- [Temporal](adapters/temporal.md)
- [Email](adapters/email.md)
- [Payment Gateways](adapters/payment_gateways.md)

### Configs

Configuration management and injection tools:

- [Configs Documentation](configs.md)

### Helpers

Utility functions and support classes:

- [Helpers Overview](helpers/index.md)
- [Decorators](helpers/decorators.md)
- [Interceptors](helpers/interceptors.md)
- [Metaclasses](helpers/metaclasses.md)
- [Utils](helpers/utils.md)

### Models

Core data structures and types:

- [Models Overview](models/index.md)
- [DTOs](models/dtos.md)
- [Entities](models/entities.md)
- [Errors](models/errors.md)
- [Types](models/types.md)

## Source Code Organization

The ArchiPy source code is organized into the following structure:

```
archipy/
├── adapters/           # External system integrations
│   ├── base/          # Base SQLAlchemy components
│   ├── elasticsearch/ # Elasticsearch adapter
│   ├── email/         # Email service adapter
│   ├── internet_payment_gateways/ # Payment gateway adapters
│   ├── kafka/         # Kafka message streaming adapter
│   ├── keycloak/      # Keycloak authentication adapter
│   ├── minio/         # MinIO object storage adapter
│   ├── postgres/      # PostgreSQL adapter
│   ├── redis/         # Redis adapter
│   ├── scylladb/      # ScyllaDB/Cassandra adapter
│   ├── sqlite/        # SQLite adapter
│   ├── starrocks/     # StarRocks adapter
│   └── temporal/      # Temporal workflow adapter
├── configs/           # Configuration management
│   ├── base_config.py
│   ├── config_template.py
│   └── environment_type.py
├── helpers/           # Utility functions and patterns
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
- [Development Guide](../contributing.md)
- [Documentation Guide](../contributing-docs.md)
