from abc import abstractmethod
from collections.abc import AsyncIterator, Awaitable, Iterable
from typing import Any

ElasticsearchResponseType = Awaitable[Any] | Any
ElasticsearchDocumentType = dict[str, Any]
ElasticsearchQueryType = dict[str, Any]
ElasticsearchIndexType = str
ElasticsearchIdType = str
ElasticsearchBulkActionType = dict[str, Any] | str | bytes
ElasticsearchBulkResultType = tuple[int, int | list[dict[str, Any]]]


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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Index a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            document (ElasticsearchDocumentType): The document to index.
            doc_id (ElasticsearchIdType | None): Optional document ID. If not provided, Elasticsearch will generate one.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Get a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Search for documents in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            query (ElasticsearchQueryType): The search query.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Update a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            doc (ElasticsearchDocumentType): The document update.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Delete a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def bulk(
        self,
        actions: Iterable[ElasticsearchBulkActionType],
        stats_only: bool = False,
        **kwargs: Any,
    ) -> ElasticsearchBulkResultType:
        """Perform bulk operations using elasticsearch.helpers.bulk.

        Args:
            actions: Iterable of helper-format documents (generators supported). Each action uses
                ``_index``, ``_id``, ``_source``, and optional ``_op_type`` fields.
            stats_only: When True, return only success and error counts instead of error details.
            **kwargs: Additional keyword arguments passed to elasticsearch.helpers.bulk.

        Returns:
            A tuple of ``(success_count, error_count_or_error_list)``.

        Raises:
            NotImplementedError: If not implemented by the subclass.
            BulkIndexError: If any bulk operation fails and raise_on_error is True (default).
        """
        raise NotImplementedError

    @abstractmethod
    def scan(
        self,
        query: ElasticsearchQueryType | None = None,
        **kwargs: Any,
    ) -> Iterable[ElasticsearchDocumentType]:
        """Iterate over all matching documents using elasticsearch.helpers.scan.

        Args:
            query: Optional search query body. Defaults to match_all when omitted.
            **kwargs: Additional keyword arguments passed to elasticsearch.helpers.scan,
                including ``index``.

        Returns:
            An iterable yielding hit documents.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def create_index(
        self,
        index: ElasticsearchIndexType,
        body: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Create an index in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            body (dict[str, Any] | None): Optional index settings and mappings.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if a document exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Index a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            document (ElasticsearchDocumentType): The document to index.
            doc_id (ElasticsearchIdType | None): Optional document ID. If not provided, Elasticsearch will generate one.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Get a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Search for documents in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            query (ElasticsearchQueryType): The search query.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Update a document in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            doc (ElasticsearchDocumentType): The document update.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Delete a document from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def bulk(
        self,
        actions: Iterable[ElasticsearchBulkActionType],
        stats_only: bool = False,
        **kwargs: Any,
    ) -> ElasticsearchBulkResultType:
        """Perform bulk operations using elasticsearch.helpers.async_bulk.

        Args:
            actions: Iterable of helper-format documents (generators supported). Each action uses
                ``_index``, ``_id``, ``_source``, and optional ``_op_type`` fields.
            stats_only: When True, return only success and error counts instead of error details.
            **kwargs: Additional keyword arguments passed to elasticsearch.helpers.async_bulk.

        Returns:
            A tuple of ``(success_count, error_count_or_error_list)``.

        Raises:
            NotImplementedError: If not implemented by the subclass.
            BulkIndexError: If any bulk operation fails and raise_on_error is True (default).
        """
        raise NotImplementedError

    @abstractmethod
    async def scan(
        self,
        query: ElasticsearchQueryType | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ElasticsearchDocumentType]:
        """Iterate over all matching documents using elasticsearch.helpers.async_scan.

        Args:
            query: Optional search query body. Defaults to match_all when omitted.
            **kwargs: Additional keyword arguments passed to elasticsearch.helpers.async_scan,
                including ``index``.

        Yields:
            Hit documents from the scroll iteration.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
        yield  # pragma: no cover - required for async generator typing

    @abstractmethod
    async def create_index(
        self,
        index: ElasticsearchIndexType,
        body: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Create an index in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            body (dict[str, Any] | None): Optional index settings and mappings.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

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
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if a document exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            doc_id (ElasticsearchIdType): The document ID.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            **kwargs (Any): Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError
