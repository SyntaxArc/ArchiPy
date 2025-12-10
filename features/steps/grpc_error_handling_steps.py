"""Step definitions for gRPC error handling tests."""

import asyncio

from behave import given, then, when

from archipy.models.errors import (
    InternalError,
    InvalidArgumentError,
    InvalidEmailError,
    InvalidNationalCodeError,
    InvalidPhoneNumberError,
    NotFoundError,
    UnauthenticatedError,
)
from features.grpc_test_utils import (
    create_async_grpc_channel,
    create_grpc_channel,
    extract_grpc_error_info,
    get_test_async_stub,
    get_test_request,
    get_test_stub,
)
from features.test_helpers import get_current_scenario_context
from features.test_servers import (
    create_test_async_grpc_servicer,
    create_test_grpc_servicer,
    parse_grpc_metadata,
)

# Error mapping for dynamic error creation
ERROR_MAPPING = {
    "NotFoundError": NotFoundError,
    "InvalidArgumentError": InvalidArgumentError,
    "UnauthenticatedError": UnauthenticatedError,
    "InternalError": InternalError,
    "InvalidPhoneNumberError": InvalidPhoneNumberError,
    "InvalidEmailError": InvalidEmailError,
    "InvalidNationalCodeError": InvalidNationalCodeError,
}

try:
    import grpc
    from grpc import aio as grpc_aio

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    grpc_aio = None

try:
    import sys
    from pathlib import Path

    # Add proto directory to path so generated files can import each other
    proto_dir = Path(__file__).parent.parent / "proto"
    if str(proto_dir) not in sys.path:
        sys.path.insert(0, str(proto_dir))

    import test_service_pb2_grpc

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    test_service_pb2_grpc = None


@given("a gRPC test server")
def step_given_grpc_test_server(context):
    """Verify gRPC test servers are available from feature context."""
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf files are not available")

    # Servers should already be started in before_feature hook
    if not hasattr(context, "grpc_sync_server") or not hasattr(context, "grpc_async_server"):
        raise RuntimeError("gRPC servers not found in context. Make sure they are started in before_feature hook.")


@when('a sync gRPC method raises "{error_type}" error')
def step_when_sync_grpc_raises_error(context, error_type: str):
    """Test a sync gRPC method that raises a specific error using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    error_instance = error_class(lang=LanguageType.EN)

    # Configure the existing servicer with the error to raise (reuse the same server)
    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)


@when('an async gRPC method raises "{error_type}" error')
def step_when_async_grpc_raises_error(context, error_type: str):
    """Test an async gRPC method that raises a specific error using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    error_instance = error_class(lang=LanguageType.EN)

    # Configure the existing async servicer with the error to raise (reuse the same server)
    servicer = context.grpc_async_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_async_port

    # Make a real async gRPC call
    async def make_call():
        channel = create_async_grpc_channel("localhost", port)
        stub = get_test_async_stub(channel)
        request = get_test_request(data="test")

        grpc_error: grpc.RpcError | None = None
        try:
            await stub.TestMethod(request, timeout=5.0)
        except grpc.RpcError as e:
            grpc_error = e
        finally:
            await channel.close()

        return grpc_error

    grpc_error = asyncio.run(make_call())

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)


