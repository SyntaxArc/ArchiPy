from abc import abstractmethod

from confluent_kafka import Message, TopicPartition
from confluent_kafka.admin import ClusterMetadata


class KafkaAdminPort:
    """Interface for Kafka admin operations.

    This interface defines the contract for performing administrative operations on Kafka topics.
    """

    @abstractmethod
    def create_topic(self, topic: str, num_partitions: int = 1, replication_factor: int = 1) -> None:
        """Creates a new Kafka topic.

        Args:
            topic (str): Name of the topic to create.
            num_partitions (int, optional): Number of partitions for the topic. Defaults to 1.
            replication_factor (int, optional): Replication factor for the topic. Defaults to 1.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_topic(self, topics: list[str]) -> None:
        """Deletes one or more Kafka topics.

        Args:
            topics (list[str]): List of topic names to delete.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def list_topics(self, topic: str | None = None, timeout: int = 1) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None, optional): Specific topic to list. If None, lists all topics.
                Defaults to None.
            timeout (int, optional): Timeout in seconds for the operation. Defaults to 1.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError


class KafkaConsumerPort:
    """Interface for Kafka consumer operations.

    This interface defines the contract for consuming messages from Kafka topics.
    """

    @abstractmethod
    def batch_consume(self, messages_number: int, timeout: int) -> list[Message]:
        """Consumes a batch of messages from subscribed topics.

        Args:
            messages_number (int): Maximum number of messages to consume.
            timeout (int): Timeout in seconds for the operation.

        Returns:
            list[Message]: List of consumed messages.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def poll(self, timeout: int) -> Message | None:
        """Polls for a single message from subscribed topics.

        Args:
            timeout (int): Timeout in seconds for the operation.

        Returns:
            Message | None: The consumed message or None if no message was received.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def commit(self, message: Message, asynchronous: bool) -> None | list[TopicPartition]:
        """Commits the offset of a consumed message.

        Args:
            message (Message): The message whose offset should be committed.
            asynchronous (bool): Whether to commit asynchronously.

        Returns:
            None | list[TopicPartition]: None for synchronous commits, or list of committed
                partitions for asynchronous commits.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, topic_list: list[str]) -> None:
        """Subscribes to a list of topics.

        Args:
            topic_list (list[str]): List of topic names to subscribe to.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def assign(self, partition_list: list[TopicPartition]) -> None:
        """Assigns specific partitions to the consumer.

        Args:
            partition_list (list[TopicPartition]): List of partitions to assign.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError


class KafkaProducerPort:
    """Interface for Kafka producer operations.

    This interface defines the contract for producing messages to Kafka topics.
    """

    @abstractmethod
    def produce(self, message: str | bytes, key: str | None = None) -> None:
        """Produces a message to the configured topic.

        Args:
            message (str | bytes): The message to produce.
            key (str | None, optional): The key for the message. Defaults to None.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def flush(self, timeout: int | None) -> None:
        """Flushes any pending messages to the broker.

        Args:
            timeout (int | None): Maximum time to wait for messages to be delivered.
                If None, wait indefinitely.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def validate_healthiness(self) -> None:
        """Validates the health of the producer connection.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def list_topics(self, topic: str | None, timeout: int) -> ClusterMetadata:
        """Lists Kafka topics.

        Args:
            topic (str | None): Specific topic to list. If None, lists all topics.
            timeout (int): Timeout in seconds for the operation.

        Returns:
            ClusterMetadata: Metadata about the Kafka cluster and topics.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError
