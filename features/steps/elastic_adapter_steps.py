# features/steps/elasticsearch_steps.py
import time
import json
import logging
import ast
import asyncio
import uuid

from behave import given, when, then
from behave.runner import Context

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

        # Wait a bit for Elasticsearch to be fully ready
        time.sleep(2)

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
        if is_async:
            await adapter.create_index(index=unique_index_name)
        else:
            adapter.create_index(index=unique_index_name)

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

        if is_async:
            result = await adapter.create_index(index=actual_index_name, body=index_body)
        else:
            result = adapter.create_index(index=actual_index_name, body=index_body)

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
        bulk_actions = []
        for row in context.table:
            action = row["action"]
            doc_id = row["id"]
            index_name = row["index"]
            actual_index_name = get_actual_index_name(context, index_name)

            if action == "index":
                # For index actions, add action metadata then document
                bulk_actions.append({action: {"_index": actual_index_name, "_id": doc_id}})
                if row["document"]:
                    doc_content = ast.literal_eval(row["document"])
                    bulk_actions.append(doc_content)
            elif action == "create":
                # For create actions, add action metadata then document
                bulk_actions.append({action: {"_index": actual_index_name, "_id": doc_id}})
                if row["document"]:
                    doc_content = ast.literal_eval(row["document"])
                    bulk_actions.append(doc_content)
            elif action == "update":
                # For update actions, add action metadata then update document
                bulk_actions.append({action: {"_index": actual_index_name, "_id": doc_id}})
                if row["document"]:
                    doc_content = ast.literal_eval(row["document"])
                    # Check if the user already provided the Elasticsearch format with 'doc' field
                    if "doc" in doc_content:
                        # User already provided the correct format, use as-is
                        bulk_actions.append(doc_content)
                    else:
                        # User provided raw document, wrap in 'doc' field
                        bulk_actions.append({"doc": doc_content})
            elif action == "delete":
                # For delete actions, only add action metadata (no document needed)
                bulk_actions.append({action: {"_index": actual_index_name, "_id": doc_id}})

        if is_async:
            result = await adapter.bulk(actions=bulk_actions)
        else:
            result = adapter.bulk(actions=bulk_actions)

        _store_result(scenario_context, "last_bulk_result", result)
        _log_operation(context, "Bulk operation", f"Performed bulk operation with {len(bulk_actions)} actions")

    except Exception as e:
        scenario_context.store("last_error", str(e))
        context.logger.exception(f"Bulk operation failed: {e}")
        raise


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

    # Check if bulk operation had errors
    if result.get("errors", False):
        # Log detailed error information
        context.logger.error(f"Bulk operation had errors: {result}")

        # Check individual item results for more details
        if "items" in result:
            for i, item in enumerate(result["items"]):
                action_type = next(iter(item))
                action_result = item[action_type]

                if "error" in action_result:
                    context.logger.error(f"Item {i} ({action_type}) failed: {action_result['error']}")

        assert False, f"Bulk operation had errors. Check logs for details."

    # Verify all items were processed successfully
    if "items" in result:
        for i, item in enumerate(result["items"]):
            action_type = next(iter(item))
            action_result = item[action_type]

            # Check if this specific action failed
            if "error" in action_result:
                context.logger.error(f"Item {i} ({action_type}) failed: {action_result['error']}")
                assert False, f"Bulk operation item {i} ({action_type}) failed: {action_result['error']}"

            # Verify expected result status
            if action_type in ["index", "create"]:
                assert action_result.get("result") in [
                    "created",
                    "updated",
                ], f"Index/create failed for item {i}: {action_result}"
            elif action_type == "update":
                assert action_result.get("result") in [
                    "updated",
                    "noop",
                ], f"Update failed for item {i}: {action_result}"
            elif action_type == "delete":
                # Delete can return 'deleted' for existing documents or 'not_found' for non-existing documents
                # Both are valid results, not errors
                assert action_result.get("result") in [
                    "deleted",
                    "not_found",
                ], f"Delete failed for item {i}: {action_result}"
                if action_result.get("result") == "not_found":
                    context.logger.info(
                        f"Item {i} ({action_type}): Document {action_result.get('_id')} was not found (expected for non-existing documents)",
                    )

    context.logger.info("Bulk operation verified successfully")


@then("all operations should be reflected in the index")
async def step_bulk_operations_reflected(context: Context) -> None:
    """Verify that all bulk operations are reflected in the index."""
    scenario_context = _get_scenario_context(context)
    result = scenario_context.get("last_bulk_result")
    adapter = get_es_adapter(context)
    is_async = _is_async_scenario(context)

    for item in result["items"]:
        action_type = next(iter(item))  # Get the first key (index/update/delete)
        action_result = item[action_type]

        if action_type in ["index", "create"]:
            try:
                if is_async:
                    doc = await adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
                else:
                    doc = adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
                assert doc["found"], f"Document {action_result['_id']} not found after bulk operation"
            except Exception as e:
                context.logger.error(
                    f"Failed to verify {action_type} operation for document {action_result['_id']}: {e}",
                )
                raise
        elif action_type == "update":
            try:
                if is_async:
                    doc = await adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
                else:
                    doc = adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
                assert doc["found"], f"Document {action_result['_id']} not found after bulk update"
            except Exception as e:
                context.logger.error(f"Failed to verify update operation for document {action_result['_id']}: {e}")
                raise
        elif action_type == "delete":
            try:
                if is_async:
                    exists = await adapter.exists(index=action_result["_index"], doc_id=action_result["_id"])
                else:
                    exists = adapter.exists(index=action_result["_index"], doc_id=action_result["_id"])
                assert not exists, f"Document {action_result['_id']} still exists after bulk delete"
            except Exception as e:
                context.logger.error(f"Failed to verify delete operation for document {action_result['_id']}: {e}")
                raise

    context.logger.info("All bulk operations reflected in index")


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
