"""Step definitions for Kafka adapter BDD tests."""

import asyncio
import socket
import time

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.adapters.kafka.adapters import (
    AsyncKafkaConsumerAdapter,
    AsyncKafkaProducerAdapter,
    KafkaAdminAdapter,
    KafkaConsumerAdapter,
    KafkaProducerAdapter,
    _apply_client_config,
    _apply_security_config,
)
from archipy.configs.config_template import KafkaConfig
from archipy.models import errors as archipy_errors
from archipy.models.errors import AlreadyExistsError, ConfigurationError, UnavailableError


def _get_kafka_config(context):
    """Retrieve the KafkaConfig from the running test container."""
    scenario_context = get_current_scenario_context(context)
    test_containers = scenario_context.get("test_containers")
    kafka_container = test_containers.get_container("kafka")
    return kafka_container.config


def get_kafka_admin_adapter(context):
    """Get or initialize the Kafka admin adapter."""
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "admin_adapter") or scenario_context.admin_adapter is None:
        scenario_context.admin_adapter = KafkaAdminAdapter(_get_kafka_config(context))
    return scenario_context.admin_adapter


def get_kafka_producer_adapter(context, topic_name):
    """Get or initialize the sync Kafka producer adapter."""
    scenario_context = get_current_scenario_context(context)
    key = f"producer_{topic_name}"
    if not hasattr(scenario_context, key) or getattr(scenario_context, key) is None:
        producer = KafkaProducerAdapter(topic_name, kafka_configs=_get_kafka_config(context))
        setattr(scenario_context, key, producer)
    return getattr(scenario_context, key)


def get_kafka_consumer_adapter(context, topic_name, group_id):
    """Get or initialize the sync Kafka consumer adapter."""
    scenario_context = get_current_scenario_context(context)
    key = f"consumer_{topic_name}_{group_id}"
    if not hasattr(scenario_context, key) or getattr(scenario_context, key) is None:
        consumer = KafkaConsumerAdapter(
            group_id=group_id, topic_list=[topic_name], kafka_configs=_get_kafka_config(context),
        )
        setattr(scenario_context, key, consumer)
    return getattr(scenario_context, key)


def get_async_kafka_producer_adapter(context, topic_name):
    """Get or initialize the async Kafka producer adapter."""
    scenario_context = get_current_scenario_context(context)
    key = f"async_producer_{topic_name}"
    if not hasattr(scenario_context, key) or getattr(scenario_context, key) is None:
        producer = AsyncKafkaProducerAdapter(topic_name, kafka_configs=_get_kafka_config(context))
        setattr(scenario_context, key, producer)
    return getattr(scenario_context, key)


def get_async_kafka_consumer_adapter(context, topic_name, group_id):
    """Get or initialize the async Kafka consumer adapter."""
    scenario_context = get_current_scenario_context(context)
    key = f"async_consumer_{topic_name}_{group_id}"
    if not hasattr(scenario_context, key) or getattr(scenario_context, key) is None:
        consumer = AsyncKafkaConsumerAdapter(
            group_id=group_id, topic_list=[topic_name], kafka_configs=_get_kafka_config(context),
        )
        setattr(scenario_context, key, consumer)
    return getattr(scenario_context, key)


def _create_topic_if_missing(admin, topic, **kwargs):
    """Create a topic, accepting that an earlier scenario of the feature already created it."""
    try:
        admin.create_topic(topic, **kwargs)
    except AlreadyExistsError:
        pass


CONSUME_DEADLINE_SECONDS = 60


def _consume_until(adapter, count, deadline_seconds=CONSUME_DEADLINE_SECONDS):
    """Consume from a sync consumer until count messages arrive or the deadline passes.

    A fresh consumer group needs a join/rebalance before the first fetch, which can exceed a
    single poll timeout on a loaded host, so one batch_consume call is not enough.
    """
    messages = []
    deadline = time.monotonic() + deadline_seconds
    while len(messages) < count and time.monotonic() < deadline:
        messages.extend(adapter.batch_consume(messages_number=count - len(messages), timeout=5))
    return messages


async def _async_consume_until(adapter, count, deadline_seconds=CONSUME_DEADLINE_SECONDS):
    """Async variant of _consume_until."""
    messages = []
    deadline = time.monotonic() + deadline_seconds
    while len(messages) < count and time.monotonic() < deadline:
        messages.extend(await adapter.batch_consume(messages_number=count - len(messages), timeout=5))
    return messages


def wait_for_topic_condition(adapter, condition_func, topic_name, max_retries=5, initial_delay=0.5):
    """Helper function to wait for a topic condition with retries."""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            topics = adapter.list_topics(timeout=2).topics
            if condition_func(topic_name, topics):
                return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
        if attempt < max_retries - 1:
            time.sleep(delay)
            delay *= 1.5
    return False


# ---------------------------------------------------------------------------
# Given steps — shared
# ---------------------------------------------------------------------------


@given("a configured Kafka admin adapter")
def step_configured_admin_adapter(context):
    """Set up and verify connectivity to the Kafka admin adapter."""
    adapter = get_kafka_admin_adapter(context)
    try:
        adapter.list_topics(timeout=1)
        context.logger.info("Successfully connected to Kafka server")
    except Exception as e:
        context.logger.exception(f"Failed to connect to Kafka: {str(e)}")
        raise


@given('a test topic named "{topic_name}"')
def step_test_topic(context, topic_name):
    """Ensure a test topic exists, creating it if necessary."""
    adapter = get_kafka_admin_adapter(context)
    try:
        topics = adapter.list_topics(timeout=1).topics
        if topic_name not in topics:
            context.logger.info(f"Creating test topic '{topic_name}'")
            _create_topic_if_missing(adapter, topic_name)
        context.logger.info(f"Ensured topic '{topic_name}' exists")
    except Exception as e:
        context.logger.exception(f"Failed to ensure topic exists: {str(e)}")
        raise


