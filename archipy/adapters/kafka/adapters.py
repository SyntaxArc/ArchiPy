import logging
from typing import override

from confluent_kafka import Consumer, KafkaError, Message, Producer, TopicPartition
from confluent_kafka.admin import AdminClient, ClusterMetadata, NewTopic

from archipy.adapters.kafka.ports import KafkaAdminPort, KafkaConsumerPort, KafkaProducerPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import KafkaConfig
from archipy.models.errors import (
    ConfigurationError,
    ConnectionTimeoutError,
    InternalError,
    InvalidArgumentError,
    NetworkError,
    ResourceExhaustedError,
    ServiceUnavailableError,
    UnavailableError,
)

logger = logging.getLogger(__name__)


class KafkaExceptionHandlerMixin:
    """Mixin class to handle Kafka exceptions in a consistent way."""

    @classmethod
    def _handle_kafka_exception(cls, exception: Exception, operation: str) -> None:
        """Handle Kafka exceptions and map them to appropriate application errors.

        Args:
            exception: The original exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_msg = str(exception).lower()

        # Configuration errors
        if "configuration" in error_msg:
            raise ConfigurationError(config_key="kafka") from exception

        # Invalid argument errors
        if "invalid" in error_msg:
            raise InvalidArgumentError(argument_name=operation) from exception

        # Timeout errors
        if "timeout" in error_msg:
            # Extract timeout value if available
            timeout = None
            if hasattr(exception, "args") and len(exception.args) > 1:
                try:
                    timeout = int(exception.args[1])
                except (IndexError, ValueError):
                    pass
            raise ConnectionTimeoutError(service="Kafka", timeout=timeout) from exception

        # Network/connectivity errors
        if "network" in error_msg:
            raise NetworkError(service="Kafka") from exception

        # Service availability errors
        if "unavailable" in error_msg or "connection" in error_msg:
            raise ServiceUnavailableError(service="Kafka") from exception
        raise InternalError(additional_data={"operation": operation}) from exception

    @classmethod
    def _handle_producer_exception(cls, exception: Exception, operation: str) -> None:
        """Handle producer-specific exceptions.

        Args:
            exception: The original exception
            operation: The name of the operation that failed

        Raises:
            ResourceExhaustedError: If the producer queue is full
            Various other errors from _handle_kafka_exception
        """
        # Producer-specific error handling
        if isinstance(exception, BufferError):
            raise ResourceExhaustedError(resource_type="producer_queue") from exception

        # Fall back to general Kafka error handling
        cls._handle_kafka_exception(exception, operation)


class KafkaAdminAdapter(KafkaAdminPort, KafkaExceptionHandlerMixin):
    """Synchronous Kafka admin adapter.

    This adapter provides synchronous administrative operations for Kafka topics.
    It implements the KafkaAdminPort interface and handles topic creation, deletion,
    and listing operations.
    """

    def __init__(self, kafka_configs: KafkaConfig | None = None) -> None:
        """Initializes the admin adapter with Kafka configuration.

        Args:
            kafka_configs (KafkaConfig | None, optional): Kafka configuration. If None,
                uses global config. Defaults to None.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error initializing the admin client.
        """
        configs: KafkaConfig = kafka_configs or BaseConfig.global_config().KAFKA
        try:
            broker_list_csv = ",".join(configs.BROKERS_LIST)
            config = {"bootstrap.servers": broker_list_csv}
            if configs.USERNAME and configs.PASSWORD and configs.SSL_CA_FILE:
                config |= {
                    "sasl.username": configs.USERNAME,
                    "sasl.password": configs.PASSWORD.get_secret_value(),
                    "security.protocol": configs.SECURITY_PROTOCOL,
                    "sasl.mechanism": configs.SASL_MECHANISM,
                    "ssl.ca.location": configs.SSL_CA_FILE,
                    "ssl.certificate.location": configs.SSL_CERT_FILE,
                    "ssl.key.location": configs.SSL_KEY_FILE,
                    "ssl.endpoint.identification.algorithm": "none",
                }
            self.adapter: AdminClient = AdminClient(config)
        except Exception as e:
            self._handle_kafka_exception(e, "KafkaAdmin_init")

    @override
    def create_topic(self, topic: str, num_partitions: int = 1, replication_factor: int = 1) -> None:
        """Creates a new Kafka topic.

        Args:
            topic (str): Name of the topic to create.
            num_partitions (int, optional): Number of partitions for the topic. Defaults to 1.
            replication_factor (int, optional): Replication factor for the topic. Defaults to 1.

        Raises:
            InvalidArgumentError: If the topic name or partition configuration is invalid.
            ServiceUnavailableError: If the Kafka service is unavailable during topic creation.
            InternalError: If there is an internal error creating the topic.
        """
        try:
            new_topic = NewTopic(topic, num_partitions, replication_factor)
            self.adapter.create_topics([new_topic])
        except Exception as e:
            self._handle_kafka_exception(e, "create_topic")

    @override
    def delete_topic(self, topics: list[str]) -> None:
        """Deletes one or more Kafka topics.

        Args:
            topics (list[str]): List of topic names to delete.

        Raises:
            InvalidArgumentError: If the topics list is invalid.
            ServiceUnavailableError: If the Kafka service is unavailable during topic deletion.
            InternalError: If there is an internal error deleting the topics.
        """
        try:
            self.adapter.delete_topics(topics)
            logger.debug("Deleted topics: %s", topics)
        except Exception as e:
            self._handle_kafka_exception(e, "delete_topic")

    @override
    def list_topics(self, topic: str | None = None, timeout: int = 1) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (int, optional): Timeout in seconds for the operation. Defaults to 1.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If the Kafka service is unavailable.
            UnavailableError: If there is an unknown issue accessing Kafka.
        """
        try:
            result = self.adapter.list_topics(topic=topic, timeout=timeout)
        except Exception as e:
            self._handle_kafka_exception(e, "list_topics")
        else:
            return result


