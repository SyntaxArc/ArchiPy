# features/steps/vespa_adapter_steps.py
from behave import given, when, then
from features.test_helpers import get_current_scenario_context, safe_run_async
from archipy.adapters.vespa.adapters import VespaAdapter, AsyncVespaAdapter
import logging
import json

logger = logging.getLogger(__name__)


def document_exists_from_response(response):
    """Determine if a document exists based on the response status code.

    Args:
        response: The response from a Vespa get operation.

    Returns:
        bool: True if the document exists, False otherwise.
    """
    # If response has a status_code attribute and it's 404, the document doesn't exist
    if hasattr(response, "status_code") and response.status_code == 404:
        return False

    # If response has a status_code attribute and it's 200, the document exists
    if hasattr(response, "status_code") and response.status_code == 200:
        return True

    # For other cases, check if the response is a dictionary with a 'pathId' key
    # This is specific to Vespa's response format
    if isinstance(response, dict) and "pathId" in response:
        return True

    # Default to True if we can't determine from the response
    # This maintains backward compatibility with existing code
    return True


def get_vespa_adapter(context):
    """Get or initialize the appropriate Vespa adapter based on scenario tags."""
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:
        if not hasattr(scenario_context, "async_adapter") or scenario_context.async_adapter is None:
            test_config = scenario_context.get("test_config")
            scenario_context.async_adapter = AsyncVespaAdapter(test_config.VESPA)
        return scenario_context.async_adapter
    if not hasattr(scenario_context, "adapter") or scenario_context.adapter is None:
        test_config = scenario_context.get("test_config")
        scenario_context.adapter = VespaAdapter(test_config.VESPA)
    return scenario_context.adapter


@given("a Vespa cluster is running")
def step_cluster_running(context):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    # Vespa doesn't have a direct ping method, so we'll try a simple query
    if "async" in context.scenario.tags:

        async def query_async(context):
            try:
                await adapter.query(query_string="select * from sources * where true limit 1", document_type=None)
                return True
            except Exception as e:
                context.logger.error(f"Error connecting to Vespa: {e}")
                return False

        result = safe_run_async(query_async)(context)
    else:
        try:
            adapter.query(query_string="select * from sources * where true limit 1", document_type=None)
            result = True
        except Exception as e:
            context.logger.error(f"Error connecting to Vespa: {e}")
            result = False

    assert result, "Vespa cluster is not running"
    context.logger.info("Vespa cluster is running")


@given('document type "{document_type}" exists')
def step_document_type_exists(context, document_type):
    # In Vespa, document types are defined in the application package
    # For testing purposes, we'll just assume the document type exists
    # and set it in the context for later use
    scenario_context = get_current_scenario_context(context)
    scenario_context.document_type = document_type
    context.logger.info(f"Using document type: {document_type}")


@given("a valid Vespa client connection")
def step_valid_connection(context):
    adapter = get_vespa_adapter(context)
    assert adapter is not None, "Vespa adapter is not initialized"
    context.logger.info("Vespa client connection is valid")


@given("I use HTTP/2 for Vespa connections")
def step_use_http2(context):
    scenario_context = get_current_scenario_context(context)
    test_config = scenario_context.get("test_config")
    test_config.VESPA.HTTP_VERSION = "HTTP/2"
    context.logger.info("Using HTTP/2 for Vespa connections")


@given("I use HTTP/1.1 for Vespa connections")
def step_use_http1(context):
    scenario_context = get_current_scenario_context(context)
    test_config = scenario_context.get("test_config")
    test_config.VESPA.HTTP_VERSION = "HTTP/1.1"
    context.logger.info("Using HTTP/1.1 for Vespa connections")


