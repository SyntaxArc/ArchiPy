from abc import abstractmethod
from collections.abc import Awaitable
from typing import Any

VespaResponseType = Awaitable[Any] | Any
VespaDocumentType = dict[str, Any]
VespaQueryType = dict[str, Any]
VespaIdType = str
VespaNamespaceType = str
VespaDocumentTypeType = str
VespaSchemaType = dict[str, Any]
VespaFieldType = dict[str, Any]


class VespaPort:
    """Interface for Vespa AI operations providing a standardized access pattern.

    This interface defines the contract for Vespa adapters, ensuring consistent
    implementation of Vespa operations across different adapters. It covers all
    essential Vespa functionality including document operations, search, and
    schema management.
    """

    @abstractmethod
    def query(
        self,
        query_string: str,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Query documents in Vespa.

        Args:
            query_string (str): The YQL query string.
            document_type (VespaDocumentTypeType): The document type to query.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The query results.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def feed(
        self,
        document: VespaDocumentType,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Feed a document to Vespa.

        Args:
            document (VespaDocumentType): The document to feed.
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The document if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        update_dict: dict[str, Any],
        **kwargs: object,
    ) -> VespaResponseType:
        """Update a document in Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            update_dict (Dict[str, Any]): The update dictionary.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def create_schema(
        self,
        schema: VespaSchemaType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Create a schema in Vespa.

        Args:
            schema (VespaSchemaType): The schema definition.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The schema if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def deploy(
        self,
        **kwargs: object,
    ) -> VespaResponseType:
        """Deploy the application to Vespa.

        Args:
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncVespaPort:
    """Async interface for Vespa AI operations providing a standardized access pattern.

    This interface defines the contract for async Vespa adapters, ensuring consistent
    implementation of Vespa operations across different adapters. It covers all
    essential Vespa functionality including document operations, search, and
    schema management.
    """

    @abstractmethod
    async def query(
        self,
        query_string: str,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Query documents in Vespa.

        Args:
            query_string (str): The YQL query string.
            document_type (VespaDocumentTypeType): The document type to query.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The query results.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def feed(
        self,
        document: VespaDocumentType,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Feed a document to Vespa.

        Args:
            document (VespaDocumentType): The document to feed.
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a document from Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The document if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        document_id: VespaIdType,
        document_type: VespaDocumentTypeType,
        update_dict: dict[str, Any],
        **kwargs: object,
    ) -> VespaResponseType:
        """Update a document in Vespa.

        Args:
            document_id (VespaIdType): The document ID.
            document_type (VespaDocumentTypeType): The document type.
            update_dict (Dict[str, Any]): The update dictionary.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_schema(
        self,
        schema: VespaSchemaType,
        **kwargs: object,
    ) -> VespaResponseType:
        """Create a schema in Vespa.

        Args:
            schema (VespaSchemaType): The schema definition.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Delete a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_schema(
        self,
        schema_name: str,
        **kwargs: object,
    ) -> VespaResponseType:
        """Get a schema from Vespa.

        Args:
            schema_name (str): The schema name.
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The schema if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def deploy(
        self,
        **kwargs: object,
    ) -> VespaResponseType:
        """Deploy the application to Vespa.

        Args:
            **kwargs (object): Additional keyword arguments passed to the Vespa client.

        Returns:
            VespaResponseType: The response from Vespa.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
