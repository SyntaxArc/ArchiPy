from behave import given, then

from archipy.models.errors import InvalidPhoneNumberError, NotFoundError, TokenExpiredError
from features.test_helpers import get_current_scenario_context

# Error Mapping - using error classes directly
error_mapping = {
    "INVALID_PHONE": InvalidPhoneNumberError,
    "NOT_FOUND": NotFoundError,
    "TOKEN_EXPIRED": TokenExpiredError,
}


@given('an error type "{error_enum}"')
def step_given_error_type(context, error_enum):
    scenario_context = get_current_scenario_context(context)
    error_class = error_mapping[error_enum]

    # Handle error classes that require parameters
    if error_enum == "INVALID_PHONE":
        error_instance = error_class(phone_number="09123456789")
    else:
        # Other error classes can be instantiated without parameters
        error_instance = error_class()

    scenario_context.store("error_detail", error_instance)


@then('the error code should be "{expected_code}"')
def step_then_check_error_code(context, expected_code):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    assert error_detail.code == expected_code, f"Expected '{expected_code}', but got '{error_detail.code}'"


@then('the English message should be "{expected_message_en}"')
def step_then_check_english_message(context, expected_message_en):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    # For t-strings, check the processed message with English language
    from archipy.models.types.language_type import LanguageType

    original_lang = error_detail.lang
    error_detail.lang = LanguageType.EN
    actual_message = error_detail.get_message()
    error_detail.lang = original_lang
    assert actual_message == expected_message_en, f"Expected '{expected_message_en}', but got '{actual_message}'"


@then('the Persian message should be "{expected_message_fa}"')
def step_then_check_persian_message(context, expected_message_fa):
    scenario_context = get_current_scenario_context(context)
    error_detail = scenario_context.get("error_detail")
    # For t-strings, check the processed message with Persian language
    from archipy.models.types.language_type import LanguageType

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
