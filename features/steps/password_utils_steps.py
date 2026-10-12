import hashlib
import os
from base64 import b64encode

from behave import given, then, when

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.password_utils import PasswordUtils
from archipy.models.errors import InvalidPasswordError
from features.test_helpers import get_current_scenario_context


@given('a password "{password}"')
def step_given_password(context, password):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("password", password)


@given("the password is hashed")
def step_given_password_hashed(context):
    scenario_context = get_current_scenario_context(context)
    password = scenario_context.get("password")
    test_config = BaseConfig.global_config()

    hashed_password = PasswordUtils.hash_password(password, test_config.AUTH)
    scenario_context.store("hashed_password", hashed_password)


@when("the password is hashed")
def step_when_password_hashed(context):
    scenario_context = get_current_scenario_context(context)
    password = scenario_context.get("password")
    test_config = BaseConfig.global_config()

    hashed_password = PasswordUtils.hash_password(password, test_config.AUTH)
    scenario_context.store("hashed_password", hashed_password)


@then("a hashed password should be returned")
def step_then_hashed_password_returned(context):
    scenario_context = get_current_scenario_context(context)
    hashed_password = scenario_context.get("hashed_password")

    assert hashed_password is not None
    assert isinstance(hashed_password, str)


@when("the password is verified")
def step_when_password_verified(context):
    scenario_context = get_current_scenario_context(context)
    password = scenario_context.get("password")
    hashed_password = scenario_context.get("hashed_password")
    test_config = BaseConfig.global_config()

    is_verified = PasswordUtils.verify_password(
        password,
        hashed_password,
        test_config.AUTH,
    )
    scenario_context.store("is_verified", is_verified)


@when('a different password "{wrong_password}" is verified')
def step_when_wrong_password_verified(context, wrong_password):
    scenario_context = get_current_scenario_context(context)
    hashed_password = scenario_context.get("hashed_password")
    test_config = BaseConfig.global_config()

    is_verified = PasswordUtils.verify_password(
        wrong_password,
        hashed_password,
        test_config.AUTH,
    )
    scenario_context.store("is_verified", is_verified)


@when("the password is validated")
def step_when_password_validated(context):
    scenario_context = get_current_scenario_context(context)
    password = scenario_context.get("password")
    test_config = BaseConfig.global_config()

    try:
        PasswordUtils.validate_password(password, test_config.AUTH)
        scenario_context.store("validation_passed", True)
    except InvalidPasswordError as e:
        scenario_context.store("validation_passed", False)
        scenario_context.store("validation_error", str(e))


@then("the password validation should succeed")
def step_then_validation_succeeds(context):
    scenario_context = get_current_scenario_context(context)
    validation_passed = scenario_context.get("validation_passed")

    assert validation_passed is True


@then("the password validation should fail")
def step_then_validation_fails_with_message(context):
    scenario_context = get_current_scenario_context(context)
    validation_passed = scenario_context.get("validation_passed")
    validation_error = scenario_context.get("validation_error")

    assert validation_passed is False
    assert validation_error is not None


@when("a secure password is generated")
def step_when_secure_password_generated(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()

    generated_password = PasswordUtils.generate_password(test_config.AUTH)
    scenario_context.store("generated_password", generated_password)


@then("the generated password should meet security requirements")
def step_then_secure_password_meets_requirements(context):
    scenario_context = get_current_scenario_context(context)
    generated_password = scenario_context.get("generated_password")
    test_config = BaseConfig.global_config()

    assert len(generated_password) >= test_config.AUTH.MIN_LENGTH
    assert any(char.isdigit() for char in generated_password)
    assert any(char.islower() for char in generated_password)
    assert any(char.isupper() for char in generated_password)
    assert any(char in test_config.AUTH.SPECIAL_CHARACTERS for char in generated_password)


@given('a password history containing "{old_password}"')
def step_given_password_history(context, old_password):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()

    password_history = [PasswordUtils.hash_password(old_password, test_config.AUTH)]
    scenario_context.store("password_history", password_history)


@when('a user attempts to reuse "{new_password}" as a new password')
def step_when_reuse_old_password(context, new_password):
    scenario_context = get_current_scenario_context(context)
    password_history = scenario_context.get("password_history")
    test_config = BaseConfig.global_config()
    auth = test_config.AUTH
    history_size = scenario_context.get("history_size")
    if history_size is not None:
        auth = auth.model_copy(update={"PASSWORD_HISTORY_SIZE": history_size})

    try:
        PasswordUtils.validate_password_history(new_password, password_history, auth)
        scenario_context.store("validation_passed", True)
    except InvalidPasswordError as e:
        scenario_context.store("validation_passed", False)
        scenario_context.store("validation_error", str(e))


@then("the password validation should fail with an error message")
def step_then_password_reuse_fails_with_message(context):
    scenario_context = get_current_scenario_context(context)
    validation_passed = scenario_context.get("validation_passed")
    validation_error = scenario_context.get("validation_error")

    assert validation_passed is False
    # The validation error now contains our custom error message in the specified language
    assert validation_error is not None
    # Print the error for debugging
    print(f"Error message: {validation_error}")
    # Less strict check - just make sure it's a password error
    assert "INVALID_PASSWORD" in validation_error


@then('the stored hash uses the "{scheme}" scheme with the configured iteration count')
def step_then_hash_is_versioned(context, scheme):
    scenario_context = get_current_scenario_context(context)
    hashed_password = scenario_context.get("hashed_password")
    parts = hashed_password.split("$")
    assert len(parts) == 4, hashed_password
    assert parts[0] == scheme
    assert int(parts[1]) == BaseConfig.global_config().AUTH.HASH_ITERATIONS


@when("the password is verified with the iteration setting changed to {iterations:d}")
def step_when_verified_with_changed_iterations(context, iterations):
    scenario_context = get_current_scenario_context(context)
    auth = BaseConfig.global_config().AUTH.model_copy(update={"HASH_ITERATIONS": iterations})
    scenario_context.store(
        "is_verified",
        PasswordUtils.verify_password(scenario_context.get("password"), scenario_context.get("hashed_password"), auth),
    )


def _legacy_hash(password, iterations):
    auth = BaseConfig.global_config().AUTH
    salt = os.urandom(auth.SALT_LENGTH)
    return b64encode(salt + hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)).decode("utf-8")


@given("the password is hashed in the legacy format with the configured iteration count")
def step_given_legacy_hash_configured(context):
    scenario_context = get_current_scenario_context(context)
    iterations = BaseConfig.global_config().AUTH.HASH_ITERATIONS
    scenario_context.store("hashed_password", _legacy_hash(scenario_context.get("password"), iterations))


@given("the password is hashed in the legacy format with {iterations:d} iterations")
def step_given_legacy_hash_iterations(context, iterations):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("hashed_password", _legacy_hash(scenario_context.get("password"), iterations))


@given('a stored hash "{stored}"')
def step_given_stored_hash(context, stored):
    get_current_scenario_context(context).store("hashed_password", stored)


@given("the password history size is {size:d}")
def step_given_history_size(context, size):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("history_size", size)


@when("an authentication configuration is built with a password history size of {size:d}")
def step_when_auth_config_history_size(context, size):
    from pydantic import ValidationError

    from archipy.configs.config_template import AuthConfig

    scenario_context = get_current_scenario_context(context)
    try:
        AuthConfig(PASSWORD_HISTORY_SIZE=size)
        scenario_context.store("config_error", None)
    except ValidationError as e:
        scenario_context.store("config_error", e)
