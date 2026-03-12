---
title: ScyllaDB Adapter Guide
description: Practical examples for using the ArchiPy ScyllaDB adapter.
---

# ScyllaDB Adapter Guide

The ScyllaDB adapter provides a clean, Pythonic interface for interacting with ScyllaDB and Apache Cassandra databases. It supports both synchronous and asynchronous operations, prepared statements, batch operations, TTL (Time To Live), and connection pool monitoring.

## Installation

The ScyllaDB adapter is included with ArchiPy. Ensure you have the required dependencies:

```bash
uv add "archipy[scylladb]"
```

!!! tip
    The ScyllaDB adapter is an optional extra. Install it only when ScyllaDB or Cassandra support is required.

## Configuration

Configure the ScyllaDB adapter via environment variables or a `ScyllaDBConfig` object.

### Environment Variables

```bash
SCYLLADB__CONTACT_POINTS='["node1.example.com", "node2.example.com"]'
SCYLLADB__PORT=9042
SCYLLADB__KEYSPACE=my_keyspace
SCYLLADB__USERNAME=scylla_user
SCYLLADB__PASSWORD=secure_password
SCYLLADB__CONSISTENCY_LEVEL=QUORUM
SCYLLADB__CONNECT_TIMEOUT=10
SCYLLADB__REQUEST_TIMEOUT=10
```

### Direct Configuration

```python
from archipy.configs.config_template import ScyllaDBConfig
from pydantic import SecretStr

config = ScyllaDBConfig(
    CONTACT_POINTS=["node1.example.com", "node2.example.com"],
    PORT=9042,
    KEYSPACE="production_keyspace",
    USERNAME="scylla_user",
    PASSWORD=SecretStr("secure_password"),
    CONSISTENCY_LEVEL="QUORUM",
    COMPRESSION=True,
    CONNECT_TIMEOUT=10,
    REQUEST_TIMEOUT=10,
)
```

### Connection Pool Configuration

```python
config = ScyllaDBConfig(
    CONTACT_POINTS=["localhost"],
    PORT=9042,
    # Connection pool settings (recommended: 1-3 connections per CPU core)
    MAX_CONNECTIONS_PER_HOST=2,
    MIN_CONNECTIONS_PER_HOST=1,
    CORE_CONNECTIONS_PER_HOST=1,
    MAX_REQUESTS_PER_CONNECTION=100,
    ENABLE_CONNECTION_POOL_MONITORING=True,
)
```

### Datacenter-Aware Configuration

```python
config = ScyllaDBConfig(
    CONTACT_POINTS=["dc1-node1", "dc1-node2"],
    PORT=9042,
    LOCAL_DC="datacenter1",
    REPLICATION_STRATEGY="NetworkTopologyStrategy",
    REPLICATION_CONFIG={"datacenter1": 3, "datacenter2": 2},
)
```

## Basic Usage

### Synchronous Adapter

```python
import logging

from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.configs.config_template import ScyllaDBConfig
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Using default configuration
    adapter = ScyllaDBAdapter()

    # Using custom configuration
    config = ScyllaDBConfig(
        CONTACT_POINTS=["localhost"],
        PORT=9042,
        KEYSPACE="my_keyspace",
    )
    adapter = ScyllaDBAdapter(config)
except DatabaseConnectionError as e:
    logger.error(f"Failed to connect to ScyllaDB: {e}")
    raise
```

### Asynchronous Adapter

```python
import asyncio
import logging

from archipy.adapters.scylladb import AsyncScyllaDBAdapter
from archipy.configs.config_template import ScyllaDBConfig
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


async def main() -> None:
    try:
        config = ScyllaDBConfig(
            CONTACT_POINTS=["localhost"],
            PORT=9042,
            KEYSPACE="my_keyspace",
        )
        adapter = AsyncScyllaDBAdapter(config)
    except DatabaseConnectionError as e:
        logger.error(f"Failed to connect to ScyllaDB: {e}")
        raise
    else:
        logger.info("Connected to ScyllaDB successfully")
        logger.info(f"Adapter ready: {adapter}")


# Run the async function
asyncio.run(main())
```

## Basic CRUD Operations

### Create Keyspace and Table

