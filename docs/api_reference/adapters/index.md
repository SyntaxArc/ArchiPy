# Adapters

The `adapters` module provides concrete implementations of external system integrations following the Ports & Adapters pattern. Each adapter directory exposes a `ports.py` (abstract interface) and an `adapters.py` (concrete implementation).

## Submodules

| Adapter | Description |
|---|---|
| [Base SQLAlchemy](base.md) | Shared SQLAlchemy session management and base CRUD adapter |
| [Redis](redis.md) | Redis cache and key-value store adapter |
| [PostgreSQL](postgres.md) | PostgreSQL database adapter via SQLAlchemy |
| [SQLite](sqlite.md) | SQLite database adapter via SQLAlchemy |
| [StarRocks](starrocks.md) | StarRocks analytical database adapter via SQLAlchemy |
| [Kafka](kafka.md) | Apache Kafka message streaming adapter |
| [Keycloak](keycloak.md) | Keycloak identity and access management adapter |
| [MinIO](minio.md) | MinIO object storage adapter |
| [ScyllaDB](scylladb.md) | ScyllaDB/Cassandra wide-column store adapter |
| [Elasticsearch](elasticsearch.md) | Elasticsearch search engine adapter |
| [Temporal](temporal.md) | Temporal workflow orchestration adapter |
| [Email](email.md) | Email service adapter |
| [Payment Gateways](payment_gateways.md) | Internet payment gateway adapters (Parsian Shaparak) |

## Source Code

📁 Location: `archipy/adapters/`

🔗 [Browse Source](https://github.com/SyntaxArc/ArchiPy/tree/master/archipy/adapters)

## API Stability

| Adapter | Status | Notes |
|---|---|---|
| Base SQLAlchemy | 🟢 Stable | Production-ready |
| Redis | 🟢 Stable | Production-ready |
| PostgreSQL | 🟢 Stable | Production-ready |
| SQLite | 🟢 Stable | Production-ready |
| StarRocks | 🟡 Beta | API may change |
| Kafka | 🟢 Stable | Production-ready |
| Keycloak | 🟢 Stable | Production-ready |
| MinIO | 🟢 Stable | Production-ready |
| ScyllaDB | 🟢 Stable | Production-ready |
| Elasticsearch | 🟢 Stable | Production-ready |
| Temporal | 🟢 Stable | Production-ready |
| Email | 🟢 Stable | Production-ready |
| Payment Gateways | 🟢 Stable | Production-ready |
