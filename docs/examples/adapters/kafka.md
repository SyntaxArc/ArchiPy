# Kafka Adapter

The Kafka adapter provides a clean interface for interacting with Apache Kafka, supporting both synchronous and
asynchronous operations.

## Features

- Topic operations (create, list, delete)
- Message publishing and consuming
- Consumer group management
- Built-in error handling and retry mechanisms
- Support for both sync and async operations
- Comprehensive logging and monitoring

## Basic Usage

### Configuration

Configure Kafka in your application's config:

```python
from archipy.configs.base_config import BaseConfig

# Using environment variables
# KAFKA__BOOTSTRAP_SERVERS=localhost:9092
# KAFKA__CLIENT_ID=my-app
# KAFKA__GROUP_ID=my-group
```

### Initializing the Adapter

```python
from archipy.adapters.kafka.adapters import KafkaAdapter, AsyncKafkaAdapter

# Use global configuration
kafka = KafkaAdapter()

# Or provide specific configuration
from archipy.configs.config_template import KafkaConfig

custom_config = KafkaConfig(
    BOOTSTRAP_SERVERS="kafka1:9092,kafka2:9092",
    CLIENT_ID="custom-client",
    GROUP_ID="custom-group"
)
kafka = KafkaAdapter(custom_config)
```

### Topic Operations

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Create a topic
try:
    kafka.create_topic("my-topic", num_partitions=3, replication_factor=1)
except Exception as e:
    logger.error(f"Failed to create topic: {e}")
    raise
else:
    logger.info("Topic created successfully")

# List all topics
try:
    topics = kafka.list_topics()
except Exception as e:
    logger.error(f"Failed to list topics: {e}")
    raise
else:
    for topic in topics:
        logger.info(f"Topic: {topic}")

# Delete a topic
try:
    kafka.delete_topic("my-topic")
except Exception as e:
    logger.error(f"Failed to delete topic: {e}")
    raise
else:
    logger.info("Topic deleted successfully")
```

### Publishing Messages

```python
import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# Publish a simple message
try:
    kafka.publish("my-topic", "Hello, Kafka!")
except Exception as e:
    logger.error(f"Failed to publish message: {e}")
    raise
else:
    logger.info("Message published successfully")

# Publish with key and headers
headers = {"source": "my-app", "version": "1.0"}
try:
    kafka.publish("my-topic", "Hello, Kafka!", key="message-1", headers=headers)
except Exception as e:
    logger.error(f"Failed to publish message with headers: {e}")
    raise
else:
    logger.info("Message with headers published successfully")

# Publish multiple messages
messages = [
    {"key": "msg1", "value": "Message 1"},
    {"key": "msg2", "value": "Message 2"}
]
try:
    kafka.publish_batch("my-topic", messages)
except Exception as e:
    logger.error(f"Failed to publish batch: {e}")
    raise
else:
    logger.info("Batch published successfully")
```

### Consuming Messages

```python
import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

# Consume messages with a callback
def process_message(message: dict[str, Any]) -> None:
    logger.info(f"Received message: {message['value']}")

# Start consuming
kafka.consume("my-topic", process_message)

# Consume with specific partition and offset
kafka.consume("my-topic", process_message, partition=0, offset=0)

# Consume with timeout
kafka.consume("my-topic", process_message, timeout_ms=5000)
```

### Async Operations

```python
import asyncio
import logging
from typing import Any

# Configure logging
logger = logging.getLogger(__name__)

async def async_example():
    # Create async Kafka adapter
    async_kafka = AsyncKafkaAdapter()

    # Publish message asynchronously
    await async_kafka.publish("my-topic", "Async message")

    # Consume messages asynchronously
    async def process_async(message: dict[str, Any]) -> None:
        logger.info(f"Received async message: {message['value']}")

    await async_kafka.consume("my-topic", process_async)

# Run the async example
asyncio.run(async_example())
```

## Error Handling

The KafkaAdapter uses ArchiPy's domain-specific exceptions for consistent error handling:

```python
import logging

from archipy.models.errors import (
    AlreadyExistsError,
    InternalError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
)

# Configure logging
logger = logging.getLogger(__name__)

try:
    kafka.create_topic("existing-topic")
except AlreadyExistsError as e:
    logger.warning(f"Topic already exists: {e}")
except PermissionDeniedError as e:
    logger.error(f"Permission denied to create topic: {e}")
    raise
except InvalidArgumentError as e:
    logger.error(f"Invalid argument: {e}")
    raise
except InternalError as e:
    logger.error(f"Internal error: {e}")
    raise
```

## Consumer Group Management

```python
import logging

# Configure logging
logger = logging.getLogger(__name__)

# List consumer groups
groups = kafka.list_consumer_groups()
for group in groups:
    logger.info(f"Group: {group['group_id']}, State: {group['state']}")

# Describe consumer group
group_info = kafka.describe_consumer_group("my-group")
logger.info(f"Group members: {group_info['members']}")

# Delete consumer group
kafka.delete_consumer_group("my-group")
```

## Integration with Web Applications

### FastAPI Example

```python
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from archipy.adapters.kafka.adapters import KafkaAdapter
from archipy.models.errors import InternalError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
kafka = KafkaAdapter()

class Message(BaseModel):
    content: str
    key: str | None = None

@app.post("/publish/{topic}")
async def publish_message(topic: str, message: Message) -> dict[str, str]:
    try:
        kafka.publish(topic, message.content, key=message.key)
    except InternalError as e:
        logger.error(f"Failed to publish message: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info(f"Message published to {topic}")
        return {"message": "Message published successfully"}

@app.get("/topics")
async def list_topics() -> dict[str, list[str]]:
    try:
        topics = kafka.list_topics()
    except InternalError as e:
        logger.error(f"Failed to list topics: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        logger.info(f"Retrieved {len(topics)} topics")
        return {"topics": topics}
```

## Testing with BDD

The Kafka adapter comes with BDD tests to verify functionality. Here's a sample feature file:

```gherkin
Feature: Kafka Operations Testing
  As a developer
  I want to test Kafka messaging operations
  So that I can ensure reliable message delivery

  Scenario: Publishing and consuming messages
    Given I have a Kafka topic "test-topic"
    When I publish a message "Hello, Kafka!" to "test-topic"
    Then I should be able to consume the message from "test-topic"
```

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - Kafka configuration setup
- [BDD Testing](../bdd_testing.md) - Testing Kafka operations
- [Kafka Adapters Feature](../../features/kafka_adapters.feature) - BDD test scenarios for Kafka
- [API Reference](../../api_reference/adapters.md) - Full Kafka adapter API documentation