```python
import logging

from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

adapter = ScyllaDBAdapter()

try:
    # Create keyspace
    adapter.create_keyspace("my_app", replication_factor=3)
    adapter.use_keyspace("my_app")

    # Create table
    table_schema = """
        CREATE TABLE IF NOT EXISTS users (
            id int PRIMARY KEY,
            username text,
            email text,
            created_at timestamp
        )
    """
    adapter.create_table(table_schema)
except DatabaseQueryError as e:
    logger.error(f"Failed to create keyspace or table: {e}")
    raise
else:
    logger.info("Keyspace and table created successfully")
```

### Insert Data

```python
import logging

from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Simple insert
    adapter.insert("users", {
        "id": 1,
        "username": "alice",
        "email": "alice@example.com",
        "created_at": "2025-01-01 00:00:00"
    })
except DatabaseQueryError as e:
    logger.error(f"Failed to insert data: {e}")
    raise
else:
    logger.info("Data inserted successfully")
```

### Select Data

```python
import logging

from archipy.models.errors import DatabaseQueryError, NotFoundError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Select all rows
    all_users = adapter.select("users")

    # Select with conditions
    user = adapter.select("users", conditions={"id": 1})

    # Select specific columns
    user_info = adapter.select("users", columns=["username", "email"], conditions={"id": 1})
except DatabaseQueryError as e:
    logger.error(f"Failed to select data: {e}")
    raise
else:
    if not user:
        raise NotFoundError(resource_type="user", additional_data={"id": 1})
    logger.info(f"Found user: {user[0].username}")
```

### Update Data

```python
import logging

from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

try:
    adapter.update(
        "users",
        data={"email": "newemail@example.com"},
        conditions={"id": 1}
    )
except DatabaseQueryError as e:
    logger.error(f"Failed to update data: {e}")
    raise
else:
    logger.info("Data updated successfully")
```

### Delete Data

```python
import logging

from archipy.models.errors import DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)

try:
    adapter.delete("users", conditions={"id": 1})
except DatabaseQueryError as e:
    logger.error(f"Failed to delete data: {e}")
    raise
else:
    logger.info("Data deleted successfully")
```

## Helper Methods

### Count Rows

```python
# Count all rows
total_users = adapter.count("users")
logger.info(f"Total users: {total_users}")

# Count with conditions (uses ALLOW FILTERING)
active_users = adapter.count("users", conditions={"active": True})
logger.info(f"Active users: {active_users}")
```

**Note:** When using conditions with `count()`, the query automatically includes `ALLOW FILTERING` to support filtering on non-primary key columns. Be aware that this may impact performance on large tables.

### Check if Row Exists

```python
# Check if a specific row exists
if adapter.exists("users", {"id": 1}):
    logger.info("User exists")
else:
    logger.info("User not found")

# Check with multiple conditions (uses ALLOW FILTERING)
if adapter.exists("users", {"username": "alice", "active": True}):
    logger.info("Active user 'alice' exists")
```

**Note:** The `exists()` method uses `ALLOW FILTERING` to support checking conditions on any column. For best performance, use primary key columns in the conditions when possible.

## Prepared Statements

Prepared statements improve performance for repeated queries and are automatically cached.

```python
# Prepare a statement
insert_stmt = adapter.prepare(
    "INSERT INTO users (id, username, email) VALUES (:id, :username, :email)"
)

# Execute prepared statement multiple times
for i in range(100):
    adapter.execute_prepared(insert_stmt, {
        "id": i,
        "username": f"user{i}",
        "email": f"user{i}@example.com"
    })
```

### Prepared Statement Caching

Prepared statements are cached automatically when enabled in configuration:

```python
config = ScyllaDBConfig(
    ENABLE_PREPARED_STATEMENT_CACHE=True,
    PREPARED_STATEMENT_CACHE_SIZE=100,
    PREPARED_STATEMENT_CACHE_TTL_SECONDS=3600,  # 1 hour
)
adapter = ScyllaDBAdapter(config)
```

## Batch Operations

Execute multiple statements atomically:

