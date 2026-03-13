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
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Use global configuration
admin = KafkaAdminAdapter()

# Create a topic
try:
    admin.create_topic("my-topic", num_partitions=3, replication_factor=1)
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

# Delete topics — accepts a list of topic names
try:
    admin.delete_topic(["my-topic"])
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

# Publish with a message key (for partition affinity)
try:
    producer.produce("Hello, Kafka with key!", key="user-123")
except InternalError as e:
    logger.error("Failed to produce keyed message: %s", e)
    raise
else:
    logger.info("Keyed message enqueued")

# Flush to ensure all pending messages are delivered
try:
    producer.flush(timeout=10)
except InternalError as e:
    logger.error("Flush failed: %s", e)
    raise
else:
    logger.info("All messages flushed")
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

# Batch consume — returns list[Message], skips messages with errors
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

The Kafka adapters map low-level Kafka errors to ArchiPy domain exceptions:

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

## Producer Health Check

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

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Kafka configuration setup
- [BDD Testing](../testing_strategy.md) — Testing Kafka operations
- [API Reference](../../api_reference/adapters/kafka.md) — Full Kafka adapter API documentation
