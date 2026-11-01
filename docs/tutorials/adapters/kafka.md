---
title: Kafka Adapter Tutorial
description: Practical examples for using the ArchiPy Kafka adapter, including sync and async variants.
---

# Kafka Adapter Tutorial

The Kafka adapter provides a clean interface for interacting with Apache Kafka through five
separate adapters — covering admin (topic management), synchronous producing/consuming, and
asynchronous producing/consuming via `confluent_kafka.aio`.

## Installation

```bash
uv add "archipy[kafka]"
```

## Configuration

Configure Kafka via environment variables or a `KafkaConfig` object.

### Environment Variables

```bash
KAFKA__BROKERS_LIST='["localhost:9092"]'
KAFKA__CLIENT_ID=my-app
KAFKA__SECURITY_PROTOCOL=PLAINTEXT
KAFKA__ACKS=all
KAFKA__AUTO_OFFSET_RESET=earliest
```

### Direct Configuration

!!! warning
    With `SECURITY_PROTOCOL` set to `SASL_PLAINTEXT` or `SASL_SSL`, `SASL_MECHANISM` is required, and `USERNAME` and
    `PASSWORD` are required for `PLAIN`, `SCRAM-SHA-256` and `SCRAM-SHA-512`. `GSSAPI` and `OAUTHBEARER` need no
    username or password. Load the password from the environment or a secrets store, not from source code.

    Each security setting is applied when it is set, based on `SECURITY_PROTOCOL`: SASL settings for the `SASL_*`
    protocols, and `SSL_CA_FILE`, `SSL_CERT_FILE`, `SSL_KEY_FILE` for `SSL` and `SASL_SSL`. mTLS without SASL works
    with `SECURITY_PROTOCOL="SSL"` and a certificate and key; leave `SSL_CA_FILE` unset to use the system CA store.

```python
from archipy.configs.config_template import KafkaConfig

config = KafkaConfig(
    BROKERS_LIST=["kafka1:9092", "kafka2:9092"],
    CLIENT_ID="my-app",
    SECURITY_PROTOCOL="SASL_SSL",
    SASL_MECHANISM="PLAIN",
    USERNAME="kafka-user",
)
```

!!! warning "Broker hostname verification is on by default"
    With `SECURITY_PROTOCOL` set to `SSL` or `SASL_SSL`, the adapters verify that each broker certificate matches the broker
    hostname (`SSL_ENDPOINT_IDENTIFICATION_ALGORITHM="https"`, the default). Earlier releases turned this check off.
    Brokers reached by IP address, or whose certificate SAN does not list the address you connect to, now fail the TLS
    handshake. Fix the certificates if you can. To keep the old behavior, set
    `SSL_ENDPOINT_IDENTIFICATION_ALGORITHM="none"` (or `KAFKA__SSL_ENDPOINT_IDENTIFICATION_ALGORITHM=none`); a warning
    is logged because this leaves connections open to man-in-the-middle attacks.

### Connection, Identity and Timeout Settings

`CLIENT_ID` (`client.id`) and `CONNECTIONS_MAX_IDLE_MS` (`connections.max.idle.ms`) are applied to every client, and
`LIST_TOPICS_TIMEOUT_MS` is the timeout `list_topics()` and the producer health check use when no `timeout` is passed.
The options below are optional; `None` leaves the librdkafka default in place.

| Field                      | librdkafka option          | Applies to |
|----------------------------|----------------------------|------------|
| `SOCKET_TIMEOUT_MS`        | `socket.timeout.ms`        | all        |
| `RECONNECT_BACKOFF_MAX_MS` | `reconnect.backoff.max.ms` | all        |
| `RETRY_BACKOFF_MS`         | `retry.backoff.ms`         | all        |
| `MESSAGE_TIMEOUT_MS`       | `message.timeout.ms`       | producers  |
| `GROUP_INSTANCE_ID`        | `group.instance.id`        | consumers  |
| `ENABLE_AUTO_OFFSET_STORE` | `enable.auto.offset.store` | consumers  |

