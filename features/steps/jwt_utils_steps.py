import time
from uuid import uuid4

from behave import given, then, when

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.models.errors import InvalidArgumentError, InvalidTokenError, TokenExpiredError
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


def _try_create(scenario_context, **kwargs):
    try:
        JWTUtils.create_access_token(scenario_context.get("user_uuid"), **kwargs)
        scenario_context.store("claims_error", None)
    except InvalidArgumentError as e:
        scenario_context.store("claims_error", e)


@when('an access token is created with the additional claim "{claim}"')
def step_when_token_with_additional_claim(context, claim):
    scenario_context = get_current_scenario_context(context)
    _try_create(scenario_context, additional_claims={claim: "forged"}, auth_config=BaseConfig.global_config().AUTH)


@when('an access token is created with the signing algorithm "{algorithm}"')
def step_when_token_with_algorithm(context, algorithm):
    scenario_context = get_current_scenario_context(context)
    auth = BaseConfig.global_config().AUTH.model_copy(update={"HASH_ALGORITHM": algorithm})
    _try_create(scenario_context, auth_config=auth)


@then("a token claims error should be raised")
def step_then_token_claims_error(context):
    error = get_current_scenario_context(context).get("claims_error")
    assert isinstance(error, InvalidArgumentError), repr(error)


@given("an access token that expired {seconds:d} seconds ago")
def step_given_token_expired_seconds_ago(context, seconds):
    scenario_context = get_current_scenario_context(context)
    token = JWTUtils.create_access_token(
        scenario_context.get("user_uuid"),
        additional_claims={"exp": int(time.time()) - seconds},
        auth_config=BaseConfig.global_config().AUTH,
    )
    scenario_context.store("token", token)


def _decode(scenario_context, **kwargs):
    auth = BaseConfig.global_config().AUTH
    leeway = kwargs.pop("leeway", None)
    if leeway is not None:
        auth = auth.model_copy(update={"JWT_LEEWAY": leeway})
    try:
        payload = JWTUtils.decode_token(scenario_context.get("token"), auth_config=auth, **kwargs)
        scenario_context.store("decode_success", True)
        scenario_context.store("decoded_payload", payload)
    except Exception as e:
        scenario_context.store("decode_success", False)
        scenario_context.store("decode_error", e)


@when("the token is decoded with a leeway of {leeway:d} seconds")
def step_when_decoded_with_leeway(context, leeway):
    _decode(get_current_scenario_context(context), leeway=leeway)


@when("the token is decoded requiring an empty token type")
def step_when_decoded_requiring_empty_type(context):
    _decode(get_current_scenario_context(context), verify_type="")


@when("an authentication configuration is built with a leeway of {leeway:d}")
def step_when_auth_config_leeway(context, leeway):
    from pydantic import ValidationError

    from archipy.configs.config_template import AuthConfig

    scenario_context = get_current_scenario_context(context)
    try:
        AuthConfig(JWT_LEEWAY=leeway)
        scenario_context.store("config_error", None)
    except ValidationError as e:
        scenario_context.store("config_error", e)


@then("the configuration is rejected")
def step_then_configuration_rejected(context):
    assert get_current_scenario_context(context).get("config_error") is not None


@when('an access token is created with a {length:d} byte signing key and the algorithm "{algorithm}"')
def step_when_token_with_key_length(context, length, algorithm):
    from pydantic import SecretStr

    auth = BaseConfig.global_config().AUTH.model_copy(
        update={"SECRET_KEY": SecretStr("k" * length), "HASH_ALGORITHM": algorithm},
    )
    _try_create(get_current_scenario_context(context), auth_config=auth)


@then("no token error is raised")
def step_then_no_token_error(context):
    assert get_current_scenario_context(context).get("claims_error") is None


