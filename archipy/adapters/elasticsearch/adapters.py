import logging
from typing import Any, override

from elasticsearch import AsyncElasticsearch, Elasticsearch

from archipy.adapters.elasticsearch.ports import (
    AsyncElasticsearchPort,
    ElasticsearchDocumentType,
    ElasticsearchIdType,
    ElasticsearchIndexType,
    ElasticsearchPort,
    ElasticsearchQueryType,
    ElasticsearchResponseType,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ElasticsearchConfig

logger = logging.getLogger(__name__)


class ElasticsearchAdapter(ElasticsearchPort):
    """Concrete implementation of the ElasticsearchPort interface using elasticsearch-py library.

    This implementation provides a standardized way to interact with Elasticsearch,
    abstracting the underlying client implementation details.
    """

    def __init__(self, elasticsearch_config: ElasticsearchConfig | None = None) -> None:
        """Initialize the ElasticsearchAdapter with configuration settings.

        Args:
            elasticsearch_config (ElasticsearchConfig, optional): Configuration settings for Elasticsearch.
                If None, retrieves from global config. Defaults to None.
        """
        configs: ElasticsearchConfig = (
            BaseConfig.global_config().ELASTIC if elasticsearch_config is None else elasticsearch_config
        )
        self.client = self._get_client(configs)

    @staticmethod
    def _get_client(configs: ElasticsearchConfig) -> Elasticsearch:
        """Create an Elasticsearch client with the specified configuration.

        Args:
            configs (ElasticsearchConfig): Configuration settings for Elasticsearch.

        Returns:
            Elasticsearch: Configured Elasticsearch client instance.
        """
        api_key: tuple[str, str] | None = None
        basic_auth: tuple[str, str] | None = None
        if configs.API_KEY and configs.API_SECRET:
            api_key = (configs.API_KEY, configs.API_SECRET.get_secret_value())
        elif configs.HTTP_USER_NAME and configs.HTTP_PASSWORD:
            basic_auth = (configs.HTTP_USER_NAME, configs.HTTP_PASSWORD.get_secret_value())

        # Build kwargs, only including SSL parameters if they have values
        kwargs: dict[str, Any] = {
            "hosts": configs.HOSTS,
            "api_key": api_key,
            "basic_auth": basic_auth,
            "request_timeout": configs.REQUEST_TIMEOUT,
            "retry_on_status": configs.RETRY_ON_STATUS,
            "retry_on_timeout": configs.RETRY_ON_TIMEOUT,
            "max_retries": configs.MAX_RETRIES,
            "http_compress": configs.HTTP_COMPRESS,
            "connections_per_node": configs.CONNECTIONS_PER_NODE,
            "verify_certs": configs.VERIFY_CERTS,
            "sniff_on_start": configs.SNIFF_ON_START,
            "sniff_before_requests": configs.SNIFF_BEFORE_REQUESTS,
            "sniff_on_node_failure": configs.SNIFF_ON_NODE_FAILURE,
            "max_dead_node_backoff": configs.MAX_DEAD_NODE_BACKOFF,
        }

        # Only add SSL parameters if they have values (to avoid passing None)
        if configs.CA_CERTS:
            kwargs["ca_certs"] = configs.CA_CERTS
        if configs.CLIENT_KEY:
            kwargs["client_key"] = configs.CLIENT_KEY
        if configs.CLIENT_CERT:
            kwargs["client_cert"] = configs.CLIENT_CERT
        if configs.SSL_ASSERT_FINGERPRINT:
            kwargs["ssl_assert_fingerprint"] = configs.SSL_ASSERT_FINGERPRINT

        return Elasticsearch(**kwargs)

    @override
    def ping(self) -> ElasticsearchResponseType:
        """Test the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: True if the connection is successful.
        """
        return self.client.ping()

    @override
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
            doc_id (ElasticsearchIdType | None): Optional document ID.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.index(index=index, document=document, id=doc_id, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.
        """
        return self.client.get(index=index, id=doc_id, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.
        """
        return self.client.search(index=index, body=query, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.update(index=index, id=doc_id, doc=doc, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.delete(index=index, id=doc_id, **kwargs)

    @override
    def bulk(
        self,
        actions: list[dict[str, Any]],
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Perform bulk operations in Elasticsearch.

        Args:
            actions (list[dict[str, Any]]): List of bulk actions to perform.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.

        Raises:
            BulkIndexError: If any of the bulk operations fail.
        """
        return self.client.bulk(operations=actions, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.indices.create(index=index, body=body, **kwargs)

    @override
    def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.indices.delete(index=index, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.
        """
        return self.client.exists(index=index, id=doc_id, **kwargs)

    @override
    def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.
        """
        return self.client.indices.exists(index=index, **kwargs)


class AsyncElasticsearchAdapter(AsyncElasticsearchPort):
    """Concrete implementation of the AsyncElasticsearchPort interface using elasticsearch-py library.

    This implementation provides a standardized way to interact with Elasticsearch asynchronously,
    abstracting the underlying client implementation details.
    """

    def __init__(self, elasticsearch_config: ElasticsearchConfig | None = None) -> None:
        """Initialize the AsyncElasticsearchAdapter with configuration settings.

        Args:
            elasticsearch_config (ElasticsearchConfig, optional): Configuration settings for Elasticsearch.
                If None, retrieves from global config. Defaults to None.
        """
        configs: ElasticsearchConfig = (
            BaseConfig.global_config().ELASTIC if elasticsearch_config is None else elasticsearch_config
        )
        self.client = self._get_client(configs)

    @staticmethod
    def _get_client(configs: ElasticsearchConfig) -> AsyncElasticsearch:
        """Create an async Elasticsearch client with the specified configuration.

        Args:
            configs (ElasticsearchConfig): Configuration settings for Elasticsearch.

        Returns:
            AsyncElasticsearch: Configured async Elasticsearch client instance.
        """
        api_key: tuple[str, str] | None = None
        basic_auth: tuple[str, str] | None = None
        if configs.API_KEY and configs.API_SECRET:
            api_key = (configs.API_KEY, configs.API_SECRET.get_secret_value())
        elif configs.HTTP_USER_NAME and configs.HTTP_PASSWORD:
            basic_auth = (configs.HTTP_USER_NAME, configs.HTTP_PASSWORD.get_secret_value())

        # Build kwargs, only including SSL parameters if they have values
        kwargs: dict[str, Any] = {
            "hosts": configs.HOSTS,
            "api_key": api_key,
            "basic_auth": basic_auth,
            "request_timeout": configs.REQUEST_TIMEOUT,
            "retry_on_status": configs.RETRY_ON_STATUS,
            "retry_on_timeout": configs.RETRY_ON_TIMEOUT,
            "max_retries": configs.MAX_RETRIES,
            "http_compress": configs.HTTP_COMPRESS,
            "connections_per_node": configs.CONNECTIONS_PER_NODE,
            "verify_certs": configs.VERIFY_CERTS,
            "sniff_on_start": configs.SNIFF_ON_START,
            "sniff_before_requests": configs.SNIFF_BEFORE_REQUESTS,
            "sniff_on_node_failure": configs.SNIFF_ON_NODE_FAILURE,
            "max_dead_node_backoff": configs.MAX_DEAD_NODE_BACKOFF,
        }

        # Only add SSL parameters if they have values (to avoid passing None)
        if configs.CA_CERTS:
            kwargs["ca_certs"] = configs.CA_CERTS
        if configs.CLIENT_KEY:
            kwargs["client_key"] = configs.CLIENT_KEY
        if configs.CLIENT_CERT:
            kwargs["client_cert"] = configs.CLIENT_CERT
        if configs.SSL_ASSERT_FINGERPRINT:
            kwargs["ssl_assert_fingerprint"] = configs.SSL_ASSERT_FINGERPRINT

        return AsyncElasticsearch(**kwargs)

    @override
    async def ping(self) -> ElasticsearchResponseType:
        """Test the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: True if the connection is successful.
        """
        return await self.client.ping()

    @override
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
            doc_id (ElasticsearchIdType | None): Optional document ID.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.index(index=index, document=document, id=doc_id, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.
        """
        return await self.client.get(index=index, id=doc_id, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.
        """
        return await self.client.search(index=index, body=query, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.update(index=index, id=doc_id, doc=doc, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.delete(index=index, id=doc_id, **kwargs)

    @override
    async def bulk(
        self,
        actions: list[dict[str, Any]],
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Perform bulk operations in Elasticsearch.

        Args:
            actions (list[dict[str, Any]]): List of bulk actions to perform.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.bulk(operations=actions, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.indices.create(index=index, body=body, **kwargs)

    @override
    async def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Delete an index from Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.indices.delete(index=index, **kwargs)

    @override
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.
        """
        return await self.client.exists(index=index, id=doc_id, **kwargs)

    @override
    async def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: object,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.
        """
        return await self.client.indices.exists(index=index, **kwargs)