!!! note
    librdkafka treats `message.timeout.ms` as an alias of `delivery.timeout.ms`, so a set `MESSAGE_TIMEOUT_MS` takes
    precedence over `DELIVERY_TIMEOUT_MS`. Earlier releases ignored `CLIENT_ID`, `CONNECTIONS_MAX_IDLE_MS` and
    `LIST_TOPICS_TIMEOUT_MS`; `list_topics()` without a `timeout` now waits `LIST_TOPICS_TIMEOUT_MS` (5 seconds by
    default) instead of 1 second. Pass `timeout=` to choose a value per call.

### Async-Specific Configuration

The async adapters respect three additional fields that tune the underlying `AIOProducer` /
`AIOConsumer` thread pools:

| Field                     | Default | Description                                      |
|---------------------------|---------|--------------------------------------------------|
| `PRODUCER_MAX_WORKERS`    | `4`     | Thread pool workers for `AIOProducer`            |
| `PRODUCER_BATCH_SIZE`     | `1000`  | Max messages per `AIOProducer` batch             |
| `PRODUCER_BUFFER_TIMEOUT` | `1.0`   | Buffer flush timeout (seconds) for `AIOProducer` |
| `CONSUMER_MAX_WORKERS`    | `2`     | Thread pool workers for `AIOConsumer`            |

```python
from archipy.configs.config_template import KafkaConfig

async_config = KafkaConfig(
    BROKERS_LIST=["kafka1:9092"],
    PRODUCER_MAX_WORKERS=8,
    PRODUCER_BATCH_SIZE=500,
    PRODUCER_BUFFER_TIMEOUT=0.5,
    CONSUMER_MAX_WORKERS=4,
)
```

## Basic Usage

### Admin — Topic Management

`KafkaAdminAdapter` handles topic CRUD operations.

```python
import logging

from archipy.adapters.kafka.adapters import KafkaAdminAdapter
from archipy.models.errors import (
    AlreadyExistsError,
    InternalError,
    InvalidArgumentError,
    NotFoundError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Use global configuration
admin = KafkaAdminAdapter()

# Create a topic. The call waits for the broker to confirm (optional `timeout` in seconds,
# default REQUEST_TIMEOUT_MS), so AlreadyExistsError and broker failures are raised here.
try:
    admin.create_topic("my-topic", num_partitions=3, replication_factor=1)
except AlreadyExistsError:
    logger.info("Topic already exists")
except InvalidArgumentError as e:
    logger.error("Invalid topic configuration: %s", e)
    raise
except ServiceUnavailableError as e:
    logger.error("Kafka service unavailable: %s", e)
    raise
except InternalError as e:
    logger.error("Internal error creating topic: %s", e)
    raise
else:
    logger.info("Topic created successfully")

# List all topics — returns ClusterMetadata
try:
    cluster_metadata = admin.list_topics()
except InternalError as e:
    logger.error("Failed to list topics: %s", e)
    raise
else:
    for topic_name in cluster_metadata.topics:
        logger.info("Topic: %s", topic_name)

# Delete topics — accepts a list of topic names; a missing topic raises NotFoundError
try:
    admin.delete_topic(["my-topic"])
except NotFoundError:
    logger.info("Topic does not exist")
except InvalidArgumentError as e:
    logger.error("Invalid topic list: %s", e)
    raise
except InternalError as e:
    logger.error("Failed to delete topic: %s", e)
    raise
else:
    logger.info("Topic deleted successfully")
```

### Producer — Publishing Messages

`KafkaProducerAdapter` is bound to a single topic at construction time.

!!! note
    `ENABLE_IDEMPOTENCE` requires `ACKS="all"` (the default), and `TRANSACTIONAL_ID` requires `ENABLE_IDEMPOTENCE`.
    Other combinations raise a `ConfigurationError` when the config is validated.

