---
title: API Reference
description: Public ArchiPy APIs by package, including adapters, configuration, helpers, and models.
---

# API Reference

Find public classes, functions, and types by package. For a working example, use the [Tutorials](../tutorials/index.md).

## Core Modules

<div class="grid cards docs-entry-grid docs-api-grid" markdown="1">
<div class="card" markdown="1">

### Adapters

Ports and implementations for external services.

- [Adapter overview](adapters/index.md) and [Base SQLAlchemy](adapters/base.md)
- [PostgreSQL](adapters/postgres.md), [MySQL](adapters/mysql.md), [SQLite](adapters/sqlite.md), [StarRocks](adapters/starrocks.md), [ScyllaDB](adapters/scylladb.md)
- [Redis](adapters/redis.md), [Elasticsearch](adapters/elasticsearch.md), [MinIO](adapters/minio.md)
- [Kafka](adapters/kafka.md), [Temporal](adapters/temporal.md), [Email](adapters/email.md)
- [Keycloak](adapters/keycloak.md), [Vault](adapters/vault.md), [Payment Gateways](adapters/payment_gateways.md)

</div>
<div class="card" markdown="1">

### Configs

[Configuration classes](configs.md) for application settings and adapter connections.

</div>
<div class="card" markdown="1">

### Helpers

[Helper overview](helpers/index.md) and APIs for common application concerns.

- [Decorators](helpers/decorators.md), [Interceptors](helpers/interceptors.md), [Metaclasses](helpers/metaclasses.md)
- [Errors](helpers/errors.md) and [Utilities](helpers/utils.md)

</div>
<div class="card" markdown="1">

### Models

[Model overview](models/index.md) and types shared across application layers.

- [DTOs](models/dtos.md), [Entities](models/entities.md), [Errors](models/errors.md), [Types](models/types.md)

</div>
</div>

## Source Code Organization

Core APIs live in `archipy/`. Optional adapters live in workspace packages under `packages/` and use the
`archipy.adapters` namespace. See [Project Structure](../getting-started/project_structure.md) for the application layout.

## API Stability

ArchiPy follows semantic versioning. Stable APIs are covered by that policy. Beta APIs can change significantly and alpha
APIs are experimental. See the [Changelog](../community/changelog/index.md) for changes between versions.

## Contributing

See the [Contributing Guide](../community/contributing.md) for development setup and documentation changes.
