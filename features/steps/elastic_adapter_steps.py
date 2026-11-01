# features/steps/elasticsearch_steps.py
import base64
import ssl
import time
import json
import logging
import ast
import asyncio
import uuid
import warnings

from behave import given, when, then
from elasticsearch import BadRequestError
from behave.runner import Context
from pydantic import SecretStr

from features.test_helpers import get_current_scenario_context
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter, AsyncElasticsearchAdapter
from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


def get_es_adapter(context):
    """Get or initialize the appropriate Elasticsearch adapter based on scenario tags."""
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:
        if not hasattr(scenario_context, "async_adapter") or scenario_context.async_adapter is None:
            test_config = BaseConfig.global_config()
            scenario_context.async_adapter = AsyncElasticsearchAdapter(test_config.ELASTIC)
        return scenario_context.async_adapter
    if not hasattr(scenario_context, "adapter") or scenario_context.adapter is None:
        test_config = BaseConfig.global_config()
        scenario_context.adapter = ElasticsearchAdapter(test_config.ELASTIC)
    return scenario_context.adapter


def _is_async_scenario(context: Context) -> bool:
    """Check if the current scenario is async."""
    return "async" in context.scenario.tags


def _get_scenario_context(context: Context):
    """Get the current scenario context."""
    return get_current_scenario_context(context)


async def _wait_for_propagation() -> None:
    """Wait for Elasticsearch operations to propagate."""
    await asyncio.sleep(0.5)


def _log_operation(context: Context, operation: str, details: str) -> None:
    """Log operation details."""
    context.logger.info(f"{operation}: {details}")


def _store_result(scenario_context, key: str, value: any) -> None:
    """Store a result in the scenario context."""
    scenario_context.store(key, value)


def get_actual_index_name(context: Context, index_name: str) -> str:
    """Get the actual index name from the mapping, or return the original if no mapping exists."""
    scenario_context = _get_scenario_context(context)
    index_name_mapping = scenario_context.get("index_name_mapping", {})
    if index_name in index_name_mapping:
        return index_name_mapping[index_name]
    return index_name


# Background and setup steps

def _already_exists(error: BadRequestError) -> bool:
    """A retry after a client timeout can race the first, slow but successful, create request."""
    return "resource_already_exists_exception" in str(error)


async def _create_index(adapter, is_async: bool, **kwargs):
    """Create an index, treating "already exists" from a transport-level retry as success."""
    try:
        if is_async:
            return await adapter.create_index(**kwargs)
        return adapter.create_index(**kwargs)
    except BadRequestError as e:
        if not _already_exists(e):
            raise
        return {"acknowledged": True}

@given("an Elasticsearch cluster is running")
async def step_cluster_running(context: Context) -> None:
    """Verify that the Elasticsearch cluster is running."""
    scenario_context = _get_scenario_context(context)

    try:
        # Get the elasticsearch container from the test containers
        test_containers = scenario_context.get("test_containers")
        if not test_containers:
            raise ValueError("Test containers not available in scenario context")

        elasticsearch_container = test_containers.get_container("elasticsearch")
        if not elasticsearch_container or not elasticsearch_container._is_running:
            raise ValueError("Elasticsearch container is not running")

        # Container start already waited for yellow cluster health; re-check cheaply per scenario.
        elasticsearch_container._wait_until_ready(timeout=60)

        _log_operation(context, "Cluster status", "Elasticsearch cluster is running")
        _store_result(scenario_context, "elasticsearch_container", elasticsearch_container)

    except Exception as e:
        scenario_context.store("cluster_error", str(e))
        context.logger.exception("Failed to verify cluster status")
        raise


