from abc import abstractmethod

class SchemaRegistryClientPort:
    """Interface for Schema Registry Client operations.

    Defines the contract for performing operations on the Confluent Schema Registry,
    such as retrieving and registering schemas.
    """

    @abstractmethod
    def get_schema(self, schema_id: int) -> str:
        """Fetches a schema string by its schema ID.

        Args:
            schema_id (int): The unique identifier of the schema.

        Returns:
            str: The string representation of the schema.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError

    @abstractmethod
    def register_schema(self, subject: str, schema_str: str, schema_type: str = "PROTOBUF") -> int:
        """Registers a schema under a given subject and returns the schema ID.

        Args:
            subject (str): The subject under which to register the schema.
            schema_str (str): The string representation of the schema.
            schema_type (str, optional): The type of schema. Defaults to "PROTOBUF".

        Returns:
            int: The unique identifier assigned to the registered schema.

        Raises:
            NotImplementedError: If the method is not implemented by the concrete class.
        """
        raise NotImplementedError