!!! note
    `SECURITY_PROTOCOL` and `SASL_MECHANISM` are case-insensitive (`ssl` equals `SSL`). `SECURITY_PROTOCOL` must be
    `PLAINTEXT`, `SSL`, `SASL_PLAINTEXT` or `SASL_SSL`; any other value raises a `ConfigurationError`.

```python
import logging

from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.models.errors import InternalError, NetworkError, ResourceExhaustedError

logger = logging.getLogger(__name__)

# Requires topic_name at construction
producer = KafkaProducerAdapter(topic_name="my-topic")

# Publish a simple string message
try:
    producer.produce("Hello, Kafka!")
except NetworkError as e:
    logger.error("Network error producing message: %s", e)
    raise
except ResourceExhaustedError as e:
    logger.error("Producer queue full: %s", e)
    raise
except InternalError as e:
    logger.error("Failed to produce message: %s", e)
    raise
else:
    logger.info("Message enqueued successfully")

# Publish with a message key (for partition affinity). Without a key the message is currently sent with an empty
# key (b""), which emits a DeprecationWarning; set KAFKA.EMPTY_KEY_FOR_MISSING_KEY=False to send no key (None).
try:
    producer.produce("Hello, Kafka with key!", key="user-123")
except InternalError as e:
    logger.error("Failed to produce keyed message: %s", e)
    raise
else:
    logger.info("Keyed message enqueued")

# Observe the delivery outcome: the callback runs while the producer is polled (later produce calls and flush).
# A failed delivery is also logged with topic, partition and key length, never with the payload.
def on_delivery(error, message):
    if error is not None:
        logger.error("Delivery to %s failed: %s", message.topic(), error)


producer.produce("Hello, Kafka with callback!", on_delivery=on_delivery)

# Flush to ensure all pending messages are delivered
try:
    producer.flush(timeout=10)
except InternalError as e:
    logger.error("Flush failed: %s", e)
    raise
else:
    logger.info("All messages flushed")
```

!!! warning
    Messages are enqueued, not delivered, when you call the producer. Call `flush()` before the process exits, or
    pending messages can be lost.

### Producer Transactions

Set `TRANSACTIONAL_ID` (with `ENABLE_IDEMPOTENCE=True`) and the synchronous `KafkaProducerAdapter` initializes
transactions when it is created. Wrap the messages that must be delivered together in a transaction. Read them with a
consumer that uses `ISOLATION_LEVEL="read_committed"`.

```python
producer = KafkaProducerAdapter(topic_name="my-topic")

producer.begin_transaction()
try:
    producer.produce("first")
    producer.produce("second")
except Exception:
    producer.abort_transaction()
    raise
else:
    producer.commit_transaction()
```

`TRANSACTION_TIMEOUT_MS` sets `transaction.timeout.ms`; it must not be lower than the delivery timeout
(`MESSAGE_TIMEOUT_MS` or `DELIVERY_TIMEOUT_MS`). When unset it is 60000, or the delivery timeout when that is higher.

!!! warning
    `AsyncKafkaProducerAdapter` does not support transactions: with `TRANSACTIONAL_ID` set it raises a
    `ConfigurationError` on first use.

### Producer Health Check

```python
import logging

from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.models.errors import UnavailableError

logger = logging.getLogger(__name__)

producer = KafkaProducerAdapter(topic_name="my-topic")

try:
    producer.validate_healthiness()
except UnavailableError as e:
    logger.error("Kafka producer is unhealthy: %s", e)
    raise
else:
    logger.info("Kafka producer connection is healthy")
```

### Consumer — Consuming Messages

`KafkaConsumerAdapter` requires a `group_id` and **exactly one** of `topic_list` (subscribe)
or `partition_list` (assign). Providing both or neither raises `InvalidArgumentError`.