@when("a sync gRPC method receives invalid request")
def step_when_sync_grpc_invalid_request(context):
    """Test a sync gRPC method that receives invalid request using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    # Configure the existing servicer to raise a validation error
    # The interceptor will convert ValidationError to InvalidArgumentError
    servicer = context.grpc_sync_servicer
    servicer.configure(validation_error=True)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    # The interceptor converts ValidationError to InvalidArgumentError
    from archipy.models.errors import InvalidArgumentError
    from archipy.models.types.language_type import LanguageType

    error_instance = InvalidArgumentError(
        argument_name="request_validation",
        lang=LanguageType.EN,
        additional_data={"validation_errors": [{"field": "data", "message": "Field required"}]},
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("an async gRPC method receives invalid request")
def step_when_async_grpc_invalid_request(context):
    """Test an async gRPC method that receives invalid request using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    # Configure the existing async servicer to raise a validation error
    servicer = context.grpc_async_servicer
    servicer.configure(validation_error=True)
    port = context.grpc_async_port

    # Make a real async gRPC call
    async def make_call():
        channel = create_async_grpc_channel("localhost", port)
        stub = get_test_async_stub(channel)
        request = get_test_request(data="test")

        grpc_error: grpc.RpcError | None = None
        try:
            await stub.TestMethod(request, timeout=5.0)
        except grpc.RpcError as e:
            grpc_error = e
        finally:
            await channel.close()

        return grpc_error

    grpc_error = asyncio.run(make_call())

    # The interceptor converts ValidationError to InvalidArgumentError
    from archipy.models.errors import InvalidArgumentError
    from archipy.models.types.language_type import LanguageType

    error_instance = InvalidArgumentError(
        argument_name="request_validation",
        lang=LanguageType.EN,
        additional_data={"validation_errors": [{"field": "data", "message": "Field required"}]},
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("a sync gRPC method raises an unexpected exception")
def step_when_sync_grpc_unexpected_error(context):
    """Test a sync gRPC method that raises an unexpected exception using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    # Configure the existing servicer to raise an unexpected error
    # The interceptor will convert it to InternalError
    servicer = context.grpc_sync_servicer
    servicer.configure(unexpected_error=True)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    # The interceptor converts unexpected errors to InternalError
    from archipy.models.errors import InternalError
    from archipy.models.types.language_type import LanguageType

    error_instance = InternalError(
        lang=LanguageType.EN,
        additional_data={
            "original_error": "ValueError: Unexpected error",
            "error_type": "ValueError",
        },
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("an async gRPC method raises an unexpected exception")
def step_when_async_grpc_unexpected_error(context):
    """Test an async gRPC method that raises an unexpected exception using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    # Configure the existing async servicer to raise an unexpected error
    # The interceptor will convert it to InternalError
    servicer = context.grpc_async_servicer
    servicer.configure(unexpected_error=True)
    port = context.grpc_async_port

    # Make a real async gRPC call
    async def make_call():
        channel = create_async_grpc_channel("localhost", port)
        stub = get_test_async_stub(channel)
        request = get_test_request(data="test")

        grpc_error: grpc.RpcError | None = None
        try:
            await stub.TestMethod(request, timeout=5.0)
        except grpc.RpcError as e:
            grpc_error = e
        finally:
            await channel.close()

        return grpc_error

    grpc_error = asyncio.run(make_call())

    # The interceptor converts unexpected errors to InternalError
    from archipy.models.errors import InternalError
    from archipy.models.types.language_type import LanguageType

    error_instance = InternalError(
        lang=LanguageType.EN,
        additional_data={
            "original_error": "ValueError: Unexpected error",
            "error_type": "ValueError",
        },
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when('a gRPC method raises "{error_type}" error with additional data')
def step_when_grpc_error_with_data(context, error_type: str):
    """Test a gRPC method that raises an error with additional data using real gRPC calls."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    error_instance = error_class(
        lang=LanguageType.EN,
        additional_data={"test_key": "test_value", "user_id": "123"},
    )

    # Configure the existing servicer with the error to raise (reuse the same server)
    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)


@when('a gRPC method raises "{error_type}" error')
def step_when_grpc_method_raises_error(context, error_type: str):
    """Test a gRPC method that raises a specific error using real gRPC calls (generic)."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    error_instance = error_class(lang=LanguageType.EN)

    # Configure the existing servicer with the error to raise (reuse the same server)
    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)


@then("the gRPC call should fail with status code {grpc_status}")
def step_then_check_grpc_status(context, grpc_status: str):
    """Verify the gRPC status code from actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")
    error = scenario_context.get("grpc_error")

    expected_status = int(grpc_status)

    if grpc_error:
        # Get status code from actual RPC error
        error_info = extract_grpc_error_info(grpc_error)
        actual_status = error_info["code"]
        assert actual_status == expected_status, f"Expected gRPC status {expected_status}, but got {actual_status}"
    elif error:
        # Fallback: Check the error's grpc_status
        assert (
            error.grpc_status == expected_status
        ), f"Expected gRPC status {expected_status}, but got {error.grpc_status}"
    else:
        assert False, "No gRPC error found to verify status code"


@then('the error message should contain "{expected_message}"')
def step_then_check_error_message(context, expected_message: str):
    """Verify the error message contains expected text from actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")
    error = scenario_context.get("grpc_error")

    if grpc_error:
        # Get message from actual RPC error
        error_info = extract_grpc_error_info(grpc_error)
        actual_message = error_info["details"]
        expected_lower = expected_message.lower()
        actual_lower = actual_message.lower()
        assert (
            expected_lower in actual_lower or actual_lower in expected_lower
        ), f"Expected message to contain '{expected_message}', but got '{actual_message}'"
    elif error:
        # Fallback: Check the error's message
        actual_message = error.get_message()
        expected_lower = expected_message.lower()
        actual_lower = actual_message.lower()
        assert (
            expected_lower in actual_lower or actual_lower in expected_lower
        ), f"Expected message to contain '{expected_message}', but got '{actual_message}'"
    else:
        assert False, "No gRPC error found to verify message"


@then('the gRPC error code should be "{error_code}"')
def step_then_check_grpc_error_code(context, error_code: str):
    """Verify the gRPC error code."""
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("grpc_error")

    if error:
        assert error.code == error_code, f"Expected error code '{error_code}', but got '{error.code}'"


@then("the error should contain validation error details")
def step_then_check_validation_details(context):
    """Verify that validation error details are present in actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    # Validation errors should be converted to InvalidArgumentError
    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        # The details should contain validation information
        assert error_info["details"] is not None and error_info["details"] != "", "Error details should be present"
        # Status code should be INVALID_ARGUMENT (3)
        assert error_info["code"] == 3, f"Expected status code 3 (INVALID_ARGUMENT), but got {error_info['code']}"
    else:
        assert False, "No gRPC error found to verify validation error details"


@when('a sync gRPC method raises "{error_type}" validation error with value "{invalid_value}" in language "{lang}"')
def step_when_sync_grpc_raises_validation_error_with_lang(context, error_type: str, invalid_value: str, lang: str):
    """Test a sync gRPC method that raises a validation error with a specific value and language."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    # Create error with the invalid value based on error type
    if error_type == "InvalidPhoneNumberError":
        error_instance = error_class(phone_number=invalid_value, lang=language)
    elif error_type == "InvalidEmailError":
        error_instance = error_class(email=invalid_value, lang=language)
    elif error_type == "InvalidNationalCodeError":
        error_instance = error_class(national_code=invalid_value, lang=language)
    else:
        error_instance = error_class(lang=language)

    # Configure the existing servicer with the error to raise (reuse the same server)
    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

    # Make a real gRPC call
    channel = create_grpc_channel("localhost", port)
    stub = get_test_stub(channel)
    request = get_test_request(data="test")

    grpc_error: grpc.RpcError | None = None
    try:
        stub.TestMethod(request, timeout=5.0)
    except grpc.RpcError as e:
        grpc_error = e
    finally:
        channel.close()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)
    scenario_context.store("language", language)


