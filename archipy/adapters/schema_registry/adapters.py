import logging
from typing import Any

from confluent_kafka.schema_registry import SchemaRegistryClient, Schema
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer, ProtobufDeserializer
from google.protobuf.message import Message

from archipy.adapters.schema_registry.ports import SchemaRegistryClientPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SchemaRegistryConfig, ProtobufSerializerConfig, ProtobufDeserializerConfig
from archipy.models.errors import (
    ConfigurationError,
    InternalError,
    InvalidArgumentError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

class SchemaRegistryExceptionHandlerMixin:
    """
    Mixin class for handling Schema Registry exceptions in a consistent way across adapters.
    Maps low-level exceptions to higher-level application errors for better error handling.
    """

    @classmethod
    def _handle_schema_registry_exception(cls, exception: Exception, operation: str) -> None:
        """
        Handles exceptions thrown by the Schema Registry client and maps them to
        application-specific error types.

        Args:
            exception (Exception): The exception raised by the underlying library.
            operation (str): The operation being performed when the error occurred.

        Raises:
            ConfigurationError: When there is a configuration-related issue.
            InvalidArgumentError: When invalid arguments are passed to an operation.
            ServiceUnavailableError: When the schema registry service is unavailable or connection fails.
            InternalError: For all other unexpected errors.
        """
        error_msg = str(exception).lower()
        if "configuration" in error_msg:
            raise ConfigurationError(config_key="schema_registry") from exception
        if "invalid" in error_msg:
            raise InvalidArgumentError(argument_name=operation) from exception
        if "unavailable" in error_msg or "connection" in error_msg:
            raise ServiceUnavailableError(service="SchemaRegistry") from exception
        raise InternalError(additional_data={"operation": operation}) from exception


class SchemaRegistryClientAdapter(SchemaRegistryClientPort, SchemaRegistryExceptionHandlerMixin):
    """
    Adapter for the Confluent Schema Registry Client.

    This adapter provides methods to interact with the schema registry, such as fetching
    and registering schemas. It implements the SchemaRegistryClientPort interface and
    offers consistent exception handling.
    """

    def __init__(self, schema_registry_config: SchemaRegistryConfig | None = None) -> None:
        """
        Initializes the Schema Registry Client adapter.

        Args:
            schema_registry_config (SchemaRegistryConfig | None, optional): Schema Registry
                configuration object. If None, uses the global configuration. Defaults to None.

        Raises:
            ConfigurationError: If there is an error in the configuration.
            InternalError: If there is an error initializing the client.
        """
        configs: SchemaRegistryConfig = schema_registry_config or BaseConfig.global_config().SCHEMA_REGISTRY
        self._adapter: SchemaRegistryClient = self._get_adapter(configs)

    @classmethod
    def _get_adapter(cls, configs: SchemaRegistryConfig) -> SchemaRegistryClient:
        """
        Instantiates and returns a SchemaRegistryClient using the provided configuration.

        Args:
            configs (SchemaRegistryConfig): The schema registry configuration.

        Returns:
            SchemaRegistryClient: Configured schema registry client.

        Raises:
            ConfigurationError, ServiceUnavailableError, InternalError
        """
        try:
            schema_registry_conf = {"url": configs.URL}
            if configs.BASIC_AUTH_USER_INFO:
                schema_registry_conf["basic.auth.user.info"] = configs.BASIC_AUTH_USER_INFO
                schema_registry_conf["basic.auth.credentials.source"] = "USER_INFO"
            if configs.SSL_CA_FILE:
                schema_registry_conf["ssl.ca.location"] = configs.SSL_CA_FILE
            if configs.SSL_CERT_FILE:
                schema_registry_conf["ssl.certificate.location"] = configs.SSL_CERT_FILE
            if configs.SSL_KEY_FILE:
                schema_registry_conf["ssl.key.location"] = configs.SSL_KEY_FILE
            schema_registry_client = SchemaRegistryClient(schema_registry_conf)
        except Exception as e:
            cls._handle_schema_registry_exception(e, "SchemaRegistryClient_init")
        else:
            return schema_registry_client

    def get_schema(self, schema_id: int) -> str:
        """
        Fetches the schema string by its schema ID.

        Args:
            schema_id (int): The unique identifier of the schema.

        Returns:
            str: The string representation of the schema.

        Raises:
            ConfigurationError: On configuration issues.
            InvalidArgumentError: If the schema ID is invalid.
            ServiceUnavailableError: If the registry is unavailable.
            InternalError: On other errors.
        """
        try:
            schema = self._adapter.get_schema(schema_id)
            return schema.schema_str
        except Exception as e:
            self._handle_schema_registry_exception(e, "get_schema")

    def register_schema(self, subject: str, schema_str: str, schema_type: str = "PROTOBUF") -> int:
        """
        Registers a schema under a given subject and returns the schema ID.

        Args:
            subject (str): The subject under which to register the schema.
            schema_str (str): The schema string (definition).
            schema_type (str, optional): The type of schema ("PROTOBUF", "AVRO", etc). Defaults to "PROTOBUF".

        Returns:
            int: The ID assigned to the registered schema.

        Raises:
            ConfigurationError: On configuration issues.
            InvalidArgumentError: If arguments are invalid.
            ServiceUnavailableError: If the registry is unavailable.
            InternalError: On other errors.
        """
        try:
            schema = Schema(schema_str, schema_type)
            schema_id = self._adapter.register_schema(subject, schema)
            return schema_id
        except Exception as e:
            self._handle_schema_registry_exception(e, "register_schema")

    def get_serializer(self, configs: ProtobufSerializerConfig, message_type: Message) -> ProtobufSerializer:
        """
        Instantiates and returns a ProtobufSerializer using the provided configuration.

        Args:
            configs (ProtobufSerializerConfig): Serializer configuration.
            message_type (Message): The protobuf message type to serialize.

        Returns:
            ProtobufSerializer: Configured protobuf serializer.

        Raises:
            ConfigurationError, ServiceUnavailableError, InternalError
        """
        try:
            config = {
                "auto.register.schemas": configs.AUTO_REGISTER_SCHEMAS,
                "normalize.schemas": configs.NORMALIZE_SCHEMAS,
                "use.schema.id": configs.USE_SCHEMA_ID,
                "use.latest.version": configs.USE_LATEST_VERSION,
                "use.latest.with.metadata": configs.USE_LATEST_WITH_METADATA,
                "skip.known.types": configs.SKIP_KNOWN_TYPES,
                "subject.name.strategy": configs.SUBJECT_NAME_STRATEGY,
                "reference.subject.name.strategy": configs.REFERENCE_SUBJECT_NAME_STRATEGY,
                "use.deprecated.format": configs.USE_DEPRECATED_FORMAT,
            }
            protobuf_serializer = ProtobufSerializer(
                msg_type=message_type,
                schema_registry_client=self._adapter,
                conf=config,
            )
        except Exception as e:
            self._handle_schema_registry_exception(e, "ProtobufSerializer")
        else:
            return protobuf_serializer

    def get_deserializer(self, configs: ProtobufDeserializerConfig, message_type: Message) -> Any:
        """
        Instantiates and returns a ProtobufDeserializer using the provided configuration.

        Args:
            configs (ProtobufDeserializerConfig): Deserializer configuration.
            message_type (Message): The protobuf message type to deserialize.

        Returns:
            ProtobufDeserializer: Configured protobuf deserializer.

        Raises:
            ConfigurationError, ServiceUnavailableError, InternalError
        """
        try:
            config = {
                "use.latest.version": configs.USE_LATEST_VERSION,
                "use.latest.with.metadata": configs.USE_LATEST_WITH_METADATA,
                "subject.name.strategy": configs.SUBJECT_NAME_STRATEGY,
                "use.deprecated.format": configs.USE_DEPRECATED_FORMAT,
            }
            protobuf_deserializer = ProtobufDeserializer(
                message_type=message_type,
                schema_registry_client=self._adapter,
                conf=config,
            )
        except Exception as e:
            self._handle_schema_registry_exception(e, "ProtobufDeserializer")
        else:
            return protobuf_deserializer
