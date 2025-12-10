"""Step definitions for FastAPI error handling tests."""

from behave import given, then, when
from pydantic import BaseModel
from starlette.testclient import TestClient

from archipy.models.errors import (
    AlreadyExistsError,
    InternalError,
    InvalidArgumentError,
    InvalidEmailError,
    InvalidNationalCodeError,
    InvalidPhoneNumberError,
    NotFoundError,
    UnauthenticatedError,
    UnknownError,
)
from archipy.models.types.language_type import LanguageType
from features.test_helpers import get_current_scenario_context
from features.test_servers import create_test_fastapi_app

# Error mapping for dynamic error creation
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


@given("a FastAPI test application")
def step_given_fastapi_test_app(context):
    """Create a FastAPI test application."""
    scenario_context = get_current_scenario_context(context)
    app = create_test_fastapi_app()
    scenario_context.store("app", app)


@when('an endpoint raises "{error_type}" error')
def step_when_endpoint_raises_error(context, error_type: str):
    """Create an endpoint that raises a specific error type."""
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    @app.get(f"/test-{error_type.lower()}")
    def raise_error():
        # Set language to English for consistent test expectations
        raise error_class(lang=LanguageType.EN)

    client = TestClient(app)
    response = client.get(f"/test-{error_type.lower()}")
    scenario_context.store("response", response)
    scenario_context.store("error_type", error_type)


@when('an endpoint raises "{error_type}" error with language "{lang}"')
def step_when_endpoint_raises_error_with_lang(context, error_type: str, lang: str):
    """Create an endpoint that raises a specific error type with language."""
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
    """Create an endpoint that raises a validation error with a specific value and language."""
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    error_class = ERROR_MAPPING.get(error_type)
    if not error_class:
        raise ValueError(f"Unknown error type: {error_type}")

    language = LanguageType.EN if lang.upper() == "EN" else LanguageType.FA

    @app.get(f"/test-{error_type.lower()}-{lang.lower()}")
    def raise_error():
        # Create error with the invalid value based on error type
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
    """Create an endpoint that raises an error with additional data."""
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
    """Create an endpoint that raises an unexpected exception."""
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
    """Create an endpoint that receives invalid request data based on description."""
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

    # Send different types of invalid data based on description
    if invalid_data_description == "missing required field":
        # Missing required fields
        response = client.post("/test-validation", json={"id": 1})
    elif invalid_data_description == "invalid field type":
        # Wrong data types
        response = client.post("/test-validation", json={"id": "not_a_number", "name": "test", "age": 25})
    elif invalid_data_description == "out of range value":
        # Out of range (age > 150)
        response = client.post("/test-validation", json={"id": 1, "name": "test", "age": 200})
    else:
        # Default: missing required field
        response = client.post("/test-validation", json={"id": 1})

    scenario_context.store("response", response)
    scenario_context.store("invalid_data_description", invalid_data_description)


@then("the response should have HTTP status code {http_status}")
def step_then_check_http_status(context, http_status: str):
    """Verify the HTTP status code in the response."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    expected_status = int(http_status)
    assert response.status_code == expected_status, f"Expected HTTP {expected_status}, but got {response.status_code}"


@then('the response should contain error code "{error_code}"')
def step_then_check_response_error_code(context, error_code: str):
    """Verify the error code in the response."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "error" in response_data, "Response should contain 'error' key"
    assert (
        response_data["error"] == error_code
    ), f"Expected error code '{error_code}', but got '{response_data['error']}'"


@then('the response should contain message "{expected_message}"')
def step_then_check_message(context, expected_message: str):
    """Verify the error message in the response."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    assert "message" in response_data["detail"], "Response detail should contain 'message' key"
    actual_message = response_data["detail"]["message"]
    # Check if expected message is contained in actual message (case-insensitive, flexible matching)
    expected_lower = expected_message.lower()
    actual_lower = actual_message.lower()
    assert (
        expected_lower in actual_lower or actual_lower in expected_lower
    ), f"Expected message to contain '{expected_message}', but got '{actual_message}'"


@then('the response JSON should have structure with "{key1}" and "{key2}" keys')
def step_then_check_json_structure(context, key1: str, key2: str):
    """Verify the JSON response structure."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert key1 in response_data, f"Response should contain '{key1}' key"
    assert key2 in response_data, f"Response should contain '{key2}' key"


