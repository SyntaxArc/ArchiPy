import asyncio
from http import HTTPStatus
from unittest.mock import patch

from behave import given, then, when
from fastapi.responses import JSONResponse
from grpc import StatusCode

from archipy.helpers.utils.error_utils import ErrorUtils
from archipy.models.errors import BaseError, InvalidPhoneNumberError, NotFoundError
from features.test_helpers import get_current_scenario_context


@given('a raised error "{error_type}" with message "{message}"')
def step_given_raised_error(context, error_type, message):
    scenario_context = get_current_scenario_context(context)
    error = eval(f"{error_type}('{message}')")
    scenario_context.store("error", error)


@when("the error is captured")
def step_when_error_is_captured(context):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    with patch("archipy.helpers.utils.error_utils.logger.exception") as mock_log:
        ErrorUtils.capture_exception(error)
        scenario_context.store("log_called", mock_log.called)


@then("it should be logged")
def step_then_error_should_be_logged(context):
    scenario_context = get_current_scenario_context(context)
    log_called = scenario_context.get("log_called")
    assert log_called is True


@given('an error with code "{code}", English message "{message_en}", and Persian message "{message_fa}"')
def step_given_create_error_detail(context, code, message_en, message_fa):
    """Create a test error class with the specified error details."""
    from typing import ClassVar

    scenario_context = get_current_scenario_context(context)

    # Store values in local variables for use in class definition
    error_code = code
    error_message_en = message_en
    error_message_fa = message_fa

    # Create a dynamic error class for testing
    class TestError(BaseError):
        code: ClassVar[str] = error_code
        message_en: ClassVar[str] = error_message_en
        message_fa: ClassVar[str] = error_message_fa
        http_status: ClassVar[int] = 500
        grpc_status: ClassVar[int] = 13

    error_instance = TestError()
    scenario_context.store("error_details", error_instance)


@when("an error detail is created")
def step_when_error_detail_is_created(context):
    pass  # No need for additional processing


@then('the response should contain code "{expected_code}"')
def step_then_error_detail_should_contain_code(context, expected_code):
    scenario_context = get_current_scenario_context(context)
    error_details = scenario_context.get("error_details")
    assert error_details.code == expected_code


@given('a FastAPI error "{error_type}"')
def step_given_fastapi_error(context, error_type):
    scenario_context = get_current_scenario_context(context)
    fastapi_error = eval(f"{error_type}()")
    scenario_context.store("fastapi_error", fastapi_error)


@when("an async FastAPI error is handled")
def step_when_fastapi_error_is_handled(context):
    scenario_context = get_current_scenario_context(context)
    fastapi_error = scenario_context.get("fastapi_error")

    async def handle_error():
        return await ErrorUtils.async_handle_fastapi_exception(None, fastapi_error)

    with patch("fastapi.responses.JSONResponse") as mock_response:
        mock_response.return_value = JSONResponse(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            content={"detail": "Error occurred"},
        )
        http_status = asyncio.run(handle_error()).status_code
        scenario_context.store("http_status", http_status)


@then("the response should have an HTTP status of 500")
def step_then_http_status_should_be_500(context):
    scenario_context = get_current_scenario_context(context)
    http_status = scenario_context.get("http_status")
    assert http_status == 500


@given('a gRPC error "{error_type}"')
def step_given_grpc_error(context, error_type):
    scenario_context = get_current_scenario_context(context)
    grpc_error = eval(f"{error_type}()")
    scenario_context.store("grpc_error", grpc_error)


@when("gRPC error is handled")
def step_when_grpc_error_is_handled(context):
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_error")
    grpc_code, _ = ErrorUtils.handle_grpc_exception(grpc_error)
    scenario_context.store("grpc_code", grpc_code)


@then('the response should have gRPC status "INTERNAL"')
def step_then_grpc_status_should_be_internal(context):
    scenario_context = get_current_scenario_context(context)
    grpc_code = scenario_context.get("grpc_code")
    assert grpc_code == StatusCode.INTERNAL.value[0]


@given("a list of FastAPI errors {error_names}")
def step_given_list_of_errors(context, error_names):
    scenario_context = get_current_scenario_context(context)
    error_mapping = {
        "InvalidPhoneNumberError": InvalidPhoneNumberError,
        "NotFoundError": NotFoundError,
        "BaseError": BaseError,
    }
    error_list = [
        error_mapping[err.strip()] for err in error_names.strip("[]").split(",") if err.strip() in error_mapping
    ]
    scenario_context.store("error_list", error_list)


@when("the FastAPI error responses are generated")
def step_when_generate_error_responses(context):
    scenario_context = get_current_scenario_context(context)
    error_list = scenario_context.get("error_list")
    responses = ErrorUtils.get_fastapi_exception_responses(error_list)
    scenario_context.store("responses", responses)


@then("the responses should contain HTTP status codes")
def step_then_responses_should_contain_status_codes(context):
    scenario_context = get_current_scenario_context(context)
    responses = scenario_context.get("responses")
    assert isinstance(responses, dict)
    assert len(responses) > 0, "Expected non-empty responses, but got empty dictionary."
    assert any(isinstance(status, HTTPStatus) for status in responses.keys()), "No valid HTTPStatus keys found."
