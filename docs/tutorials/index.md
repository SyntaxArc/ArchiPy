---
title: Tutorials
description: Overview of all ArchiPy tutorials and usage guides.
---

# Tutorials

This section contains practical examples of using ArchiPy components with **Python 3.14 type hints**, **proper exception
handling patterns**, and **comprehensive error chaining**.

All examples follow ArchiPy's coding standards:

- ✅ **Python 3.14 Type Hints**: Using `|` for unions, lowercase built-in types (`str`, `int`, `list`, `dict`)
- ✅ **Exception Chaining**: All exceptions use `raise ... from e` to preserve error context
- ✅ **Try-Except-Else Pattern**: Explicit `else` blocks with return statements for clear control flow
- ✅ **Proper Logging**: Using `logger` instead of `print()` statements throughout
- ✅ **Domain-Specific Errors**: ArchiPy custom exceptions instead of generic `ValueError` or `Exception`

## Adapters

Learn how to use ArchiPy's database, cache, messaging, and storage adapters with complete error handling:

- [PostgreSQL](adapters/postgres.md) - Database operations with SQLAlchemy and atomic transactions
- [MySQL](adapters/mysql.md) - Database operations with SQLAlchemy and atomic transactions
- [SQLite](adapters/sqlite.md) - Lightweight database adapter for local storage
- [SQLAlchemy Search Totals](adapters/sqlalchemy.md) - Search pagination with total counts for SQLAlchemy adapters
- [StarRocks](adapters/starrocks.md) - Analytics database adapter
- [ScyllaDB](adapters/scylladb.md) - NoSQL database adapter for ScyllaDB and Apache Cassandra
- [Redis](adapters/redis.md) - Cache operations, pub/sub, and testing with testcontainers
- [Elasticsearch](adapters/elasticsearch.md) - Search and indexing with the Elasticsearch adapter
- [Vault](adapters/vault.md) - Secrets management with HashiCorp Vault
- [Email](adapters/email.md) - Email sending with proper error handling
- [Keycloak](adapters/keycloak.md) - Authentication and authorization with proper exception chaining
- [MinIO](adapters/minio.md) - Object storage operations with presigned URLs
- [Kafka](adapters/kafka.md) - Message streaming with producer/consumer patterns
- [Temporal](adapters/temporal.md) - Workflow orchestration
- [Payment Gateways](adapters/payment_gateways.md) - Iranian payment gateway integration (
  [Parsian](https://github.com/SyntaxArc/ArchiPy/tree/master/packages/parsian-ipg),
  [Saman](https://github.com/SyntaxArc/ArchiPy/tree/master/packages/saman-ipg))

## Helpers

Utility functions and decorators following best practices:

- [Decorators](helpers/decorators.md) - Retry, timeout, caching, and transaction decorators with Python 3.14 types
- [Interceptors](helpers/interceptors.md) - gRPC and FastAPI interceptors for cross-cutting concerns
- [Metaclasses](helpers/metaclasses.md) - Singleton and registry metaclass patterns
- [Utils](helpers/utils.md) - Datetime, JWT, password, file, and validation utilities with proper error handling

## Configuration

Type-safe configuration management:

- [Configuration Management](config_management.md) - Environment-based configuration with Pydantic and security best
  practices

## Testing

Behavior-Driven Development with Behave:

- [BDD Testing](testing_strategy.md) — Gherkin features, mock adapters, testcontainers, and the Ports & Adapters testing
  pattern

## Models

Data Transfer Objects and type-safe models:

- [Protobuf DTOs](models/protobuf_dtos.md) - Converting between Pydantic DTOs and Protocol Buffers with Python 3.14
  syntax

## Error Handling

Comprehensive error handling patterns:

- [Error Handling](error_handling.md) - Domain-specific exceptions, error recovery, and proper exception
  chaining

## Dependency Injection

- [Dependency Injection](dependency_injection.md) - Wiring adapters and logics with dependency injection

## Observability

- [Observability](observability.md) - OpenTelemetry traces, metrics, and logs

---

> **Note**: Each adapter tutorial links to its BDD scenarios and API reference.

## See Also

- [API Reference](../api_reference/index.md) - Full API documentation
- [Concepts](../getting-started/concepts.md) - ArchiPy architectural patterns
