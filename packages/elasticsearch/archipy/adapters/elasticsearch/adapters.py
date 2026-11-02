"""Elasticsearch adapter implementations for ArchiPy."""

from __future__ import annotations

import functools
import inspect
import logging
import warnings
from functools import cache
from typing import TYPE_CHECKING, Any, NoReturn, override

from elastic_transport import ConnectionError as TransportConnectionError, ConnectionTimeout, TransportError
from elasticsearch import ApiError, AsyncElasticsearch, Elasticsearch
from elasticsearch.helpers import async_bulk, async_scan, bulk as es_bulk, scan as es_scan

from archipy.adapters.elasticsearch.ports import (
    AsyncElasticsearchPort,
    ElasticsearchBulkActionType,
    ElasticsearchBulkResultType,
    ElasticsearchDocumentType,
    ElasticsearchIdType,
    ElasticsearchIndexType,
    ElasticsearchPort,
    ElasticsearchQueryType,
    ElasticsearchResponseType,
)
from archipy.configs.base_config import BaseConfig
from archipy.models.errors import (
    AlreadyExistsError,
    BadGatewayError,
    BaseError,
    ConflictError,
    ConnectionTimeoutError,
    GatewayTimeoutError,
    InternalError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    ServiceUnavailableError,
    UnauthenticatedError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator

    from archipy.configs.config_template import ElasticsearchConfig

logger = logging.getLogger(__name__)

# Body keys whose client keyword differs from the JSON field name.
_BODY_FIELD_ALIASES: dict[str, str] = {"from": "from_"}


_STATUS_ERRORS: dict[int, type[BaseError]] = {
    400: InvalidArgumentError,
    401: UnauthenticatedError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitExceededError,
    502: BadGatewayError,
    503: ServiceUnavailableError,
    504: GatewayTimeoutError,
}

# Elasticsearch error types that are more specific than their status code (409 covers both)
_ERROR_TYPE_ERRORS: dict[str, type[BaseError]] = {"resource_already_exists_exception": AlreadyExistsError}

_ERROR_MAPPING_DEPRECATION = (
    "Elasticsearch adapters currently raise raw elasticsearch-py exceptions. "
    "Set ELASTIC.MAP_ERRORS=True to raise ArchiPy errors instead; this will become the default in a future release."
)


def _to_archipy_error(error: Exception) -> BaseError | None:
    """Translate an elasticsearch-py exception into an ArchiPy error.

    Args:
        error (Exception): The exception raised by the client.

    Returns:
        BaseError | None: The ArchiPy error, or None when the exception is not an Elasticsearch failure.
    """
    if isinstance(error, ApiError):
        status = error.meta.status
        by_type = _ERROR_TYPE_ERRORS.get(str(getattr(error, "error", "")))
        if by_type is not None:
            return by_type()
        return _STATUS_ERRORS.get(status, InternalError)()
    if isinstance(error, ConnectionTimeout):
        return ConnectionTimeoutError()
    if isinstance(error, TransportConnectionError):
        return ServiceUnavailableError()
    if isinstance(error, TransportError):
        return InternalError()
    return None


def _raise_mapped(error: Exception) -> NoReturn:
    """Raise the ArchiPy error for an Elasticsearch failure, or re-raise the original.

    Args:
        error (Exception): The exception raised by the client.

    Raises:
        BaseError: The mapped ArchiPy error, chained from the original.
        Exception: The original exception when it is not an Elasticsearch failure.
    """
    mapped = _to_archipy_error(error)
    if mapped is None:
        raise error
    raise mapped from error


def _errors_mapped(adapter: object) -> bool:
    """Return whether the adapter was configured to map client errors."""
    return bool(getattr(adapter, "_map_errors", False))


def _map_sync_errors[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """Map client exceptions to ArchiPy errors when the adapter has MAP_ERRORS enabled."""

    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        adapter = args[0]
        try:
            return function(*args, **kwargs)
        except Exception as error:
            if not _errors_mapped(adapter):
                raise
            _raise_mapped(error)

    return wrapper


def _map_sync_gen_errors[**P, R](function: Callable[P, Iterable[R]]) -> Callable[P, Iterator[R]]:
    """Generator variant of ``_map_sync_errors``; errors surface while iterating."""

    @functools.wraps(function)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Iterator[R]:
        adapter = args[0]
        try:
            yield from function(*args, **kwargs)
        except Exception as error:
            if not _errors_mapped(adapter):
                raise
            _raise_mapped(error)

    return wrapper


def _map_async_errors[**P, R](function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    """Async variant of ``_map_sync_errors``."""

    @functools.wraps(function)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        adapter = args[0]
        try:
            return await function(*args, **kwargs)
        except Exception as error:
            if not _errors_mapped(adapter):
                raise
            _raise_mapped(error)

    return wrapper


def _map_async_gen_errors[**P, R](function: Callable[P, AsyncIterator[R]]) -> Callable[P, AsyncIterator[R]]:
    """Async-generator variant of ``_map_sync_errors``."""

    @functools.wraps(function)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> AsyncIterator[R]:
        adapter = args[0]
        try:
            async for item in function(*args, **kwargs):
                yield item
        except Exception as error:
            if not _errors_mapped(adapter):
                raise
            _raise_mapped(error)

    return wrapper


def _warn_error_mapping_disabled(configs: ElasticsearchConfig) -> bool:
    """Return the MAP_ERRORS flag and warn when it is off.

    Args:
        configs (ElasticsearchConfig): Configuration settings for Elasticsearch.

    Returns:
        bool: Whether ArchiPy error mapping is enabled.
    """
    if not configs.MAP_ERRORS:
        warnings.warn(_ERROR_MAPPING_DEPRECATION, DeprecationWarning, stacklevel=3)
    return configs.MAP_ERRORS


def _apply_optional_client_kwargs(kwargs: dict[str, Any], configs: ElasticsearchConfig) -> None:
    """Add the client options that are only passed when set, so unset keeps the client defaults.

    Args:
        kwargs (dict[str, Any]): Client keyword arguments, updated in place.
        configs (ElasticsearchConfig): Configuration settings for Elasticsearch.
    """
    if configs.BEARER_AUTH:
        kwargs["bearer_auth"] = configs.BEARER_AUTH.get_secret_value()
    if configs.SSL_VERSION is not None:
        kwargs["ssl_version"] = configs.SSL_VERSION
    if configs.SSL_CONTEXT is not None:
        kwargs["ssl_context"] = configs.SSL_CONTEXT
    if configs.OPAQUE_ID:
        kwargs["opaque_id"] = configs.OPAQUE_ID
    if configs.HEADERS:
        kwargs["headers"] = configs.HEADERS
    if configs.CLOUD_ID:
        # The client rejects hosts, and any sniffing option (even False), together with a cloud ID
        kwargs["cloud_id"] = configs.CLOUD_ID
        for option in (
            "hosts",
            "sniff_on_start",
            "sniff_before_requests",
            "sniff_on_node_failure",
            "min_delay_between_sniffing",
        ):
            kwargs.pop(option, None)


@cache
def _keyword_parameters(function: Callable[..., Any]) -> frozenset[str]:
    """Return the keyword parameters of an elasticsearch-py API function, excluding ``body``.

    Args:
        function (Callable[..., Any]): The unbound client API function.

    Returns:
        frozenset[str]: The accepted keyword parameter names.
    """
    return frozenset(inspect.signature(function).parameters) - {"self", "body"}


def _expand_body(body: dict[str, Any] | None, kwargs: dict[str, Any], method: Callable[..., Any]) -> dict[str, Any]:
    """Expand a request body into client keyword arguments.

    elasticsearch-py deprecates passing ``body=`` together with body field keywords (such as ``size``).
    Body fields the client accepts as keywords are expanded; unknown fields stay in ``body``.

    Args:
        body (dict[str, Any] | None): The request body.
        kwargs (dict[str, Any]): Keyword arguments supplied by the caller.
        method (Callable[..., Any]): The bound client API method that receives the arguments.

    Returns:
        dict[str, Any]: Keyword arguments for the client method.

    Raises:
        ValueError: If a field is given both in the body and as a keyword argument.
    """
    parameters = _keyword_parameters(getattr(method, "__func__", method))
    merged = dict(kwargs)
    remaining: dict[str, Any] = {}
    for key, value in (body or {}).items():
        name = _BODY_FIELD_ALIASES.get(key, key)
        if name not in parameters:
            remaining[key] = value
            continue
        if name in merged:
            msg = f"Received multiple values for '{key}', specify it either in the body or as a keyword."
            raise ValueError(msg)
        merged[name] = value
    if remaining:
        merged["body"] = remaining
    return merged


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
        configs: ElasticsearchConfig = elasticsearch_config or BaseConfig.global_config().ELASTIC
        self._map_errors = _warn_error_mapping_disabled(configs)
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
            "dead_node_backoff_factor": configs.DEAD_NODE_BACKOFF_FACTOR,
            "node_selector_class": configs.NODE_SELECTOR_CLASS,
            "retry_backoff_base": configs.RETRY_BACKOFF_BASE,
            "retry_backoff_cap": configs.RETRY_BACKOFF_CAP,
        }
        # Leave the backoff options out when unset so the client keeps its own defaults
        kwargs = {
            key: value for key, value in kwargs.items() if value is not None or not key.startswith("retry_backoff")
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
        # The client forces sniff_before_requests when a sniffing delay is passed, so only pass it when enabled
        if configs.SNIFF_BEFORE_REQUESTS:
            kwargs["min_delay_between_sniffing"] = configs.MIN_DELAY_BETWEEN_SNIFFING

        _apply_optional_client_kwargs(kwargs, configs)
        client = Elasticsearch(**kwargs)
        # ignore_status is a per-client option set through options(), not a constructor argument
        if configs.IGNORE_STATUS:
            client = client.options(ignore_status=configs.IGNORE_STATUS)
        return client

    @override
    @_map_sync_errors
    def ping(self) -> ElasticsearchResponseType:
        """Test the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: True if the connection is successful.
        """
        return self.client.ping()

    @override
    @_map_sync_errors
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
            doc_id (ElasticsearchIdType | None): Optional document ID.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        # An auto-id POST replayed after a timeout would create a duplicate document
        client = self.client.options(max_retries=0) if doc_id is None else self.client
        return client.index(index=index, document=document, id=doc_id, **kwargs)

    @override
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.
        """
        return self.client.get(index=index, id=doc_id, **kwargs)

    @override
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.
        """
        return self.client.search(index=index, **_expand_body(query, kwargs, self.client.search))

    @override
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        # A scripted update replayed after a timeout could apply the script twice
        client = self.client.options(max_retries=0) if "script" in kwargs else self.client
        return client.update(index=index, id=doc_id, doc=doc, **kwargs)

    @override
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return self.client.delete(index=index, id=doc_id, **kwargs)

    @override
    @_map_sync_errors
    def bulk(
        self,
        actions: Iterable[ElasticsearchBulkActionType],
        stats_only: bool = False,
        **kwargs: Any,
    ) -> ElasticsearchBulkResultType:
        """Perform bulk operations using elasticsearch.helpers.bulk.

        Args:
            actions: Iterable of helper-format documents (generators supported).
            stats_only: When True, return only success and error counts.
            kwargs: Additional keyword arguments passed to elasticsearch.helpers.bulk.

        Returns:
            A tuple of (success_count, error_count_or_error_list).

        Raises:
            BulkIndexError: If any bulk operation fails and raise_on_error is True (default).
        """
        return es_bulk(self.client, actions, stats_only=stats_only, **kwargs)

    @override
    @_map_sync_gen_errors
    def scan(
        self,
        query: ElasticsearchQueryType | None = None,
        **kwargs: Any,
    ) -> Iterable[ElasticsearchDocumentType]:
        """Iterate over all matching documents using elasticsearch.helpers.scan.

        Args:
            query: Optional search query body.
            kwargs: Additional keyword arguments passed to elasticsearch.helpers.scan.

        Returns:
            An iterable yielding hit documents.
        """
        return es_scan(self.client, query=query, **kwargs)

    @override
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        indices = self.client.indices
        return indices.create(index=index, **_expand_body(body, kwargs, indices.create))

    @override
    @_map_sync_errors
    def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
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
    @_map_sync_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.
        """
        return self.client.exists(index=index, id=doc_id, **kwargs)

    @override
    @_map_sync_errors
    def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.
        """
        return self.client.indices.exists(index=index, **kwargs)

    @override
    def close(self) -> None:
        """Close the client and release its connection pool."""
        self.client.close()


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
        configs: ElasticsearchConfig = elasticsearch_config or BaseConfig.global_config().ELASTIC
        self._map_errors = _warn_error_mapping_disabled(configs)
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
            "dead_node_backoff_factor": configs.DEAD_NODE_BACKOFF_FACTOR,
            "node_selector_class": configs.NODE_SELECTOR_CLASS,
            "retry_backoff_base": configs.RETRY_BACKOFF_BASE,
            "retry_backoff_cap": configs.RETRY_BACKOFF_CAP,
        }
        # Leave the backoff options out when unset so the client keeps its own defaults
        kwargs = {
            key: value for key, value in kwargs.items() if value is not None or not key.startswith("retry_backoff")
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
        # The client forces sniff_before_requests when a sniffing delay is passed, so only pass it when enabled
        if configs.SNIFF_BEFORE_REQUESTS:
            kwargs["min_delay_between_sniffing"] = configs.MIN_DELAY_BETWEEN_SNIFFING

        _apply_optional_client_kwargs(kwargs, configs)
        client = AsyncElasticsearch(**kwargs)
        # ignore_status is a per-client option set through options(), not a constructor argument
        if configs.IGNORE_STATUS:
            client = client.options(ignore_status=configs.IGNORE_STATUS)
        return client

    @override
    @_map_async_errors
    async def ping(self) -> ElasticsearchResponseType:
        """Test the connection to the Elasticsearch server.

        Returns:
            ElasticsearchResponseType: True if the connection is successful.
        """
        return await self.client.ping()

    @override
    @_map_async_errors
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
            doc_id (ElasticsearchIdType | None): Optional document ID.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        # An auto-id POST replayed after a timeout would create a duplicate document
        client = self.client.options(max_retries=0) if doc_id is None else self.client
        return await client.index(index=index, document=document, id=doc_id, **kwargs)

    @override
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The document if found.
        """
        return await self.client.get(index=index, id=doc_id, **kwargs)

    @override
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The search results.
        """
        return await self.client.search(index=index, **_expand_body(query, kwargs, self.client.search))

    @override
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        # A scripted update replayed after a timeout could apply the script twice
        client = self.client.options(max_retries=0) if "script" in kwargs else self.client
        return await client.update(index=index, id=doc_id, doc=doc, **kwargs)

    @override
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        return await self.client.delete(index=index, id=doc_id, **kwargs)

    @override
    @_map_async_errors
    async def bulk(
        self,
        actions: Iterable[ElasticsearchBulkActionType],
        stats_only: bool = False,
        **kwargs: Any,
    ) -> ElasticsearchBulkResultType:
        """Perform bulk operations using elasticsearch.helpers.async_bulk.

        Args:
            actions: Iterable of helper-format documents (generators supported).
            stats_only: When True, return only success and error counts.
            kwargs: Additional keyword arguments passed to elasticsearch.helpers.async_bulk.

        Returns:
            A tuple of (success_count, error_count_or_error_list).

        Raises:
            BulkIndexError: If any bulk operation fails and raise_on_error is True (default).
        """
        return await async_bulk(self.client, actions, stats_only=stats_only, **kwargs)

    @override
    @_map_async_gen_errors
    async def scan(
        self,
        query: ElasticsearchQueryType | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ElasticsearchDocumentType]:
        """Iterate over all matching documents using elasticsearch.helpers.async_scan.

        Args:
            query: Optional search query body.
            kwargs: Additional keyword arguments passed to elasticsearch.helpers.async_scan.

        Yields:
            Hit documents from the scroll iteration.
        """
        async for document in async_scan(self.client, query=query, **kwargs):
            yield document

    @override
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: The response from Elasticsearch.
        """
        indices = self.client.indices
        return await indices.create(index=index, **_expand_body(body, kwargs, indices.create))

    @override
    @_map_async_errors
    async def delete_index(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
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
    @_map_async_errors
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
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the document exists, False otherwise.
        """
        return await self.client.exists(index=index, id=doc_id, **kwargs)

    @override
    @_map_async_errors
    async def index_exists(
        self,
        index: ElasticsearchIndexType,
        **kwargs: Any,
    ) -> ElasticsearchResponseType:
        """Check if an index exists in Elasticsearch.

        Args:
            index (ElasticsearchIndexType): The index name.
            kwargs: Additional keyword arguments passed to the Elasticsearch client.

        Returns:
            ElasticsearchResponseType: True if the index exists, False otherwise.
        """
        return await self.client.indices.exists(index=index, **kwargs)

    @override
    async def aclose(self) -> None:
        """Close the client and release its connection pool."""
        await self.client.close()
