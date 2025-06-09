from abc import abstractmethod
from collections.abc import Awaitable
from typing import Any

ElasticsearchResponseType = Awaitable[Any] | Any
ElasticsearchDocumentType = dict[str, Any]
ElasticsearchQueryType = dict[str, Any]
ElasticsearchIndexType = str
ElasticsearchIdType = str


class ElasticsearchPort:
    """Interface for Elasticsearch operations providing a standardized access pattern.

    This interface defines the contract for Elasticsearch adapters, ensuring consistent
    implementation of Elasticsearch operations across different adapters. It covers all
    essential Elasticsearch functionality including document operations, search, and
    index management.
    """

    @abstractmethod
    def ping(self) -> ElasticsearchResponseType:
        """Tests the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: The response from the server.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def index(
        self,
        index: ElasticsearchIndexType,
        document: ElasticsearchDocumentType,
        doc_id: ElasticsearchIdType | None = None,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Index a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            document (ElasticsearchDocumentType): The document to index.
            doc_id (ElasticsearchIdType | None): Optional document ID. If not provided, Elasticsearch will generate one.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Get a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        index: ElasticsearchIndexType,
        query: ElasticsearchQueryType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Search for documents in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            query (ElasticsearchQueryType): The search query.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        doc: ElasticsearchDocumentType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Update a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            doc (ElasticsearchDocumentType): The document update.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def bulk(
        self,
        actions: list[dict[str, Any]],
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Perform bulk operations in Elasticsearch.

        Args:
            actions (list[dict[str, Any]]): List of bulk actions to perform.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def create_index(
        self,
        index: ElasticsearchIndexType,
        body: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Create an index in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            body (dict[str, Any] | None): Optional index settings and mappings.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def exists(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Check if a document exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


class AsyncElasticsearchPort:
    """Async interface for Elasticsearch operations providing a standardized access pattern.

    This interface defines the contract for async Elasticsearch adapters, ensuring consistent
    implementation of Elasticsearch operations across different adapters. It covers all
    essential Elasticsearch functionality including document operations, search, and
    index management.
    """

    @abstractmethod
    async def ping(self) -> ElasticsearchResponseType:
        """Tests the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: The response from the server.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def index(
        self,
        index: ElasticsearchIndexType,
        document: ElasticsearchDocumentType,
        doc_id: ElasticsearchIdType | None = None,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Index a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            document (ElasticsearchDocumentType): The document to index.
            doc_id (ElasticsearchIdType | None): Optional document ID. If not provided, Elasticsearch will generate one.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Get a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        index: ElasticsearchIndexType,
        query: ElasticsearchQueryType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Search for documents in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            query (ElasticsearchQueryType): The search query.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        doc: ElasticsearchDocumentType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Update a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            doc (ElasticsearchDocumentType): The document update.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def bulk(
        self,
        actions: list[dict[str, Any]],
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Perform bulk operations in Elasticsearch.

        Args:
            actions (list[dict[str, Any]]): List of bulk actions to perform.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_index(
        self,
        index: ElasticsearchIndexType,
        body: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Create an index in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            body (dict[str, Any] | None): Optional index settings and mappings.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        index: ElasticsearchIndexType,
        doc_id: ElasticsearchIdType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Check if a document exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (object): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
