"""Kafka configuration."""

import logging
from typing import Literal

from pydantic import BaseModel, Field, SecretStr, model_validator

from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)


class KafkaConfig(BaseModel):
    """Configuration settings for Apache Kafka integration.

    Controls Kafka producer and consumer behavior, including broker connections,
    message delivery guarantees, and performance settings.
    """

    BROKERS_LIST: list[str] = Field(default=["localhost:9092"], description="List of Kafka broker addresses")
    SECURITY_PROTOCOL: str = Field(default="PLAINTEXT", description="Security protocol for Kafka connections")
    SASL_MECHANISM: str | None = Field(default=None, description="SASL mechanism for authentication")
    USERNAME: str | None = Field(default=None, description="Username for SASL authentication")
    PASSWORD: SecretStr | None = Field(default=None, description="Password for SASL authentication")
    SSL_CA_FILE: str | None = Field(default=None, description="Path to SSL CA certificate file")
    SSL_CERT_FILE: str | None = Field(default=None, description="Path to SSL certificate file")
    SSL_KEY_FILE: str | None = Field(default=None, description="Path to SSL key file")
    ACKS: Literal["0", "1", "all"] = Field(default="all", description="Acknowledgment mode for producers")
    AUTO_OFFSET_RESET: Literal["earliest", "latest", "none"] = Field(
        default="earliest",
        description="Offset reset policy for consumers",
    )
    ENABLE_AUTO_COMMIT: bool = Field(default=False, description="Enable auto-commit for consumer offsets")
    FETCH_MIN_BYTES: int = Field(default=1, ge=1, description="Minimum bytes to fetch per poll")
    SESSION_TIMEOUT_MS: int = Field(default=10000, ge=1000, description="Consumer session timeout (ms)")
    HEARTBEAT_INTERVAL_MS: int = Field(default=3000, ge=100, description="Consumer heartbeat interval (ms)")
    REQUEST_TIMEOUT_MS: int = Field(default=30000, ge=1000, description="Request timeout (ms)")
    DELIVERY_TIMEOUT_MS: int = Field(default=120000, ge=1000, description="Message delivery timeout (ms)")
    COMPRESSION_TYPE: Literal["none", "gzip", "snappy", "lz4", "zstd"] | None = Field(
        default=None,
        description="Compression type for messages",
    )
    LINGER_MS: int = Field(default=0, ge=0, description="Time to buffer messages before sending (ms)")
    BATCH_SIZE: int = Field(default=16384, ge=0, description="Maximum batch size in bytes")
    MAX_IN_FLIGHT_REQUESTS: int = Field(default=5, ge=1, description="Maximum unacknowledged requests per connection")
    RETRIES: int = Field(default=5, ge=0, description="Number of retries for failed producer requests")
    LIST_TOPICS_TIMEOUT_MS: int = Field(default=5000, ge=1000, description="Timeout for listing topics (ms)")
    CLIENT_ID: str = Field(default="kafka-client", description="Client identifier")
    CONNECTIONS_MAX_IDLE_MS: int = Field(
        default=540000,
        description="Close idle connections after this number of milliseconds",
    )
    ENABLE_IDEMPOTENCE: bool = Field(default=False, description="Enable idempotent producer for exactly-once delivery")
    TRANSACTIONAL_ID: str | None = Field(default=None, description="Transactional ID for the producer")
    ISOLATION_LEVEL: Literal["read_uncommitted", "read_committed"] = Field(
        default="read_uncommitted",
        description="Isolation level for consumer",
    )
    MAX_POLL_INTERVAL_MS: int = Field(default=300000, ge=1000, description="Maximum time between poll invocations")
    PARTITION_ASSIGNMENT_STRATEGY: str = Field(
        default="range",
        description="Partition assignment strategy for consumer",
    )
    FETCH_MAX_BYTES: int = Field(
        default=52428800,
        ge=0,
        description="Maximum amount of data the server returns for a fetch request",
    )
    MAX_PARTITION_FETCH_BYTES: int = Field(
        default=1048576,
        ge=0,
        description="Maximum amount of data per partition the server returns",
    )
    QUEUE_BUFFERING_MAX_MESSAGES: int = Field(
        default=100000,
        ge=0,
        description="Maximum number of messages allowed on the producer queue",
    )
    STATISTICS_INTERVAL_MS: int = Field(
        default=0,
        ge=0,
        description="Frequency in milliseconds to send statistics data",
    )

    # Async adapter settings (AIOProducer / AIOConsumer)
    CONSUMER_MAX_WORKERS: int = Field(default=2, ge=1, description="Thread pool workers for AIOConsumer")
    PRODUCER_BATCH_SIZE: int = Field(default=1000, ge=1, description="Max messages per AIOProducer batch")
    PRODUCER_BUFFER_TIMEOUT: float = Field(
        default=1.0,
        ge=0.0,
        description="Buffer flush timeout for AIOProducer (seconds)",
    )
    PRODUCER_MAX_WORKERS: int = Field(default=4, ge=1, description="Thread pool workers for AIOProducer")

    @model_validator(mode="after")
    def validate_security_settings(self) -> KafkaConfig:
        """Validate security-related settings for Kafka configuration.

        Ensures that SASL authentication settings are properly configured when
        using SASL security protocols, and warns about missing SSL certificates
        when SSL is enabled.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If SASL authentication is incomplete.
        """
        if self.SECURITY_PROTOCOL in ["SASL_PLAINTEXT", "SASL_SSL"] and not (
            self.SASL_MECHANISM and self.USERNAME and self.PASSWORD
        ):
            raise ConfigurationError(operation="kafka_validate", reason="sasl_auth_incomplete")
        if self.SECURITY_PROTOCOL == "SSL" and not (self.SSL_CA_FILE or self.SSL_CERT_FILE or self.SSL_KEY_FILE):
            logger.warning("SSL enabled but no SSL certificates provided; this may cause connection issues.")
        return self

    @model_validator(mode="after")
    def validate_consumer_settings(self) -> KafkaConfig:
        """Validate consumer-specific settings for Kafka configuration.

        Ensures that auto-commit and offset reset settings are compatible,
        and that heartbeat interval is less than session timeout.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If consumer settings are incompatible.
        """
        if self.ENABLE_AUTO_COMMIT and self.AUTO_OFFSET_RESET == "none":
            raise ConfigurationError(operation="kafka_consumer", reason="auto_commit_offset_reset_conflict")
        if self.HEARTBEAT_INTERVAL_MS >= self.SESSION_TIMEOUT_MS:
            raise ConfigurationError(operation="kafka_consumer", reason="heartbeat_exceeds_session_timeout")
        return self

    @model_validator(mode="after")
    def validate_idempotence_and_transactions(self) -> KafkaConfig:
        """Validate idempotence and transaction settings for Kafka configuration.

        Ensures that idempotence is properly configured with 'all' acknowledgments,
        and that transactional producers have idempotence enabled.

        Returns:
            KafkaConfig: The validated configuration instance.

        Raises:
            ValueError: If idempotence or transaction settings are invalid.
        """
        if self.ENABLE_IDEMPOTENCE and self.ACKS != "all":
            raise ConfigurationError(operation="kafka_producer", reason="idempotence_requires_acks_all")
        if self.TRANSACTIONAL_ID is not None and not self.ENABLE_IDEMPOTENCE:
            raise ConfigurationError(operation="kafka_producer", reason="transactional_id_requires_idempotence")
        return self