@then('the response JSON should have "{key}" key with value "{value}"')
def step_then_check_json_key_value(context, key: str, value: str):
    """Verify a specific key-value pair in the JSON response."""
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

    # Try to convert value to int if it's numeric
    try:
        expected_value = int(value)
        assert actual_value == expected_value, f"Expected '{key}' to be {expected_value}, but got {actual_value}"
    except ValueError:
        assert str(actual_value) == value, f"Expected '{key}' to be '{value}', but got '{actual_value}'"


@then('the response JSON "{key_path}" should contain "{sub_key}" key')
def step_then_check_json_contains_key(context, key_path: str, sub_key: str):
    """Verify that a nested key exists in the JSON response."""
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
    """Verify that a nested key has a specific value in the JSON response (string value)."""
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

    # Try to convert value to int if it's numeric
    try:
        expected_value = int(value)
        assert (
            actual_value == expected_value
        ), f"Expected '{key_path}.{sub_key}' to be {expected_value}, but got {actual_value}"
    except ValueError:
        assert str(actual_value) == value, f"Expected '{key_path}.{sub_key}' to be '{value}', but got '{actual_value}'"


@then('the response JSON "{key_path}" should contain "{sub_key}" with value {value}')
def step_then_check_json_nested_key_value_numeric(context, key_path: str, sub_key: str, value: int):
    """Verify that a nested key has a specific value in the JSON response (numeric value)."""
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

    # Convert both to int for comparison to handle type mismatches
    actual_int = int(actual_value) if actual_value is not None else None
    expected_int = int(value)

    assert (
        actual_int == expected_int
    ), f"Expected '{key_path}.{sub_key}' to be {expected_int} (type: {type(expected_int).__name__}), but got {actual_value} (type: {type(actual_value).__name__})"


@then('the response detail should contain "{key}"')
def step_then_check_detail_contains(context, key: str):
    """Verify that the detail contains a specific key."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    detail = response_data["detail"]

    # Detail can be a dict or a list (for validation errors)
    if isinstance(detail, dict):
        # Check if key exists directly or in nested structure
        if key in detail:
            return

        # Check in nested structures (like validation_errors)
        for value in detail.values():
            if isinstance(value, dict) and key in value:
                return
            if isinstance(value, list) and any(isinstance(item, dict) and key in item for item in value):
                return
    elif isinstance(detail, list):
        # For validation errors, detail is a list of error objects
        # Check if any error object contains the key (like "field", "message", "value")
        for item in detail:
            if isinstance(item, dict):
                if key in item:
                    return
                # Check nested structures in list items
                for value in item.values():
                    if isinstance(value, dict) and key in value:
                        return
        # Also check if the key name appears in any string values (for "validation_errors" text search)
        detail_str = str(detail).lower()
        if key.lower() in detail_str:
            return

    assert False, f"Key '{key}' not found in response detail. Detail structure: {type(detail)}"


@then('the response message should be in "{lang}" language')
def step_then_check_message_language(context, lang: str):
    """Verify the message language."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()
    error_type = scenario_context.get("error_type")
    language = scenario_context.get("language")

    if not error_type or not language:
        # If not set, check based on message content (basic check)
        message = response_data.get("detail", {}).get("message", "")
        if lang.upper() == "FA":
            # Check for Persian characters
            has_persian = any("\u0600" <= char <= "\u06ff" for char in message)
            assert has_persian, f"Expected Persian message, but got: {message}"
        else:
            # English - no Persian characters
            has_persian = any("\u0600" <= char <= "\u06ff" for char in message)
            assert not has_persian, f"Expected English message, but got: {message}"
    else:
        # Verify using the error instance
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
    """Verify the message matches the expected localized message."""
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
    """Verify that additional data is present in the response detail."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    response_data = response.json()

    assert "detail" in response_data, "Response should contain 'detail' key"
    detail = response_data["detail"]

    # Check for expected additional data fields
    assert "user_id" in detail or "timestamp" in detail, "Additional data fields not found in detail"


@then('the response message should contain "{expected_message_part}"')
def step_then_check_message_contains(context, expected_message_part: str):
    """Verify that the response message contains the expected part."""
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    assert response is not None, "Response not found"

    response_data = response.json()
    message = response_data.get("detail", {}).get("message", "")

    assert (
        expected_message_part.lower() in message.lower()
    ), f"Expected message to contain '{expected_message_part}', but got '{message}'"
