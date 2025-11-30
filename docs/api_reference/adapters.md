# Adapters

The `adapters` module provides standardized interfaces to external systems and services. It follows the ports and
adapters pattern (also known as hexagonal architecture) to decouple application logic from external dependencies.

## Key Features

- **Consistent interfaces** for all external services
- **Built-in mock implementations** for testing
- **Port definitions** for dependency inversion
- **Ready-to-use implementations** for common services

## Available Adapters

### Database Adapters

The database adapters provide standardized interfaces for different database systems using SQLAlchemy. Each database
type has its own dedicated adapter implementation.

#### Base SQLAlchemy Components

The base SQLAlchemy components provide the core functionality used by all database-specific adapters:

::: archipy.adapters.base.sqlalchemy.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.base.sqlalchemy.ports
options:
show_root_heading: true
show_source: true

::: archipy.adapters.base.sqlalchemy.session_managers
options:
show_root_heading: true
show_source: true

::: archipy.adapters.base.sqlalchemy.session_manager_registry
options:
show_root_heading: true
show_source: true

#### PostgreSQL

PostgreSQL database adapter with SQLAlchemy integration.

```python
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter, AsyncPostgresSQLAlchemyAdapter

# Create an ORM adapter (uses global config)
orm_adapter = PostgresSQLAlchemyAdapter()

# Use the adapter
users = orm_adapter.query(User).filter(User.active == True).all()
```

::: archipy.adapters.postgres.sqlalchemy.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.postgres.sqlalchemy.session_managers
options:
show_root_heading: true
show_source: true

::: archipy.adapters.postgres.sqlalchemy.session_manager_registry
options:
show_root_heading: true
show_source: true

#### SQLite

SQLite database adapter with SQLAlchemy integration.

```python
from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter, AsyncSQLiteSQLAlchemyAdapter

# Create an ORM adapter (uses global config)
orm_adapter = SQLiteSQLAlchemyAdapter()
```

::: archipy.adapters.sqlite.sqlalchemy.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.sqlite.sqlalchemy.session_managers
options:
show_root_heading: true
show_source: true

::: archipy.adapters.sqlite.sqlalchemy.session_manager_registry
options:
show_root_heading: true
show_source: true

#### StarRocks

StarRocks database adapter with SQLAlchemy integration.

```python
from archipy.adapters.starrocks.sqlalchemy.adapters import StarrocksSQLAlchemyAdapter, AsyncStarrocksSQLAlchemyAdapter

# Create an ORM adapter (uses global config)
orm_adapter = StarrocksSQLAlchemyAdapter()
```

::: archipy.adapters.starrocks.sqlalchemy.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.starrocks.sqlalchemy.session_managers
options:
show_root_heading: true
show_source: true

::: archipy.adapters.starrocks.sqlalchemy.session_manager_registry
options:
show_root_heading: true
show_source: true

#### ScyllaDB

ScyllaDB and Apache Cassandra database adapter with native CQL support.

```python
from archipy.adapters.scylladb.adapters import ScyllaDBAdapter, AsyncScyllaDBAdapter

# Create a ScyllaDB adapter (uses global config)
adapter = ScyllaDBAdapter()

# Create keyspace
adapter.create_keyspace("my_app", replication_factor=3)
adapter.use_keyspace("my_app")

# Create table
adapter.create_table("""
    CREATE TABLE IF NOT EXISTS users (
        id int PRIMARY KEY,
        username text,
        email text
    )
""")

# Insert data
adapter.insert("users", {"id": 1, "username": "alice", "email": "alice@example.com"})

# Select data
users = adapter.select("users", conditions={"id": 1})
```

For detailed examples and usage guidelines, see the [ScyllaDB Adapter Examples](../examples/adapters/scylladb.md).

::: archipy.adapters.scylladb.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.scylladb.ports
options:
show_root_heading: true
show_source: true

### Email

Email sending functionality with standardized interface.

```python
from archipy.adapters.email import EmailAdapter, EmailPort

# Configure email adapter
email_adapter = EmailAdapter(host="smtp.example.com", port=587, username="user", password="pass")

# Send an email
email_adapter.send_email(
    subject="Test Email",
    body="This is a test email",
    recipients=["recipient@example.com"],
)
```

::: archipy.adapters.email.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.email.ports
options:
show_root_heading: true
show_source: true

### Keycloak

Keycloak integration for authentication and authorization services.

```python
from archipy.adapters.keycloak import KeycloakAdapter, AsyncKeycloakAdapter

# Create a Keycloak adapter (synchronous)
keycloak = KeycloakAdapter()  # Uses global config by default

# Authenticate a user
token = keycloak.get_token("username", "password")

# Validate token
is_valid = keycloak.validate_token(token["access_token"])

# Check user roles
has_admin = keycloak.has_role(token["access_token"], "admin")

# Async usage example
import asyncio

async def auth_example():
    # Create async Keycloak adapter
    async_keycloak = AsyncKeycloakAdapter()

    # Get token asynchronously
    token = await async_keycloak.get_token("username", "password")

    # Get user info
    user_info = await async_keycloak.get_userinfo(token["access_token"])
    return user_info

# Run the async example
user_info = asyncio.run(auth_example())
```