```python
statements = [
    "INSERT INTO users (id, username) VALUES (1, 'alice')",
    "INSERT INTO users (id, username) VALUES (2, 'bob')",
    "INSERT INTO users (id, username) VALUES (3, 'charlie')",
]

adapter.batch_execute(statements)
```

## TTL Support

Set Time To Live for data that should automatically expire:

### Insert with TTL

```python
# Insert data that expires in 1 hour (3600 seconds)
adapter.insert(
    "cache",
    data={"key": "session_123", "value": "user_data"},
    ttl=3600
)
```

### Update with TTL

```python
# Update data with new TTL
adapter.update(
    "cache",
    data={"value": "updated_data"},
    conditions={"key": "session_123"},
    ttl=7200  # 2 hours
)
```

### Use Cases for TTL

```python
# Session management (30 minutes)
adapter.insert("sessions", {
    "session_id": "abc123",
    "user_id": 42,
    "data": "session_data"
}, ttl=1800)

# Rate limiting (1 minute)
adapter.insert("rate_limits", {
    "user_id": 42,
    "endpoint": "/api/data",
    "count": 1
}, ttl=60)

# Temporary cache (1 day)
adapter.insert("temp_cache", {
    "cache_key": "expensive_computation",
    "result": "cached_value"
}, ttl=86400)
```

## Async Operations

All operations have async equivalents:

```python
import asyncio
import logging

from archipy.adapters.scylladb import AsyncScyllaDBAdapter

logger = logging.getLogger(__name__)

async def main() -> None:
    adapter = AsyncScyllaDBAdapter()

    # Create keyspace
    await adapter.create_keyspace("async_app", replication_factor=1)
    await adapter.use_keyspace("async_app")

    # Create table
    await adapter.create_table("""
        CREATE TABLE IF NOT EXISTS products (
            id int PRIMARY KEY,
            name text,
            price double
        )
    """)

    # Insert data
    await adapter.insert("products", {
        "id": 1,
        "name": "Laptop",
        "price": 999.99
    })

    # Select data
    products = await adapter.select("products")

    # Count rows
    total = await adapter.count("products")
    logger.info(f"Total products: {total}")

    # Check existence
    exists = await adapter.exists("products", {"id": 1})
    logger.info(f"Product exists: {exists}")

    # Insert with TTL
    await adapter.insert("cache", {
        "key": "temp",
        "value": "data"
    }, ttl=3600)

asyncio.run(main())
```

## Connection Pool Monitoring

Monitor connection pool health and performance:

```python
import logging

from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.configs.config_template import ScyllaDBConfig

logger = logging.getLogger(__name__)

# Enable monitoring
config = ScyllaDBConfig(
    CONTACT_POINTS=["localhost"],
    ENABLE_CONNECTION_POOL_MONITORING=True,
)
adapter = ScyllaDBAdapter(config)

# Get pool statistics
stats = adapter.get_pool_stats()

logger.info(f"Monitoring enabled: {stats['monitoring_enabled']}")
logger.info(f"Total hosts: {stats.get('total_hosts', 0)}")
logger.info(f"Total open connections: {stats.get('total_open_connections', 0)}")
logger.info(f"Total in-flight queries: {stats.get('total_in_flight_queries', 0)}")

# Per-host statistics
for host_stat in stats.get('hosts', []):
    logger.info(f"Host: {host_stat['host']}")
    logger.info(f"  Open connections: {host_stat['open_connections']}")
    logger.info(f"  In-flight queries: {host_stat['in_flight_queries']}")
```

## Advanced Configuration

### Retry Policies

```python
# Exponential backoff (default)
config = ScyllaDBConfig(
    RETRY_POLICY="EXPONENTIAL_BACKOFF",
    RETRY_MAX_NUM_RETRIES=3,
    RETRY_MIN_INTERVAL=0.1,
    RETRY_MAX_INTERVAL=10.0,
)

# No retries (fail fast)
config = ScyllaDBConfig(
    RETRY_POLICY="FALLTHROUGH",
)
```

### Consistency Levels

```python
config = ScyllaDBConfig(
    CONSISTENCY_LEVEL="QUORUM",  # Options: ONE, TWO, THREE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, LOCAL_ONE, ANY
)
```

### Shard Awareness