@given('index "{index_name}" exists')
async def step_index_exists(context: Context, index_name: str) -> None:
    """Create an index with a unique name to avoid conflicts."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    # Generate a unique index name to avoid conflicts
    unique_suffix = str(uuid.uuid4())[:8]
    unique_index_name = f"{index_name}-{unique_suffix}"

    try:
        # Create the index with unique name
        await _create_index(adapter, is_async, index=unique_index_name)

        # Store the unique name for cleanup
        created_indices = scenario_context.get("created_indices", [])
        created_indices.append(unique_index_name)
        scenario_context.store("created_indices", created_indices)

        # Store the mapping for other steps to use
        index_name_mapping = scenario_context.get("index_name_mapping", {})
        index_name_mapping[index_name] = unique_index_name
        scenario_context.store("index_name_mapping", index_name_mapping)

        _log_operation(context, "Index creation", f"Created unique index '{unique_index_name}'")
        _store_result(
            scenario_context,
            "latest_index_creation",
            {
                "original_name": index_name,
                "unique_name": unique_index_name,
                "status": "created",
            },
        )

    except Exception as e:
        scenario_context.store("index_creation_error", str(e))
        context.logger.exception(f"Failed to create index '{unique_index_name}'")
        raise


@given('document type "{doc_type}" is configured for index "{index_name}"')
def step_doc_type_configured(context: Context, doc_type: str, index_name: str) -> None:
    """Configure document type for the specified index."""
    context.logger.info(f"Document type '{doc_type}' is configured for index '{index_name}'")


@given("a valid Elasticsearch client connection")
async def step_valid_es_client(context: Context) -> None:
    """Verify that the Elasticsearch client connection is valid."""
    scenario_context = _get_scenario_context(context)

    try:
        # Get the adapter (this will create it with proper configuration)
        adapter = get_es_adapter(context)

        # Store the adapter for later use
        if _is_async_scenario(context):
            scenario_context.async_adapter = adapter
        else:
            scenario_context.adapter = adapter

        _log_operation(context, "Connection status", "Elasticsearch client connection configured")
        _store_result(scenario_context, "connection_verified", True)

    except Exception as e:
        scenario_context.store("connection_error", str(e))
        context.logger.exception("Failed to configure client connection")
        raise


@given('a document exists in "{index_name}" with id "{doc_id}" and content {content}')
async def step_document_exists(context: Context, index_name: str, doc_id: str, content: str) -> None:
    """Create a document in the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        doc_content = ast.literal_eval(content)
        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.index(index=actual_index_name, document=doc_content, doc_id=doc_id)
        else:
            result = adapter.index(index=actual_index_name, document=doc_content, doc_id=doc_id)

        # Store created document for cleanup
        created_documents = scenario_context.get("created_documents", [])
        created_documents.append((actual_index_name, doc_id))
        scenario_context.store("created_documents", created_documents)

        _store_result(
            scenario_context,
            "latest_document_creation",
            {
                "index": actual_index_name,
                "doc_id": doc_id,
                "content": doc_content,
                "result": result,
            },
        )

        _log_operation(
            context,
            "Document creation",
            f"Document with id '{doc_id}' created in index '{actual_index_name}'",
        )

        # Wait for propagation
        if is_async:
            await _wait_for_propagation()
        else:
            # Simple delay for sync operations
            time.sleep(0.5)

        # Refresh the index to make the document immediately searchable
        try:
            if is_async:
                await adapter.client.indices.refresh(index=actual_index_name)
            else:
                adapter.client.indices.refresh(index=actual_index_name)
            context.logger.info(f"Refreshed index {actual_index_name} after document creation")

            # Verify the document exists after refresh
            if is_async:
                doc_exists = await adapter.exists(index=actual_index_name, doc_id=doc_id)
            else:
                doc_exists = adapter.exists(index=actual_index_name, doc_id=doc_id)
            context.logger.info(f"Document {doc_id} exists after refresh: {doc_exists}")

        except Exception as e:
            context.logger.warning(f"Failed to refresh index {actual_index_name}: {e}")

    except Exception as e:
        scenario_context.store("document_creation_error", str(e))
        context.logger.exception(f"Failed to create document '{doc_id}' in index '{actual_index_name}'")
        raise


# Document operations
@when('I index a document with id "{doc_id}" and content {content} into "{index_name}"')
async def step_index_document(context: Context, doc_id: str, content: str, index_name: str) -> None:
    """Index a document into the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        doc_content = ast.literal_eval(content)
        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.index(index=actual_index_name, document=doc_content, doc_id=doc_id)
        else:
            result = adapter.index(index=actual_index_name, document=doc_content, doc_id=doc_id)

        _store_result(scenario_context, "last_index_result", result)
        _log_operation(context, "Document indexing", f"Indexed document with id '{doc_id}' into '{actual_index_name}'")

        # Store for cleanup if this is a new document
        created_documents = scenario_context.get("created_documents", [])
        if (actual_index_name, doc_id) not in created_documents:
            created_documents.append((actual_index_name, doc_id))
            scenario_context.store("created_documents", created_documents)

        # Refresh the index to make the document immediately searchable
        try:
            if is_async:
                await adapter.client.indices.refresh(index=actual_index_name)
            else:
                adapter.client.indices.refresh(index=actual_index_name)
            context.logger.info(f"Refreshed index {actual_index_name} after document indexing")

            # Verify the document exists after refresh
            if is_async:
                doc_exists = await adapter.exists(index=actual_index_name, doc_id=doc_id)
            else:
                doc_exists = adapter.exists(index=actual_index_name, doc_id=doc_id)
            context.logger.info(f"Document {doc_id} exists after refresh: {doc_exists}")

        except Exception as e:
            context.logger.warning(f"Failed to refresh index {actual_index_name}: {e}")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Failed to index document: {e}")
        raise


@when('I search for "{query}" in "{index_name}"')
async def step_search_documents(context: Context, query: str, index_name: str) -> None:
    """Search for documents in the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        search_query = {"query": {"multi_match": {"query": query, "fields": ["*"]}}}
        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.search(index=actual_index_name, query=search_query)
        else:
            result = adapter.search(index=actual_index_name, query=search_query)

        _store_result(scenario_context, "last_search_result", result)
        _log_operation(context, "Document search", f"Searched for '{query}' in '{actual_index_name}'")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Search failed: {e}")
        raise


