"""Step definitions for error handling tests."""

from http import HTTPStatus
from typing import ClassVar
from unittest.mock import patch

from behave import given, then, when
from pydantic import BaseModel
from starlette.testclient import TestClient

from archipy.helpers.utils.error_utils import ErrorUtils
from archipy.models.errors import (
    AlreadyExistsError,
    BaseError,
    InternalError,
    InvalidArgumentError,
    InvalidEmailError,
    InvalidNationalCodeError,
    InvalidPhoneNumberError,
    NotFoundError,
    TokenExpiredError,
    UnauthenticatedError,
    UnknownError,
)
from archipy.models.types.language_type import LanguageType
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
    create_test_fastapi_app,
    create_test_grpc_servicer,
    parse_grpc_metadata,
)

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

    proto_dir = Path(__file__).parent.parent / "proto"
    if str(proto_dir) not in sys.path:
        sys.path.insert(0, str(proto_dir))

    import test_service_pb2_grpc

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    test_service_pb2_grpc = None

ERROR_MAPPING = {
    "NotFoundError": NotFoundError,
    "InvalidArgumentError": InvalidArgumentError,
    "UnauthenticatedError": UnauthenticatedError,
    "InternalError": InternalError,
    "UnknownError": UnknownError,
    "AlreadyExistsError": AlreadyExistsError,
    "InvalidPhoneNumberError": InvalidPhoneNumberError,
    "InvalidEmailError": InvalidEmailError,
    "InvalidNationalCodeError": InvalidNationalCodeError,
}

ERROR_TYPE_MAPPING = {
    "INVALID_PHONE": InvalidPhoneNumberError,
    "NOT_FOUND": NotFoundError,
    "TOKEN_EXPIRED": TokenExpiredError,
}


@given("a FastAPI test application")
def step_given_fastapi_test_app(context):
    scenario_context = get_current_scenario_context(context)
    app = create_test_fastapi_app()
    scenario_context.store("app", app)


@given("a gRPC test server")
def step_given_grpc_test_server(context):
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf files are not available")

    if not hasattr(context, "grpc_sync_server") or not hasattr(context, "grpc_async_server"):
        raise RuntimeError("gRPC servers not found in context. Make sure they are started in before_feature hook.")


@given('an error type "{error_enum}"')
def step_given_error_type(context, error_enum):
    scenario_context = get_current_scenario_context(context)
    error_class = ERROR_TYPE_MAPPING[error_enum]

    if error_enum == "INVALID_PHONE":
        error_instance = error_class(phone_number="09123456789")
    else:
        error_instance = error_class()

    scenario_context.store("error_detail", error_instance)


@given('a raised error "{error_type}" with message "{message}"')
def step_given_raised_error(context, error_type, message):
    scenario_context = get_current_scenario_context(context)
    error = eval(f"{error_type}('{message}')")
    scenario_context.store("error", error)


@given('an error with code "{code}", English message "{message_en}", and Persian message "{message_fa}"')
def step_given_create_error_detail(context, code, message_en, message_fa):
    scenario_context = get_current_scenario_context(context)

    from typing import ClassVar

    error_code = code
    error_msg_en = message_en
    error_msg_fa = message_fa

    class TestError(BaseError):
        code: ClassVar[str] = error_code
        message_en: ClassVar[str] = error_msg_en
        message_fa: ClassVar[str] = error_msg_fa
        http_status: ClassVar[int] = 500
        grpc_status: ClassVar[int] = 13

    error_instance = TestError()
    scenario_context.store("error_details", error_instance)


@when("the error is captured")
def step_when_error_is_captured(context):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    with patch("archipy.helpers.utils.error_utils.logger.exception") as mock_log:
        ErrorUtils.capture_exception(error)
        scenario_context.store("log_called", mock_log.called)


@when("an error detail is created")
def step_when_error_detail_is_created(context):
    pass


