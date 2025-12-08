# Examples

This section contains practical examples of using ArchiPy components with **Python 3.14 type hints**, **proper exception handling patterns**, and **comprehensive error chaining**.

All examples follow ArchiPy's coding standards:

- ✅ **Python 3.14 Type Hints**: Using `|` for unions, lowercase built-in types (`str`, `int`, `list`, `dict`)
- ✅ **Exception Chaining**: All exceptions use `raise ... from e` to preserve error context
- ✅ **Try-Except-Else Pattern**: Explicit `else` blocks with return statements for clear control flow
- ✅ **Proper Logging**: Using `logger` instead of `print()` statements throughout
- ✅ **Domain-Specific Errors**: ArchiPy custom exceptions instead of generic `ValueError` or `Exception`

## Adapters

Learn how to use ArchiPy's database, cache, messaging, and storage adapters with complete error handling:

- [PostgreSQL](adapters/postgres.md) - Database operations with SQLAlchemy and atomic transactions
- [SQLite](adapters/sqlite.md) - Lightweight database adapter for local storage
- [StarRocks](adapters/starrocks.md) - Analytics database adapter
- [ScyllaDB](adapters/scylladb.md) - NoSQL database adapter for ScyllaDB and Apache Cassandra
- [Redis](adapters/redis.md) - Cache operations, pub/sub, and async mock testing
- [Email](adapters/email.md) - Email sending with proper error handling
- [Keycloak](adapters/keycloak.md) - Authentication and authorization with proper exception chaining
- [MinIO](adapters/minio.md) - Object storage operations with presigned URLs
- [Kafka](adapters/kafka.md) - Message streaming with producer/consumer patterns
- [Temporal](adapters/temporal.md) - Workflow orchestration
- [Payment Gateways](adapters/parsian_payment.md) - Iranian payment gateway integration

## Helpers

Utility functions and decorators following best practices:

- [Decorators](helpers/decorators.md) - Retry, timeout, caching, and transaction decorators with Python 3.14 types
- [Interceptors](helpers/interceptors.md) - gRPC and FastAPI interceptors for cross-cutting concerns
- [Utils](helpers/utils.md) - Datetime, JWT, password, file, and validation utilities with proper error handling

## Configuration

Type-safe configuration management:

- [Configuration Management](config_management.md) - Environment-based configuration with Pydantic and security best practices

## Testing

Behavior-Driven Development with Behave:

- [BDD Testing](bdd_testing.md) - Writing Gherkin scenarios and step definitions with exception chaining

## Models

Data Transfer Objects and type-safe models:

- [Protobuf DTOs](models/protobuf_dtos.md) - Converting between Pydantic DTOs and Protocol Buffers with Python 3.14 syntax

## Error Handling

Comprehensive error handling patterns:

- [Error Handling Examples](error_handling.md) - Domain-specific exceptions, error recovery, and proper exception chaining

---

> **Note**: All code examples in this section have been updated to follow ArchiPy's architectural principles and Python 3.14 best practices. Each adapter example includes links to its corresponding BDD test scenarios and API reference documentation.
