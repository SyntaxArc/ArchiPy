# features/steps/kafka_steps.py
from behave import given, then, when
from confluent_kafka import TopicPartition
from features.test_helpers import get_current_scenario_context

from archipy.adapters.kafka.adapters import KafkaAdminAdapter, KafkaConsumerAdapter, KafkaProducerAdapter
from archipy.configs.config_template import KafkaConfig
from archipy.models.errors import UnavailableError

def get_kafka_admin_adapter(context):
    """Get or initialize the Kafka admin adapter."""
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "admin_adapter") or scenario_context.admin_adapter is None:
        # Get the kafka container
        test_containers = scenario_context.get("test_containers")
        kafka_container = test_containers.get_container("kafka")

        # Create Kafka Config
        kafka_config = KafkaConfig(
            BROKERS_LIST=[kafka_container.bootstrap_servers],
            SECURITY_PROTOCOL="PLAINTEXT",  # Test container uses plaintext
            REQUEST_TIMEOUT_MS=30000,  # Increase timeout for container startup
            LIST_TOPICS_TIMEOUT_MS=10000,  # Increase topic listing timeout
        )

        context.logger.info("Initializing Kafka admin adapter")
        scenario_context.admin_adapter = KafkaAdminAdapter(kafka_config)
    return scenario_context.admin_adapter


def get_kafka_producer_adapter(context, topic_name):
    """Get or initialize the Kafka producer adapter."""
    scenario_context = get_current_scenario_context(context)
    if (
        not hasattr(scenario_context, f"producer_{topic_name}")
        or getattr(scenario_context, f"producer_{topic_name}") is None
    ):
        # Get the kafka container
        test_containers = scenario_context.get("test_containers")
        kafka_container = test_containers.get_container("kafka")

        # Create KafkaConfig
        kafka_config = KafkaConfig(
            BROKERS_LIST=[kafka_container.bootstrap_servers],
            SECURITY_PROTOCOL="PLAINTEXT",  # Test container uses plaintext
            REQUEST_TIMEOUT_MS=30000,  # Increase timeout for container startup
            DELIVERY_TIMEOUT_MS=120000,  # Increase delivery timeout
        )

        context.logger.info(f"Initializing Kafka producer for topic: {topic_name}")
        producer = KafkaProducerAdapter(topic_name, kafka_configs=kafka_config)
        setattr(scenario_context, f"producer_{topic_name}", producer)
    return getattr(scenario_context, f"producer_{topic_name}")


def get_kafka_consumer_adapter(context, topic_name, group_id):
    """Get or initialize the Kafka consumer adapter."""
    scenario_context = get_current_scenario_context(context)
    consumer_key = f"consumer_{topic_name}_{group_id}"
    if not hasattr(scenario_context, consumer_key) or getattr(scenario_context, consumer_key) is None:
        # Get the kafka container
        test_containers = scenario_context.get("test_containers")
        kafka_container = test_containers.get_container("kafka")

        # Create KafkaConfig
        kafka_config = KafkaConfig(
            BROKERS_LIST=[kafka_container.bootstrap_servers],
            SECURITY_PROTOCOL="PLAINTEXT",  # Test container uses plaintext
            REQUEST_TIMEOUT_MS=30000,  # Increase timeout for container startup
            SESSION_TIMEOUT_MS=15000,  # Increase session timeout
            HEARTBEAT_INTERVAL_MS=5000,  # Increase heartbeat interval
        )

        context.logger.info(f"Initializing Kafka consumer for topic: {topic_name}, group: {group_id}")
        consumer = KafkaConsumerAdapter(group_id=group_id, topic_list=[topic_name], kafka_configs=kafka_config)
        setattr(scenario_context, consumer_key, consumer)
    return getattr(scenario_context, consumer_key)

# Given steps
@given("a configured Kafka admin adapter")
def step_configured_admin_adapter(context):
    adapter = get_kafka_admin_adapter(context)
    try:
        adapter.list_topics(timeout=1)
        context.logger.info("Successfully connected to Kafka server")
    except Exception as e:
        context.logger.exception(f"Failed to connect to Kafka: {str(e)}")
        raise


@given('a test topic named "{topic_name}"')
def step_test_topic(context, topic_name):
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


@given('a Kafka producer for topic "{topic_name}"')
def step_producer_exists(context, topic_name):
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter.validate_healthiness()
        context.logger.info(f"Ensured producer for topic '{topic_name}' is healthy")
    except Exception as e:
        context.logger.exception(f"Failed to initialize producer: {str(e)}")
        raise