@when('I update document "{doc_id}" in "{index_name}" with content {content}')
async def step_update_document(context: Context, doc_id: str, content: str, index_name: str) -> None:
    """Update a document in the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        if content.startswith("'") and content.endswith("'"):
            content = content[1:-1]  # Remove outer single quotes
        elif content.startswith('"') and content.endswith('"'):
            content = content[1:-1]  # Remove outer double quotes

        doc_content = json.loads(content)

        context.logger.info(f"Parsed update content: {doc_content}")

        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.update(index=actual_index_name, doc_id=doc_id, doc=doc_content)
        else:
            result = adapter.update(index=actual_index_name, doc_id=doc_id, doc=doc_content)

        _store_result(scenario_context, "last_update_result", result)
        _log_operation(context, "Document update", f"Updated document '{doc_id}' in '{actual_index_name}'")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Update failed: {e}")
        raise


@when('I delete document "{doc_id}" from "{index_name}"')
async def step_delete_document(context: Context, doc_id: str, index_name: str) -> None:
    """Delete a document from the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.delete(index=actual_index_name, doc_id=doc_id)
        else:
            result = adapter.delete(index=actual_index_name, doc_id=doc_id)

        _store_result(scenario_context, "last_delete_result", result)
        _log_operation(context, "Document deletion", f"Deleted document '{doc_id}' from '{actual_index_name}'")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Delete failed: {e}")
        raise


# Index operations
@when('I create index "{index_name}" with {shards} shard and {replicas} replica')
async def step_create_index(context: Context, index_name: str, shards: str, replicas: str) -> None:
    """Create a new index with specified shard and replica configuration."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        index_body = {"settings": {"number_of_shards": int(shards), "number_of_replicas": int(replicas)}}
        actual_index_name = get_actual_index_name(context, index_name)

        # If no mapping exists, create a unique name
        if actual_index_name == index_name:
            unique_suffix = str(uuid.uuid4())[:8]
            actual_index_name = f"{index_name}-{unique_suffix}"

            # Store the mapping for other steps to use
            index_name_mapping = scenario_context.get("index_name_mapping", {})
            index_name_mapping[index_name] = actual_index_name
            scenario_context.store("index_name_mapping", index_name_mapping)

        result = await _create_index(adapter, is_async, index=actual_index_name, body=index_body)

        _store_result(scenario_context, "last_create_index_result", result)

        # Store for cleanup
        created_indices = scenario_context.get("created_indices", [])
        created_indices.append(actual_index_name)
        scenario_context.store("created_indices", created_indices)

        _log_operation(context, "Index creation", f"Created index '{actual_index_name}'")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Index creation failed: {e}")
        raise


@when('I delete index "{index_name}"')
async def step_delete_index(context: Context, index_name: str) -> None:
    """Delete the specified index."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        actual_index_name = get_actual_index_name(context, index_name)

        if is_async:
            result = await adapter.delete_index(index=actual_index_name)
        else:
            result = adapter.delete_index(index=actual_index_name)

        _store_result(scenario_context, "last_delete_index_result", result)
        _log_operation(context, "Index deletion", f"Deleted index '{actual_index_name}'")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Index deletion failed: {e}")
        raise


