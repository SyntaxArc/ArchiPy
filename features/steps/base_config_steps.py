import os

from behave import given, then, when
from features.environment import TestConfig

from archipy.configs.base_config import BaseConfig
from features.test_helpers import get_current_scenario_context


@given("a custom BaseConfig instance")
def step_given_custom_base_config(context):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    BaseConfig.set_global(config)


@when("the global configuration is set")
def step_when_set_global_config(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    BaseConfig.set_global(test_config)


@then("retrieving global configuration should return the same instance")
def step_then_check_global_config(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    assert BaseConfig.global_config() is test_config


@given("BaseConfig is not initialized globally")
def step_given_no_global_config(context):
    BaseConfig._BaseConfig__global_config = None  # Force reset


@when("retrieving global configuration")
def step_when_get_global_config(context):
    scenario_context = get_current_scenario_context(context)
    try:
        global_config = BaseConfig.global_config()
        scenario_context.store("global_config", global_config)
    except AssertionError as e:
        scenario_context.store("error_message", str(e))


@then('an error should be raised with message "{expected_message}"')
def step_then_check_error_message(context, expected_message):
    scenario_context = get_current_scenario_context(context)
    error_message = scenario_context.get("error_message")
    assert error_message == expected_message, f"Expected: '{expected_message}', but got: '{error_message}'"


@when("the configuration is initialized")
def step_when_config_is_initialized(context):
    scenario_context = get_current_scenario_context(context)
    instance = TestConfig()
    scenario_context.store("instance", instance)


@then('the attribute "{attribute}" should exist')
def step_then_check_attributes(context, attribute):
    scenario_context = get_current_scenario_context(context)
    instance = scenario_context.get("instance")
    assert hasattr(instance, attribute), f"Expected attribute '{attribute}' to exist"


@given('an env file with key "{key}" and value "{value}"')
def step_given_env_file_override(context, key, value):
    scenario_context = get_current_scenario_context(context)
    os.environ[key] = value  # Mock environment variable
    scenario_context.store("env_key", key)
    scenario_context.store("env_value", value)


@when("BaseConfig is initialized")
def step_when_initialize_base_config(context):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    BaseConfig.set_global(config)


@then('the ENVIRONMENT should be "{expected_value}"')
def step_then_check_environment_variable(context, expected_value):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    assert (
        test_config.ENVIRONMENT.name == expected_value
    ), f"Expected '{expected_value}', but got '{test_config.ENVIRONMENT.name}'"