@when('an endpoint raises "{error_type}" error')
def step_when_endpoint_raises_error(context, error_type: str):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    @app.get(f"/test-{error_type.lower()}")
    def raise_error():
        raise error_class(lang=LanguageType.EN)

    client = TestClient(app)
    response = client.get(f"/test-{error_type.lower()}")
    scenario_context.store("response", response)
    scenario_context.store("error_type", error_type)


@when('an endpoint raises "{error_type}" error with language "{lang}"')
def step_when_endpoint_raises_error_with_lang(context, error_type: str, lang: str):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    @app.get(f"/test-{error_type.lower()}-{lang.lower()}")
    def raise_error():
        raise error_class(lang=language)

    client = TestClient(app)
    response = client.get(f"/test-{error_type.lower()}-{lang.lower()}")
    scenario_context.store("response", response)
    scenario_context.store("error_type", error_type)
    scenario_context.store("language", language)


@when('an endpoint raises "{error_type}" validation error with value "{invalid_value}" in language "{lang}"')
def step_when_endpoint_raises_validation_error_with_lang(context, error_type: str, invalid_value: str, lang: str):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    @app.get(f"/test-{error_type.lower()}-{lang.lower()}")
    def raise_error():
        if error_type == "InvalidPhoneNumberError":
            raise error_class(phone_number=invalid_value, lang=language)
        elif error_type == "InvalidEmailError":
            raise error_class(email=invalid_value, lang=language)
        elif error_type == "InvalidNationalCodeError":
            raise error_class(national_code=invalid_value, lang=language)
        else:
            raise error_class(lang=language)

    client = TestClient(app)
    response = client.get(f"/test-{error_type.lower()}-{lang.lower()}")
    scenario_context.store("response", response)
    scenario_context.store("error_type", error_type)
    scenario_context.store("language", language)