```python
import logging

from archipy.adapters.kafka.adapters import KafkaConsumerAdapter
from archipy.models.errors import InternalError, ServiceUnavailableError

logger = logging.getLogger(__name__)

# Subscribe to topics by name
consumer = KafkaConsumerAdapter(
    group_id="my-consumer-group",
    topic_list=["my-topic"],
)

# Batch consume — returns list[Message]. Messages that carry a harmless error (end of partition, unknown topic)
# are skipped; fatal, authentication and authorization errors and a lost connection to all brokers are raised.
try:
    messages = consumer.batch_consume(messages_number=10, timeout=5)
except ServiceUnavailableError as e:
    logger.error("Kafka unavailable during consume: %s", e)
    raise
except InternalError as e:
    logger.error("Error consuming messages: %s", e)
    raise
else:
    for msg in messages:
        value = msg.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        logger.info("Received: %s", value)
        # Commit offset after processing
        consumer.commit(msg, asynchronous=False)

# Poll for a single message
msg = consumer.poll(timeout=1)
if msg is not None:
    logger.info("Polled: %s", msg.value().decode("utf-8"))
```

### Assign to Specific Partitions

```python
import logging

from confluent_kafka import TopicPartition

from archipy.adapters.kafka.adapters import KafkaConsumerAdapter

logger = logging.getLogger(__name__)

# Assign to specific topic partitions (manual partition control)
consumer = KafkaConsumerAdapter(
    group_id="partition-consumer-group",
    partition_list=[
        TopicPartition("my-topic", partition=0),
        TopicPartition("my-topic", partition=1),
    ],
)

messages = consumer.batch_consume(messages_number=100, timeout=10)
logger.info("Consumed %d messages from assigned partitions", len(messages))
```

## Async Adapters

The `AsyncKafkaProducerAdapter` and `AsyncKafkaConsumerAdapter` wrap `confluent_kafka.aio`'s
`AIOProducer` and `AIOConsumer` respectively. Both use **lazy initialisation** — the underlying
`AIOProducer` / `AIOConsumer` is created on the first `await` call, not at construction time.
This makes them safe to construct in non-async contexts (e.g., at module level or in
dependency-injection containers) without requiring a running event loop.

### Async Producer

```python
import asyncio
import logging

from archipy.adapters.kafka.adapters import AsyncKafkaProducerAdapter
from archipy.models.errors import InternalError, NetworkError, ResourceExhaustedError, UnavailableError

logger = logging.getLogger(__name__)


async def publish_events() -> None:
    """Publish a batch of events using the async producer.

    Raises:
        NetworkError: If a network error prevents message delivery.
        ResourceExhaustedError: If the internal producer queue is full.
        InternalError: If an unexpected error occurs.
    """
    producer = AsyncKafkaProducerAdapter(topic_name="events")

    try:
        await producer.produce("event-payload-1")
        await producer.produce("event-payload-2", key="user-42")
        await producer.flush()
    except NetworkError as e:
        logger.error("Network error: %s", e)
        raise
    except ResourceExhaustedError as e:
        logger.error("Producer queue exhausted: %s", e)
        raise
    except InternalError as e:
        logger.error("Unexpected error: %s", e)
        raise
    finally:
        await producer.close()

    logger.info("Events published successfully")


asyncio.run(publish_events())
```

### Async Consumer

`AsyncKafkaConsumerAdapter` mirrors the sync consumer API — provide exactly one of
`topic_list` or `partition_list`.

```python
import asyncio
import logging

from archipy.adapters.kafka.adapters import AsyncKafkaConsumerAdapter
from archipy.models.errors import InternalError, ServiceUnavailableError

logger = logging.getLogger(__name__)


async def consume_events() -> None:
    """Consume a batch of events using the async consumer.

    Raises:
        ServiceUnavailableError: If Kafka is unreachable.
        InternalError: If an unexpected error occurs.
    """
    consumer = AsyncKafkaConsumerAdapter(
        group_id="async-consumer-group",
        topic_list=["events"],
    )

    try:
        messages = await consumer.batch_consume(messages_number=50, timeout=5)
    except ServiceUnavailableError as e:
        logger.error("Kafka unavailable: %s", e)
        raise
    except InternalError as e:
        logger.error("Error consuming messages: %s", e)
        raise
    else:
        for msg in messages:
            value = msg.value()
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            logger.info("Received: %s", value)
            await consumer.commit(msg, asynchronous=False)
    finally:
        await consumer.close()


asyncio.run(consume_events())
```