@then("the Vespa adapter should be using {http_version}")
def step_verify_http_version(context, http_version):
    adapter = get_vespa_adapter(context)

    # Get the HTTP version information
    http_version_info = adapter.get_http_version()
    context.logger.info(f"HTTP version info: {http_version_info}")

    # Check if the adapter is configured to use the expected HTTP version
    expected_config = f"Configured to use {http_version}"
    assert (
        expected_config in http_version_info
    ), f"Expected HTTP version configuration '{expected_config}' not found in '{http_version_info}'"

    # For async adapters, also check the actual HTTP version if possible
    if "async" in context.scenario.tags and hasattr(adapter, "check_actual_http_version"):

        async def check_version_async(context):
            headers = await adapter.check_actual_http_version()
            if headers:
                context.logger.info(f"Response headers from test request: {headers}")
                # Log any headers that might indicate HTTP version
                for header_name in ["Via", "Server", "X-Powered-By", "X-HTTP-Version"]:
                    if header_name in headers:
                        context.logger.info(f"{header_name} header: {headers[header_name]}")
            return headers

        headers = safe_run_async(check_version_async)(context)
        if headers:
            context.logger.info(f"Successfully checked actual HTTP version with headers: {headers}")

    # For sync adapters, check the actual HTTP version if possible
    elif hasattr(adapter, "check_actual_http_version"):
        headers = adapter.check_actual_http_version()
        if headers:
            context.logger.info(f"Response headers from test request: {headers}")
            # Log any headers that might indicate HTTP version
            for header_name in ["Via", "Server", "X-Powered-By", "X-HTTP-Version"]:
                if header_name in headers:
                    context.logger.info(f"{header_name} header: {headers[header_name]}")

    context.logger.info(f"Verified Vespa adapter is configured to use {http_version}")


@when('I feed a document with id "{doc_id}" and content \'{content}\' into "{document_type}"')
def step_feed_document(context, doc_id, content, document_type):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        assert False, f"Invalid JSON content: {content}"

    if "async" in context.scenario.tags:

        async def feed_async(context):
            response = await adapter.feed(document=document, document_id=doc_id, document_type=document_type)
            return response

        response = safe_run_async(feed_async)(context)
    else:
        response = adapter.feed(document=document, document_id=doc_id, document_type=document_type)

    scenario_context.last_response = response
    scenario_context.last_document_id = doc_id
    scenario_context.last_document_type = document_type
    scenario_context.last_document = document