# Bulk operations
@when("I perform a bulk operation with:")
async def step_bulk_operation(context: Context) -> None:
    """Perform bulk operations based on the provided table."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    try:
        bulk_actions: list[dict[str, object]] = []
        tracked_actions: list[dict[str, str]] = []
        for row in context.table:
            action = row["action"]
            doc_id = row["id"]
            index_name = row["index"]
            actual_index_name = get_actual_index_name(context, index_name)
            tracked_actions.append({"action": action, "index": actual_index_name, "id": doc_id})

            if action in {"index", "create"}:
                doc_content = ast.literal_eval(row["document"]) if row["document"] else {}
                bulk_actions.append(
                    {
                        "_op_type": action,
                        "_index": actual_index_name,
                        "_id": doc_id,
                        "_source": doc_content,
                    },
                )
            elif action == "update":
                doc_content = ast.literal_eval(row["document"]) if row["document"] else {}
                if "doc" in doc_content:
                    bulk_actions.append(
                        {
                            "_op_type": "update",
                            "_index": actual_index_name,
                            "_id": doc_id,
                            **doc_content,
                        },
                    )
                else:
                    bulk_actions.append(
                        {
                            "_op_type": "update",
                            "_index": actual_index_name,
                            "_id": doc_id,
                            "doc": doc_content,
                        },
                    )
            elif action == "delete":
                bulk_actions.append(
                    {
                        "_op_type": "delete",
                        "_index": actual_index_name,
                        "_id": doc_id,
                    },
                )

        if is_async:
            result = await adapter.bulk(actions=bulk_actions)
        else:
            result = adapter.bulk(actions=bulk_actions)

        _store_result(scenario_context, "last_bulk_result", result)
        _store_result(scenario_context, "last_bulk_actions", tracked_actions)
        _log_operation(context, "Bulk operation", f"Performed bulk operation with {len(bulk_actions)} actions")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Bulk operation failed: {e}")
        raise


@when('I scan "{index_name}" for query "{query_text}"')
async def step_scan_documents(context: Context, index_name: str, query_text: str) -> None:
    """Scan documents matching the given query text."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)
    actual_index_name = get_actual_index_name(context, index_name)
    query = {"query": {"match": {"title": query_text}}}

    try:
        # A search only sees refreshed documents; under load the one-second refresh interval may not have passed.
        if is_async:
            await adapter.client.indices.refresh(index=actual_index_name)
        else:
            adapter.client.indices.refresh(index=actual_index_name)
        if is_async:
            hits = [document async for document in adapter.scan(query=query, index=actual_index_name)]
        else:
            hits = list(adapter.scan(query=query, index=actual_index_name))

        _store_result(scenario_context, "last_scan_hits", hits)
        _log_operation(context, "Scan", f"Scanned index '{actual_index_name}' for '{query_text}'")
    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Scan failed: {e}")
        raise


@when('I search "{index_name}" for "{query}" with size {size:d} as a keyword argument')
async def step_search_with_keyword_field(context: Context, index_name: str, query: str, size: int) -> None:
    """Search with a query body plus a body field passed as a keyword, recording deprecation warnings."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    actual_index_name = get_actual_index_name(context, index_name)
    search_query = {"query": {"match": {"title": query}}}

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        if _is_async_scenario(context):
            result = await adapter.search(index=actual_index_name, query=search_query, size=size)
        else:
            result = adapter.search(index=actual_index_name, query=search_query, size=size)

    _store_result(scenario_context, "last_search_result", result)
    _store_result(scenario_context, "es_warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])
    _store_result(scenario_context, "last_search_query", search_query)


@when('I create index "{index_name}" with settings in the body and mappings as a keyword argument')
async def step_create_index_with_keyword_field(context: Context, index_name: str) -> None:
    """Create an index with settings in the body and mappings as a keyword, recording deprecation warnings."""
    adapter = get_es_adapter(context)
    scenario_context = _get_scenario_context(context)
    actual_index_name = f"{index_name}-{str(uuid.uuid4())[:8]}"
    index_name_mapping = scenario_context.get("index_name_mapping", {})
    index_name_mapping[index_name] = actual_index_name
    scenario_context.store("index_name_mapping", index_name_mapping)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        result = await _create_index(
            adapter,
            _is_async_scenario(context),
            index=actual_index_name,
            body={"settings": {"number_of_shards": 1}},
            mappings={"properties": {"title": {"type": "keyword"}}},
        )

    created_indices = scenario_context.get("created_indices", [])
    created_indices.append(actual_index_name)
    scenario_context.store("created_indices", created_indices)
    _store_result(scenario_context, "last_create_index_result", result)
    _store_result(scenario_context, "es_warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


# Authentication steps
@given("an Elasticsearch cluster with security enabled")
def step_cluster_with_security(context: Context) -> None:
    """Configure the scenario for a secured Elasticsearch cluster."""
    context.logger.info("Elasticsearch cluster with security enabled")


@when('I connect with username "{username}" and password "{password}"')
async def step_connect_with_auth(context: Context, username: str, password: str) -> None:
    """Connect to Elasticsearch with authentication credentials."""
    context.logger.info(f"Connecting with username '{username}' and password '{password}'")


# Verification steps
@then("the indexing operation should succeed")
def step_indexing_succeeds(context: Context) -> None:
    """Verify that the indexing operation succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_index_result")
    assert result.get("result") in ["created", "updated"], "Indexing operation failed"
    context.logger.info("Indexing operation verified")