### Async Consumer — Assign to Specific Partitions

```python
import asyncio
import logging

from confluent_kafka import TopicPartition

from archipy.adapters.kafka.adapters import AsyncKafkaConsumerAdapter

logger = logging.getLogger(__name__)


async def consume_from_partitions() -> None:
    """Consume messages from manually assigned partitions.

    Raises:
        InternalError: If an unexpected error occurs during consumption.
    """
    consumer = AsyncKafkaConsumerAdapter(
        group_id="async-partition-group",
        partition_list=[
            TopicPartition("events", partition=0),
            TopicPartition("events", partition=1),
        ],
    )

    try:
        messages = await consumer.batch_consume(messages_number=100, timeout=10)
        logger.info("Consumed %d messages", len(messages))
    finally:
        await consumer.close()


asyncio.run(consume_from_partitions())
```

### Async Producer Health Check

```python
import asyncio
import logging

from archipy.adapters.kafka.adapters import AsyncKafkaProducerAdapter
from archipy.models.errors import UnavailableError

logger = logging.getLogger(__name__)


async def check_health() -> None:
    """Check health of the async Kafka producer.

    Raises:
        UnavailableError: If the Kafka service is unreachable.
    """
    producer = AsyncKafkaProducerAdapter(topic_name="health-check")
    try:
        await producer.validate_healthiness()
    except UnavailableError as e:
        logger.error("Async Kafka producer is unhealthy: %s", e)
        raise
    else:
        logger.info("Async Kafka producer connection is healthy")
    finally:
        await producer.close()


asyncio.run(check_health())
```

## Error Handling

The Kafka adapters map low-level Kafka errors to ArchiPy domain exceptions by librdkafka error code:

| Kafka error | ArchiPy error |
|---|---|
| Timeouts (`_MSG_TIMED_OUT`, `_TIMED_OUT`, `REQUEST_TIMED_OUT`) | `ConnectionTimeoutError` |
| Transport failure (`_TRANSPORT`, `NETWORK_EXCEPTION`) | `NetworkError` |
| No broker reachable (`_ALL_BROKERS_DOWN`, `_RESOLVE`, `BROKER_NOT_AVAILABLE`) | `ServiceUnavailableError` |
| Authentication failure (`_AUTHENTICATION`, `SASL_AUTHENTICATION_FAILED`) | `UnauthenticatedError` |
| Authorization failure (topic, group, cluster, transactional id) | `PermissionDeniedError` |
| `_INVALID_ARG` | `InvalidArgumentError`, or `ConfigurationError` when a client setting is rejected |
| Full producer queue (`BufferError`) | `ResourceExhaustedError` |
| Anything else | `InternalError` |

```python
import logging

from archipy.adapters.kafka.adapters import KafkaAdminAdapter, KafkaProducerAdapter
from archipy.models.errors import (
    ConfigurationError,
    ConnectionTimeoutError,
    InternalError,
    InvalidArgumentError,
    NetworkError,
    ResourceExhaustedError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

try:
    admin = KafkaAdminAdapter()
    admin.create_topic("my-topic")
except ConfigurationError as e:
    logger.error("Kafka misconfigured: %s", e)
    raise
except InvalidArgumentError as e:
    logger.error("Invalid topic name or partition config: %s", e)
    raise
except ConnectionTimeoutError as e:
    logger.error("Timed out connecting to Kafka: %s", e)
    raise
except ServiceUnavailableError as e:
    logger.error("Kafka broker unavailable: %s", e)
    raise
except InternalError as e:
    logger.error("Unexpected Kafka error: %s", e)
    raise

try:
    producer = KafkaProducerAdapter(topic_name="my-topic")
    producer.produce("test message")
    producer.flush()
except NetworkError as e:
    logger.error("Network error: %s", e)
    raise
except ResourceExhaustedError as e:
    logger.error("Producer queue exhausted: %s", e)
    raise
except InternalError as e:
    logger.error("Unexpected error: %s", e)
    raise
```