For detailed examples and usage guidelines, see the [Keycloak Adapter Examples](../examples/adapters/keycloak.md).

::: archipy.adapters.keycloak.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.keycloak.ports
options:
show_root_heading: true
show_source: true

### MinIO

MinIO integration for S3-compatible object storage operations.

```python
from archipy.adapters.minio import MinioAdapter

# Create a MinIO adapter
minio = MinioAdapter()  # Uses global config by default

# Create a bucket
if not minio.bucket_exists("my-bucket"):
    minio.make_bucket("my-bucket")

# Upload a file
minio.put_object("my-bucket", "document.pdf", "/path/to/local/file.pdf")

# Generate a download URL (valid for 1 hour)
download_url = minio.presigned_get_object("my-bucket", "document.pdf")
```

For detailed examples and usage guidelines, see the [MinIO Adapter Examples](../examples/adapters/minio.md).

::: archipy.adapters.minio.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.minio.ports
options:
show_root_heading: true
show_source: true

### Redis

Redis integration for caching and key-value storage.

```python
from archipy.adapters.redis import RedisAdapter, AsyncRedisAdapter

# Create a Redis adapter (uses global config)
redis = RedisAdapter()
```

::: archipy.adapters.redis.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.redis.ports
options:
show_root_heading: true
show_source: true

### Kafka

Kafka integration for message streaming and event-driven architectures.

```python
from archipy.adapters.kafka import KafkaAdapter

# Create a Kafka adapter
kafka = KafkaAdapter()  # Uses global config by default

# Publish a message
kafka.publish("my-topic", "Hello, Kafka!")

# Consume messages
def process_message(message: dict[str, Any]) -> None:
    print(f"Received: {message['value']}")

kafka.consume("my-topic", process_message)

```

For detailed examples and usage guidelines, see the [Kafka Adapter Examples](../examples/adapters/kafka.md).

::: archipy.adapters.kafka.adapters
options:
show_root_heading: true
show_source: true

::: archipy.adapters.kafka.ports
options:
show_root_heading: true
show_source: true

### Payment Gateways

Integrations with various payment processing services for online transactions.

#### Parsian Shaparak

Parsian Shaparak payment gateway adapter for processing online payments in Iran.

```python
from archipy.adapters.internet_payment_gateways.ir.parsian.adapters import (
    ParsianShaparakPaymentAdapter,
    PaymentRequestDTO,
    ConfirmRequestDTO
)

# Create a Parsian Shaparak payment adapter
payment_adapter = ParsianShaparakPaymentAdapter()  # Uses global config by default

# Create payment request
payment_request = PaymentRequestDTO(
    amount=10000,  # Amount in IRR
    order_id=12345,  # Your unique order ID
    callback_url="https://your-app.com/payment/callback",
)

# Send payment request
payment_response = payment_adapter.initiate_payment(payment_request)

if payment_response.status == 0:  # 0 means success
    # Redirect user to payment page
    payment_url = f"https://pec.shaparak.ir/NewIPG/?Token={payment_response.token}"
```

For detailed examples and usage guidelines, see the [Parsian Payment Gateway Examples](../examples/adapters/parsian_payment.md).

::: archipy.adapters.internet_payment_gateways.ir.parsian.adapters
options:
show_root_heading: true
show_source: true

### Temporal {#temporal}

Temporal workflow orchestration adapter for durable workflow execution and activity coordination.

```python
from archipy.adapters.temporal.adapters import TemporalAdapter
from archipy.adapters.temporal.worker import TemporalWorkerManager
from archipy.adapters.temporal.base import BaseWorkflow, BaseActivity

# Create a Temporal adapter
temporal_adapter = TemporalAdapter()  # Uses global config by default

# Start a workflow execution
workflow_handle = await temporal_adapter.start_workflow(
    workflow="MyWorkflow",
    arg={"input": "data"},
    workflow_id="unique-workflow-id",
    task_queue="my-task-queue"
)

# Execute a workflow and wait for completion
result = await temporal_adapter.execute_workflow(
    workflow="MyWorkflow",
    arg={"input": "data"},
    workflow_id="unique-workflow-id-2",
    task_queue="my-task-queue"
)

# Signal a workflow
await temporal_adapter.signal_workflow(
    workflow_id="unique-workflow-id",
    signal_name="update_signal",
    arg={"update": "data"}
)

# Query a workflow
query_result = await temporal_adapter.query_workflow(
    workflow_id="unique-workflow-id",
    query_name="get_status"
)

# Worker management
worker_manager = TemporalWorkerManager()

# Start a worker
worker_handle = await worker_manager.start_worker(
    task_queue="my-task-queue",
    workflows=[MyWorkflow],
    activities=[my_activity_instance]
)
```

For detailed examples and usage guidelines, see the [Temporal Examples](../examples/adapters/temporal.md).

#### Temporal Adapter

::: archipy.adapters.temporal.adapters
options:
show_root_heading: true
show_source: true

#### Temporal Ports

::: archipy.adapters.temporal.ports
options:
show_root_heading: true
show_source: true

#### Temporal Worker Manager

::: archipy.adapters.temporal.worker
options:
show_root_heading: true
show_source: true

#### Temporal Base Classes

::: archipy.adapters.temporal.base
options:
show_root_heading: true
show_source: true
