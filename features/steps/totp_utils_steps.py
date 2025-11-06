from behave import given, then, when

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.totp_utils import TOTPUtils
from features.test_helpers import get_current_scenario_context


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
