---
title: Adapter Examples
description: Overview and index of all ArchiPy adapter usage examples.
---

# Adapter Examples

ArchiPy provides a variety of adapters to help interface with external systems, maintaining a clean separation between
your business logic and external dependencies.

## Available Adapters

| Adapter                   | Purpose                        | Example                                              | API Reference                                     |
|---------------------------|--------------------------------|------------------------------------------------------|---------------------------------------------------|
| [Email](email.md)         | Email sending interface        | Connect to SMTP servers for sending emails           | [API](../../api_reference/adapters/email.md)      |
| [Keycloak](keycloak.md)   | Authentication & authorization | User management and access control with Keycloak     | [API](../../api_reference/adapters/keycloak.md)   |
| [Kafka](kafka.md)         | Message streaming              | Event-driven architectures with Apache Kafka         | [API](../../api_reference/adapters/kafka.md)      |
| [MinIO](minio.md)         | Object storage                 | S3-compatible object storage for files and documents | [API](../../api_reference/adapters/minio.md)      |
| [Payment Gateways](payment_gateways.md) | Payment gateway    | Process online payments with Parsian Shaparak        | [API](../../api_reference/adapters/payment_gateways.md) |
| [PostgreSQL](postgres.md) | Database access                | SQLAlchemy integration for PostgreSQL                | [API](../../api_reference/adapters/postgres.md)   |
| [SQLite](sqlite.md)       | Database access                | SQLAlchemy integration for SQLite                    | [API](../../api_reference/adapters/sqlite.md)     |
| [StarRocks](starrocks.md) | Database access                | SQLAlchemy integration for StarRocks                 | [API](../../api_reference/adapters/starrocks.md)  |
| [ScyllaDB](scylladb.md)   | NoSQL database                 | Wide-column store for ScyllaDB and Cassandra         | [API](../../api_reference/adapters/scylladb.md)   |
| [Elasticsearch](elasticsearch.md) | Search & analytics  | Full-text search, document indexing, aggregations    | [API](../../api_reference/adapters/elasticsearch.md) |
| [Redis](redis.md)         | Key-value store                | Caching, pub/sub, and data storage with Redis        | [API](../../api_reference/adapters/redis.md)      |
| [Temporal](temporal.md)   | Workflow orchestration     | Durable workflow execution and activity coordination  | [API](../../api_reference/adapters/temporal.md)   |

## Adapter Architecture

ArchiPy follows the ports and adapters pattern (hexagonal architecture):

```
┌────────────────────────────────────────┐
│             Domain Logic               │
└───────────────────┬────────────────────┘
                    │ uses
┌───────────────────▼────────────────────┐
│                 Ports                  │
│          (Abstract Interfaces)         │
└───────────────────┬────────────────────┘
                    │ implemented by
┌───────────────────▼────────────────────┐
│                Adapters                │
│         (Concrete Implementations)     │
└───────────────────┬────────────────────┘
                    │ connects to
┌───────────────────▼────────────────────┐
│            External Systems            │
│   (Databases, APIs, Message Queues)    │
└────────────────────────────────────────┘
```

## Creating Custom Adapters

Creating custom adapters is straightforward:

1. Define a port (abstract interface)
2. Implement the adapter class
3. Optionally create a mock implementation

See the [Architecture](../../architecture.md) guide for more details on creating custom adapters.


## See Also

- [API Reference - Adapters](../../api_reference/adapters/index.md) - Full adapters API documentation
- [Examples Overview](../index.md) - Overview of all examples
