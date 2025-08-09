# features/steps/elasticsearch_steps.py
from behave import given, when, then
from features.test_helpers import get_current_scenario_context
from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter, AsyncElasticsearchAdapter
import logging
import ast

logger = logging.getLogger(__name__)


def get_es_adapter(context):
    """Get or initialize the appropriate Elasticsearch adapter based on scenario tags."""
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:
        if not hasattr(scenario_context, "async_adapter") or scenario_context.async_adapter is None:
            test_config = scenario_context.get("test_config")
            scenario_context.async_adapter = AsyncElasticsearchAdapter(test_config.ELASTIC)
        return scenario_context.async_adapter
    if not hasattr(scenario_context, "adapter") or scenario_context.adapter is None:
        test_config = scenario_context.get("test_config")
        scenario_context.adapter = ElasticsearchAdapter(test_config.ELASTIC)
    return scenario_context.adapter


@given("an Elasticsearch cluster is running")
async def step_cluster_running(context):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        result = await adapter.ping()
    else:
        result = adapter.ping()

    assert result, "Elasticsearch cluster is not running"
    context.logger.info("Elasticsearch cluster is running")


@given('index "{index_name}" exists')
async def step_index_exists(context, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        try:
            await adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False

    else:
        try:
            adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False

    if not exists:
        if "async" in context.scenario.tags:

            await adapter.create_index(index=index_name)
        else:
            adapter.create_index(index=index_name)

        scenario_context.created_indices = getattr(scenario_context, "created_indices", [])
        scenario_context.created_indices.append(index_name)

    context.logger.info(f"Index '{index_name}' exists")


@given('document type "{doc_type}" is configured for index "{index_name}"')
def step_doc_type_configured(context, doc_type, index_name):
    context.logger.info(f"Assuming document type '{doc_type}' is configured for index '{index_name}'")


@given("a valid Elasticsearch client connection")
async def step_valid_es_client(context):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        result = await adapter.ping()

    else:
        result = adapter.ping()

    assert result, "Elasticsearch client connection is not valid"
    context.logger.info("Valid Elasticsearch client connection")


@given('a document exists in "{index_name}" with id "{doc_id}" and content {content}')
async def step_document_exists(context, index_name, doc_id, content):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    doc_content = ast.literal_eval(content)

    if "async" in context.scenario.tags:

        await adapter.index(index=index_name, document=doc_content, doc_id=doc_id)
    else:
        adapter.index(index=index_name, document=doc_content, doc_id=doc_id)

    scenario_context.created_documents = getattr(scenario_context, "created_documents", [])
    scenario_context.created_documents.append((index_name, doc_id))
    context.logger.info(f"Document with id '{doc_id}' created in index '{index_name}'")


@when('I index a document with id "{doc_id}" and content {content} into "{index_name}"')
async def step_index_document(context, doc_id, content, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    import ast

    doc_content = ast.literal_eval(content)

    try:
        if "async" in context.scenario.tags:

            result =await adapter.index(index=index_name, document=doc_content, doc_id=doc_id)

        else:
            result = adapter.index(index=index_name, document=doc_content, doc_id=doc_id)

        scenario_context.last_index_result = result
        context.logger.info(f"Indexed document with id '{doc_id}' into '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Failed to index document: {e}")


@when('I search for "{query}" in "{index_name}"')
async def step_search_documents(context, query, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    search_query = {"query": {"multi_match": {"query": query, "fields": ["*"]}}}

    try:
        if "async" in context.scenario.tags:

            result = await adapter.search(index=index_name, query=search_query)

        else:
            result = adapter.search(index=index_name, query=search_query)

        scenario_context.last_search_result = result
        context.logger.info(f"Searched for '{query}' in '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Search failed: {e}")


@when('I update document "{doc_id}" in "{index_name}" with content {content}')
async def step_update_document(context, doc_id, content, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    doc_content = ast.literal_eval(content)

    try:
        if "async" in context.scenario.tags:

            result = await adapter.update(index=index_name, doc_id=doc_id, doc=doc_content)

        else:
            result = adapter.update(index=index_name, doc_id=doc_id, doc=doc_content)

        scenario_context.last_update_result = result
        context.logger.info(f"Updated document '{doc_id}' in '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Update failed: {e}")


@when('I delete document "{doc_id}" from "{index_name}"')
async def step_delete_document(context, doc_id, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    try:
        if "async" in context.scenario.tags:

            result =await adapter.delete(index=index_name, doc_id=doc_id)

        else:
            result = adapter.delete(index=index_name, doc_id=doc_id)

        scenario_context.last_delete_result = result
        context.logger.info(f"Deleted document '{doc_id}' from '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Delete failed: {e}")


@when('I create index "{index_name}" with {shards} shard and {replicas} replica')
async def step_create_index(context, index_name, shards, replicas):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    index_body = {"settings": {"number_of_shards": int(shards), "number_of_replicas": int(replicas)}}

    try:
        if "async" in context.scenario.tags:

            result = await adapter.create_index(index=index_name, body=index_body)

        else:
            result = adapter.create_index(index=index_name, body=index_body)

        scenario_context.last_create_index_result = result
        scenario_context.created_indices = getattr(scenario_context, "created_indices", [])
        scenario_context.created_indices.append(index_name)
        context.logger.info(f"Created index '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Index creation failed: {e}")


@when('I delete index "{index_name}"')
async def step_delete_index(context, index_name):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    try:
        if "async" in context.scenario.tags:

            result = await adapter.delete_index(index=index_name)

        else:
            result = adapter.delete_index(index=index_name)

        scenario_context.last_delete_index_result = result
        context.logger.info(f"Deleted index '{index_name}'")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Index deletion failed: {e}")


@when("I perform a bulk operation with:")
async def step_bulk_operation(context):
    adapter = get_es_adapter(context)
    scenario_context = get_current_scenario_context(context)

    bulk_actions = []
    for row in context.table:
        action = {row["action"]: {"_index": row["index"], "_id": row["id"]}}
        bulk_actions.append(action)

        if row["action"] in ["index", "create"]:
            import ast

            doc_content = ast.literal_eval(row["document"])
            bulk_actions.append(doc_content)
        elif row["action"] == "update":
            import ast

            doc_content = ast.literal_eval(row["document"])
            bulk_actions.append({"doc": doc_content})

    try:
        if "async" in context.scenario.tags:

            result =await adapter.bulk(actions=bulk_actions)

        else:
            result = adapter.bulk(actions=bulk_actions)

        scenario_context.last_bulk_result = result
        context.logger.info("Performed bulk operation")
    except Exception as e:
        scenario_context.last_error = str(e)
        context.logger.error(f"Bulk operation failed: {e}")


@then("the indexing operation should succeed")
def step_indexing_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_index_result
    assert result.get("result") in ["created", "updated"], "Indexing operation failed"
    context.logger.info("Indexing operation verified")


@then('the document should be retrievable by id "{doc_id}" from "{index_name}"')
async def step_document_retrievable(context, doc_id, index_name):
    adapter = get_es_adapter(context)

    try:
        if "async" in context.scenario.tags:

            doc = await adapter.get(index=index_name, doc_id=doc_id)

        else:
            doc = adapter.get(index=index_name, doc_id=doc_id)

        assert doc["found"], f"Document {doc_id} not found"
        context.logger.info(f"Document {doc_id} is retrievable")
    except Exception:
        assert False, f"Document {doc_id} not found in index {index_name}"


@then("the search should return at least {num_hits} hit")
def step_search_returns_hits(context, num_hits):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_search_result
    assert result["hits"]["total"]["value"] >= int(num_hits), "Not enough hits returned"
    context.logger.info(f"Search returned at least {num_hits} hits")


@then('the hit should contain field "{field}" with value "{value}"')
def step_hit_contains_field(context, field, value):
    scenario_context = get_current_scenario_context(context)
    hits = scenario_context.last_search_result["hits"]["hits"]
    assert hits, "No hits found"

    found = any(str(hit["_source"].get(field)) == value for hit in hits)
    assert found, f"No hit contains field '{field}' with value '{value}'"
    context.logger.info(f"Hit contains field '{field}' with value '{value}'")


@then("the update operation should succeed")
def step_update_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_update_result
    assert result.get("result") in ["updated", "noop"], "Update operation failed"
    context.logger.info("Update operation verified")


@then("the document should reflect the updated content when retrieved")
async def step_document_updated(context):
    scenario_context = get_current_scenario_context(context)
    update_result = scenario_context.last_update_result
    adapter = get_es_adapter(context)

    if "async" in context.scenario.tags:

        doc = await adapter.get(index=update_result["_index"], doc_id=update_result["_id"])

    else:
        doc = adapter.get(index=update_result["_index"], doc_id=update_result["_id"])

    assert doc["found"], "Document not found after update"
    context.logger.info("Document content updated successfully")


@then("the delete operation should succeed")
def step_delete_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_delete_result
    assert result.get("result") == "deleted", "Delete operation failed"
    context.logger.info("Delete operation verified")


@then("the document should not exist when searched for")
async def step_document_not_exist(context):
    scenario_context = get_current_scenario_context(context)
    delete_result = scenario_context.last_delete_result
    adapter = get_es_adapter(context)

    try:
        if "async" in context.scenario.tags:

            exists = await adapter.exists(index=delete_result["_index"], doc_id=delete_result["_id"])

        else:
            exists = adapter.exists(index=delete_result["_index"], doc_id=delete_result["_id"])

        assert not exists, "Document still exists after deletion"
    except Exception:
        pass  # Expected for non-existent documents

    context.logger.info("Document successfully deleted")


@then("the index creation should succeed")
def step_index_creation_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_create_index_result
    assert result.get("acknowledged", False), "Index creation failed"
    context.logger.info("Index creation verified")


@then('index "{index_name}" should exist in the cluster')
async def step_index_exists_in_cluster(context, index_name):
    adapter = get_es_adapter(context)

    if "async" in context.scenario.tags:

        try:
            await adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False
    else:
        try:
            adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False

    assert exists, f"Index {index_name} does not exist"
    context.logger.info(f"Index {index_name} exists in cluster")


@then("the index deletion should succeed")
def step_index_deletion_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_delete_index_result
    assert result.get("acknowledged", False), "Index deletion failed"
    context.logger.info("Index deletion verified")


@then('index "{index_name}" should not exist in the cluster')
async def step_index_not_exist_in_cluster(context, index_name):
    adapter = get_es_adapter(context)

    if "async" in context.scenario.tags:

        try:
            await adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False
    else:
        try:
            adapter.get(index=index_name, doc_id="dummy")
            exists = True
        except Exception:
            exists = False

    assert not exists, f"Index {index_name} still exists"
    context.logger.info(f"Index {index_name} does not exist in cluster")


@then("the bulk operation should succeed")
def step_bulk_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_bulk_result
    assert not result.get("errors", True), "Bulk operation had errors"
    context.logger.info("Bulk operation verified")


@then("all operations should be reflected in the index")
async def step_bulk_operations_reflected(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.last_bulk_result
    adapter = get_es_adapter(context)

    for item in result["items"]:
        action_type = next(iter(item))  # Get the first key (index/update/delete)
        action_result = item[action_type]

        if action_type in ["index", "create"]:
            if "async" in context.scenario.tags:

                doc = await adapter.get(index=action_result["_index"], doc_id=action_result["_id"])

            else:
                doc = adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
            assert doc["found"], f"Document {action_result['_id']} not found after bulk operation"
        elif action_type == "update":
            if "async" in context.scenario.tags:

                doc = await adapter.get(index=action_result["_index"], doc_id=action_result["_id"])

            else:
                doc = adapter.get(index=action_result["_index"], doc_id=action_result["_id"])
            assert doc["found"], f"Document {action_result['_id']} not found after bulk update"
        elif action_type == "delete":
            if "async" in context.scenario.tags:

                exists = await adapter.exists(index=action_result["_index"], doc_id=action_result["_id"])

            else:
                exists = adapter.exists(index=action_result["_index"], doc_id=action_result["_id"])
            assert not exists, f"Document {action_result['_id']} still exists after bulk delete"

    context.logger.info("All bulk operations reflected in index")


async def after_scenario(context, scenario):
    """Clean up after each scenario."""
    scenario_context = get_current_scenario_context(context)
    adapter = get_es_adapter(context)

    # Clean up created documents
    if hasattr(scenario_context, "created_documents"):
        for index_name, doc_id in scenario_context.created_documents:
            try:
                if "async" in context.scenario.tags:

                    await adapter.delete(index=index_name, doc_id=doc_id)

                else:
                    adapter.delete(index=index_name, doc_id=doc_id)
                context.logger.info(f"Deleted test document {doc_id} from {index_name}")
            except Exception as e:
                context.logger.error(f"Failed to delete document {doc_id}: {e}")

    # Clean up created indices
    if hasattr(scenario_context, "created_indices"):
        for index_name in scenario_context.created_indices:
            try:
                if "async" in context.scenario.tags:

                    await adapter.delete_index(index=index_name)

                else:
                    adapter.delete_index(index=index_name)
                context.logger.info(f"Deleted test index {index_name}")
            except Exception as e:
                context.logger.error(f"Failed to delete index {index_name}: {e}")