```python
# Disable for Docker/NAT environments
config = ScyllaDBConfig(
    DISABLE_SHARD_AWARENESS=True,
)
```

### Protocol Version

```python
config = ScyllaDBConfig(
    PROTOCOL_VERSION=4,  # 3, 4, or 5
)
```

## Error Handling

The adapter maps ScyllaDB/Cassandra exceptions to ArchiPy's standard exceptions with proper exception chaining:

```python
import logging

from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseQueryError,
    NotFoundError,
    ServiceUnavailableError,
    ConnectionTimeoutError,
    InvalidCredentialsError,
)

# Configure logging
logger = logging.getLogger(__name__)

adapter = ScyllaDBAdapter()

try:
    result = adapter.select("nonexistent_table")
except NotFoundError as e:
    # The adapter's exception handler will have already
    # converted the exception with proper chaining using `from e`
    logger.error(f"Table not found: {e}")
    raise
except DatabaseQueryError as e:
    logger.error(f"Query error: {e}")
    raise
except ServiceUnavailableError as e:
    logger.error(f"ScyllaDB unavailable: {e}")
    raise
except ConnectionTimeoutError as e:
    logger.error(f"Connection timeout: {e}")
    raise
except DatabaseConnectionError as e:
    logger.error(f"Connection error: {e}")
    raise
else:
    logger.info(f"Query executed successfully, found {len(result)} rows")
    return result
```

## Best Practices

### 1. Connection Pooling

Configure connection pools based on your cluster size and workload:

```python
# For production: 1-3 connections per CPU core per node
config = ScyllaDBConfig(
    MAX_CONNECTIONS_PER_HOST=2,
    MIN_CONNECTIONS_PER_HOST=1,
    CORE_CONNECTIONS_PER_HOST=1,
)
```

### 2. Use Prepared Statements

For repeated queries, always use prepared statements:

```python
# Good
stmt = adapter.prepare("SELECT * FROM users WHERE id = :id")
for user_id in user_ids:
    adapter.execute_prepared(stmt, {"id": user_id})

# Avoid
for user_id in user_ids:
    adapter.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

### 3. Choose Appropriate Consistency Levels

```python
# For reads that can tolerate stale data
config = ScyllaDBConfig(CONSISTENCY_LEVEL="ONE")

# For critical writes
config = ScyllaDBConfig(CONSISTENCY_LEVEL="QUORUM")

# For strong consistency
config = ScyllaDBConfig(CONSISTENCY_LEVEL="ALL")
```

### 4. Use TTL for Temporary Data

```python
# Session data
adapter.insert("sessions", session_data, ttl=1800)  # 30 minutes

# Cache entries
adapter.insert("cache", cache_data, ttl=3600)  # 1 hour

# Rate limiting
adapter.insert("rate_limits", limit_data, ttl=60)  # 1 minute
```

### 5. Monitor Connection Pools

Enable monitoring in production:

```python
config = ScyllaDBConfig(
    ENABLE_CONNECTION_POOL_MONITORING=True,
)

# Periodically check pool health
stats = adapter.get_pool_stats()
if stats.get('total_open_connections', 0) > threshold:
    logger.warning("High connection count detected")
```

### 6. Use Datacenter-Aware Routing

For multi-datacenter deployments:

```python
config = ScyllaDBConfig(
    LOCAL_DC="datacenter1",
    REPLICATION_STRATEGY="NetworkTopologyStrategy",
    REPLICATION_CONFIG={"datacenter1": 3, "datacenter2": 2},
)
```

### 7. Health Checks

Implement regular health checks:

```python
health = adapter.health_check()
if health["status"] == "healthy":
    logger.info(f"ScyllaDB healthy (latency: {health['latency_ms']:.2f}ms)")
else:
    logger.info(f"ScyllaDB unhealthy: {health['error']}")
```

### 8. Batch Operations Carefully

Use batch operations for related writes to the same partition:

```python
# Good: Same partition key
statements = [
    "INSERT INTO user_events (user_id, event_id, data) VALUES (1, 1, 'data1')",
    "INSERT INTO user_events (user_id, event_id, data) VALUES (1, 2, 'data2')",
]
adapter.batch_execute(statements)

