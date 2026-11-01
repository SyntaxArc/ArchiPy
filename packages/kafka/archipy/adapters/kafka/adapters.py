"""Kafka adapter implementations for ArchiPy."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NoReturn, override

import confluent_kafka
from confluent_kafka import (
    ConcurrentModificationException,
    Consumer,
    IllegalStateException,
    KafkaError,
    KafkaException,
    Message,
    Producer,
    TopicPartition,
)
from confluent_kafka.admin import AdminClient, ClusterMetadata, NewTopic
from confluent_kafka.aio import AIOConsumer, AIOProducer

from archipy.adapters.kafka.ports import (
    AsyncKafkaConsumerPort,
    AsyncKafkaProducerPort,
    KafkaAdminPort,
    KafkaConsumerPort,
    KafkaProducerPort,
)
from archipy.configs.base_config import BaseConfig
from archipy.models.errors import (
    AlreadyExistsError,
    BaseError,
    ConfigurationError,
    ConnectionTimeoutError,
    InternalError,
    InvalidArgumentError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    ResourceExhaustedError,
    ServiceUnavailableError,
    UnauthenticatedError,
    UnavailableError,
)

if TYPE_CHECKING:
    from concurrent.futures import Future

    from archipy.configs.config_template import KafkaConfig

logger = logging.getLogger(__name__)


def _end_consume_span(consumer: Consumer) -> None:
    """End the OpenTelemetry consume span of the polled message once its offset is committed.

    The Kafka instrumentor opens a ``<topic> process`` span when a message is polled and only ends it on the next
    ``poll``, ``consume`` or ``close``. The span then outlives the processing of the message and stays the current
    span of the thread, so spans of unrelated work become its children. A commit marks the end of processing,
    so it ends the span there.

    Args:
        consumer: The underlying ``confluent_kafka.Consumer``. Consumers that are not instrumented are left alone.
    """
    span = getattr(consumer, "_current_consume_span", None)
    if span is None:
        return
    token = getattr(consumer, "_current_context_token", None)
    if token is not None:
        from opentelemetry import context

        context.detach(token)
    # State owned by the instrumentor's consumer subclass, unknown to the confluent_kafka stubs.
    consumer._current_context_token = None  # ty: ignore[unresolved-attribute]
    span.end()
    consumer._current_consume_span = None  # ty: ignore[unresolved-attribute]


def _apply_security_config(config: dict[str, str | int | float], configs: KafkaConfig) -> None:
    """Add the security, SASL and SSL settings to a client configuration.

    ``security.protocol`` is always set. SASL settings are added for the SASL protocols and SSL settings for the
    SSL protocols; each is applied only when it is set, so mTLS without SASL, SASL_PLAINTEXT, GSSAPI, OAUTHBEARER
    and the system CA store all work. Broker hostname verification follows
    ``SSL_ENDPOINT_IDENTIFICATION_ALGORITHM`` (``https`` by default).

    Args:
        config: The librdkafka configuration dictionary to update in place.
        configs: Kafka configuration.
    """
    protocol = configs.SECURITY_PROTOCOL
    config["security.protocol"] = protocol
    if protocol in ("SASL_PLAINTEXT", "SASL_SSL"):
        if configs.SASL_MECHANISM:
            config["sasl.mechanism"] = configs.SASL_MECHANISM
        if configs.USERNAME:
            config["sasl.username"] = configs.USERNAME
        if configs.PASSWORD:
            config["sasl.password"] = configs.PASSWORD.get_secret_value()
    if protocol in ("SSL", "SASL_SSL"):
        if configs.SSL_CA_FILE:
            config["ssl.ca.location"] = configs.SSL_CA_FILE
        if configs.SSL_CERT_FILE:
            config["ssl.certificate.location"] = configs.SSL_CERT_FILE
        if configs.SSL_KEY_FILE:
            config["ssl.key.location"] = configs.SSL_KEY_FILE
        config["ssl.endpoint.identification.algorithm"] = configs.SSL_ENDPOINT_IDENTIFICATION_ALGORITHM


def _apply_client_config(config: dict[str, str | int | float], configs: KafkaConfig, *, role: str) -> None:
    """Add the client identity, connection and retry settings to a client configuration.

    ``client.id`` and ``connections.max.idle.ms`` are always set. The remaining options are applied only when set
    (``None`` keeps the librdkafka default). Producer-only and consumer-only options are added for their role only.

    Args:
        config: The librdkafka configuration dictionary to update in place.
        configs: Kafka configuration.
        role: ``"producer"``, ``"consumer"`` or ``"admin"``.
    """
    config["client.id"] = configs.CLIENT_ID
    config["connections.max.idle.ms"] = configs.CONNECTIONS_MAX_IDLE_MS
    optional: dict[str, str | int | bool | None] = {
        "socket.timeout.ms": configs.SOCKET_TIMEOUT_MS,
        "reconnect.backoff.max.ms": configs.RECONNECT_BACKOFF_MAX_MS,
        "retry.backoff.ms": configs.RETRY_BACKOFF_MS,
    }
    if role == "producer":
        optional["message.timeout.ms"] = configs.MESSAGE_TIMEOUT_MS
    elif role == "consumer":
        optional["group.instance.id"] = configs.GROUP_INSTANCE_ID
        optional["enable.auto.offset.store"] = configs.ENABLE_AUTO_OFFSET_STORE
    config.update({key: value for key, value in optional.items() if value is not None})


def _resolve_list_topics_timeout(configs: KafkaConfig, timeout: float | None) -> float:
    """Return the explicit timeout in seconds, or ``LIST_TOPICS_TIMEOUT_MS`` converted to seconds when None."""
    return configs.LIST_TOPICS_TIMEOUT_MS / 1000 if timeout is None else timeout


# Library/runtime failures observed at the Kafka client boundary.
_KAFKA_CLIENT_ERRORS: tuple[type[Exception], ...] = (
    KafkaException,
    BufferError,
    ConcurrentModificationException,
    IllegalStateException,
    ValueError,
    TypeError,
    OSError,
)


def _extract_kafka_error(exception: Exception) -> KafkaError | None:
    """Return the ``KafkaError`` carried by a ``KafkaException``, or None."""
    if isinstance(exception, KafkaException) and exception.args and isinstance(exception.args[0], KafkaError):
        return exception.args[0]
    return None


_TIMEOUT_CODES = frozenset({KafkaError._MSG_TIMED_OUT, KafkaError._TIMED_OUT, KafkaError.REQUEST_TIMED_OUT})
_NETWORK_CODES = frozenset({KafkaError._TRANSPORT, KafkaError.NETWORK_EXCEPTION})
_UNAVAILABLE_CODES = frozenset(
    {KafkaError._ALL_BROKERS_DOWN, KafkaError._RESOLVE, KafkaError.BROKER_NOT_AVAILABLE},
)
_AUTHENTICATION_CODES = frozenset({KafkaError._AUTHENTICATION, KafkaError.SASL_AUTHENTICATION_FAILED})
_AUTHORIZATION_CODES = frozenset(
    {
        KafkaError.TOPIC_AUTHORIZATION_FAILED,
        KafkaError.GROUP_AUTHORIZATION_FAILED,
        KafkaError.CLUSTER_AUTHORIZATION_FAILED,
        KafkaError.TRANSACTIONAL_ID_AUTHORIZATION_FAILED,
    },
)


class KafkaExceptionHandlerMixin:
    """Mixin class to handle Kafka exceptions in a consistent way."""

    @classmethod
    def _handle_kafka_exception(cls, exception: Exception, operation: str) -> NoReturn:
        """Handle Kafka exceptions and map them to appropriate application errors.

        Args:
            exception: The original exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_msg = str(exception).lower()

        kafka_error = _extract_kafka_error(exception)
        if kafka_error is not None:
            cls._raise_for_error_code(kafka_error, exception, operation)

        # Fallback for exceptions that carry no error code
        if "configuration" in error_msg:
            raise ConfigurationError(operation="kafka") from exception
        if "invalid" in error_msg:
            raise InvalidArgumentError(argument_name=operation) from exception
        if "timeout" in error_msg or "timed out" in error_msg:
            raise ConnectionTimeoutError(service="Kafka") from exception
        if "network" in error_msg:
            raise NetworkError(service="Kafka") from exception
        if "unavailable" in error_msg or "connection" in error_msg:
            raise ServiceUnavailableError(service="Kafka") from exception
        raise InternalError(additional_data={"operation": operation}) from exception

    @classmethod
    def _raise_for_error_code(cls, kafka_error: KafkaError, exception: Exception, operation: str) -> None:
        """Raise the application error that matches a librdkafka error code, or return for unknown codes.

        Args:
            kafka_error: The error carried by the exception.
            exception: The original exception, chained as the cause.
            operation: The name of the operation that failed.

        Raises:
            ConnectionTimeoutError: For timeout codes.
            NetworkError: For transport failures.
            ServiceUnavailableError: When no broker is reachable.
            UnauthenticatedError: For authentication failures.
            PermissionDeniedError: For authorization failures.
            InvalidArgumentError: For invalid arguments.
        """
        code = kafka_error.code()
        if code in _TIMEOUT_CODES:
            raise ConnectionTimeoutError(service="Kafka") from exception
        if code in _NETWORK_CODES:
            raise NetworkError(service="Kafka") from exception
        if code in _UNAVAILABLE_CODES:
            raise ServiceUnavailableError(service="Kafka") from exception
        if code in _AUTHENTICATION_CODES:
            raise UnauthenticatedError from exception
        if code in _AUTHORIZATION_CODES:
            raise PermissionDeniedError from exception
        if code == KafkaError._INVALID_ARG:
            # librdkafka reports a rejected client setting as an invalid argument naming the property.
            if "configuration property" in str(kafka_error.str()).lower():
                raise ConfigurationError(operation="kafka") from exception
            raise InvalidArgumentError(argument_name=operation) from exception

    @classmethod
    def _handle_producer_exception(cls, exception: Exception, operation: str) -> NoReturn:
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
        self._configs = configs
        try:
            broker_list_csv = ",".join(configs.BROKERS_LIST)
            config: dict[str, str | int | float] = {"bootstrap.servers": broker_list_csv}
            _apply_security_config(config, configs)
            _apply_client_config(config, configs, role="admin")
            self.adapter: AdminClient = AdminClient(config)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "KafkaAdmin_init")

    def _admin_timeout(self, timeout: float | None) -> float:
        """Return the explicit timeout in seconds, or ``REQUEST_TIMEOUT_MS`` converted to seconds when None."""
        return self._configs.REQUEST_TIMEOUT_MS / 1000 if timeout is None else timeout

    def _await_admin_futures(self, futures: dict[str, Future[None]], timeout: float | None, operation: str) -> None:
        """Wait for the per-topic futures of an admin call and raise the first failure.

        Args:
            futures: The ``{topic: Future}`` mapping returned by the confluent-kafka admin client.
            timeout: Seconds to wait for each future; None uses ``REQUEST_TIMEOUT_MS``.
            operation: The name of the operation, used for error mapping.

        Raises:
            AlreadyExistsError: If a topic to create already exists.
            NotFoundError: If a topic to delete does not exist.
            ConnectionTimeoutError: If a result does not arrive in time.
            Various other errors from the exception handler for broker failures.
        """
        wait = self._admin_timeout(timeout)
        for topic, future in futures.items():
            try:
                future.result(wait)
            except KafkaException as e:
                kafka_error = _extract_kafka_error(e)
                code = kafka_error.code() if kafka_error is not None else None
                if code == KafkaError.TOPIC_ALREADY_EXISTS:
                    raise AlreadyExistsError(resource_type=f"topic {topic}") from e
                if code == KafkaError.UNKNOWN_TOPIC_OR_PART:
                    raise NotFoundError(resource_type=f"topic {topic}") from e
                self._handle_kafka_exception(e, operation)
            except TimeoutError as e:
                raise ConnectionTimeoutError(service="Kafka", timeout=int(wait)) from e

    @override
    def create_topic(
        self,
        topic: str,
        num_partitions: int = 3,
        replication_factor: int = 1,
        timeout: float | None = None,
    ) -> None:
        """Creates a new Kafka topic and waits until the broker confirms it.

        Args:
            topic (str): Name of the topic to create.
            num_partitions (int, optional): Number of partitions for the topic. Defaults to 3.
            replication_factor (int, optional): Replication factor for the topic. Defaults to 1.
            timeout (float | None, optional): Seconds to wait for the broker. Defaults to None, which uses
                ``REQUEST_TIMEOUT_MS``.

        Raises:
            AlreadyExistsError: If the topic already exists.
            InvalidArgumentError: If the topic name or partition configuration is invalid.
            ConnectionTimeoutError: If the broker does not confirm in time.
            ServiceUnavailableError: If the Kafka service is unavailable during topic creation.
            InternalError: If there is an internal error creating the topic.
        """
        try:
            new_topic = NewTopic(topic, num_partitions, replication_factor)
            futures = self.adapter.create_topics([new_topic])
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "create_topic")
        self._await_admin_futures(futures, timeout, "create_topic")

    @override
    def delete_topic(self, topics: list[str], timeout: float | None = None) -> None:
        """Deletes one or more Kafka topics and waits until the broker confirms it.

        Args:
            topics (list[str]): List of topic names to delete.
            timeout (float | None, optional): Seconds to wait for the broker. Defaults to None, which uses
                ``REQUEST_TIMEOUT_MS``.

        Raises:
            NotFoundError: If a topic does not exist.
            InvalidArgumentError: If the topics list is invalid.
            ConnectionTimeoutError: If the broker does not confirm in time.
            ServiceUnavailableError: If the Kafka service is unavailable during topic deletion.
            InternalError: If there is an internal error deleting the topics.
        """
        try:
            futures = self.adapter.delete_topics(topics)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "delete_topic")
        self._await_admin_futures(futures, timeout, "delete_topic")
        logger.debug("Deleted topics: %s", topics)

    @override
    def list_topics(self, topic: str | None = None, timeout: float | None = None) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (float | None, optional): Timeout in seconds for the operation. Defaults to None, which uses
                ``LIST_TOPICS_TIMEOUT_MS``.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If the Kafka service is unavailable.
            UnavailableError: If there is an unknown issue accessing Kafka.
        """
        try:
            result = self.adapter.list_topics(topic=topic, timeout=_resolve_list_topics_timeout(self._configs, timeout))
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "list_topics")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # result is ClusterMetadata from confluent_kafka, compatible with port return type
            typed_result: ClusterMetadata = result
            return typed_result


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
            config: dict[str, str | int | float] = {
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
            _apply_security_config(config, configs)
            _apply_client_config(config, configs, role="consumer")
            # Looked up on the module at call time: OpenTelemetry's Kafka instrumentor replaces
            # ``confluent_kafka.Consumer``, so a name bound at import time would never be traced.
            consumer = confluent_kafka.Consumer(config)
        except _KAFKA_CLIENT_ERRORS as e:
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
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "batch_consume")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # result_list is list[Message] from confluent_kafka, compatible with port return type
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
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "poll")
        else:
            return message

    @override
    def commit(self, message: Message | None = None, asynchronous: bool = True) -> list[TopicPartition] | None:
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
                if message is not None:
                    self._adapter.commit(message=message, asynchronous=True)
                else:
                    self._adapter.commit(asynchronous=True)
                result = None
            elif message is not None:
                result = self._adapter.commit(message=message, asynchronous=False)
            else:
                result = self._adapter.commit(asynchronous=False)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "commit")
        else:
            _end_consume_span(self._adapter)
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
        except _KAFKA_CLIENT_ERRORS as e:
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
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "assign")

    @override
    def close(self) -> None:
        """Closes the consumer, leaving the consumer group and committing offsets.

        Raises:
            ServiceUnavailableError: If Kafka is unavailable during close.
            InternalError: If there is an error closing the consumer.
        """
        try:
            self._adapter.close()
            logger.debug("Consumer closed")
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "close")


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
        self._configs = configs
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
            config: dict[str, str | int | float] = {
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
            _apply_security_config(config, configs)
            _apply_client_config(config, configs, role="producer")
            # See the consumer: resolved at call time so the OpenTelemetry instrumentor can wrap it.
            producer = confluent_kafka.Producer(config)
        except _KAFKA_CLIENT_ERRORS as e:
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
            # Handle None key - convert to empty bytes if None
            processed_key = self._pre_process_message(key) if key is not None else b""
            self._adapter.produce(
                topic=self._topic_name,
                value=processed_message,
                callback=self._delivery_callback,
                key=processed_key,
            )
        except _KAFKA_CLIENT_ERRORS as e:
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
            remaining_messages = self._adapter.flush(timeout=timeout if timeout is not None else -1)
            if remaining_messages > 0:
                logger.warning("%d messages left in the queue after flush", remaining_messages)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "flush")

    @override
    def validate_healthiness(self) -> None:
        """Validates the health of the Kafka connection.

        Raises:
            UnavailableError: If the Kafka service is unavailable.
        """
        try:
            self.list_topics()
        except (*_KAFKA_CLIENT_ERRORS, BaseError) as e:
            raise UnavailableError(resource_type="Kafka") from e

    @override
    def list_topics(self, topic: str | None = None, timeout: float | None = None) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (float | None, optional): Timeout in seconds for the operation. Defaults to None, which uses
                ``LIST_TOPICS_TIMEOUT_MS``.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If the Kafka service is unavailable.
            UnavailableError: If there is an unknown issue accessing Kafka.
        """
        try:
            result = self._adapter.list_topics(
                topic=topic,
                timeout=_resolve_list_topics_timeout(self._configs, timeout),
            )
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "list_topics")
            raise  # Exception handler always raises, but type checker needs this to be explicit
        else:
            # result is ClusterMetadata from confluent_kafka, compatible with port return type
            typed_result: ClusterMetadata = result
            return typed_result

    @override
    def close(self) -> None:
        """Closes the producer, flushing any remaining messages.

        Raises:
            ConnectionTimeoutError: If the flush times out.
            ServiceUnavailableError: If Kafka is unavailable during close.
            InternalError: If there is an error closing the producer.
        """
        try:
            self._adapter.flush()
            # close() releases the client and aborts any open transaction (confluent-kafka 2.16+); flush alone did not
            self._adapter.close()
            logger.debug("Producer flushed and closed")
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "close")