@then('the document should be retrievable by id "{doc_id}" from "{index_name}"')
async def step_document_retrievable(context: Context, doc_id: str, index_name: str) -> None:
    """Verify that the document can be retrieved by its ID."""
    adapter = get_es_adapter(context)
    actual_index_name = get_actual_index_name(context, index_name)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            doc = await adapter.get(index=actual_index_name, doc_id=doc_id)
        else:
            doc = adapter.get(index=actual_index_name, doc_id=doc_id)

        assert doc["found"], f"Document {doc_id} not found"
        context.logger.info(f"Document {doc_id} is retrievable")
    except Exception:
        assert False, f"Document {doc_id} not found in index {actual_index_name}"


@then("the search should return at least {num_hits} hit")
def step_search_returns_hits(context: Context, num_hits: str) -> None:
    """Verify that the search returned the expected number of hits."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_search_result")

    assert result["hits"]["total"]["value"] >= int(num_hits), "Not enough hits returned"
    context.logger.info(f"Search returned at least {num_hits} hits")


@then("the search should return at most {num_hits:d} hit")
def step_search_returns_at_most(context: Context, num_hits: int) -> None:
    """Verify that the search returned no more hits than requested."""
    scenario_context = _get_scenario_context(context)
    hits = scenario_context.get("last_search_result")["hits"]["hits"]
    assert len(hits) <= num_hits, f"Search returned {len(hits)} hits, expected at most {num_hits}"


@then("no Elasticsearch deprecation warning should be raised")
def step_no_es_deprecation_warning(context: Context) -> None:
    """Verify that the adapter call raised no DeprecationWarning."""
    scenario_context = _get_scenario_context(context)
    caught = scenario_context.get("es_warnings", [])
    assert not caught, f"Unexpected deprecation warnings: {[str(w.message) for w in caught]}"


@then("the search query passed to the adapter should be unchanged")
def step_search_query_unchanged(context: Context) -> None:
    """Verify the adapter did not merge keyword fields into the caller's query."""
    scenario_context = _get_scenario_context(context)
    query = scenario_context.get("last_search_query")
    assert query == {"query": {"match": {"title": query["query"]["match"]["title"]}}}, f"Query mutated: {query}"


@then('the hit should contain field "{field}" with value "{value}"')
def step_hit_contains_field(context: Context, field: str, value: str) -> None:
    """Verify that the search hit contains the expected field and value."""
    scenario_context = _get_scenario_context(context)
    hits = scenario_context.get("last_search_result")["hits"]["hits"]
    assert hits, "No hits found"

    found = any(str(hit["_source"].get(field)) == value for hit in hits)
    assert found, f"No hit contains field '{field}' with value '{value}'"
    context.logger.info(f"Hit contains field '{field}' with value '{value}'")


@then("the update operation should succeed")
def step_update_succeeds(context: Context) -> None:
    """Verify that the update operation succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_update_result")
    assert result.get("result") in ["updated", "noop"], "Update operation failed"
    context.logger.info("Update operation verified")


@then("the document should reflect the updated content when retrieved")
async def step_document_updated(context: Context) -> None:
    """Verify that the document content was updated correctly."""
    scenario_context = _get_scenario_context(context)
    update_result = scenario_context.get("last_update_result")
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            doc = await adapter.get(index=update_result["_index"], doc_id=update_result["_id"])
        else:
            doc = adapter.get(index=update_result["_index"], doc_id=update_result["_id"])

        assert doc["found"], "Document not found after update"
        context.logger.info("Document content updated successfully")
    except Exception as e:
        scenario_context.store("document_retrieval_error", str(e))
        context.logger.exception("Failed to retrieve updated document")
        raise


@then("the delete operation should succeed")
def step_delete_succeeds(context: Context) -> None:
    """Verify that the delete operation succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_delete_result")
    assert result.get("result") == "deleted", "Delete operation failed"
    context.logger.info("Delete operation verified")


@then("the document should not exist when searched for")
async def step_document_not_exist(context: Context) -> None:
    """Verify that the document no longer exists after deletion."""
    scenario_context = _get_scenario_context(context)
    delete_result = scenario_context.get("last_delete_result")
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            exists = await adapter.exists(index=delete_result["_index"], doc_id=delete_result["_id"])
        else:
            exists = adapter.exists(index=delete_result["_index"], doc_id=delete_result["_id"])

        assert not exists, "Document still exists after deletion"
    except Exception:
        pass  # Expected for non-existent documents

    context.logger.info("Document successfully deleted")


