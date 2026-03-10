# Kafka Adapter

The Kafka adapter provides a clean interface for interacting with Apache Kafka through three
separate adapters — one for each concern: admin (topic management), producing, and consuming.

## Features

- Topic operations (create, list, delete)
- Message producing (single, with key)
- Message consuming (batch, poll, commit)
- Built-in error handling with domain-specific exceptions
- SASL+SSL authentication support

## Basic Usage

### Configuration

Configure Kafka in your application's config:

```python
from archipy.configs.base_config import BaseConfig

# Using environment variables:
# KAFKA__BROKERS_LIST='["localhost:9092"]'
# KAFKA__CLIENT_ID=my-app
```

Or provide a custom `KafkaConfig` directly to any adapter:

```python
from archipy.configs.config_template import KafkaConfig

custom_config = KafkaConfig(
    BROKERS_LIST=["kafka1:9092", "kafka2:9092"],
    CLIENT_ID="custom-client",
)
```

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

# Configure logging
logger = logging.getLogger(__name__)

# Use global configuration
admin = KafkaAdminAdapter()

# Create a topic
try:
    admin.create_topic("my-topic", num_partitions=3, replication_factor=1)
except InvalidArgumentError as e:
    logger.error(f"Invalid topic configuration: {e}")
    raise
except ServiceUnavailableError as e:
    logger.error(f"Kafka service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Internal error creating topic: {e}")
    raise
else:
    logger.info("Topic created successfully")

# List all topics — returns ClusterMetadata
try:
    cluster_metadata = admin.list_topics()
except InternalError as e:
    logger.error(f"Failed to list topics: {e}")
    raise
else:
    for topic_name in cluster_metadata.topics:
        logger.info(f"Topic: {topic_name}")

# Delete topics — accepts a list of topic names
try:
    admin.delete_topic(["my-topic"])
except InvalidArgumentError as e:
    logger.error(f"Invalid topic list: {e}")
    raise
except InternalError as e:
    logger.error(f"Failed to delete topic: {e}")
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

# Configure logging
logger = logging.getLogger(__name__)

# Requires topic_name at construction
producer = KafkaProducerAdapter(topic_name="my-topic")

# Publish a simple string message
try:
    producer.produce("Hello, Kafka!")
except NetworkError as e:
    logger.error(f"Network error producing message: {e}")
    raise
except ResourceExhaustedError as e:
    logger.error(f"Producer queue full: {e}")
    raise
except InternalError as e:
    logger.error(f"Failed to produce message: {e}")
    raise
else:
    logger.info("Message enqueued successfully")

# Publish with a message key (for partition affinity)
try:
    producer.produce("Hello, Kafka with key!", key="user-123")
except InternalError as e:
    logger.error(f"Failed to produce keyed message: {e}")
    raise
else:
    logger.info("Keyed message enqueued")

# Flush to ensure all pending messages are delivered
try:
    producer.flush(timeout=10)
except InternalError as e:
    logger.error(f"Flush failed: {e}")
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

# Configure logging
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
    logger.error(f"Kafka unavailable during consume: {e}")
    raise
except InternalError as e:
    logger.error(f"Error consuming messages: {e}")
    raise
else:
    for msg in messages:
        value = msg.value()
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        logger.info(f"Received: {value}")
        # Commit offset after processing
        consumer.commit(msg, asynchronous=False)

# Poll for a single message
msg = consumer.poll(timeout=1)
if msg is not None:
    logger.info(f"Polled: {msg.value().decode('utf-8')}")
```

### Assign to Specific Partitions

```python
import logging

from confluent_kafka import TopicPartition

from archipy.adapters.kafka.adapters import KafkaConsumerAdapter

# Configure logging
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
logger.info(f"Consumed {len(messages)} messages from assigned partitions")
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

# Configure logging
logger = logging.getLogger(__name__)

try:
    admin = KafkaAdminAdapter()
    admin.create_topic("my-topic")
except ConfigurationError as e:
    logger.error(f"Kafka misconfigured: {e}")
    raise
except InvalidArgumentError as e:
    logger.error(f"Invalid topic name or partition config: {e}")
    raise
except ConnectionTimeoutError as e:
    logger.error(f"Timed out connecting to Kafka: {e}")
    raise
except ServiceUnavailableError as e:
    logger.error(f"Kafka broker unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Unexpected Kafka error: {e}")
    raise

try:
    producer = KafkaProducerAdapter(topic_name="my-topic")
    producer.produce("test message")
    producer.flush()
except NetworkError as e:
    logger.error(f"Network error: {e}")
    raise
except ResourceExhaustedError as e:
    # Producer internal queue is full
    logger.error(f"Producer queue exhausted: {e}")
    raise
except InternalError as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

## Producer Health Check

```python
import logging

from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.models.errors import UnavailableError

# Configure logging
logger = logging.getLogger(__name__)

producer = KafkaProducerAdapter(topic_name="my-topic")

try:
    producer.validate_healthiness()
except UnavailableError as e:
    logger.error(f"Kafka producer is unhealthy: {e}")
    raise
else:
    logger.info("Kafka producer connection is healthy")
```

## Integration with FastAPI

```python
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from archipy.adapters.kafka.adapters import KafkaProducerAdapter
from archipy.models.errors import InternalError, NetworkError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
producer = KafkaProducerAdapter(topic_name="events")


class EventMessage(BaseModel):
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
    try:
        producer.produce(event.content, key=event.key)
        producer.flush(timeout=5)
    except UnavailableError as e:
        logger.error(f"Kafka unavailable: {e}")
        raise HTTPException(status_code=503, detail="Kafka service unavailable") from e
    except NetworkError as e:
        logger.error(f"Network error publishing event: {e}")
        raise HTTPException(status_code=502, detail="Network error") from e
    except InternalError as e:
        logger.error(f"Failed to publish event: {e}")
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
    from archipy.adapters.kafka.adapters import KafkaAdminAdapter

    try:
        admin = KafkaAdminAdapter()
        cluster_metadata = admin.list_topics()
    except InternalError as e:
        logger.error(f"Failed to list topics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info("Retrieved topic list")
        return {"topics": list(cluster_metadata.topics.keys())}
```

## Testing with BDD

The Kafka adapter ships with BDD tests that run against a real Kafka broker via testcontainers:

```gherkin
Feature: Kafka Operations Testing
  As a developer
  I want to test Kafka messaging operations
  So that I can ensure reliable message delivery

  Scenario: Produce and consume a message
    Given I have a Kafka producer for topic "test-topic"
    And I have a Kafka consumer subscribed to "test-topic"
    When I produce the message "Hello Kafka"
    Then I should consume the message "Hello Kafka" from "test-topic"

  Scenario: Validate producer health
    Given I have a Kafka producer for topic "test-topic"
    When I validate the producer healthiness
    Then the producer should be healthy
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - Kafka configuration setup
- [BDD Testing](../bdd_testing.md) - Testing Kafka operations
- [API Reference](../../api_reference/adapters.md) - Full Kafka adapter API documentation