class AsyncKafkaProducerAdapter(AsyncKafkaProducerPort, KafkaExceptionHandlerMixin):
    """Async Kafka producer adapter.

    This adapter provides async message production to Kafka topics using AIOProducer.
    It implements the AsyncKafkaProducerPort interface.
    """

    def __init__(self, topic_name: str, kafka_configs: KafkaConfig | None = None) -> None:
        """Initializes the async producer adapter with Kafka configuration.

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
        self._configs = configs
        self._adapter: AIOProducer | None = None

    def _build_producer_conf(self, configs: KafkaConfig) -> dict[str, str | int | float]:
        """Builds the producer configuration dictionary.

        Args:
            configs (KafkaConfig): Kafka configuration.

        Returns:
            dict[str, str | int | float]: Producer configuration dictionary.
        """
        broker_list_csv = ",".join(configs.BROKERS_LIST)
        config: dict[str, str | int | float] = {
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
        _apply_security_config(config, configs)
        _apply_client_config(config, configs, role="producer")
        return config

    async def _get_adapter(self) -> AIOProducer:
        """Returns the AIOProducer, creating it lazily on first async call.

        Returns:
            AIOProducer: The configured async producer instance.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error creating the producer.
        """
        if self._adapter is None:
            try:
                config = self._build_producer_conf(self._configs)
                self._adapter = AIOProducer(
                    config,
                    max_workers=self._configs.PRODUCER_MAX_WORKERS,
                    batch_size=self._configs.PRODUCER_BATCH_SIZE,
                    buffer_timeout=self._configs.PRODUCER_BUFFER_TIMEOUT,
                )
            except _KAFKA_CLIENT_ERRORS as e:
                self._handle_kafka_exception(e, "AsyncKafkaProducer_init")
        return self._adapter

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

    @override
    async def produce(self, message: str | bytes, key: str | None = None) -> None:
        """Produces a message to the configured topic asynchronously.

        Args:
            message (str | bytes): The message to produce.
            key (str | None, optional): The key for the message. Defaults to None.

        Raises:
            NetworkError: If there is a network error producing the message.
            ResourceExhaustedError: If the producer queue is full.
            InternalError: If there is an error producing the message.
        """
        try:
            adapter = await self._get_adapter()
            processed_message = self._pre_process_message(message)
            processed_key = self._pre_process_message(key) if key is not None else b""
            await adapter.produce(
                topic=self._topic_name,
                value=processed_message,
                key=processed_key,
            )
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_producer_exception(e, "produce")

    @override
    async def flush(self, timeout: int | None = None) -> None:
        """Flushes the producer queue asynchronously.

        Args:
            timeout (int | None, optional): Timeout in seconds for the operation. Defaults to None.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error flushing the queue.
        """
        try:
            adapter = await self._get_adapter()
            await adapter.flush()
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "flush")

    @override
    async def validate_healthiness(self) -> None:
        """Validates the health of the async Kafka producer connection.

        Raises:
            UnavailableError: If the Kafka service is unavailable.
        """
        try:
            await self.list_topics()
        except (*_KAFKA_CLIENT_ERRORS, BaseError) as e:
            raise UnavailableError(resource_type="Kafka") from e

    @override
    async def list_topics(self, topic: str | None = None, timeout: float | None = None) -> ClusterMetadata:
        """Lists Kafka topics asynchronously.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (float | None, optional): Timeout in seconds for the operation. Defaults to None, which uses
                ``LIST_TOPICS_TIMEOUT_MS``.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            ConnectionTimeoutError: If the operation times out.
            ServiceUnavailableError: If the Kafka service is unavailable.
            UnavailableError: If there is an unknown issue accessing Kafka.
        """
        try:
            adapter = await self._get_adapter()
            result = await adapter.list_topics(
                topic=topic,
                timeout=_resolve_list_topics_timeout(self._configs, timeout),
            )
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "list_topics")
            raise
        else:
            typed_result: ClusterMetadata = result
            return typed_result

    @override
    async def close(self) -> None:
        """Closes the async producer, flushing any remaining messages.

        Raises:
            ConnectionTimeoutError: If the flush times out.
            ServiceUnavailableError: If Kafka is unavailable during close.
            InternalError: If there is an error closing the producer.
        """
        try:
            if self._adapter is not None:
                await self._adapter.close()
                self._adapter = None
                logger.debug("Async producer closed")
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "close")


class AsyncKafkaConsumerAdapter(AsyncKafkaConsumerPort, KafkaExceptionHandlerMixin):
    """Async Kafka consumer adapter.

    This adapter provides async message consumption from Kafka topics using AIOConsumer.
    It implements the AsyncKafkaConsumerPort interface.
    """

    def __init__(
        self,
        group_id: str,
        topic_list: list[str] | None = None,
        partition_list: list[TopicPartition] | None = None,
        kafka_configs: KafkaConfig | None = None,
    ) -> None:
        """Initializes the async consumer adapter with Kafka configuration and subscription.

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
        self._configs = configs
        self._group_id = group_id
        self._topic_list = topic_list
        self._partition_list = partition_list
        self._adapter: AIOConsumer | None = None

        if not (topic_list or partition_list) or (topic_list and partition_list):
            logger.error("Invalid topic or partition list")
            raise InvalidArgumentError(
                argument_name="topic_list or partition_list",
                additional_data={"reason": "Exactly one of topic_list or partition_list must be provided"},
            )

    def _build_consumer_conf(self, configs: KafkaConfig) -> dict[str, str | int | float]:
        """Builds the consumer configuration dictionary.

        Args:
            configs (KafkaConfig): Kafka configuration.

        Returns:
            dict[str, str | int | float]: Consumer configuration dictionary.
        """
        broker_list_csv = ",".join(configs.BROKERS_LIST)
        config: dict[str, str | int | float] = {
            "bootstrap.servers": broker_list_csv,
            "group.id": self._group_id,
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
        _apply_security_config(config, configs)
        _apply_client_config(config, configs, role="consumer")
        return config

    async def _get_adapter(self) -> AIOConsumer:
        """Returns the AIOConsumer, creating and subscribing it lazily on first async call.

        Returns:
            AIOConsumer: The configured async consumer instance.

        Raises:
            ConfigurationError: If there is an error in the Kafka configuration.
            InternalError: If there is an error creating the consumer.
        """
        if self._adapter is None:
            try:
                config = self._build_consumer_conf(self._configs)
                self._adapter = AIOConsumer(config, max_workers=self._configs.CONSUMER_MAX_WORKERS)
                if self._topic_list:
                    await self._adapter.subscribe(self._topic_list)
                elif self._partition_list:
                    await self._adapter.assign(self._partition_list)
            except _KAFKA_CLIENT_ERRORS as e:
                self._handle_kafka_exception(e, "AsyncKafkaConsumer_init")
        return self._adapter

    @override
    async def batch_consume(self, messages_number: int = 500, timeout: int = 1) -> list[Message]:
        """Consumes a batch of messages from subscribed topics asynchronously.

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
            adapter = await self._get_adapter()
            result_list: list[Message] = []
            messages: list[Message] = await adapter.consume(num_messages=messages_number, timeout=timeout)
            for message in messages:
                if message.error():
                    logger.error("Async consumer error: %s", message.error())
                    continue
                logger.debug("Async message consumed: %s", message)
                message.set_value(message.value())
                result_list.append(message)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "batch_consume")
            raise
        else:
            return result_list

    @override
    async def poll(self, timeout: int = 1) -> Message | None:
        """Polls for a single message from subscribed topics asynchronously.

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
            adapter = await self._get_adapter()
            message: Message | None = await adapter.poll(timeout)
            if message is None:
                logger.debug("No async message received")
                return None
            if message.error():
                logger.error("Async consumer error: %s", message.error())
                return None
            logger.debug("Async message consumed: %s", message)
            message.set_value(message.value())
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "poll")
        else:
            return message

    @override
    async def commit(self, message: Message | None = None, asynchronous: bool = True) -> list[TopicPartition] | None:
        """Commits the offset for a message asynchronously.

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
            adapter = await self._get_adapter()
            result = await adapter.commit(message=message, asynchronous=asynchronous)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "commit")
        else:
            return result

    @override
    async def subscribe(self, topic_list: list[str]) -> None:
        """Subscribes to a list of topics asynchronously.

        Args:
            topic_list (list[str]): List of topics to subscribe to.

        Raises:
            InvalidArgumentError: If the topic list is invalid.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error subscribing to topics.
        """
        try:
            adapter = await self._get_adapter()
            await adapter.subscribe(topic_list)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "subscribe")

    @override
    async def assign(self, partition_list: list[TopicPartition]) -> None:
        """Assigns the async consumer to a list of topic partitions.

        Args:
            partition_list (list[TopicPartition]): List of partitions to assign.

        Raises:
            InvalidArgumentError: If the partition list is invalid.
            ServiceUnavailableError: If Kafka is unavailable.
            InternalError: If there is an error assigning partitions.
        """
        try:
            adapter = await self._get_adapter()
            await adapter.assign(partition_list)
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "assign")

    @override
    async def close(self) -> None:
        """Closes the async consumer, leaving the consumer group and committing offsets.

        Raises:
            ServiceUnavailableError: If Kafka is unavailable during close.
            InternalError: If there is an error closing the consumer.
        """
        try:
            if self._adapter is not None:
                await self._adapter.close()
                self._adapter = None
                logger.debug("Async consumer closed")
        except _KAFKA_CLIENT_ERRORS as e:
            self._handle_kafka_exception(e, "close")