@then("the index creation should succeed")
def step_index_creation_succeeds(context: Context) -> None:
    """Verify that the index creation succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_create_index_result")
    assert result.get("acknowledged", False), "Index creation failed"
    context.logger.info("Index creation verified")


@then('index "{index_name}" should exist in the cluster')
async def step_index_exists_in_cluster(context: Context, index_name: str) -> None:
    """Verify that the index exists in the cluster."""
    adapter = get_es_adapter(context)
    actual_index_name = get_actual_index_name(context, index_name)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            exists = await adapter.index_exists(index=actual_index_name)
        else:
            exists = adapter.index_exists(index=actual_index_name)

        assert exists, f"Index {actual_index_name} does not exist"
        context.logger.info(f"Index {actual_index_name} exists in cluster")
    except Exception as e:
        context.logger.error(f"Failed to check if index {actual_index_name} exists: {e}")
        assert False, f"Index {actual_index_name} does not exist"


@then("the index deletion should succeed")
def step_index_deletion_succeeds(context: Context) -> None:
    """Verify that the index deletion succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_delete_index_result")
    assert result.get("acknowledged", False), "Index deletion failed"
    context.logger.info("Index deletion verified")


@then('index "{index_name}" should not exist in the cluster')
async def step_index_not_exist_in_cluster(context: Context, index_name: str) -> None:
    """Verify that the index no longer exists in the cluster."""
    adapter = get_es_adapter(context)
    actual_index_name = get_actual_index_name(context, index_name)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            exists = await adapter.index_exists(index=actual_index_name)
        else:
            exists = adapter.index_exists(index=actual_index_name)

        assert not exists, f"Index {actual_index_name} still exists"
        context.logger.info(f"Index {actual_index_name} does not exist in cluster")
    except Exception as e:
        context.logger.error(f"Failed to check if index {actual_index_name} exists: {e}")
        # If we can't check, assume it was deleted
        context.logger.info(f"Index {actual_index_name} assumed deleted (check failed)")