@given('a topic named "{topic_name}" exists')
def step_topic_exists(context, topic_name):
    """Ensure a topic exists, creating it if necessary."""
    adapter = get_kafka_admin_adapter(context)
    try:
        topics = adapter.list_topics(timeout=1).topics
        if topic_name not in topics:
            context.logger.info(f"Creating topic '{topic_name}'")
            _create_topic_if_missing(adapter, topic_name)
        context.logger.info(f"Ensured topic '{topic_name}' exists")
    except Exception as e:
        context.logger.exception(f"Failed to create topic: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# Given steps — sync
# ---------------------------------------------------------------------------


@given('a Kafka producer for topic "{topic_name}"')
def step_producer_exists(context, topic_name):
    """Initialize and health-check a sync Kafka producer."""
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter.validate_healthiness()
        context.logger.info(f"Ensured producer for topic '{topic_name}' is healthy")
    except Exception as e:
        context.logger.exception(f"Failed to initialize producer: {str(e)}")
        raise


@given('a Kafka consumer subscribed to topic "{topic_name}" with group "{group_id}"')
def step_consumer_exists(context, topic_name, group_id):
    """Initialize and subscribe a sync Kafka consumer."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        adapter.subscribe([topic_name])
        context.logger.info(f"Ensured consumer subscribed to '{topic_name}' with group '{group_id}'")
    except Exception as e:
        context.logger.exception(f"Failed to initialize consumer: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# Given steps — async
# ---------------------------------------------------------------------------


@given('an async Kafka producer for topic "{topic_name}"')
async def step_async_producer_exists(context, topic_name):
    """Initialize and health-check an async Kafka producer."""
    adapter = get_async_kafka_producer_adapter(context, topic_name)
    try:
        await adapter.validate_healthiness()
        context.logger.info(f"Ensured async producer for topic '{topic_name}' is healthy")
    except Exception as e:
        context.logger.exception(f"Failed to initialize async producer: {str(e)}")
        raise


@given('an async Kafka consumer subscribed to topic "{topic_name}" with group "{group_id}"')
async def step_async_consumer_exists(context, topic_name, group_id):
    """Initialize and subscribe an async Kafka consumer."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        await adapter.subscribe([topic_name])
        context.logger.info(f"Ensured async consumer subscribed to '{topic_name}' with group '{group_id}'")
    except Exception as e:
        context.logger.exception(f"Failed to initialize async consumer: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# When steps — shared
# ---------------------------------------------------------------------------


@when('I create a topic named "{topic_name}"')
def step_create_topic(context, topic_name):
    """Create a Kafka topic."""
    adapter = get_kafka_admin_adapter(context)
    try:
        _create_topic_if_missing(adapter, topic_name)
        context.logger.info(f"Created topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to create topic: {str(e)}")
        raise


@when('I delete the topic "{topic_name}"')
def step_delete_topic(context, topic_name):
    """Delete a Kafka topic."""
    adapter = get_kafka_admin_adapter(context)
    try:
        adapter.delete_topic([topic_name])
        context.logger.info(f"Deleted topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to delete topic: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# When steps — sync
# ---------------------------------------------------------------------------


@when('I produce a message "{message}" to topic "{topic_name}"')
def step_produce_message(context, message, topic_name):
    """Produce a single message to a topic."""
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter.produce(message)
        adapter.flush(timeout=1)
        context.logger.info(f"Produced message '{message}' to '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to produce message: {str(e)}")
        raise e


@when('I produce one message "{message}" with key "{key}" to topic "{topic_name}"')
def step_produce_message_with_key(context, message, key, topic_name):
    """Produce a single keyed message to a topic."""
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter.produce(message, key=key)
        adapter.flush(timeout=1)
        context.logger.info(f"Produced message '{message}' to '{topic_name}' with key '{key}'")
    except Exception as e:
        context.logger.exception(f"Failed to produce message with key: {str(e)}")
        raise e


@when('I produce {count:d} messages to topic "{topic_name}"')
def step_produce_multiple_messages(context, count, topic_name):
    """Produce multiple numbered messages to a topic."""
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        for i in range(count):
            adapter.produce(f"message-{i + 1}")
        adapter.flush(timeout=5)
        context.logger.info(f"Produced {count} messages to '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to produce multiple messages: {str(e)}")
        raise e


@when('I validate the producer health for topic "{topic_name}"')
def step_validate_health(context, topic_name):
    """Validate that a sync Kafka producer is healthy."""
    producer = get_kafka_producer_adapter(context, topic_name)
    try:
        producer.validate_healthiness()
        context.logger.info(f"Producer health validated for topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Health validation failed: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# When steps — async
# ---------------------------------------------------------------------------


@when('I async produce a message "{message}" to topic "{topic_name}"')
async def step_async_produce_message(context, message, topic_name):
    """Async produce a single message to a topic."""
    adapter = get_async_kafka_producer_adapter(context, topic_name)
    try:
        await adapter.produce(message)
        await adapter.flush()
        context.logger.info(f"Async produced message '{message}' to '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to async produce message: {str(e)}")
        raise e


@when('I async produce one message "{message}" with key "{key}" to topic "{topic_name}"')
async def step_async_produce_message_with_key(context, message, key, topic_name):
    """Async produce a single keyed message to a topic."""
    adapter = get_async_kafka_producer_adapter(context, topic_name)
    try:
        await adapter.produce(message, key=key)
        await adapter.flush()
        context.logger.info(f"Async produced message '{message}' to '{topic_name}' with key '{key}'")
    except Exception as e:
        context.logger.exception(f"Failed to async produce message with key: {str(e)}")
        raise e


@when('I async produce {count:d} messages to topic "{topic_name}"')
async def step_async_produce_multiple_messages(context, count, topic_name):
    """Async produce multiple numbered messages to a topic."""
    adapter = get_async_kafka_producer_adapter(context, topic_name)
    try:
        for i in range(count):
            await adapter.produce(f"message-{i + 1}")
        await adapter.flush()
        context.logger.info(f"Async produced {count} messages to '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to async produce multiple messages: {str(e)}")
        raise e


@when('I validate the async producer health for topic "{topic_name}"')
async def step_validate_async_health(context, topic_name):
    """Validate that an async Kafka producer is healthy."""
    producer = get_async_kafka_producer_adapter(context, topic_name)
    try:
        await producer.validate_healthiness()
        context.logger.info(f"Async producer health validated for topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Async health validation failed: {str(e)}")
        raise


# ---------------------------------------------------------------------------
# Then steps — shared
# ---------------------------------------------------------------------------


@then('the topic "{topic_name}" should exist')
def step_topic_should_exist(context, topic_name):
    """Assert that a topic exists in Kafka."""
    adapter = get_kafka_admin_adapter(context)
    if wait_for_topic_condition(adapter, lambda name, topics: name in topics, topic_name):
        context.logger.info(f"Verified topic '{topic_name}' exists")
    else:
        raise AssertionError(f"Topic '{topic_name}' does not exist after retries")


@then('the topic "{topic_name}" should not exist')
def step_topic_should_not_exist(context, topic_name):
    """Assert that a topic does not exist in Kafka."""
    adapter = get_kafka_admin_adapter(context)
    if wait_for_topic_condition(adapter, lambda name, topics: name not in topics, topic_name):
        context.logger.info(f"Verified topic '{topic_name}' does not exist")
    else:
        raise AssertionError(f"Topic '{topic_name}' still exists after retries")


@then('the topic list should include "{topic_name}"')
def step_topic_list_includes(context, topic_name):
    """Assert that a topic appears in the Kafka topic list."""
    adapter = get_kafka_admin_adapter(context)
    if wait_for_topic_condition(adapter, lambda name, topics: name in topics, topic_name):
        context.logger.info(f"Verified '{topic_name}' in topic list")
    else:
        raise AssertionError(f"Topic '{topic_name}' not in topic list after retries")


# ---------------------------------------------------------------------------
# Then steps — sync
# ---------------------------------------------------------------------------


@then('the consumer should receive message "{expected_message}" from topic "{topic_name}" with group "{group_id}"')
def step_consumer_receive(context, expected_message, topic_name, group_id):
    """Assert that a consumer receives the expected single message."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        messages = _consume_until(adapter, 1)
        assert len(messages) > 0, "No messages received"
        received_message = messages[0].value().decode("utf-8")
        assert received_message == expected_message, f"Expected '{expected_message}', got '{received_message}'"
        scenario_context = get_current_scenario_context(context)
        scenario_context.last_messages = messages
        context.logger.info(f"Verified received message '{expected_message}'")
    except Exception as e:
        context.logger.exception(f"Failed to consume message: {str(e)}")
        raise


@then('the consumer should receive {count:d} messages from topic "{topic_name}" with group "{group_id}"')
def step_consumer_receive_multiple(context, count, topic_name, group_id):
    """Assert that a consumer receives the expected number of messages."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        messages = _consume_until(adapter, count)
        assert len(messages) == count, f"Expected {count} messages, got {len(messages)}"
        scenario_context = get_current_scenario_context(context)
        scenario_context.last_messages = messages
        context.logger.info(f"Verified received {count} messages from '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to batch consume messages: {str(e)}")
        raise


@then('the received message should have key "{expected_key}"')
def step_received_message_has_key(context, expected_key):
    """Assert that the last consumed message has the expected key."""
    scenario_context = get_current_scenario_context(context)
    messages = getattr(scenario_context, "last_messages", None)
    assert messages and len(messages) > 0, "No messages found in scenario context"
    actual_key = messages[0].key()
    assert actual_key is not None, "Message has no key"
    assert actual_key.decode("utf-8") == expected_key, (
        f"Expected key '{expected_key}', got '{actual_key.decode('utf-8')}'"
    )
    context.logger.info(f"Verified message key '{expected_key}'")


@then("the commit should succeed")
def step_commit_should_succeed(context):
    """Assert that a previously executed commit completed without error."""
    scenario_context = get_current_scenario_context(context)
    commit_error = getattr(scenario_context, "commit_error", None)
    assert commit_error is None, f"Commit failed with error: {commit_error}"
    context.logger.info("Verified commit succeeded")


@then('I commit the consumed offset for topic "{topic_name}" with group "{group_id}"')
def step_commit_consumed_offset(context, topic_name, group_id):
    """Commit the consumed offset for a sync consumer."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        messages = getattr(scenario_context, "last_messages", None)
        assert messages and len(messages) > 0, "No consumed messages available to commit"
        adapter.commit(messages[0])
        scenario_context.commit_error = None
        context.logger.info(f"Committed offset for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.commit_error = e
        context.logger.exception(f"Commit failed: {str(e)}")
        raise


@when('I commit without message for topic "{topic_name}" with group "{group_id}"')
def step_commit_without_message(context, topic_name, group_id):
    """Commit without a specific message (commits current position)."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        adapter.commit(message=None, asynchronous=False)
        scenario_context.commit_error = None
        context.logger.info(f"Committed without message for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.commit_error = e
        context.logger.exception(f"Null commit failed: {str(e)}")
        raise


@then("the null commit should succeed")
def step_null_commit_should_succeed(context):
    """Assert that a null commit completed without error."""
    scenario_context = get_current_scenario_context(context)
    commit_error = getattr(scenario_context, "commit_error", None)
    assert commit_error is None, f"Null commit failed with error: {commit_error}"
    context.logger.info("Verified null commit succeeded")


@then('I commit the batch for topic "{topic_name}" with group "{group_id}"')
def step_commit_batch(context, topic_name, group_id):
    """Commit offsets for a batch of consumed messages."""
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        messages = getattr(scenario_context, "last_messages", None)
        assert messages and len(messages) > 0, "No consumed messages available to commit"
        adapter.commit()
        scenario_context.commit_error = None
        context.logger.info(f"Committed batch for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.commit_error = e
        context.logger.exception(f"Batch commit failed: {str(e)}")
        raise


@then("the async null commit should succeed")
def step_async_null_commit_should_succeed(context):
    """Assert that an async null commit completed without error."""
    scenario_context = get_current_scenario_context(context)
    commit_error = getattr(scenario_context, "async_commit_error", None)
    assert commit_error is None, f"Async null commit failed with error: {commit_error}"
    context.logger.info("Verified async null commit succeeded")


@when('I async commit without message for topic "{topic_name}" with group "{group_id}"')
async def step_async_commit_without_message(context, topic_name, group_id):
    """Async commit without a specific message (commits current position)."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        await adapter.commit(message=None, asynchronous=False)
        scenario_context.async_commit_error = None
        context.logger.info(f"Async committed without message for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.async_commit_error = e
        context.logger.exception(f"Async null commit failed: {str(e)}")
        raise


@then('I async commit the batch for topic "{topic_name}" with group "{group_id}"')
async def step_async_commit_batch(context, topic_name, group_id):
    """Async commit offsets for a batch of consumed messages."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        messages = getattr(scenario_context, "last_messages", None)
        assert messages and len(messages) > 0, "No consumed messages available to commit"
        await adapter.commit()
        scenario_context.async_commit_error = None
        context.logger.info(f"Async committed batch for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.async_commit_error = e
        context.logger.exception(f"Async batch commit failed: {str(e)}")
        raise


@then("the producer health check should pass")
def step_health_check_pass(context):
    """Assert that the most recently initialized sync producer is healthy.

    This step exists for backward compatibility with existing scenarios that set up
    a single producer via 'a Kafka producer for topic'. For new scenarios use
    'I validate the producer health for topic' instead.
    """
    scenario_context = get_current_scenario_context(context)
    producer_key = next(
        (k for k in vars(scenario_context) if k.startswith("producer_") and not k.startswith("producer_async")),
        None,
    )
    if not producer_key:
        context.logger.error("No producer found for health check")
        raise AssertionError("Producer not initialized")
    producer = getattr(scenario_context, producer_key)
    try:
        producer.validate_healthiness()
        context.logger.info("Producer health check passed")
    except UnavailableError as e:
        context.logger.error(f"Health check failed: {str(e)}")
        raise AssertionError(f"Producer health check failed: {str(e)}")


# ---------------------------------------------------------------------------
# Then steps — async
# ---------------------------------------------------------------------------


@then(
    'the async consumer should receive message "{expected_message}" from topic "{topic_name}" with group "{group_id}"',
)
async def step_async_consumer_receive(context, expected_message, topic_name, group_id):
    """Assert that an async consumer receives the expected single message."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        messages = await _async_consume_until(adapter, 1)
        assert len(messages) > 0, "No async messages received"
        received_message = messages[0].value().decode("utf-8")
        assert received_message == expected_message, f"Expected '{expected_message}', got '{received_message}'"
        scenario_context = get_current_scenario_context(context)
        scenario_context.last_messages = messages
        context.logger.info(f"Async verified received message '{expected_message}'")
    except Exception as e:
        context.logger.exception(f"Failed to async consume message: {str(e)}")
        raise


@then('the async consumer should receive {count:d} messages from topic "{topic_name}" with group "{group_id}"')
async def step_async_consumer_receive_multiple(context, count, topic_name, group_id):
    """Assert that an async consumer receives the expected number of messages."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        messages = await _async_consume_until(adapter, count)
        assert len(messages) == count, f"Expected {count} messages, got {len(messages)}"
        scenario_context = get_current_scenario_context(context)
        scenario_context.last_messages = messages
        context.logger.info(f"Async verified received {count} messages from '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to async batch consume messages: {str(e)}")
        raise


@then('the async received message should have key "{expected_key}"')
def step_async_received_message_has_key(context, expected_key):
    """Assert that the last async consumed message has the expected key."""
    scenario_context = get_current_scenario_context(context)
    messages = getattr(scenario_context, "last_messages", None)
    assert messages and len(messages) > 0, "No messages found in scenario context"
    actual_key = messages[0].key()
    assert actual_key is not None, "Message has no key"
    assert actual_key.decode("utf-8") == expected_key, (
        f"Expected key '{expected_key}', got '{actual_key.decode('utf-8')}'"
    )
    context.logger.info(f"Async verified message key '{expected_key}'")


@then("the async commit should succeed")
def step_async_commit_should_succeed(context):
    """Assert that a previously executed async commit completed without error."""
    scenario_context = get_current_scenario_context(context)
    commit_error = getattr(scenario_context, "async_commit_error", None)
    assert commit_error is None, f"Async commit failed with error: {commit_error}"
    context.logger.info("Verified async commit succeeded")


@then('I async commit the consumed offset for topic "{topic_name}" with group "{group_id}"')
async def step_async_commit_consumed_offset(context, topic_name, group_id):
    """Commit the consumed offset for an async consumer."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    scenario_context = get_current_scenario_context(context)
    try:
        messages = getattr(scenario_context, "last_messages", None)
        assert messages and len(messages) > 0, "No consumed messages available to commit"
        await adapter.commit(messages[0])
        scenario_context.async_commit_error = None
        context.logger.info(f"Async committed offset for '{topic_name}' group '{group_id}'")
    except Exception as e:
        scenario_context.async_commit_error = e
        context.logger.exception(f"Async commit failed: {str(e)}")
        raise


@then("the async producer health check should pass")
async def step_async_health_check_pass(context):
    """Assert that the most recently initialized async producer is healthy."""
    scenario_context = get_current_scenario_context(context)
    producer_key = next(
        (k for k in vars(scenario_context) if k.startswith("async_producer_")),
        None,
    )
    if not producer_key:
        context.logger.error("No async producer found for health check")
        raise AssertionError("Async producer not initialized")
    producer = getattr(scenario_context, producer_key)
    try:
        await producer.validate_healthiness()
        context.logger.info("Async producer health check passed")
    except UnavailableError as e:
        context.logger.error(f"Async health check failed: {str(e)}")
        raise AssertionError(f"Async producer health check failed: {str(e)}")


@when('I produce and consume a message on topic "{topic}" through the async Kafka adapters')
def step_async_kafka_roundtrip(context, topic):
    """Round-trip one message through the async adapters (used by the span scenarios)."""
    import asyncio
    import uuid

    admin = get_kafka_admin_adapter(context)
    _create_topic_if_missing(admin, topic, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(admin, lambda name, topics: name in topics, topic)

    async def roundtrip():
        producer = get_async_kafka_producer_adapter(context, topic)
        consumer = get_async_kafka_consumer_adapter(context, topic, f"async-span-group-{uuid.uuid4().hex[:6]}")
        await consumer.subscribe([topic])
        await producer.produce("async-span-message")
        await producer.flush(timeout=5)
        deadline = time.monotonic() + 10
        message = None
        while message is None and time.monotonic() < deadline:
            message = await consumer.poll(timeout=1)
        await consumer.close()
        await producer.close()
        return message

    assert asyncio.run(roundtrip()) is not None, "Async consumer received no message"


# --- Consume span lifetime (OpenTelemetry) ---


def _consume_span_telemetry(context):
    return get_current_scenario_context(context).get("adapter_span_telemetry")


def _consume_spans(context, topic):
    telemetry = _consume_span_telemetry(context)
    telemetry.flush()
    return [span for span in telemetry.spans() if span.name == f"{topic} process"]


@when('I produce {count:d} messages on topic "{topic}" and consume them as one batch')
def step_produce_and_batch_consume(context, count, topic):
    """Produce messages, then read them with a single ``batch_consume`` call."""
    import uuid

    admin = get_kafka_admin_adapter(context)
    _create_topic_if_missing(admin, topic, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(admin, lambda name, topics: name in topics, topic)

    producer = get_kafka_producer_adapter(context, topic)
    for index in range(count):
        producer.produce(f"batch-message-{index}")
    producer.flush(timeout=5)

    consumer = get_kafka_consumer_adapter(context, topic, f"batch-span-group-{uuid.uuid4().hex[:6]}")
    consumer.subscribe([topic])
    messages = consumer.batch_consume(messages_number=count, timeout=15)
    assert len(messages) == count, f"Expected {count} messages in one batch, got {len(messages)}"
    get_current_scenario_context(context).store("batch_consumer", consumer)
    get_current_scenario_context(context).store("batch_messages", messages)


@when("I commit the last message of the batch")
def step_commit_last_batch_message(context):
    scenario_context = get_current_scenario_context(context)
    consumer = scenario_context.get("batch_consumer")
    consumer.commit(scenario_context.get("batch_messages")[-1], asynchronous=False)


@then('the consume span of topic "{topic}" should not have been exported yet')
def step_consume_span_not_exported(context, topic):
    spans = _consume_spans(context, topic)
    assert not spans, f"The consume span ended before the message was committed: {[s.name for s in spans]}"


@then('exactly one consume span of topic "{topic}" should be exported with {links:d} links')
def step_one_consume_span_with_links(context, topic, links):
    telemetry = _consume_span_telemetry(context)
    spans = telemetry.wait_for(lambda: _consume_spans(context, topic), timeout=10)
    assert len(spans) == 1, f"Expected one consume span for the batch, got {len(spans)}"
    assert len(spans[0].links) == links, f"Expected {links} links, got {len(spans[0].links)}"


@when('I poll one message from topic "{topic}" with auto commit enabled')
def step_poll_with_auto_commit(context, topic):
    """Poll one message with ``enable.auto.commit`` on, so the adapter's ``commit`` is never called."""
    import uuid

    admin = get_kafka_admin_adapter(context)
    _create_topic_if_missing(admin, topic, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(admin, lambda name, topics: name in topics, topic)

    producer = get_kafka_producer_adapter(context, topic)
    producer.produce("auto-commit-message")
    producer.flush(timeout=5)

    configs = _get_kafka_config(context).model_copy(update={"ENABLE_AUTO_COMMIT": True})
    consumer = KafkaConsumerAdapter(
        group_id=f"auto-commit-span-group-{uuid.uuid4().hex[:6]}",
        topic_list=[topic],
        kafka_configs=configs,
    )
    consumer.subscribe([topic])
    deadline = time.monotonic() + 15
    message = None
    while message is None and time.monotonic() < deadline:
        message = consumer.poll(timeout=1)
    assert message is not None, "Consumer received no message"
    get_current_scenario_context(context).store("auto_commit_consumer", consumer)


@when("the auto commit consumer is closed")
def step_close_auto_commit_consumer(context):
    get_current_scenario_context(context).get("auto_commit_consumer").close()


def _prepare_topic_with_messages(context, topic, count):
    """Create the topic, produce ``count`` messages and subscribe a fresh consumer to it."""
    import uuid

    admin = get_kafka_admin_adapter(context)
    _create_topic_if_missing(admin, topic, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(admin, lambda name, topics: name in topics, topic)

    producer = get_kafka_producer_adapter(context, topic)
    for index in range(count):
        producer.produce(f"multi-message-{index}")
    producer.flush(timeout=5)

    consumer = get_kafka_consumer_adapter(context, topic, f"multi-span-group-{uuid.uuid4().hex[:6]}")
    consumer.subscribe([topic])
    get_current_scenario_context(context).store("multi_consumer", consumer)


def _poll_one(consumer):
    deadline = time.monotonic() + 15
    message = None
    while message is None and time.monotonic() < deadline:
        message = consumer.poll(timeout=1)
    assert message is not None, "Consumer received no message"
    return message


@when('{count:d} messages are produced on topic "{topic}" and polled and committed one by one')
def step_poll_and_commit_each(context, count, topic):
    _prepare_topic_with_messages(context, topic, count)
    consumer = get_current_scenario_context(context).get("multi_consumer")
    for _ in range(count):
        consumer.commit(_poll_one(consumer), asynchronous=False)


@when('{count:d} messages are produced on topic "{topic}" and polled without committing')
def step_poll_without_commit(context, count, topic):
    _prepare_topic_with_messages(context, topic, count)
    consumer = get_current_scenario_context(context).get("multi_consumer")
    for _ in range(count):
        _poll_one(consumer)


@when("the multi message consumer is closed")
def step_close_multi_consumer(context):
    get_current_scenario_context(context).get("multi_consumer").close()


@then('{count:d} consume spans of topic "{topic}" should be exported')
def step_n_consume_spans(context, count, topic):
    telemetry = _consume_span_telemetry(context)
    spans = telemetry.wait_for(
        lambda: (lambda found: found if len(found) >= count else [])(_consume_spans(context, topic)),
        timeout=10,
    )
    assert len(spans) == count, f"Expected {count} consume spans, got {len(spans)}"
    assert len({span.context.span_id for span in spans}) == count, "Consume spans must be distinct"


@then('{count:d} consume spans of topic "{topic}" should be exported and the last one still open')
def step_ended_consume_spans_only(context, count, topic):
    """Without a commit each span ends at the next poll, so the last polled message has no exported span yet."""
    telemetry = _consume_span_telemetry(context)
    spans = telemetry.wait_for(
        lambda: (lambda found: found if len(found) >= count else [])(_consume_spans(context, topic)),
        timeout=10,
    )
    assert len(spans) == count, f"Expected {count} ended consume spans, got {len(spans)}"


# ---------------------------------------------------------------------------
# Hot paths: unreachable broker, error translation, assign, poll, close
# ---------------------------------------------------------------------------


def _closed_port_config(context, **updates):
    """Build a KafkaConfig whose only broker is a local port nobody listens on."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return _get_kafka_config(context).model_copy(update={"BROKERS_LIST": [f"127.0.0.1:{port}"], **updates})


def _capture_error(context, operation):
    """Run ``operation`` and keep the raised exception (or None) in the scenario context."""
    scenario_context = get_current_scenario_context(context)
    try:
        operation()
    except Exception as e:
        scenario_context.store("kafka_operation_error", e)
    else:
        scenario_context.store("kafka_operation_error", None)


@given("an unreachable Kafka broker")
def step_unreachable_broker(context):
    """Point the scenario at a closed local port, so every call fails within about a second."""
    get_current_scenario_context(context).store("kafka_unreachable_config", _closed_port_config(context))


@when("I validate the health of a {mode} producer on that broker")
def step_validate_health_unreachable(context, mode):
    """Run the producer health check against the unreachable broker."""
    config = get_current_scenario_context(context).get("kafka_unreachable_config")
    if mode == "sync":
        _capture_error(context, KafkaProducerAdapter("health-topic", kafka_configs=config).validate_healthiness)
    else:
        _capture_error(
            context,
            lambda: asyncio.run(AsyncKafkaProducerAdapter("health-topic", kafka_configs=config).validate_healthiness()),
        )


@when("I list topics with the {adapter_kind} adapter on that broker")
def step_list_topics_unreachable(context, adapter_kind):
    """List topics through the admin, sync producer or async producer adapter against the unreachable broker."""
    config = get_current_scenario_context(context).get("kafka_unreachable_config")
    if adapter_kind == "admin":
        _capture_error(context, lambda: KafkaAdminAdapter(config).list_topics(timeout=1))
    elif adapter_kind == "sync producer":
        _capture_error(context, lambda: KafkaProducerAdapter("t", kafka_configs=config).list_topics(timeout=1))
    else:
        _capture_error(
            context,
            lambda: asyncio.run(AsyncKafkaProducerAdapter("t", kafka_configs=config).list_topics(timeout=1)),
        )


@when("I produce {count:d} messages with a producer whose queue holds only {capacity:d} message on that broker")
def step_produce_into_full_queue(context, count, capacity):
    """Produce more messages than the local queue holds while the broker cannot accept any."""
    config = _closed_port_config(context, QUEUE_BUFFERING_MAX_MESSAGES=capacity)
    producer = KafkaProducerAdapter("full-queue-topic", kafka_configs=config)

    def produce_all():
        for index in range(count):
            producer.produce(f"queued-{index}")

    _capture_error(context, produce_all)


@when("I use a {mode} {role} configured with an invalid setting")
def step_use_invalid_configuration(context, mode, role):
    """Create the adapter with a rejected librdkafka setting and use it once (async adapters build lazily)."""
    if role == "producer":
        config = _get_kafka_config(context).model_copy(update={"ACKS": "bogus"})
    else:
        config = _get_kafka_config(context).model_copy(update={"AUTO_OFFSET_RESET": "bogus"})

    def use():
        if mode == "sync" and role == "producer":
            KafkaProducerAdapter("invalid-config-topic", kafka_configs=config)
        elif mode == "sync":
            KafkaConsumerAdapter("invalid-config-group", topic_list=["invalid-config-topic"], kafka_configs=config)
        elif role == "producer":
            asyncio.run(AsyncKafkaProducerAdapter("invalid-config-topic", kafka_configs=config).produce("x"))
        else:
            asyncio.run(
                AsyncKafkaConsumerAdapter(
                    "invalid-config-group",
                    topic_list=["invalid-config-topic"],
                    kafka_configs=config,
                ).poll(timeout=1),
            )

    _capture_error(context, use)


@when("I create a {mode} consumer with {arguments}")
def step_create_consumer_with_arguments(context, mode, arguments):
    """Create a consumer with an invalid combination of topic and partition lists."""
    from confluent_kafka import TopicPartition

    config = _get_kafka_config(context)
    topics = ["argument-topic"] if arguments == "both topics and partitions" else None
    partitions = [TopicPartition("argument-topic", 0)] if arguments == "both topics and partitions" else None
    consumer_class = KafkaConsumerAdapter if mode == "sync" else AsyncKafkaConsumerAdapter
    _capture_error(
        context,
        lambda: consumer_class("argument-group", topic_list=topics, partition_list=partitions, kafka_configs=config),
    )


@when('I try to {operation} topic "{topic_name}"')
def step_try_admin_operation(context, operation, topic_name):
    """Create an already existing topic or delete a missing one, keeping the outcome."""
    adapter = get_kafka_admin_adapter(context)
    if operation == "create an existing":
        _create_topic_if_missing(adapter, topic_name)
        _capture_error(context, lambda: adapter.create_topic(topic_name))
    else:
        _capture_error(context, lambda: adapter.delete_topic([topic_name]))


@then('the Kafka operation should raise "{error_name}"')
def step_operation_should_raise(context, error_name):
    """Assert the captured exception is the named ArchiPy error."""
    error = get_current_scenario_context(context).get("kafka_operation_error")
    expected = getattr(archipy_errors, error_name)
    assert isinstance(error, expected), f"Expected {error_name}, got {error!r}"


@given('a single partition topic named "{topic_name}"')
def step_single_partition_topic(context, topic_name):
    """Create a one partition topic so that partition 0 holds every message."""
    adapter = get_kafka_admin_adapter(context)
    _create_topic_if_missing(adapter, topic_name, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(adapter, lambda name, topics: name in topics, topic_name)


def _poll_until_message(poll, deadline_seconds=20):
    """Poll once per second until a message arrives or the deadline passes."""
    deadline = time.monotonic() + deadline_seconds
    message = None
    while message is None and time.monotonic() < deadline:
        message = poll(1)
    return message


async def _async_poll_until_message(consumer, deadline_seconds=20):
    deadline = time.monotonic() + deadline_seconds
    message = None
    while message is None and time.monotonic() < deadline:
        message = await consumer.poll(timeout=1)
    return message


@then('a {mode} consumer assigned to partition 0 of topic "{topic_name}" should receive message "{expected}"')
def step_assigned_consumer_receives(context, mode, topic_name, expected):
    """Read a message through a consumer that was assigned a partition instead of subscribing."""
    from confluent_kafka import TopicPartition

    config = _get_kafka_config(context)
    partitions = [TopicPartition(topic_name, 0)]
    if mode == "sync":
        consumer = KafkaConsumerAdapter("assigned-group-sync", partition_list=partitions, kafka_configs=config)
        try:
            message = _poll_until_message(consumer.poll)
        finally:
            consumer.close()
    else:

        async def run():
            consumer = AsyncKafkaConsumerAdapter(
                "assigned-group-async", partition_list=partitions, kafka_configs=config,
            )
            try:
                return await _async_poll_until_message(consumer)
            finally:
                await consumer.close()

        message = asyncio.run(run())
    assert message is not None, "Assigned consumer received no message"
    assert message.value().decode("utf-8") == expected


@then('a {mode} consumer polling topic "{topic_name}" with group "{group_id}" should receive message "{expected}"')
def step_poll_receives(context, mode, topic_name, group_id, expected):
    """Poll a single message (not a batch) through a freshly created consumer."""
    config = _get_kafka_config(context)
    if mode == "sync":
        consumer = KafkaConsumerAdapter(group_id, topic_list=[topic_name], kafka_configs=config)
        try:
            message = _poll_until_message(consumer.poll)
        finally:
            consumer.close()
    else:

        async def run():
            consumer = AsyncKafkaConsumerAdapter(group_id, topic_list=[topic_name], kafka_configs=config)
            try:
                return await _async_poll_until_message(consumer)
            finally:
                await consumer.close()

        message = asyncio.run(run())
    assert message is not None, "Consumer polled no message"
    assert message.value().decode("utf-8") == expected


@then('a {mode} consumer polling the empty topic "{topic_name}" with group "{group_id}" should receive nothing')
def step_poll_receives_nothing(context, mode, topic_name, group_id):
    """Polling a topic without messages returns None instead of failing."""
    config = _get_kafka_config(context)
    if mode == "sync":
        consumer = KafkaConsumerAdapter(group_id, topic_list=[topic_name], kafka_configs=config)
        try:
            message = consumer.poll(timeout=1)
        finally:
            consumer.close()
    else:

        async def run():
            consumer = AsyncKafkaConsumerAdapter(group_id, topic_list=[topic_name], kafka_configs=config)
            try:
                return await consumer.poll(timeout=1)
            finally:
                await consumer.close()

        message = asyncio.run(run())
    assert message is None, f"Expected no message, got {message!r}"


@when('a {mode} producer for topic "{topic_name}" produces "{message}" without flushing and is closed')
def step_produce_and_close(context, mode, topic_name, message):
    """Closing a producer must flush what is still queued."""
    config = _get_kafka_config(context)
    if mode == "sync":
        producer = KafkaProducerAdapter(topic_name, kafka_configs=config)
        producer.produce(message)
        producer.close()
    else:

        async def run():
            producer = AsyncKafkaProducerAdapter(topic_name, kafka_configs=config)
            await producer.produce(message)
            await producer.close()

        asyncio.run(run())


@then('a {mode} producer for topic "{topic_name}" should list that topic')
def step_producer_lists_topic(context, mode, topic_name):
    """List one topic through a producer and find it in the metadata."""
    config = _get_kafka_config(context)
    if mode == "sync":
        metadata = KafkaProducerAdapter(topic_name, kafka_configs=config).list_topics(topic=topic_name, timeout=5)
    else:

        async def run():
            producer = AsyncKafkaProducerAdapter(topic_name, kafka_configs=config)
            try:
                return await producer.list_topics(topic=topic_name, timeout=5)
            finally:
                await producer.close()

        metadata = asyncio.run(run())
    assert topic_name in metadata.topics, f"{topic_name} missing from {list(metadata.topics)}"


# SASL_SSL client settings and broker hostname verification


def _sasl_ssl_config(setting):
    """Build a SASL_SSL configuration, leaving hostname verification at its default unless a value is given."""
    values = {
        "SECURITY_PROTOCOL": "SASL_SSL",
        "SASL_MECHANISM": "PLAIN",
        "USERNAME": "user",
        "PASSWORD": "pass",
        "SSL_CA_FILE": "/etc/ssl/certs/kafka-ca.pem",
    }
    if setting != "default":
        values["SSL_ENDPOINT_IDENTIFICATION_ALGORITHM"] = setting
    return KafkaConfig(**values)


@when("Kafka client settings are built for a {role} with hostname verification {setting}")
def step_build_sasl_ssl_settings(context, role, setting):
    """Build the librdkafka settings a client of the given role would use."""
    config = _sasl_ssl_config(setting)
    if role == "sync client":
        # The admin, sync producer and sync consumer apply the shared security settings while creating the client.
        settings = {}
        _apply_security_config(settings, config)
    elif role == "async producer":
        settings = AsyncKafkaProducerAdapter("tls-topic", kafka_configs=config)._build_producer_conf(config)
    else:
        adapter = AsyncKafkaConsumerAdapter(group_id="tls-group", topic_list=["tls-topic"], kafka_configs=config)
        settings = adapter._build_consumer_conf(config)
    get_current_scenario_context(context).store("kafka_client_settings", settings)


@then('the Kafka broker hostname verification should be "{expected}"')
def step_check_hostname_verification(context, expected):
    """The SSL settings must carry the expected endpoint identification algorithm."""
    settings = get_current_scenario_context(context).get("kafka_client_settings")
    actual = settings.get("ssl.endpoint.identification.algorithm")
    assert actual == expected, f"Expected hostname verification {expected!r}, got {actual!r}"


def _optional(value):
    """Map the feature-file placeholder '-' to None."""
    return None if value == "-" else value


def _security_values(protocol, mechanism, username, extra):
    """Build KafkaConfig keyword arguments, leaving out every setting given as '-'."""
    values = {"SECURITY_PROTOCOL": protocol, **extra}
    if _optional(mechanism):
        values["SASL_MECHANISM"] = mechanism
    if _optional(username):
        values["USERNAME"] = username
        values["PASSWORD"] = "pass"
    return values


@when(
    "Kafka client settings are built for protocol {protocol} with mechanism {mechanism}, username {username}, "
    "CA file {ca}, certificate {cert} and key {key}",
)
def step_build_protocol_settings(context, protocol, mechanism, username, ca, cert, key):
    """Build the librdkafka settings for a protocol and the security options that are set."""
    files = {"SSL_CA_FILE": ca, "SSL_CERT_FILE": cert, "SSL_KEY_FILE": key}
    extra = {name: value for name, value in files.items() if _optional(value)}
    config = KafkaConfig(**_security_values(protocol, mechanism, username, extra))
    settings = {}
    _apply_security_config(settings, config)
    get_current_scenario_context(context).store("kafka_client_settings", settings)


@then('the Kafka client settings should include "{keys}"')
def step_settings_include(context, keys):
    """Every listed librdkafka key must be present."""
    settings = get_current_scenario_context(context).get("kafka_client_settings")
    missing = [key for key in keys.split(",") if key not in settings]
    assert not missing, f"Missing {missing} in {sorted(settings)}"


@then('the Kafka client settings should not include "{keys}"')
def step_settings_exclude(context, keys):
    """None of the listed librdkafka keys may be present."""
    settings = get_current_scenario_context(context).get("kafka_client_settings")
    present = [key for key in keys.split(",") if key in settings]
    assert not present, f"Unexpected {present} in {sorted(settings)}"


@when("a Kafka configuration is validated with protocol {protocol}, mechanism {mechanism} and username {username}")
def step_validate_protocol_config(context, protocol, mechanism, username):
    """Try to build a Kafka configuration and keep the outcome."""
    error = None
    try:
        KafkaConfig(**_security_values(protocol, mechanism, username, {}))
    except (ConfigurationError, ValueError) as exc:
        error = exc
    get_current_scenario_context(context).store("kafka_config_error", error)


@then("the Kafka configuration should be rejected as incomplete")
def step_config_rejected(context):
    """Validation must fail with the incomplete SASL authentication reason."""
    error = get_current_scenario_context(context).get("kafka_config_error")
    assert error is not None, "Expected the configuration to be rejected"
    assert "sasl_auth_incomplete" in str(error), f"Unexpected error: {error}"


@when('I close the producer for topic "{topic_name}"')
def step_close_producer(context, topic_name):
    """Close the sync producer for a topic."""
    get_kafka_producer_adapter(context, topic_name).close()


@then('producing to the closed producer for topic "{topic_name}" should fail')
def step_produce_after_close_fails(context, topic_name):
    """Check the underlying client rejects writes once the adapter is closed."""
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter._adapter.produce(topic_name, b"after-close")
    except Exception as error:  # the client raises a RuntimeError (or KafkaException) once closed
        context.logger.info(f"Closed producer rejected the write: {type(error).__name__}")
        return
    raise AssertionError("Expected a closed producer to reject produce()")


# Applied client identity, connection and timeout settings


@when("Kafka client settings are built for a {role} with Kafka setting {setting} set to {value}")
def step_build_settings_with_option(context, role, setting, value):
    """Build the librdkafka settings of a client role with one KafkaConfig field set (or left unset)."""
    updates = {} if value == "unset" else {setting: value}
    config = KafkaConfig(**updates)
    if role == "sync client":
        settings = {}
        _apply_security_config(settings, config)
        _apply_client_config(settings, config, role="producer")
    elif role == "async producer":
        settings = AsyncKafkaProducerAdapter("opt-topic", kafka_configs=config)._build_producer_conf(config)
    else:
        adapter = AsyncKafkaConsumerAdapter(group_id="opt-group", topic_list=["opt-topic"], kafka_configs=config)
        settings = adapter._build_consumer_conf(config)
    get_current_scenario_context(context).store("kafka_client_settings", settings)


@then('the Kafka client option "{option}" should be "{expected}"')
def step_check_client_option(context, option, expected):
    """The built settings must carry the option with the expected value, or lack it when 'absent' is expected."""
    settings = get_current_scenario_context(context).get("kafka_client_settings")
    actual = "absent" if option not in settings else str(settings[option])
    assert actual == expected, f"Expected {option} to be {expected!r}, got {actual!r}"


@when(
    "I list topics with the {adapter_kind} adapter on that broker with the default timeout set to {timeout_ms:d} ms",
)
def step_list_topics_default_timeout(context, adapter_kind, timeout_ms):
    """List topics without a timeout argument so the configured LIST_TOPICS_TIMEOUT_MS applies, and time the call."""
    config = get_current_scenario_context(context).get("kafka_unreachable_config")
    config = config.model_copy(update={"LIST_TOPICS_TIMEOUT_MS": timeout_ms})
    started = time.monotonic()
    if adapter_kind == "admin":
        _capture_error(context, KafkaAdminAdapter(config).list_topics)
    elif adapter_kind == "sync producer":
        _capture_error(context, KafkaProducerAdapter("t", kafka_configs=config).list_topics)
    else:
        _capture_error(context, lambda: asyncio.run(AsyncKafkaProducerAdapter("t", kafka_configs=config).list_topics()))
    get_current_scenario_context(context).store("kafka_list_topics_elapsed", time.monotonic() - started)


@then("listing topics should have waited at least {seconds:f} seconds")
def step_list_topics_waited(context, seconds):
    """The call must fail only after the configured timeout elapsed."""
    scenario_context = get_current_scenario_context(context)
    elapsed = scenario_context.get("kafka_list_topics_elapsed")
    assert scenario_context.get("kafka_operation_error") is not None, "Expected listing topics to fail"
    assert elapsed >= seconds - 0.1, f"Failed after {elapsed:.2f}s, expected to wait at least {seconds}s"
