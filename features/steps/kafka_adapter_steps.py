"""Step definitions for Kafka adapter BDD tests."""

import time

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.adapters.kafka.adapters import (
    AsyncKafkaConsumerAdapter,
    AsyncKafkaProducerAdapter,
    KafkaAdminAdapter,
    KafkaConsumerAdapter,
    KafkaProducerAdapter,
)
from archipy.models.errors import UnavailableError


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
        consumer = KafkaConsumerAdapter(group_id=group_id, topic_list=[topic_name], kafka_configs=_get_kafka_config(context))
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
        consumer = AsyncKafkaConsumerAdapter(group_id=group_id, topic_list=[topic_name], kafka_configs=_get_kafka_config(context))
        setattr(scenario_context, key, consumer)
    return getattr(scenario_context, key)


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
            adapter.create_topic(topic_name)
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
            adapter.create_topic(topic_name)
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
        adapter.create_topic(topic_name)
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
        messages = adapter.batch_consume(messages_number=1, timeout=10)
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
        messages = adapter.batch_consume(messages_number=count, timeout=10)
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
    assert actual_key.decode("utf-8") == expected_key, f"Expected key '{expected_key}', got '{actual_key.decode('utf-8')}'"
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


@then('the async consumer should receive message "{expected_message}" from topic "{topic_name}" with group "{group_id}"')
async def step_async_consumer_receive(context, expected_message, topic_name, group_id):
    """Assert that an async consumer receives the expected single message."""
    adapter = get_async_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        messages = await adapter.batch_consume(messages_number=1, timeout=10)
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
        messages = await adapter.batch_consume(messages_number=count, timeout=10)
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
    assert actual_key.decode("utf-8") == expected_key, f"Expected key '{expected_key}', got '{actual_key.decode('utf-8')}'"
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