@given('a Kafka consumer subscribed to topic "{topic_name}" with group "{group_id}"')
def step_consumer_exists(context, topic_name, group_id):
    adapter = get_kafka_consumer_adapter(context, topic_name, group_id)
    try:
        adapter.subscribe([topic_name])
        context.logger.info(f"Ensured consumer subscribed to '{topic_name}' with group '{group_id}'")
    except Exception as e:
        context.logger.exception(f"Failed to initialize consumer: {str(e)}")
        raise


# When steps
@when('I create a topic named "{topic_name}"')
def step_create_topic(context, topic_name):
    adapter = get_kafka_admin_adapter(context)
    try:
        adapter.create_topic(topic_name)
        context.logger.info(f"Created topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to create topic: {str(e)}")
        raise


@when('I produce a message "{message}" to topic "{topic_name}"')
def step_produce_message(context, message, topic_name):
    adapter = get_kafka_producer_adapter(context, topic_name)
    try:
        adapter.produce(message)
        adapter.flush(timeout=1)
        context.logger.info(f"Produced message '{message}' to '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to produce message: {str(e)}")
        raise e


@when("I validate the producer health")
def step_validate_health(context):
    scenario_context = get_current_scenario_context(context)
    producer = getattr(scenario_context, "producer_test-topic", None)
    if not producer:
        context.logger.error("No producer found for health validation")
        raise AssertionError("Producer not initialized")
    try:
        producer.validate_healthiness()
        context.logger.info("Producer health validated")
    except Exception as e:
        context.logger.exception(f"Health validation failed: {str(e)}")
        raise


@when('I delete the topic "{topic_name}"')
def step_delete_topic(context, topic_name):
    adapter = get_kafka_admin_adapter(context)
    try:
        adapter.delete_topic([topic_name])
        context.logger.info(f"Deleted topic '{topic_name}'")
    except Exception as e:
        context.logger.exception(f"Failed to delete topic: {str(e)}")
        raise


# Then steps
@then('the topic "{topic_name}" should exist')
def step_topic_should_exist(context, topic_name):
    adapter = get_kafka_admin_adapter(context)
    try:
        topics = adapter.list_topics(timeout=1).topics
        assert topic_name in topics, f"Topic '{topic_name}' does not exist"
        context.logger.info(f"Verified topic '{topic_name}' exists")
    except Exception as e:
        context.logger.exception(f"Failed to verify topic existence: {str(e)}")
        raise


@then('the topic "{topic_name}" should not exist')
def step_topic_should_not_exist(context, topic_name):
    adapter = get_kafka_admin_adapter(context)
    try:
        topics = adapter.list_topics(timeout=1).topics
        assert topic_name not in topics, f"Topic '{topic_name}' still exists"
        context.logger.info(f"Verified topic '{topic_name}' does not exist")
    except Exception as e:
        context.logger.exception(f"Failed to verify topic non-existence: {str(e)}")
        raise


@then('the topic list should include "{topic_name}"')
def step_topic_list_includes(context, topic_name):
    adapter = get_kafka_admin_adapter(context)
    try:
        topics = adapter.list_topics(timeout=1).topics
        assert topic_name in topics, f"Topic '{topic_name}' not in topic list"
        context.logger.info(f"Verified '{topic_name}' in topic list")
    except Exception as e:
        context.logger.exception(f"Failed to verify topic list: {str(e)}")
        raise


@then('the consumer should receive message "{expected_message}" from topic "{topic_name}"')
def step_consumer_receive(context, expected_message, topic_name):
    adapter = get_kafka_consumer_adapter(context, topic_name, "test-group")
    try:
        messages = adapter.batch_consume(messages_number=1, timeout=2)
        assert len(messages) > 0, "No messages received"
        received_message = messages[0].value().decode("utf-8")
        assert received_message == expected_message, f"Expected '{expected_message}', got '{received_message}'"
        context.logger.info(f"Verified received message '{expected_message}'")
    except Exception as e:
        context.logger.exception(f"Failed to consume message: {str(e)}")
        raise


@then("the producer health check should pass")
def step_health_check_pass(context):
    scenario_context = get_current_scenario_context(context)
    producer = getattr(scenario_context, "producer_test-topic", None)
    if not producer:
        context.logger.error("No producer found for health check")
        raise AssertionError("Producer not initialized")
    try:
        producer.validate_healthiness()
        context.logger.info("Producer health check passed")
    except UnavailableError as e:
        context.logger.error(f"Health check failed: {str(e)}")
        raise AssertionError(f"Producer health check failed: {str(e)}")