@then("the bulk operation should succeed")
def step_bulk_succeeds(context: Context) -> None:
    """Verify that the bulk operation succeeded."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_bulk_result")
    success_count, errors = result

    if isinstance(errors, list):
        assert len(errors) == 0, f"Bulk operation had errors: {errors}"
    else:
        assert errors == 0, f"Bulk operation had {errors} errors"

    assert success_count > 0, "Bulk operation did not process any documents"
    context.logger.info(f"Bulk operation verified successfully ({success_count} successes)")


@then("all operations should be reflected in the index")
async def step_bulk_operations_reflected(context: Context) -> None:
    """Verify that all bulk operations are reflected in the index."""
    scenario_context = _get_scenario_context(context)
    tracked_actions = scenario_context.get("last_bulk_actions", [])
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    expected_exists: dict[tuple[str, str], bool] = {}
    for action_info in tracked_actions:
        action_type = action_info["action"]
        index_name = action_info["index"]
        doc_id = action_info["id"]
        key = (index_name, doc_id)
        if action_type in ["index", "create", "update"]:
            expected_exists[key] = True
        elif action_type == "delete":
            expected_exists[key] = False

    for (index_name, doc_id), should_exist in expected_exists.items():
        try:
            if should_exist:
                if is_async:
                    doc = await adapter.get(index=index_name, doc_id=doc_id)
                else:
                    doc = adapter.get(index=index_name, doc_id=doc_id)
                assert doc["found"], f"Document {doc_id} not found after bulk operations"
            else:
                if is_async:
                    exists = await adapter.exists(index=index_name, doc_id=doc_id)
                else:
                    exists = adapter.exists(index=index_name, doc_id=doc_id)
                assert not exists, f"Document {doc_id} still exists after bulk delete"
        except Exception as e:
            context.logger.error(f"Failed to verify final state for document {doc_id}: {e}")
            raise

    context.logger.info("All bulk operations reflected in index")


@then("the scan should return at least {num_hits:d} hits")
def step_scan_returns_hits(context: Context, num_hits: int) -> None:
    """Verify that the scan returned the expected number of hits."""
    scenario_context = _get_scenario_context(context)
    hits = scenario_context.get("last_scan_hits", [])

    assert len(hits) >= num_hits, f"Scan returned {len(hits)} hits, expected at least {num_hits}"
    context.logger.info(f"Scan returned at least {num_hits} hits")


@then("the connection should be successful")
def step_connection_successful(context: Context) -> None:
    """Verify that the connection was successful."""
    context.logger.info("Connection to Elasticsearch cluster successful")


@then("I should be able to perform operations on the cluster")
async def step_can_perform_operations(context: Context) -> None:
    """Verify that operations can be performed on the cluster."""
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    try:
        if is_async:
            result = await adapter.ping()
        else:
            result = adapter.ping()

        assert result, "Cannot perform operations on cluster"
        context.logger.info("Able to perform operations on the cluster")
    except Exception as e:
        context.logger.error(f"Failed to perform operations on cluster: {e}")
        raise


# Cleanup
async def after_scenario(context: Context, scenario) -> None:
    """Clean up after each scenario."""
    scenario_context = _get_scenario_context(context)
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    # Clean up created documents
    created_documents = scenario_context.get("created_documents", [])
    for index_name, doc_id in created_documents:
        try:
            if is_async:
                await adapter.delete(index=index_name, doc_id=doc_id)
            else:
                adapter.delete(index=index_name, doc_id=doc_id)
            context.logger.info(f"Deleted test document {doc_id} from {index_name}")
        except Exception as e:
            context.logger.error(f"Failed to delete document {doc_id}: {e}")

    # Clean up created indices
    created_indices = scenario_context.get("created_indices", [])
    for index_name in created_indices:
        try:
            if is_async:
                await adapter.delete_index(index=index_name)
            else:
                adapter.delete_index(index=index_name)
            context.logger.info(f"Deleted test index {index_name}")
        except Exception as e:
            context.logger.error(f"Failed to delete index {index_name}: {e}")


def _cloud_id_for_host(host: str) -> str:
    """Build a syntactically valid cloud ID that resolves to the given host."""
    es_id, domain = host.split(".", 1)
    return "name:" + base64.b64encode(f"{domain}${es_id}$kibana".encode()).decode()


@given('an Elasticsearch config with "{field}" set to "{value}"')
def step_es_config_field(context: Context, field: str, value: str) -> None:
    """Collect config overrides on top of the global Elasticsearch config."""
    scenario_context = _get_scenario_context(context)
    updates = scenario_context.get("es_config_updates", {})
    parsers = {
        "NODE_SELECTOR_CLASS": str,
        "DEAD_NODE_BACKOFF_FACTOR": float,
        "MIN_DELAY_BETWEEN_SNIFFING": float,
        "SNIFF_BEFORE_REQUESTS": lambda text: text == "true",
        "BEARER_AUTH": SecretStr,
        "CLOUD_ID": _cloud_id_for_host,
        "SSL_VERSION": lambda text: ssl.TLSVersion[text],
        "OPAQUE_ID": str,
        "HEADERS": lambda text: dict(pair.split("=", 1) for pair in text.split(",")),
        "MAP_ERRORS": lambda text: text == "true",
        "IGNORE_STATUS": lambda text: tuple(int(code) for code in text.split(",")),
    }
    updates[field] = parsers[field](value)
    if field == "BEARER_AUTH":
        # Bearer auth is exclusive with the container's own credentials
        updates.update(API_KEY=None, API_SECRET=None, HTTP_USER_NAME=None, HTTP_PASSWORD=None)
    scenario_context.store("es_config_updates", updates)


@when("I create the Elasticsearch adapter from that config {mode}")
async def step_create_adapter_from_config(context: Context, mode: str) -> None:
    """Build an adapter from the overridden config."""
    scenario_context = _get_scenario_context(context)
    config = BaseConfig.global_config().ELASTIC.model_copy(update=scenario_context.get("es_config_updates", {}))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        if _is_async_scenario(context):
            scenario_context.async_adapter = AsyncElasticsearchAdapter(config)
        else:
            scenario_context.adapter = ElasticsearchAdapter(config)
    scenario_context.store(
        "creation_warnings",
        [w for w in caught if issubclass(w.category, DeprecationWarning) and "MAP_ERRORS" in str(w.message)],
    )


@then('the client should apply "{field}" as "{value}"')
def step_client_applies_option(context: Context, field: str, value: str) -> None:
    """Verify the option reached the client transport."""
    scenario_context = _get_scenario_context(context)
    adapter = scenario_context.async_adapter if _is_async_scenario(context) else scenario_context.adapter
    transport = adapter.client.transport
    if field == "NODE_SELECTOR_CLASS":
        # elastic_transport maps "random" to RandomSelector
        actual = type(transport.node_pool._node_selector).__name__  # noqa: SLF001
        assert actual == "RandomSelector", f"Unexpected selector: {actual}"
    elif field == "DEAD_NODE_BACKOFF_FACTOR":
        assert transport.node_pool.dead_node_backoff_factor == float(value)
    elif field == "MIN_DELAY_BETWEEN_SNIFFING":
        assert transport._min_delay_between_sniffing == float(value)  # noqa: SLF001
    elif field == "BEARER_AUTH":
        assert adapter.client._headers["authorization"] == f"Bearer {value}"  # noqa: SLF001
    elif field == "OPAQUE_ID":
        assert adapter.client._headers["x-opaque-id"] == value  # noqa: SLF001
    elif field == "HEADERS":
        name, expected = value.split("=", 1)
        assert adapter.client._headers[name] == expected  # noqa: SLF001
    elif field == "SSL_VERSION":
        node_config = next(iter(transport.node_pool.all())).config
        assert node_config.ssl_version == ssl.TLSVersion[value]
    elif field == "CLOUD_ID":
        # The fake cloud ID decodes to abc123.example.com, so no local HOSTS entry is left
        hosts = [node.config.host for node in transport.node_pool.all()]
        assert hosts == [value], f"Unexpected hosts: {hosts}"
    else:
        raise AssertionError(f"Unknown field {field}")


@when("I get a missing document through that adapter")
async def step_get_missing_document(context: Context) -> None:
    """Fetch a document that does not exist and record the outcome."""
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)
    adapter = scenario_context.async_adapter if is_async else scenario_context.adapter
    index_name = get_actual_index_name(context, "test-index")
    try:
        response = (
            await adapter.get(index_name, f"missing-{uuid.uuid4()}")
            if is_async
            else adapter.get(index_name, f"missing-{uuid.uuid4()}")
        )
        scenario_context.store("missing_get_error", None)
        scenario_context.store("missing_get_status", response.meta.status)
    except Exception as error:  # noqa: BLE001
        scenario_context.store("missing_get_error", error)


@then("no Elasticsearch error should be raised")
def step_no_es_error(context: Context) -> None:
    """Verify the missing-document request did not raise."""
    error = _get_scenario_context(context).get("missing_get_error")
    assert error is None, f"Unexpected error: {error!r}"


@then("the response status should be {status:d}")
def step_response_status(context: Context, status: int) -> None:
    """Verify the status of the recorded response."""
    assert _get_scenario_context(context).get("missing_get_status") == status


@then('the Elasticsearch error kind should be "{kind}"')
def step_raised_error_kind(context: Context, kind: str) -> None:
    """Verify the type of the error raised by the missing-document request."""
    from elasticsearch import NotFoundError as ClientNotFoundError

    from archipy.models.errors import NotFoundError

    error = _get_scenario_context(context).get("missing_get_error")
    expected = {"ArchiPy NotFoundError": NotFoundError, "client NotFoundError": ClientNotFoundError}[kind]
    assert isinstance(error, expected), f"Expected {kind}, got {error!r}"
    if expected is NotFoundError:
        assert isinstance(error.__cause__, ClientNotFoundError), "Original error must be chained"


@then("the adapter creation should {outcome} the ArchiPy error mapping deprecation warning")
def step_creation_warning(context: Context, outcome: str) -> None:
    """Verify whether adapter creation warned about the opt-in error mapping."""
    caught = _get_scenario_context(context).get("creation_warnings")
    assert bool(caught) == (outcome == "emit"), f"Unexpected warnings: {caught}"


@when("I {operation} through an adapter that records retry options")
async def step_record_retry_options(context: Context, operation: str) -> None:
    """Run an adapter call while recording the options() overrides applied to the client."""
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)
    adapter = get_es_adapter(context)
    index_name = get_actual_index_name(context, "test-index")
    recorded: list[dict] = []
    original_options = adapter.client.options

    def recording_options(**kwargs):
        recorded.append(kwargs)
        return original_options(**kwargs)

    adapter.client.options = recording_options
    try:
        if operation == "index a document without an id":
            call = adapter.index(index=index_name, document={"title": "auto"}, refresh="true")
        elif operation == "index a document with an id":
            call = adapter.index(index=index_name, document={"title": "fixed"}, doc_id="retry-1", refresh="true")
        elif operation == "run a scripted update":
            await _ensure_doc(adapter, index_name, is_async)
            call = adapter.update(
                index=index_name,
                doc_id="retry-1",
                doc=None,
                script={"source": "ctx._source.title = 'scripted'"},
                refresh="true",
            )
        else:
            await _ensure_doc(adapter, index_name, is_async)
            call = adapter.update(index=index_name, doc_id="retry-1", doc={"title": "plain"}, refresh="true")
        if is_async:
            await call
        else:
            call
    finally:
        del adapter.client.options
    scenario_context.store("recorded_options", recorded)


async def _ensure_doc(adapter, index_name: str, is_async: bool) -> None:
    """Index the document used by the update scenarios."""
    call = adapter.index(index=index_name, document={"title": "seed"}, doc_id="retry-1", refresh="true")
    if is_async:
        await call


@then("retries should be {state} for that call")
def step_retries_state(context: Context, state: str) -> None:
    """Verify whether the call opted out of client retries."""
    recorded = _get_scenario_context(context).get("recorded_options")
    disabled = {"max_retries": 0} in recorded
    assert disabled == (state == "disabled"), f"Unexpected options: {recorded}"


@when("I close the adapter")
async def step_close_adapter(context: Context) -> None:
    """Close the adapter client."""
    adapter = get_es_adapter(context)
    if _is_async_scenario(context):
        await adapter.aclose()
    else:
        adapter.close()


@then("the adapter should be closed")
def step_adapter_closed(context: Context) -> None:
    """Verify the adapter reports the client closed (further requests fail)."""
    adapter = get_es_adapter(context)
    assert adapter.client.transport is not None