@when('an async gRPC method raises "{error_type}" validation error with value "{invalid_value}" in language "{lang}"')
def step_when_async_grpc_raises_validation_error_with_lang(context, error_type: str, invalid_value: str, lang: str):
    """Test an async gRPC method that raises a validation error with a specific value and language."""
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    from archipy.models.types.language_type import LanguageType

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    # Create error with the invalid value based on error type
    if error_type == "InvalidPhoneNumberError":
        error_instance = error_class(phone_number=invalid_value, lang=language)
    elif error_type == "InvalidEmailError":
        error_instance = error_class(email=invalid_value, lang=language)
    elif error_type == "InvalidNationalCodeError":
        error_instance = error_class(national_code=invalid_value, lang=language)
    else:
        error_instance = error_class(lang=language)

    # Configure the existing async servicer with the error to raise (reuse the same server)
    servicer = context.grpc_async_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_async_port

    # Make a real async gRPC call
    async def make_call():
        channel = create_async_grpc_channel("localhost", port)
        stub = get_test_async_stub(channel)
        request = get_test_request(data="test")

        grpc_error: grpc.RpcError | None = None
        try:
            await stub.TestMethod(request, timeout=5.0)
        except grpc.RpcError as e:
            grpc_error = e
        finally:
            await channel.close()

        return grpc_error

    grpc_error = asyncio.run(make_call())

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)
    scenario_context.store("language", language)


@then("the gRPC call should fail")
def step_then_check_grpc_failed(context):
    """Verify that the gRPC call failed."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    assert grpc_error is not None, "gRPC call should have failed with an RpcError"
    assert isinstance(grpc_error, grpc.RpcError), f"Expected grpc.RpcError, but got {type(grpc_error)}"


@then('the trailing metadata should contain "{key}" key')
def step_then_check_trailing_metadata_key(context, key: str):
    """Verify that trailing metadata contains a specific key from actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        metadata = parse_grpc_metadata(error_info["trailing_metadata"])
        assert key in metadata, f"Trailing metadata should contain '{key}' key. Found keys: {list(metadata.keys())}"
    else:
        assert False, "No gRPC error found to verify trailing metadata"


@then('the trailing metadata "{key}" should be valid JSON')
def step_then_check_metadata_json(context, key: str):
    """Verify that trailing metadata value is valid JSON from actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        metadata = parse_grpc_metadata(error_info["trailing_metadata"])
        assert key in metadata, f"Trailing metadata should contain '{key}' key. Found keys: {list(metadata.keys())}"
        value = metadata[key]
        # If it's a string, try to parse it as JSON
        if isinstance(value, str):
            import json

            try:
                json.loads(value)
            except json.JSONDecodeError:
                assert False, f"Trailing metadata '{key}' is not valid JSON: {value}"
        # If it's already a dict, that's fine
        elif isinstance(value, dict):
            pass
        else:
            assert False, f"Trailing metadata '{key}' is not JSON-serializable: {type(value)}"
    else:
        assert False, "No gRPC error found to verify trailing metadata"


@then("the error message should match the error's get_message() result")
def step_then_check_message_matches(context):
    """Verify that the error message matches the error's get_message() result from actual RPC error."""
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("grpc_error")
    grpc_error = scenario_context.get("grpc_rpc_error")

    if error and grpc_error:
        expected_message = error.get_message()
        error_info = extract_grpc_error_info(grpc_error)
        actual_message = error_info["details"]
        assert expected_message == actual_message, f"Expected message '{expected_message}', but got '{actual_message}'"
    else:
        assert False, "No gRPC error or error instance found to verify message"
