import time
from uuid import uuid4

from behave import given, then, when

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.models.errors import InvalidTokenError, TokenExpiredError
from features.test_helpers import get_current_scenario_context


@given("a valid user UUID")
def step_given_valid_user_uuid(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("user_uuid", uuid4())


@when("an access token is created")
def step_when_access_token_created(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = scenario_context.get("user_uuid")
    test_config = BaseConfig.global_config()

    token = JWTUtils.create_access_token(user_uuid, auth_config=test_config.AUTH)
    scenario_context.store("token", token)


@when("a refresh token is created")
def step_when_refresh_token_created(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = scenario_context.get("user_uuid")
    test_config = BaseConfig.global_config()

    token = JWTUtils.create_refresh_token(user_uuid, auth_config=test_config.AUTH)
    scenario_context.store("token", token)


@then("a JWT token should be returned")
def step_then_jwt_token_returned(context):
    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get("token")

    assert token is not None
    assert isinstance(token, str)


@given("a valid access token")
def step_given_valid_access_token(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = scenario_context.get("user_uuid")
    test_config = BaseConfig.global_config()

    token = JWTUtils.create_access_token(user_uuid, auth_config=test_config.AUTH)
    scenario_context.store("token", token)


@given("a valid refresh token")
def step_given_valid_refresh_token(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = scenario_context.get("user_uuid")
    test_config = BaseConfig.global_config()

    token = JWTUtils.create_refresh_token(user_uuid, auth_config=test_config.AUTH)
    scenario_context.store("token", token)


@given("an expired access token")
def step_given_expired_access_token(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = scenario_context.get("user_uuid")
    test_config = BaseConfig.global_config()

    token = JWTUtils.create_access_token(
        user_uuid,
        additional_claims={"exp": time.time() - 10},
        auth_config=test_config.AUTH,
    )
    scenario_context.store("token", token)


@given("an invalid token")
def step_given_invalid_token(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("token", "invalid.token.structure")


@when("the token is decoded")
def step_when_token_decoded(context):
    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get("token")
    test_config = BaseConfig.global_config()

    try:
        decoded_payload = JWTUtils.decode_token(token, auth_config=test_config.AUTH)
        scenario_context.store("decode_success", True)
        scenario_context.store("decoded_payload", decoded_payload)
    except Exception as e:
        scenario_context.store("decode_success", False)
        scenario_context.store("decode_error", e)


@then("the decoded payload should be valid")
def step_then_decoded_payload_valid(context):
    scenario_context = get_current_scenario_context(context)
    decode_success = scenario_context.get("decode_success")
    decoded_payload = scenario_context.get("decoded_payload")

    assert decode_success is True
    assert isinstance(decoded_payload, dict)
    assert "sub" in decoded_payload
    assert "type" in decoded_payload


@then("a TokenExpiredError should be raised")
def step_then_token_expired_exception_raised(context):
    scenario_context = get_current_scenario_context(context)
    decode_error = scenario_context.get("decode_error")

    assert isinstance(decode_error, TokenExpiredError)


@then("an InvalidTokenError should be raised")
def step_then_invalid_token_exception_raised(context):
    scenario_context = get_current_scenario_context(context)
    decode_error = scenario_context.get("decode_error")

    assert isinstance(decode_error, InvalidTokenError)
