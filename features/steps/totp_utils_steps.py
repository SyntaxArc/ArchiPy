from datetime import timedelta
from unittest.mock import patch

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils
from archipy.helpers.utils.totp_utils import TOTPUtils
from archipy.models.errors import InvalidArgumentError, InvalidTokenError


@given('a valid secret "{secret}"')
def step_given_valid_secret(context, secret):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("secret", secret)


@given("a TOTP code is generated")
def step_given_totp_generated(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    test_config = BaseConfig.global_config()

    totp_code, expires = TOTPUtils.generate_totp(secret, test_config.AUTH)

    scenario_context.store("totp_code", totp_code)
    scenario_context.store("expires", expires)


@given('an invalid TOTP code "{totp_code}"')
def step_given_invalid_totp_code(context, totp_code):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("invalid_totp_code", totp_code)


@when("a TOTP is generated")
def step_when_totp_generated(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    test_config = BaseConfig.global_config()

    totp_code, expires = TOTPUtils.generate_totp(secret, test_config.AUTH)

    scenario_context.store("totp_code", totp_code)
    scenario_context.store("expires", expires)


@when("the TOTP code is verified")
def step_when_totp_verified(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    totp_code = scenario_context.get("totp_code")
    test_config = BaseConfig.global_config()

    is_verified = TOTPUtils.verify_totp(secret, totp_code, test_config.AUTH)

    scenario_context.store("is_verified", is_verified)


@when("the invalid TOTP code is verified")
def step_when_invalid_totp_verified(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    invalid_totp_code = scenario_context.get("invalid_totp_code")
    test_config = BaseConfig.global_config()

    is_verified = TOTPUtils.verify_totp(secret, invalid_totp_code, test_config.AUTH)

    scenario_context.store("is_verified", is_verified)


@when("a secret key is generated")
def step_when_secret_key_generated(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()

    secret_key = TOTPUtils.generate_secret_key_for_totp(test_config.AUTH)

    scenario_context.store("secret_key", secret_key)


@then("a TOTP code is returned")
def step_then_totp_code_returned(context):
    scenario_context = get_current_scenario_context(context)
    totp_code = scenario_context.get("totp_code")

    assert totp_code.isdigit()


@then("an expiration time is provided")
def step_then_expiration_time_provided(context):
    scenario_context = get_current_scenario_context(context)
    expires = scenario_context.get("expires")

    assert expires is not None


@then("a secret key is returned")
def step_then_secret_key_returned(context):
    scenario_context = get_current_scenario_context(context)
    secret_key = scenario_context.get("secret_key")

    assert secret_key is not None


@given("the current epoch time is {epoch:d}")
def step_given_epoch_time(context, epoch):
    patcher = patch.object(DatetimeUtils, "get_epoch_time_now", return_value=epoch)
    patcher.start()
    context.add_cleanup(patcher.stop)


@when('the TOTP code "{totp_code}" is checked')
def step_when_totp_code_checked(context, totp_code):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    test_config = BaseConfig.global_config()
    try:
        scenario_context.store("code_result", TOTPUtils.verify_totp(secret, totp_code, test_config.AUTH))
        scenario_context.store("code_error", None)
    except InvalidTokenError as e:
        scenario_context.store("code_result", None)
        scenario_context.store("code_error", e)


@then("the code check reports not valid")
def step_then_code_check_not_valid(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("code_error") is None, scenario_context.get("code_error")
    assert scenario_context.get("code_result") is False


@then("the code check raises InvalidTokenError")
def step_then_code_check_invalid_token(context):
    assert isinstance(get_current_scenario_context(context).get("code_error"), InvalidTokenError)


@then('the TOTP code is "{expected}"')
def step_then_totp_code_is(context, expected):
    assert get_current_scenario_context(context).get("totp_code") == expected


@then("the TOTP code verifies")
def step_then_totp_code_verifies(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret")
    assert TOTPUtils.verify_totp(secret, scenario_context.get("totp_code"), BaseConfig.global_config().AUTH) is True


@when("a TOTP is generated from the generated secret key")
def step_when_totp_from_generated_secret(context):
    scenario_context = get_current_scenario_context(context)
    secret = scenario_context.get("secret_key")
    totp_code, expires = TOTPUtils.generate_totp(secret, BaseConfig.global_config().AUTH)
    scenario_context.store("secret", secret)
    scenario_context.store("totp_code", totp_code)
    scenario_context.store("expires", expires)


@then("the expiration is no later than the verification window allows")
def step_then_expiration_within_window(context):
    expires = get_current_scenario_context(context).get("expires")
    auth = BaseConfig.global_config().AUTH
    remaining = expires - DatetimeUtils.get_datetime_now()
    longest = timedelta(seconds=(auth.TOTP_VERIFICATION_WINDOW + 1) * auth.TOTP_TIME_STEP)
    assert remaining <= longest + timedelta(seconds=1), f"{remaining} > {longest}"


@when("a secret key is generated without a TOTP master key")
def step_when_secret_key_without_master_key(context):
    scenario_context = get_current_scenario_context(context)
    auth = BaseConfig.global_config().AUTH.model_copy(update={"TOTP_SECRET_KEY": None})
    try:
        TOTPUtils.generate_secret_key_for_totp(auth)
        scenario_context.store("secret_key_error", None)
    except Exception as e:
        scenario_context.store("secret_key_error", e)


@then("the secret key generation raises InvalidArgumentError")
def step_then_secret_key_invalid_argument(context):
    error = get_current_scenario_context(context).get("secret_key_error")
    assert isinstance(error, InvalidArgumentError), repr(error)


@given("a replay guard that remembers used time steps")
def step_given_replay_guard(context):
    scenario_context = get_current_scenario_context(context)
    asked: list[int] = []
    used: set[int] = set()

    def guard(step: int) -> bool:
        asked.append(step)
        if step in used:
            return False
        used.add(step)
        return True

    scenario_context.store("replay_guard", guard)
    scenario_context.store("replay_guard_asked", asked)


def _verify_with_guard(context, code_key):
    scenario_context = get_current_scenario_context(context)
    is_verified = TOTPUtils.verify_totp(
        scenario_context.get("secret"),
        scenario_context.get(code_key),
        BaseConfig.global_config().AUTH,
        replay_guard=scenario_context.get("replay_guard"),
    )
    scenario_context.store("is_verified", is_verified)


@when("the TOTP code is verified with the replay guard")
def step_when_verified_with_guard(context):
    _verify_with_guard(context, "totp_code")


@when("the invalid TOTP code is verified with the replay guard")
def step_when_invalid_verified_with_guard(context):
    _verify_with_guard(context, "invalid_totp_code")


@then("the replay guard was asked about {count:d} time step")
@then("the replay guard was asked about {count:d} time steps")
def step_then_replay_guard_asked(context, count):
    asked = get_current_scenario_context(context).get("replay_guard_asked")
    assert len(asked) == count, f"Expected {count} guard calls, got {asked}"