class KafkaConsumerAdapter(KafkaConsumerPort, KafkaExceptionHandlerMixin):
    """Synchronous Kafka consumer adapter.

    This adapter provides synchronous message consumption from Kafka topics.
    It implements the KafkaConsumerPort interface and handles message polling,
    batch consumption, and offset management.
    """

    def __init__(
        self,
        group_id: str,
        topic_list: list[str] | None = None,
        partition_list: list[TopicPartition] | None = None,
        kafka_configs: KafkaConfig | None = None,
    ) -> None:
        """Initializes the consumer adapter with Kafka configuration and subscription.

        Args:
            group_id (str): Consumer group ID.
            topic_list (list[str] | None, optional): List of topics to subscribe to.
                Defaults to None.
            partition_list (list[TopicPartition] | None, optional): List of partitions
                to assign. Defaults to None.
            kafka_configs (KafkaConfig | None, optional): Kafka configuration. If None,
                uses global config. Defaults to None.

        Raises:
            InvalidArgumentError: If both topic_list and partition_list are provided or
                neither is provided.
            InternalError: If there is an error initializing the consumer.
        """
        configs: KafkaConfig = kafka_configs or BaseConfig.global_config().KAFKA
        self._adapter: Consumer = self._get_adapter(group_id, configs)
        if topic_list and not partition_list:
            self.subscribe(topic_list)
        elif not topic_list and partition_list:
            self.assign(partition_list)
        else:
            logger.error("Invalid topic or partition list")
            raise InvalidArgumentError(
                argument_name="topic_list or partition_list",
                additional_data={"reason": "Exactly one of topic_list or partition_list must be provided"},
            )

    @classmethod
    def _get_adapter(cls, group_id: str, configs: KafkaConfig) -> Consumer:
        """Creates and configures a Kafka Consumer instance.

        Args:
            group_id (str): Consumer group ID.
            configs (KafkaConfig): Kafka configuration.

        Returns:
            Consumer: Configured Kafka Consumer instance.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error creating the consumer.
        """
        try:
            broker_list_csv = ",".join(configs.BROKERS_LIST)
            config = {
                "bootstrap.servers": broker_list_csv,
                "group.id": group_id,
                "session.timeout.ms": configs.SESSION_TIMEOUT_MS,
                "auto.offset.reset": configs.AUTO_OFFSET_RESET,
                "enable.auto.commit": configs.ENABLE_AUTO_COMMIT,
                "fetch.min.bytes": configs.FETCH_MIN_BYTES,
                "heartbeat.interval.ms": configs.HEARTBEAT_INTERVAL_MS,
                "isolation.level": configs.ISOLATION_LEVEL,
                "max.poll.interval.ms": configs.MAX_POLL_INTERVAL_MS,
                "partition.assignment.strategy": configs.PARTITION_ASSIGNMENT_STRATEGY,
                "fetch.max.bytes": configs.FETCH_MAX_BYTES,
                "max.partition.fetch.bytes": configs.MAX_PARTITION_FETCH_BYTES,
            }
            if configs.USERNAME and configs.PASSWORD and configs.SSL_CA_FILE:
                config |= {
                    "sasl.username": configs.USERNAME,
                    "sasl.password": configs.PASSWORD.get_secret_value(),
                    "security.protocol": configs.SECURITY_PROTOCOL,
                    "sasl.mechanism": configs.SASL_MECHANISM,
                    "ssl.ca.location": configs.SSL_CA_FILE,
                    "ssl.certificate.location": configs.SSL_CERT_FILE,
                    "ssl.key.location": configs.SSL_KEY_FILE,
                    "ssl.endpoint.identification.algorithm": "none",
                }
            consumer = Consumer(config)
        except Exception as e:
            cls._handle_kafka_exception(e, "KafkaConsumer_init")
        else:
            return consumer

    @override
    def batch_consume(self, messages_number: int = 500, timeout: int = 1) -> list[Message]:
        """Consumes a batch of messages from subscribed topics.

        Args:
            messages_number (int, optional): Maximum number of messages to consume.
                Defaults to 500.
            timeout (int, optional): Timeout in seconds for the operation. Defaults to 1.

        Returns:
            list[Message]: List of consumed messages.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error consuming messages.
        """
        try:
            result_list: list[Message] = []
            messages: list[Message] = self._adapter.consume(num_messages=messages_number, timeout=timeout)
            for message in messages:
                if message.error():
                    logger.error("Consumer error: %s", message.error())
                    continue
                logger.debug("Message consumed: %s", message)
                message.set_value(message.value())
                result_list.append(message)
        except Exception as e:
            self._handle_kafka_exception(e, "batch_consume")
        else:
            return result_list

    @override
    def poll(self, timeout: int = 1) -> Message | None:
        """Polls for a single message from subscribed topics.

        Args:
            timeout (int, optional): Timeout in seconds for the operation. Defaults to 1.

        Returns:
            Message | None: The consumed message or None if no message was received.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error polling for messages.
        """
        try:
            message: Message | None = self._adapter.poll(timeout)
            if message is None:
                logger.debug("No message received")
                return None
            if message.error():
                logger.error("Consumer error: %s", message.error())
                return None
            logger.debug("Message consumed: %s", message)
            message.set_value(message.value())
        except Exception as e:
            self._handle_kafka_exception(e, "poll")
        else:
            return message

    @override
    def commit(self, message: Message, asynchronous: bool = True) -> None | list[TopicPartition]:
        """Commits the offset for a message.

        Args:
            message (Message): The message to commit.
            asynchronous (bool, optional): Whether to commit asynchronously. Defaults to True.

        Returns:
            None | list[TopicPartition]: None for async commits, list of TopicPartition for sync commits.

        Raises:
            InvalidArgumentError: If the message is invalid.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error committing the offset.
        """
        try:
            if asynchronous:
                self._adapter.commit(message=message, asynchronous=True)
                result = None
            else:
                result = self._adapter.commit(message=message, asynchronous=False)
        except Exception as e:
            self._handle_kafka_exception(e, "commit")
        else:
            return result

    @override
    def subscribe(self, topic_list: list[str]) -> None:
        """Subscribes to a list of topics.

        Args:
            topic_list (list[str]): List of topics to subscribe to.

        Raises:
            InvalidArgumentError: If the topic list is invalid.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error subscribing to topics.
        """
        try:
            self._adapter.subscribe(topic_list)
        except Exception as e:
            self._handle_kafka_exception(e, "subscribe")

    @override
    def assign(self, partition_list: list[TopicPartition]) -> None:
        """Assigns the consumer to a list of topic partitions.

        Args:
            partition_list (list[TopicPartition]): List of partitions to assign.

        Raises:
            InvalidArgumentError: If the partition list is invalid.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error assigning partitions.
        """
        try:
            self._adapter.assign(partition_list)
        except Exception as e:
            self._handle_kafka_exception(e, "assign")