# Avoid: Different partitions (degrades performance)
statements = [
    "INSERT INTO users (id, name) VALUES (1, 'Alice')",
    "INSERT INTO users (id, name) VALUES (2, 'Bob')",
]
```

### 9. Use Helper Methods Wisely

Leverage count() and exists() for cleaner code, but be mindful of performance:

```python
# Good: Check existence using primary key
if not adapter.exists("users", {"id": 123}):
    adapter.insert("users", user_data)

# Caution: Uses ALLOW FILTERING (may be slow on large tables)
if adapter.exists("users", {"email": "user@example.com"}):
    logger.info("User with this email exists")

# Good: Count all rows
total_items = adapter.count("items")

# Caution: Count with non-primary key conditions uses ALLOW FILTERING
active_count = adapter.count("users", {"active": True})

# Pagination
total_pages = (adapter.count("items") + page_size - 1) // page_size
```

**Performance Tip:** When using `count()` or `exists()` with conditions on non-primary key columns, consider:
- Creating a secondary index for frequently queried columns
- Using materialized views for common query patterns
- Limiting use on large tables in production

### 10. Async for High Concurrency

Use async adapter for I/O-bound workloads:

```python
async def process_users(user_ids: list[str]) -> None:
    adapter = AsyncScyllaDBAdapter()
    tasks = [adapter.select("users", conditions={"id": uid}) for uid in user_ids]
    results = await asyncio.gather(*tasks)
    return results
```

## Complete Example

Here's a complete example demonstrating various features:

```python
from archipy.adapters.scylladb import ScyllaDBAdapter
from archipy.configs.config_template import ScyllaDBConfig
from pydantic import SecretStr

# Configure adapter
config = ScyllaDBConfig(
    CONTACT_POINTS=["localhost"],
    PORT=9042,
    USERNAME="scylla",
    PASSWORD=SecretStr("password"),
    CONSISTENCY_LEVEL="QUORUM",
    MAX_CONNECTIONS_PER_HOST=2,
    ENABLE_CONNECTION_POOL_MONITORING=True,
    ENABLE_PREPARED_STATEMENT_CACHE=True,
)

adapter = ScyllaDBAdapter(config)

# Create schema
adapter.create_keyspace("ecommerce", replication_factor=3)
adapter.use_keyspace("ecommerce")

adapter.create_table("""
    CREATE TABLE IF NOT EXISTS products (
        id int PRIMARY KEY,
        name text,
        category text,
        price double,
        stock int
    )
""")

# Insert products
products = [
    {"id": 1, "name": "Laptop", "category": "Electronics", "price": 999.99, "stock": 50},
    {"id": 2, "name": "Mouse", "category": "Electronics", "price": 25.50, "stock": 200},
    {"id": 3, "name": "Desk", "category": "Furniture", "price": 299.00, "stock": 30},
]

for product in products:
    adapter.insert("products", product)

# Query products
electronics = adapter.select("products", conditions={"category": "Electronics"})
logger.info(f"Found {len(electronics)} electronics")

# Count by category
total_products = adapter.count("products")
logger.info(f"Total products: {total_products}")

# Check stock
if adapter.exists("products", {"id": 1}):
    product = adapter.select("products", conditions={"id": 1})[0]
    logger.info(f"Product: {product.name}, Stock: {product.stock}")

# Update with TTL for flash sale
adapter.update(
    "products",
    data={"price": 799.99},
    conditions={"id": 1},
    ttl=3600  # Sale lasts 1 hour
)

# Monitor pool
stats = adapter.get_pool_stats()
logger.info(f"Pool stats: {stats}")

# Health check
health = adapter.health_check()
logger.info(f"Health: {health['status']}, Latency: {health['latency_ms']:.2f}ms")
```

## References

- [ScyllaDB Documentation](https://docs.scylladb.com/)
- [Cassandra Query Language (CQL)](https://cassandra.apache.org/doc/latest/cql/)
- [ArchiPy Configuration Guide](../../usage.md)

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - ScyllaDB configuration setup
- [BDD Testing](../bdd_testing.md) - Testing ScyllaDB operations
- [API Reference](../../api_reference/adapters/scylladb.md) - Full ScyllaDB adapter API documentation