@when("an endpoint raises an error with additional data")
def step_when_endpoint_raises_error_with_data(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    @app.get("/test-error-with-data")
    def raise_error():
        raise NotFoundError(
            resource_type="user",
            lang=LanguageType.EN,
            additional_data={"user_id": "123", "timestamp": "2024-01-01"},
        )

    client = TestClient(app)
    response = client.get("/test-error-with-data")
    scenario_context.store("response", response)


@when("an endpoint raises an unexpected exception")
def step_when_endpoint_raises_unexpected(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    @app.get("/test-unexpected")
    def raise_unexpected():
        raise ValueError("Unexpected error")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-unexpected")
    scenario_context.store("response", response)


@when('an endpoint receives invalid request data "{invalid_data_description}"')
def step_when_endpoint_receives_invalid_data(context, invalid_data_description: str):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    from pydantic import Field

    class TestSchema(BaseModel):
        id: int = Field(gt=0, description="ID must be positive")
        name: str = Field(min_length=1, description="Name is required")
        age: int = Field(ge=0, le=150, description="Age must be between 0 and 150")

    @app.post("/test-validation")
    def validate_data(schema: TestSchema):
        return {"message": "Valid"}

    client = TestClient(app)

    if invalid_data_description == "missing required field":
        response = client.post("/test-validation", json={"id": 1})
    elif invalid_data_description == "invalid field type":
        response = client.post("/test-validation", json={"id": "not_a_number", "name": "test", "age": 25})
    elif invalid_data_description == "out of range value":
        response = client.post("/test-validation", json={"id": 1, "name": "test", "age": 200})
    else:
        response = client.post("/test-validation", json={"id": 1})

    scenario_context.store("response", response)
    scenario_context.store("invalid_data_description", invalid_data_description)


@when('a sync gRPC method raises "{error_type}" error')
def step_when_sync_grpc_raises_error(context, error_type: str):
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    error_instance = error_class(lang=LanguageType.EN)

    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

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
async def step_when_async_grpc_raises_error(context, error_type: str):
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    error_instance = error_class(lang=LanguageType.EN)

    servicer = context.grpc_async_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_async_port

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

    grpc_error = await make_call()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)


@when("a sync gRPC method receives invalid request")
def step_when_sync_grpc_invalid_request(context):
    scenario_context = get_current_scenario_context(context)

    servicer = context.grpc_sync_servicer
    servicer.configure(validation_error=True)
    port = context.grpc_sync_port

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

    error_instance = InvalidArgumentError(
        argument_name="request_validation",
        lang=LanguageType.EN,
        additional_data={"validation_errors": [{"field": "data", "message": "Field required"}]},
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("a sync gRPC method raises an unexpected exception")
def step_when_sync_grpc_unexpected_error(context):
    scenario_context = get_current_scenario_context(context)

    servicer = context.grpc_sync_servicer
    servicer.configure(unexpected_error=True)
    port = context.grpc_sync_port

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

    error_instance = InternalError(
        lang=LanguageType.EN,
        additional_data={
            "original_error": "ValueError: Unexpected error",
            "error_type": "ValueError",
        },
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("an async gRPC method receives invalid request")
async def step_when_async_grpc_invalid_request(context):
    scenario_context = get_current_scenario_context(context)

    servicer = context.grpc_async_servicer
    servicer.configure(validation_error=True)
    port = context.grpc_async_port

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

    grpc_error = await make_call()

    error_instance = InvalidArgumentError(
        argument_name="request_validation",
        lang=LanguageType.EN,
        additional_data={"validation_errors": [{"field": "data", "message": "Field required"}]},
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("an async gRPC method raises an unexpected exception")
async def step_when_async_grpc_unexpected_error(context):
    scenario_context = get_current_scenario_context(context)

    servicer = context.grpc_async_servicer
    servicer.configure(unexpected_error=True)
    port = context.grpc_async_port

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

    grpc_error = await make_call()

    error_instance = InternalError(
        lang=LanguageType.EN,
        additional_data={
            "original_error": "ValueError: Unexpected error",
            "error_type": "ValueError",
        },
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("a <mode> gRPC method receives invalid request")
async def step_when_grpc_invalid_request(context, mode: str):
    scenario_context = get_current_scenario_context(context)

    if mode == "sync":
        servicer = context.grpc_sync_servicer
        servicer.configure(validation_error=True)
        port = context.grpc_sync_port

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
    else:
        servicer = context.grpc_async_servicer
        servicer.configure(validation_error=True)
        port = context.grpc_async_port

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

        grpc_error = await make_call()

    error_instance = InvalidArgumentError(
        argument_name="request_validation",
        lang=LanguageType.EN,
        additional_data={"validation_errors": [{"field": "data", "message": "Field required"}]},
    )

    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("grpc_error", error_instance)


@when("a <mode> gRPC method raises an unexpected exception")
async def step_when_grpc_unexpected_exception(context, mode: str):
    scenario_context = get_current_scenario_context(context)

    if mode == "sync":
        servicer = context.grpc_sync_servicer
        servicer.configure(unexpected_error=True)
        port = context.grpc_sync_port

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
    else:
        servicer = context.grpc_async_servicer
        servicer.configure(unexpected_error=True)
        port = context.grpc_async_port

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

        grpc_error = await make_call()

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
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    error_instance = error_class(
        lang=LanguageType.EN,
        additional_data={"test_key": "test_value", "user_id": "123"},
    )

    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

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
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    error_instance = error_class(lang=LanguageType.EN)

    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

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


@when('a sync gRPC method raises "{error_type}" validation error with value "{invalid_value}" in language "{lang}"')
def step_when_sync_grpc_raises_validation_error_with_lang(context, error_type: str, invalid_value: str, lang: str):
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    if error_type == "InvalidPhoneNumberError":
        error_instance = error_class(phone_number=invalid_value, lang=language)
    elif error_type == "InvalidEmailError":
        error_instance = error_class(email=invalid_value, lang=language)
    elif error_type == "InvalidNationalCodeError":
        error_instance = error_class(national_code=invalid_value, lang=language)
    else:
        error_instance = error_class(lang=language)

    servicer = context.grpc_sync_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_sync_port

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
async def step_when_async_grpc_raises_validation_error_with_lang(context, error_type: str, invalid_value: str, lang: str):
    scenario_context = get_current_scenario_context(context)

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    if error_type == "InvalidPhoneNumberError":
        error_instance = error_class(phone_number=invalid_value, lang=language)
    elif error_type == "InvalidEmailError":
        error_instance = error_class(email=invalid_value, lang=language)
    elif error_type == "InvalidNationalCodeError":
        error_instance = error_class(national_code=invalid_value, lang=language)
    else:
        error_instance = error_class(lang=language)

    servicer = context.grpc_async_servicer
    servicer.configure(error_to_raise=error_instance)
    port = context.grpc_async_port

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

    grpc_error = await make_call()

    scenario_context.store("grpc_error", error_instance)
    scenario_context.store("grpc_rpc_error", grpc_error)
    scenario_context.store("error_type", error_type)
    scenario_context.store("language", language)


@then("it should be logged")
def step_then_error_should_be_logged(context):
    scenario_context = get_current_scenario_context(context)
    log_called = scenario_context.get("log_called")
    assert log_called is True


@then('the response should contain code "{expected_code}"')
def step_then_error_detail_should_contain_code(context, expected_code):
    scenario_context = get_current_scenario_context(context)
    error_details = scenario_context.get("error_details")
    assert error_details.code == expected_code


@then('the error code should be "{expected_code}"')
def step_then_check_error_code(context, expected_code):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    assert error_detail.code == expected_code, f"Expected '{expected_code}', but got '{error_detail.code}'"


@then('the English message should be "{expected_message_en}"')
def step_then_check_english_message(context, expected_message_en):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")

    original_lang = error_detail.lang
    error_detail.lang = LanguageType.EN
    actual_message = error_detail.get_message()
    error_detail.lang = original_lang
    assert actual_message == expected_message_en, f"Expected '{expected_message_en}', but got '{actual_message}'"


@then('the Persian message should be "{expected_message_fa}"')
def step_then_check_persian_message(context, expected_message_fa):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")

    original_lang = error_detail.lang
    error_detail.lang = LanguageType.FA
    actual_message = error_detail.get_message()
    error_detail.lang = original_lang
    assert actual_message == expected_message_fa, f"Expected '{expected_message_fa}', but got '{actual_message}'"


@then("the HTTP status should be {http_status}")
def step_then_check_http_status(context, http_status):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    assert error_detail.http_status == int(
        http_status,
    ), f"Expected HTTP {http_status}, but got {error_detail.http_status}"


@then("the gRPC status should be {grpc_status}")
def step_then_check_grpc_status(context, grpc_status):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    assert error_detail.grpc_status == int(
        grpc_status,
    ), f"Expected gRPC {grpc_status}, but got {error_detail.grpc_status}"


@then("the response should have HTTP status code {http_status}")
def step_then_check_http_status(context, http_status: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    expected_status = int(http_status)
    assert response.status_code == expected_status, f"Expected HTTP {expected_status}, but got {response.status_code}"


@then('the response should contain error code "{error_code}"')
def step_then_check_response_error_code(context, error_code: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "error" in response_data, "Response should contain 'error' key"
    assert (
        response_data["error"] == error_code
    ), f"Expected error code '{error_code}', but got '{response_data['error']}'"


@then('the response should contain message "{expected_message}"')
def step_then_check_message(context, expected_message: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    assert "message" in response_data["detail"], "Response detail should contain 'message' key"
    actual_message = response_data["detail"]["message"]
    expected_lower = expected_message.lower()
    actual_lower = actual_message.lower()
    assert (
        expected_lower in actual_lower or actual_lower in expected_lower
    ), f"Expected message to contain '{expected_message}', but got '{actual_message}'"


@then('the response JSON should have structure with "{key1}" and "{key2}" keys')
def step_then_check_json_structure(context, key1: str, key2: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert key1 in response_data, f"Response should contain '{key1}' key"
    assert key2 in response_data, f"Response should contain '{key2}' key"


@then('the response JSON should have "{key}" key with value "{value}"')
def step_then_check_json_key_value(context, key: str, value: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    keys = key.split(".")
    current = response_data
    for k in keys[:-1]:
        assert k in current, f"Key '{k}' not found in response"
        current = current[k]

    final_key = keys[-1]
    assert final_key in current, f"Key '{final_key}' not found in response"
    actual_value = current[final_key]

    try:
        expected_value = int(value)
        assert actual_value == expected_value, f"Expected '{key}' to be {expected_value}, but got {actual_value}"
    except ValueError:
        assert str(actual_value) == value, f"Expected '{key}' to be '{value}', but got '{actual_value}'"


@then('the response JSON "{key_path}" should contain "{sub_key}" key')
def step_then_check_json_contains_key(context, key_path: str, sub_key: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    keys = key_path.split(".")
    current = response_data
    for k in keys:
        assert k in current, f"Key '{k}' not found in response path '{key_path}'"
        current = current[k]

    assert isinstance(current, dict), f"Value at '{key_path}' is not a dictionary"
    assert sub_key in current, f"Key '{sub_key}' not found in '{key_path}'"


@then('the response JSON "{key_path}" should contain "{sub_key}" with value "{value}"')
def step_then_check_json_nested_key_value_string(context, key_path: str, sub_key: str, value: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    keys = key_path.split(".")
    current = response_data
    for k in keys:
        assert k in current, f"Key '{k}' not found in response path '{key_path}'"
        current = current[k]

    assert isinstance(current, dict), f"Value at '{key_path}' is not a dictionary"
    assert sub_key in current, f"Key '{sub_key}' not found in '{key_path}'"
    actual_value = current[sub_key]

    try:
        expected_value = int(value)
        assert (
            actual_value == expected_value
        ), f"Expected '{key_path}.{sub_key}' to be {expected_value}, but got {actual_value}"
    except ValueError:
        assert str(actual_value) == value, f"Expected '{key_path}.{sub_key}' to be '{value}', but got '{actual_value}'"


@then('the response JSON "{key_path}" should contain "{sub_key}" with value {value}')
def step_then_check_json_nested_key_value_numeric(context, key_path: str, sub_key: str, value: int):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    keys = key_path.split(".")
    current = response_data
    for k in keys:
        assert k in current, f"Key '{k}' not found in response path '{key_path}'"
        current = current[k]

    assert isinstance(current, dict), f"Value at '{key_path}' is not a dictionary"
    assert sub_key in current, f"Key '{sub_key}' not found in '{key_path}'"
    actual_value = current[sub_key]

    actual_int = int(actual_value) if actual_value is not None else None
    expected_int = int(value)

    assert (
        actual_int == expected_int
    ), f"Expected '{key_path}.{sub_key}' to be {expected_int} (type: {type(expected_int).__name__}), but got {actual_value} (type: {type(actual_value).__name__})"


@then('the response detail should contain "{key}"')
def step_then_check_detail_contains(context, key: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    detail = response_data["detail"]

    if isinstance(detail, dict):
        if key in detail:
            return

        for value in detail.values():
            if isinstance(value, dict) and key in value:
                return
            if isinstance(value, list) and any(isinstance(item, dict) and key in item for item in value):
                return
    elif isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                if key in item:
                    return
                for value in item.values():
                    if isinstance(value, dict) and key in value:
                        return
        detail_str = str(detail).lower()
        if key.lower() in detail_str:
            return

    assert False, f"Key '{key}' not found in response detail. Detail structure: {type(detail)}"


@then('the response message should be in "{lang}" language')
def step_then_check_message_language(context, lang: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()
    error_type = scenario_context.get("error_type")
    language = scenario_context.get("language")

    if not error_type or not language:
        message = response_data.get("detail", {}).get("message", "")
        if lang.upper() == "FA":
            has_persian = any("\u0600" <= char <= "\u06ff" for char in message)
            assert has_persian, f"Expected Persian message, but got: {message}"
        else:
            has_persian = any("\u0600" <= char <= "\u06ff" for char in message)
            assert not has_persian, f"Expected English message, but got: {message}"
    else:
        error_class = ERROR_MAPPING.get(error_type)
        if error_class:
            error_instance = error_class(lang=language)
            expected_message = error_instance.get_message()
            actual_message = response_data.get("detail", {}).get("message", "")
            assert (
                expected_message == actual_message
            ), f"Expected message '{expected_message}', but got '{actual_message}'"


@then('the message should match the expected "{lang}" message')
def step_then_check_expected_message(context, lang: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()
    error_type = scenario_context.get("error_type")
    language = scenario_context.get("language")

    if error_type and language:
        error_class = ERROR_MAPPING.get(error_type)
        if error_class:
            error_instance = error_class(lang=language)
            expected_message = error_instance.get_message()
            actual_message = response_data.get("detail", {}).get("message", "")
            assert (
                expected_message == actual_message
            ), f"Expected message '{expected_message}', but got '{actual_message}'"


@then("the response detail should contain the additional data fields")
def step_then_check_additional_data(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    detail = response_data["detail"]

    assert "user_id" in detail or "timestamp" in detail, "Additional data fields not found in detail"


@then('the response message should contain "{expected_message_part}"')
def step_then_check_message_contains(context, expected_message_part: str):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    assert response is not None, "Response not found"

    response_data = response.json()
    message = response_data.get("detail", {}).get("message", "")

    assert (
        expected_message_part.lower() in message.lower()
    ), f"Expected message to contain '{expected_message_part}', but got '{message}'"


@then("the gRPC call should fail with status code {grpc_status}")
def step_then_check_grpc_status(context, grpc_status: str):
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")
    error = scenario_context.get("grpc_error")

    expected_status = int(grpc_status)

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        actual_status = error_info["code"]
        assert actual_status == expected_status, f"Expected gRPC status {expected_status}, but got {actual_status}"
    elif error:
        assert (
            error.grpc_status == expected_status
        ), f"Expected gRPC status {expected_status}, but got {error.grpc_status}"
    else:
        assert False, "No gRPC error found to verify status code"


@then('the error message should contain "{expected_message}"')
def step_then_check_error_message(context, expected_message: str):
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")
    error = scenario_context.get("grpc_error")

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        actual_message = error_info["details"]
        expected_lower = expected_message.lower()
        actual_lower = actual_message.lower()
        assert (
            expected_lower in actual_lower or actual_lower in expected_lower
        ), f"Expected message to contain '{expected_message}', but got '{actual_message}'"
    elif error:
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
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("grpc_error")

    if error:
        assert error.code == error_code, f"Expected error code '{error_code}', but got '{error.code}'"


@then("the error should contain validation error details")
def step_then_check_validation_details(context):
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        assert error_info["details"] is not None and error_info["details"] != "", "Error details should be present"
        assert error_info["code"] == 3, f"Expected status code 3 (INVALID_ARGUMENT), but got {error_info['code']}"
    else:
        assert False, "No gRPC error found to verify validation error details"


@then("the gRPC call should fail")
def step_then_check_grpc_failed(context):
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    assert grpc_error is not None, "gRPC call should have failed with an RpcError"
    assert isinstance(grpc_error, grpc.RpcError), f"Expected grpc.RpcError, but got {type(grpc_error)}"


@then('the trailing metadata should contain "{key}" key')
def step_then_check_trailing_metadata_key(context, key: str):
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
    scenario_context = get_current_scenario_context(context)
    grpc_error = scenario_context.get("grpc_rpc_error")

    if grpc_error:
        error_info = extract_grpc_error_info(grpc_error)
        metadata = parse_grpc_metadata(error_info["trailing_metadata"])
        assert key in metadata, f"Trailing metadata should contain '{key}' key. Found keys: {list(metadata.keys())}"
        value = metadata[key]
        if isinstance(value, str):
            import json

            try:
                json.loads(value)
            except json.JSONDecodeError:
                assert False, f"Trailing metadata '{key}' is not valid JSON: {value}"
        elif isinstance(value, dict):
            pass
        else:
            assert False, f"Trailing metadata '{key}' is not JSON-serializable: {type(value)}"
    else:
        assert False, "No gRPC error found to verify trailing metadata"


@then("the error message should match the error's get_message() result")
def step_then_check_message_matches(context):
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