@then("the feed operation should succeed")
def step_feed_success(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from feed operation"
    assert response.status_code == 200, f"Feed operation failed with status code {response.status_code}"
    context.logger.info("Feed operation succeeded")


@when('I query for "{query_string}" in "{document_type}"')
def step_query_documents(context, query_string, document_type):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        async def query_async(context):
            response = await adapter.query(query_string=query_string, document_type=None)
            return response

        response = safe_run_async(query_async)(context)
    else:
        response = adapter.query(query_string=query_string, document_type=None)

    scenario_context.last_response = response
    scenario_context.last_query = query_string


@then("the query should return at least {count:d} hit")
def step_query_results(context, count):

    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from query operation"
    assert response.status_code == 200, f"Query operation failed with status code {response.status_code}"

    hits = []
    response_json = response.json

    if isinstance(response_json, dict):
        # Try standard Vespa response format
        if "root" in response_json and "children" in response_json["root"]:
            hits = response_json["root"]["children"]
        # Try alternative format
        elif "hits" in response_json:
            hits = response_json["hits"]
        # Try another alternative format
        elif "results" in response_json:
            hits = response_json["results"]

    context.logger.info(f"Response JSON: {response_json}")
    assert len(hits) >= count, f"Expected at least {count} hits, got {len(hits)}"
    context.logger.info(f"Query returned {len(hits)} hits")


@then("the query should return at least {count:d} hits")
def step_query_results_plural(context, count):
    # Call the original step implementation
    step_query_results(context, count)


@when('I get document "{doc_id}" from "{document_type}"')
def step_get_document(context, doc_id, document_type):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        async def get_async(context):
            response = await adapter.get(document_id=doc_id, document_type=document_type)
            return response

        response = safe_run_async(get_async)(context)
    else:
        response = adapter.get(document_id=doc_id, document_type=document_type)

    scenario_context.last_response = response
    scenario_context.last_document_id = doc_id
    scenario_context.last_document_type = document_type


@then('the document should be retrievable by id "{doc_id}" from document type "{document_type}"')
def step_document_retrievable(context, doc_id, document_type):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        async def get_async(context):
            response = await adapter.get(document_id=doc_id, document_type=document_type)
            return response

        response = safe_run_async(get_async)(context)
    else:
        response = adapter.get(document_id=doc_id, document_type=document_type)

    assert response is not None, "No response received from get operation"
    assert response.status_code == 200, f"Get operation failed with status code {response.status_code}"
    assert "fields" in response.json, "Document fields not found in response"
    context.logger.info(f"Document {doc_id} retrieved successfully")


@when('I update document "{doc_id}" in document type "{document_type}" with content \'{content}\'')
def step_update_document(context, doc_id, document_type, content):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    try:
        update_dict = json.loads(content)
    except json.JSONDecodeError:
        assert False, f"Invalid JSON content: {content}"

    if "async" in context.scenario.tags:

        async def update_async(context):
            response = await adapter.update(document_id=doc_id, document_type=document_type, update_dict=update_dict)
            return response

        response = safe_run_async(update_async)(context)
    else:
        response = adapter.update(document_id=doc_id, document_type=document_type, update_dict=update_dict)

    scenario_context.last_response = response
    scenario_context.last_document_id = doc_id
    scenario_context.last_document_type = document_type
    scenario_context.last_update = update_dict


@then("the Vespa update operation should succeed")
def step_update_success(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from update operation"
    assert response.status_code == 200, f"Update operation failed with status code {response.status_code}"
    context.logger.info("Update operation succeeded")


@then("the Vespa document should reflect the updated content when retrieved")
def step_verify_update(context):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)
    doc_id = scenario_context.last_document_id
    document_type = scenario_context.last_document_type
    update_dict = scenario_context.last_update

    if "async" in context.scenario.tags:

        async def get_async(context):
            response = await adapter.get(document_id=doc_id, document_type=document_type)
            return response

        response = safe_run_async(get_async)(context)
    else:
        response = adapter.get(document_id=doc_id, document_type=document_type)

    assert response is not None, "No response received from get operation"
    assert response.status_code == 200, f"Get operation failed with status code {response.status_code}"

    # Check that the document contains the updated fields
    document = response.json.get("fields", {})
    for key, value in update_dict.items():
        assert key in document, f"Updated field {key} not found in document"
        assert document[key] == value, f"Field {key} has value {document[key]}, expected {value}"

    context.logger.info("Document update verified")


@when('I delete document "{doc_id}" from document type "{document_type}"')
def step_delete_document(context, doc_id, document_type):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        async def delete_async(context):
            response = await adapter.delete(document_id=doc_id, document_type=document_type)
            return response

        response = safe_run_async(delete_async)(context)
    else:
        response = adapter.delete(document_id=doc_id, document_type=document_type)

    scenario_context.last_response = response
    scenario_context.last_document_id = doc_id
    scenario_context.last_document_type = document_type


@then("the Vespa delete operation should succeed")
def step_delete_success(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from delete operation"
    assert response.status_code == 200, f"Delete operation failed with status code {response.status_code}"
    context.logger.info("Delete operation succeeded")


@then("the Vespa document should not exist when searched for")
def step_document_not_exists(context):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)
    doc_id = scenario_context.last_document_id
    document_type = scenario_context.last_document_type

    if "async" in context.scenario.tags:

        async def get_async(context):
            try:
                response = await adapter.get(document_id=doc_id, document_type=document_type)
                # Use the helper function to determine if the document exists
                exists = document_exists_from_response(response)
                if not exists:
                    context.logger.info(f"Document not found: {response}")
                else:
                    context.logger.info(f"Document found: {response}")
                return exists
            except Exception as e:
                context.logger.error(f"Error checking document existence: {e}")
                return False

        exists = safe_run_async(get_async)(context)
    else:
        try:
            response = adapter.get(document_id=doc_id, document_type=document_type)
            # Use the helper function to determine if the document exists
            exists = document_exists_from_response(response)
        except Exception:
            exists = False

    assert not exists, f"Document {doc_id} still exists after deletion"
    context.logger.info(f"Document {doc_id} confirmed deleted")


@given('a document exists in document type "{document_type}" with id "{doc_id}" and content \'{content}\'')
def step_document_exists(context, document_type, doc_id, content):
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        assert False, f"Invalid JSON content: {content}"

    # First try to get the document
    document_exists = False
    if "async" in context.scenario.tags:

        async def check_exists_async(context):
            try:
                response = await adapter.get(document_id=doc_id, document_type=document_type)
                # Use the helper function to determine if the document exists
                exists = document_exists_from_response(response)
                if exists:
                    context.logger.info(f"Document found: {doc_id}")
                else:
                    context.logger.info(f"Document not found: {doc_id}")
                return exists
            except Exception as e:
                context.logger.error(f"Error checking document existence: {e}")
                return False

        document_exists = safe_run_async(check_exists_async)(context)
    else:
        try:
            response = adapter.get(document_id=doc_id, document_type=document_type)
            # Use the helper function to determine if the document exists
            document_exists = document_exists_from_response(response)
        except Exception:
            document_exists = False

    # If document doesn't exist, create it
    if not document_exists:
        if "async" in context.scenario.tags:

            async def feed_async(context):
                response = await adapter.feed(document=document, document_id=doc_id, document_type=document_type)
                return response

            response = safe_run_async(feed_async)(context)
        else:
            response = adapter.feed(document=document, document_id=doc_id, document_type=document_type)

        assert response.status_code == 200, f"Failed to create document: {response.status_code}"

    context.logger.info(f"Document {doc_id} exists in {document_type}")


@given('a document exists in Vespa "{document_type}" with id "{doc_id}" and content \'{content}\'')
def step_document_exists_alt(context, document_type, doc_id, content):
    # Call the original step implementation
    step_document_exists(context, document_type, doc_id, content)


@given('the scenario is tagged as "{tag}"')
def step_scenario_tagged(context, tag):
    """Mark the scenario with a specific tag."""
    if tag not in context.scenario.tags:
        context.scenario.tags.append(tag)
    context.logger.info(f"Scenario tagged as {tag}")


@when('I get schema information for "{schema_name}"')
def step_get_schema(context, schema_name):
    """Get schema information from Vespa."""
    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    if "async" in context.scenario.tags:

        async def get_schema_async(context):
            response = await adapter.get_schema(schema_name=schema_name)
            return response

        response = safe_run_async(get_schema_async)(context)
    else:
        response = adapter.get_schema(schema_name=schema_name)

    scenario_context.last_response = response
    scenario_context.last_schema_name = schema_name


@then("the schema information should be retrieved successfully")
def step_schema_retrieved(context):
    """Verify that schema information was retrieved successfully."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from get_schema operation"
    # For schema operations, the response might be a dictionary or a response object
    if hasattr(response, "status_code"):
        assert response.status_code == 200, f"Get schema operation failed with status code {response.status_code}"

    context.logger.info("Schema information retrieved successfully")


@when("I deploy a test application to Vespa Docker")
def step_deploy_docker(context):
    """Deploy a test application to Vespa Docker."""
    from vespa.package import Schema, Document, Field, ApplicationPackage

    adapter = get_vespa_adapter(context)
    scenario_context = get_current_scenario_context(context)

    # Create a simple application package for testing
    doc = Document(fields=[Field(name="title", type="string", indexing=["summary", "index"])])
    schema = Schema(name="testapp", document=doc)
    app_package = ApplicationPackage(name="testapp", schema=[schema])

    if "async" in context.scenario.tags:

        async def deploy_async(context):
            response = await adapter.deploy(
                deployment_type="docker",
                application_package=app_package,
                max_wait_configserver=30,
                max_wait_deployment=150,
                debug=True,
            )
            return response

        response = safe_run_async(deploy_async)(context)
    else:
        response = adapter.deploy(
            deployment_type="docker",
            application_package=app_package,
            max_wait_configserver=30,
            max_wait_deployment=150,
            debug=True,
        )

    scenario_context.last_response = response


@then("the deployment should succeed")
def step_deploy_success(context):
    """Verify that deployment was successful."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.last_response

    assert response is not None, "No response received from deploy operation"

    # The deploy response format might vary, so we'll check for common success indicators
    if isinstance(response, dict):
        assert "error" not in response, f"Deployment failed: {response.get('error', 'Unknown error')}"
    elif hasattr(response, "status_code"):
        assert response.status_code in [200, 201], f"Deployment failed with status code {response.status_code}"

    context.logger.info("Deployment succeeded")