@when("the token is decoded with a {length:d} byte signing key")
def step_when_decoded_with_short_key(context, length):
    from pydantic import SecretStr

    scenario_context = get_current_scenario_context(context)
    auth = BaseConfig.global_config().AUTH.model_copy(update={"SECRET_KEY": SecretStr("k" * length)})
    try:
        JWTUtils.decode_token(scenario_context.get("token"), auth_config=auth)
        scenario_context.store("claims_error", None)
    except InvalidArgumentError as e:
        scenario_context.store("claims_error", e)


@given("a valid {kind} token")
def step_given_valid_token_of_kind(context, kind):
    scenario_context = get_current_scenario_context(context)
    create = JWTUtils.create_access_token if kind == "access" else JWTUtils.create_refresh_token
    scenario_context.store(
        "token", create(scenario_context.get("user_uuid"), auth_config=BaseConfig.global_config().AUTH)
    )


@when("the token is verified as a {required} token")
def step_when_token_verified_as(context, required):
    scenario_context = get_current_scenario_context(context)
    verify = JWTUtils.verify_access_token if required == "access" else JWTUtils.verify_refresh_token
    try:
        verify(scenario_context.get("token"), auth_config=BaseConfig.global_config().AUTH)
        scenario_context.store("is_verified", True)
    except InvalidTokenError:
        scenario_context.store("is_verified", False)


@when("the token is decoded after the configured token version changes")
def step_when_decoded_after_version_change(context):
    scenario_context = get_current_scenario_context(context)
    auth_config = BaseConfig.global_config().AUTH
    newer = auth_config.model_copy(update={"TOKEN_VERSION": auth_config.TOKEN_VERSION + 1})
    try:
        JWTUtils.decode_token(scenario_context.get("token"), auth_config=newer)
        scenario_context.store("decode_error", None)
    except Exception as error:
        scenario_context.store("decode_error", error)


_SUBJECT_PAYLOADS = {
    "a valid subject": lambda: {"sub": str(uuid4())},
    "a missing subject": lambda: {},
    "a numeric subject": lambda: {"sub": 42},
    "a malformed subject": lambda: {"sub": "not-a-uuid"},
}


@when("the user UUID is extracted from {case}")
def step_when_user_uuid_extracted(context, case):
    scenario_context = get_current_scenario_context(context)
    try:
        JWTUtils.extract_user_uuid(_SUBJECT_PAYLOADS[case]())
        scenario_context.store("extraction_error", None)
    except InvalidTokenError as error:
        scenario_context.store("extraction_error", error)


@then("the extraction should {outcome}")
def step_then_extraction_outcome(context, outcome):
    error = get_current_scenario_context(context).get("extraction_error")
    if outcome == "succeed":
        assert error is None, error
    else:
        assert isinstance(error, InvalidTokenError), error


@when("the token expiry is read")
def step_when_token_expiry_read(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.store(
            "token_expiry",
            JWTUtils.get_token_expiry(scenario_context.get("token"), auth_config=BaseConfig.global_config().AUTH),
        )
        scenario_context.store("decode_error", None)
    except Exception as error:
        scenario_context.store("decode_error", error)


@then("the expiry should match the expiry claim")
def step_then_expiry_matches_claim(context):
    scenario_context = get_current_scenario_context(context)
    payload = JWTUtils.decode_token(scenario_context.get("token"), auth_config=BaseConfig.global_config().AUTH)
    assert scenario_context.get("token_expiry") == int(payload["exp"])


@when("a token is created from {case}")
def step_when_token_created_from(context, case):
    scenario_context = get_current_scenario_context(context)
    arguments = {"empty data": ({}, 60), "a zero expiry": ({"sub": "x"}, 0), "a negative expiry": ({"sub": "x"}, -5)}
    data, expires_in = arguments[case]
    try:
        JWTUtils.create_token(data, expires_in, auth_config=BaseConfig.global_config().AUTH)
        scenario_context.store("claims_error", None)
    except InvalidArgumentError as error:
        scenario_context.store("claims_error", error)
