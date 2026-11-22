---
title: Tutorials
description: Connect integrations, build application features, and operate ArchiPy services.
---

# Tutorials

Find a guide for the service you want to connect or the feature you want to build. If you are setting up your first
ArchiPy project, start with the [Quickstart](../getting-started/quickstart.md).

## Integrations { #adapters }

### Databases and search

- [PostgreSQL](adapters/postgres.md), [MySQL](adapters/mysql.md), and [SQLite](adapters/sqlite.md) for relational data
- [SQLAlchemy Search Totals](adapters/sqlalchemy.md) for paginated results with total counts
- [StarRocks](adapters/starrocks.md) for analytics and [ScyllaDB](adapters/scylladb.md) for wide-column storage
- [Elasticsearch](adapters/elasticsearch.md) for indexing and [Elasticsearch patterns](adapters/elasticsearch_patterns.md)
  for application-level search

### Caches, files, and secrets

- [Redis](adapters/redis.md) for caching and pub/sub
- [MinIO](adapters/minio.md) for object storage and presigned URLs
- [Vault](adapters/vault.md) for application secrets

### Messaging, workflows, and external services

- [Kafka](adapters/kafka.md) for event streams and [Temporal](adapters/temporal.md) for workflows
- [Keycloak](adapters/keycloak.md) for authentication and authorization
- [Email](adapters/email.md) for outbound messages
- [Payment Gateways](adapters/payment_gateways.md) for Parsian and Saman payments

## Application patterns

### Configuration

[Configuration Management](config_management.md) covers environment variables and validated settings.

### Dependency Injection

[Dependency Injection](dependency_injection.md) shows how to wire adapters into application logic.

### Helpers

- [Decorators](helpers/decorators.md) for retry, timeout, cache, and transaction behavior
- [Interceptors](helpers/interceptors.md) for cross-cutting behavior in gRPC and FastAPI
- [Metaclasses](helpers/metaclasses.md) for singleton and registry patterns
- [Utilities](helpers/utils.md) for dates, JWTs, passwords, and files

### Models

[Protobuf DTOs](models/protobuf_dtos.md) shows how to convert between Pydantic and Protocol Buffers.

### Error Handling

[Error Handling](error_handling.md) covers domain exceptions and preserving underlying error context.

### Testing

[BDD Testing](testing_strategy.md) pairs Behave scenarios with real services through testcontainers.

## Operations

- [Caching](cache.md) for in-process TTL caches
- [Scheduler](scheduler.md) for APScheduler jobs
- [Health Checks and Shutdown](health_checks.md) for readiness checks and graceful shutdown

### Observability

- [Observability](observability.md) for OpenTelemetry traces, metrics, and logs
- [Pydantic AI](pydantic_ai.md) for agent telemetry

## See Also

- [API Reference](../api_reference/index.md) for adapter and helper signatures
- [Concepts](../getting-started/concepts.md) for ArchiPy’s application layers and import rules