class KafkaProducerAdapter(KafkaProducerPort, KafkaExceptionHandlerMixin):
    """Synchronous Kafka producer adapter.

    This adapter provides synchronous message production to Kafka topics.
    It implements the KafkaProducerPort interface and handles message production.
    """

    def __init__(self, topic_name: str, kafka_configs: KafkaConfig | None = None) -> None:
        """Initializes the producer adapter with Kafka configuration.

        Args:
            topic_name (str): Default topic name to produce messages to.
            kafka_configs (KafkaConfig | None, optional): Kafka configuration. If None,
                uses global config. Defaults to None.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error initializing the producer.
        """
        self._topic_name = topic_name
        configs: KafkaConfig = kafka_configs or BaseConfig.global_config().KAFKA
        self._adapter: Producer = self._get_adapter(configs)

    @classmethod
    def _get_adapter(cls, configs: KafkaConfig) -> Producer:
        """Creates and configures a Kafka Producer instance.

        Args:
            configs (KafkaConfig): Kafka configuration.

        Returns:
            Producer: Configured Kafka Producer instance.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error creating the producer.
        """
        try:
            broker_list_csv = ",".join(configs.BROKERS_LIST)
            config = {
                "bootstrap.servers": broker_list_csv,
                "linger.ms": configs.LINGER_MS,
                "batch.size": configs.BATCH_SIZE,
                "acks": configs.ACKS,
                "request.timeout.ms": configs.REQUEST_TIMEOUT_MS,
                "delivery.timeout.ms": configs.DELIVERY_TIMEOUT_MS,
                "compression.type": configs.COMPRESSION_TYPE or "none",
                "max.in.flight.requests.per.connection": configs.MAX_IN_FLIGHT_REQUESTS,
                "retries": configs.RETRIES,
                "enable.idempotence": configs.ENABLE_IDEMPOTENCE,
                "queue.buffering.max.messages": configs.QUEUE_BUFFERING_MAX_MESSAGES,
                "statistics.interval.ms": configs.STATISTICS_INTERVAL_MS,
            }
            if configs.TRANSACTIONAL_ID:
                config["transactional.id"] = configs.TRANSACTIONAL_ID
            if configs.USERNAME and configs.PASSWORD and configs.SSL_CA_FILE:
                config |= {
                    "sasl.username": configs.USERNAME,
                    "sasl.password": configs.PASSWORD.get_secret_value(),
                    "security.protocol": configs.SECURITY_PROTOCOL,
                    "sasl.mechanism": configs.SASL_MECHANISM,
                    "ssl.ca.location": configs.SSL_CA_FILE,
                    "ssl.certificate.location": configs.SSL_CERT_FILE,
                    "ssl.key.location": configs.SSL_KEY_FILE,
                    "ssl.endpoint.identification.algorithm": "none",
                }
            producer = Producer(config)
        except Exception as e:
            cls._handle_kafka_exception(e, "KafkaProducer_init")
        else:
            return producer

    @staticmethod
    def _pre_process_message(message: str | bytes) -> bytes:
        """Pre-processes a message to ensure it's in the correct format.

        Args:
            message (str | bytes): The message to pre-process.

        Returns:
            bytes: The pre-processed message as bytes.
        """
        if isinstance(message, str):
            return message.encode("utf-8")
        return message

    @staticmethod
    def _delivery_callback(error: KafkaError | None, message: Message) -> None:
        """Callback for message delivery confirmation.

        Args:
            error (KafkaError | None): Error that occurred during delivery, or None if successful.
            message (Message): The delivered message.
        """
        if error:
            logger.error("Message delivery failed: %s: %s", error, message.value())
        else:
            logger.debug(
                "Message delivered to %s [%d] at offset %d",
                message.topic(),
                message.partition(),
                message.offset(),
            )

    @override
    def produce(self, message: str | bytes, key: str | None = None) -> None:
        """Produces a message to the configured topic.

        Args:
            message (str | bytes): The message to produce.
            key (str | None, optional): The key for the message. Defaults to None.

        Raises:
            NetworkError: If there is a network error producing the message.
            ResourceExhaustedError: If the producer queue is full.
            InternalError: If there is an error producing the message.
        """
        try:
            processed_message = self._pre_process_message(message)
            processed_key = self._pre_process_message(key)
            self._adapter.produce(
                topic=self._topic_name,
                value=processed_message,
                callback=self._delivery_callback,
                key=processed_key,
            )
        except Exception as e:
            self._handle_producer_exception(e, "produce")

    @override
    def flush(self, timeout: int | None = None) -> None:
        """Flushes the producer queue.

        Args:
            timeout (int | None, optional): Timeout in seconds for the operation. Defaults to None.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error flushing the queue.
        """
        try:
            remaining_messages = self._adapter.flush(timeout=timeout)
            if remaining_messages > 0:
                logger.warning("%d messages left in the queue after flush", remaining_messages)
        except Exception as e:
            self._handle_kafka_exception(e, "flush")

    @override
    def validate_healthiness(self) -> None:
        """Validates the health of the Kafka connection.

        Raises:
            UnavailableError: If the Kafka service is unavailable.
        """
        try:
            self.list_topics(timeout=1)
        except Exception as e:
            raise UnavailableError(service="Kafka") from e

    @override
    def list_topics(self, topic: str | None = None, timeout: int = 1) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (int, optional): Timeout in seconds for the operation. Defaults to 1.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If the Kafka service is unavailable.
            UnavailableError: If there is an unknown issue accessing Kafka.
        """
        try:
            result = self._adapter.list_topics(topic=topic, timeout=timeout)
        except Exception as e:
            self._handle_kafka_exception(e, "list_topics")
        else:
            return result