## Integration with FastAPI

The async adapters are designed for use in `async` frameworks such as FastAPI. Use a single
shared adapter instance (e.g., via application lifespan) and call `close()` on shutdown.

```python
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from archipy.adapters.kafka.adapters import AsyncKafkaProducerAdapter, KafkaAdminAdapter
from archipy.models.errors import InternalError, NetworkError, UnavailableError

logger = logging.getLogger(__name__)

producer: AsyncKafkaProducerAdapter | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage async producer lifecycle.

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    global producer
    producer = AsyncKafkaProducerAdapter(topic_name="events")
    yield
    if producer is not None:
        await producer.close()


app = FastAPI(lifespan=lifespan)


class EventMessage(BaseModel):
    """Payload for publishing an event."""

    content: str
    key: str | None = None


@app.post("/events/publish")
async def publish_event(event: EventMessage) -> dict[str, str]:
    """Publish an event to Kafka.

    Args:
        event: Event message with content and optional key.

    Returns:
        Status message.

    Raises:
        HTTPException: If the message cannot be delivered.
    """
    if producer is None:
        raise HTTPException(status_code=503, detail="Producer not initialised")
    try:
        await producer.produce(event.content, key=event.key)
        await producer.flush()
    except UnavailableError as e:
        logger.error("Kafka unavailable: %s", e)
        raise HTTPException(status_code=503, detail="Kafka service unavailable") from e
    except NetworkError as e:
        logger.error("Network error publishing event: %s", e)
        raise HTTPException(status_code=502, detail="Network error") from e
    except InternalError as e:
        logger.error("Failed to publish event: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Event published to 'events' topic")
        return {"message": "Event published successfully"}


@app.get("/topics")
async def list_topics() -> dict[str, list[str]]:
    """List all Kafka topics.

    Returns:
        Dictionary with list of topic names.

    Raises:
        HTTPException: If topic listing fails.
    """
    try:
        admin = KafkaAdminAdapter()
        cluster_metadata = admin.list_topics()
    except InternalError as e:
        logger.error("Failed to list topics: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Retrieved topic list")
        return {"topics": list(cluster_metadata.topics.keys())}
```

## Tracing

With the `archipy[otel-kafka]` extra and `OTEL__IS_ENABLED=true`, producers and consumers (sync and async) emit
`send` and `recv` spans through the Confluent Kafka instrumentor.

The instrumentor opens a `<topic> process` span when a message is polled. It ends when the next `poll`, `consume` or
`close` runs, which would include idle time and make unrelated work its children. `KafkaConsumerAdapter.commit` therefore
ends the span as soon as the offset is committed, so commit after the message is processed. A consumer that never
commits (auto-commit) keeps the upstream behaviour.

!!! tip
    Commit after the message is processed, not before, so the span covers the handler.

- **Batches:** `batch_consume` produces one `<topic> process` span for the whole batch, with a link to the producer
  trace of every message. Commit once after processing the batch.
- **One message at a time:** each polled message gets its own span, ended by its commit. Without commits, each span ends
  when the next `poll` starts and the last one ends on `close`.
- **Auto-commit:** `ENABLE_AUTO_COMMIT=true` commits in the background, so the adapter never sees the end of
  processing. Spans end at the next `poll`, `consume` or `close`; open your own span around the handler instead. The async consumer adapter is not changed: its polls run in an
executor thread, so its span still ends on the next poll or close.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Kafka configuration setup
- [BDD Testing](../testing_strategy.md) — Testing Kafka operations
- BDD feature files — [`kafka_adapters.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/kafka_adapters.feature), [`kafka_adapters_apm.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/kafka_adapters_apm.feature), [`kafka_clients_spans.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/kafka_clients_spans.feature)
- [API Reference](../../api_reference/adapters/kafka.md) — Full Kafka adapter API documentation
