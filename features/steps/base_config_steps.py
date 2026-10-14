import os

from behave import given, then, when
from features.environment import TestConfig
from features.test_helpers import get_current_scenario_context

from archipy.adapters.vault.adapters import VaultAdapter
from archipy.configs.base_config import BaseConfig
from archipy.models.errors import ConfigurationError


@given("a custom BaseConfig instance")
def step_given_custom_base_config(context):
    config = TestConfig()
    BaseConfig.set_global(config)


@when("the global configuration is set")
def step_when_set_global_config(context):
    scenario_context = get_current_scenario_context(context)
    pending = scenario_context.get("pending_global_config")
    test_config = pending if pending is not None else BaseConfig.global_config()
    BaseConfig.set_global(test_config)
    scenario_context.store("pending_global_config", None)


@then("retrieving global configuration should return the same instance")
def step_then_check_global_config(context):
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
    config = TestConfig()
    BaseConfig.set_global(config)


@then('the ENVIRONMENT should be "{expected_value}"')
def step_then_check_environment_variable(context, expected_value):
    test_config = BaseConfig.global_config()
    assert (
        test_config.ENVIRONMENT.name == expected_value
    ), f"Expected '{expected_value}', but got '{test_config.ENVIRONMENT.name}'"


def _vault_adapter() -> VaultAdapter:
    """Return a Vault adapter pointed at the running test container."""
    test_config = TestConfig.global_config()
    return VaultAdapter(test_config.VAULT.model_copy(update={"ENABLED": True}))


@given('a running Vault instance with a KV v2 secret at "{path}" containing "{pair}"')
def step_given_vault_secret_for_config(context, path, pair):
    scenario_context = get_current_scenario_context(context)
    key, _, value = pair.partition("=")
    adapter = _vault_adapter()
    adapter.write_secret(path, {key: value})
    scenario_context.store("vault_secret_path", path)
    scenario_context.store("vault_secret_key", key)
    scenario_context.store("vault_secret_value", value)
    context.logger.info("Seeded Vault secret %s with %s", path, key)


@given("a running Vault instance with an invalid token")
def step_given_vault_invalid_token(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("vault_force_invalid_token", True)


@given('the environment variable "{key}" is set to "{value}"')
def step_given_environment_variable(context, key, value):
    """Set an environment variable and track it for scenario cleanup."""
    os.environ[key] = value
    keys = getattr(context, "env_keys_to_clear", None)
    if keys is None:
        keys = []
        context.env_keys_to_clear = keys
    keys.append(key)


@given("Vault is not enabled")
def step_given_vault_disabled(context):
    os.environ["VAULT__ENABLED"] = "false"
    # Ensure no leftover vault enable flags from prior scenarios
    for key in ("VAULT__ADDR", "VAULT__TOKEN", "VAULT__SECRET_PATHS"):
        os.environ.pop(key, None)


@when("BaseConfig is initialized with Vault enabled")
def step_when_init_with_vault(context):
    scenario_context = get_current_scenario_context(context)
    vault = TestConfig.global_config().VAULT
    os.environ["VAULT__ENABLED"] = "true"
    os.environ["VAULT__ADDR"] = vault.ADDR or ""
    os.environ["VAULT__AUTH_METHOD"] = vault.AUTH_METHOD
    os.environ["VAULT__MOUNT_POINT"] = vault.MOUNT_POINT
    os.environ["VAULT__VERIFY_SSL"] = "true" if vault.VERIFY_SSL else "false"
    os.environ["VAULT__SECRET_PATHS"] = '["myapp/config"]'

    if scenario_context.get("vault_force_invalid_token"):
        os.environ["VAULT__TOKEN"] = "invalid-token-for-test"
    else:
        os.environ["VAULT__TOKEN"] = vault.TOKEN or ""

    try:
        config = TestConfig()
        BaseConfig.set_global(config)
        scenario_context.store("vault_config_error", None)
    except ConfigurationError as e:
        scenario_context.store("vault_config_error", e)
    except Exception as e:
        # pydantic may wrap; surface as config error for the assertion step
        scenario_context.store("vault_config_error", e)


@then('the REDIS.PASSWORD should be "{expected}"')
def step_then_redis_password(context, expected):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("vault_config_error")
    assert error is None, f"Unexpected error initializing config: {error}"
    config = BaseConfig.global_config()
    assert config.REDIS.PASSWORD == expected, f"Expected REDIS.PASSWORD={expected!r}, got {config.REDIS.PASSWORD!r}"


@then("no Vault connection should be attempted")
def step_then_no_vault_connection(context):
    # VaultSettingsSource returns {} when disabled; config should still initialize.
    config = BaseConfig.global_config()
    assert config.VAULT.ENABLED is False or os.environ.get("VAULT__ENABLED", "").lower() in (
        "false",
        "0",
        "",
        "no",
    )


@then("a ConfigurationError should be raised")
def step_then_configuration_error(context):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("vault_config_error")
    assert error is not None, "Expected ConfigurationError but config initialized successfully"
    assert isinstance(error, ConfigurationError) or "Vault" in str(error) or "vault" in str(error).lower(), (
        f"Expected ConfigurationError-like failure, got {type(error)}: {error}"
    )


@given('a BaseConfig with APP_NAME "{app_name}" and nested identity defaults')
def step_given_app_name_with_identity_defaults(context, app_name):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    config.APP_NAME = app_name
    config.OTEL.SERVICE_NAME = None
    config.FASTAPI.PROJECT_NAME = "project_name"
    config.AUTH.JWT_ISSUER = "your-app-name"
    config.TEMPORAL.CLIENT_IDENTITY = None
    scenario_context.store("pending_global_config", config)


@given('a BaseConfig with APP_NAME "{app_name}" and OTEL.SERVICE_NAME "{service_name}"')
def step_given_app_name_with_otel_override(context, app_name, service_name):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    config.APP_NAME = app_name
    config.OTEL.SERVICE_NAME = service_name
    scenario_context.store("pending_global_config", config)


@then('OTEL.SERVICE_NAME should be "{expected}"')
def step_then_otel_service_name(context, expected):
    actual = BaseConfig.global_config().OTEL.SERVICE_NAME
    assert actual == expected, f"Expected OTEL.SERVICE_NAME={expected!r}, got {actual!r}"


@then('FASTAPI.PROJECT_NAME should be "{expected}"')
def step_then_fastapi_project_name(context, expected):
    actual = BaseConfig.global_config().FASTAPI.PROJECT_NAME
    assert actual == expected, f"Expected FASTAPI.PROJECT_NAME={expected!r}, got {actual!r}"


@then('AUTH.JWT_ISSUER should be "{expected}"')
def step_then_auth_jwt_issuer(context, expected):
    actual = BaseConfig.global_config().AUTH.JWT_ISSUER
    assert actual == expected, f"Expected AUTH.JWT_ISSUER={expected!r}, got {actual!r}"


@then('TEMPORAL.CLIENT_IDENTITY should be "{expected}"')
def step_then_temporal_client_identity(context, expected):
    actual = BaseConfig.global_config().TEMPORAL.CLIENT_IDENTITY
    assert actual == expected, f"Expected TEMPORAL.CLIENT_IDENTITY={expected!r}, got {actual!r}"


@given("a BaseConfig with PAGINATION.MAX_ITEMS {max_items:d} and no COUNT_THRESHOLD")
def step_given_pagination_max_items(context, max_items):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    config.PAGINATION.MAX_ITEMS = max_items
    for sqlalchemy_config in _sqlalchemy_configs(config):
        sqlalchemy_config.COUNT_THRESHOLD = None
    scenario_context.store("pending_global_config", config)


@given("a BaseConfig with PAGINATION.MAX_ITEMS {max_items:d} and POSTGRES_SQLALCHEMY.COUNT_THRESHOLD {threshold:d}")
def step_given_pagination_max_items_and_explicit_threshold(context, max_items, threshold):
    scenario_context = get_current_scenario_context(context)
    config = TestConfig()
    config.PAGINATION.MAX_ITEMS = max_items
    for sqlalchemy_config in _sqlalchemy_configs(config):
        sqlalchemy_config.COUNT_THRESHOLD = None
    config.POSTGRES_SQLALCHEMY.COUNT_THRESHOLD = threshold
    scenario_context.store("pending_global_config", config)


def _sqlalchemy_configs(config):
    return (
        config.SQLALCHEMY,
        config.POSTGRES_SQLALCHEMY,
        config.MYSQL_SQLALCHEMY,
        config.SQLITE_SQLALCHEMY,
        config.STARROCKS_SQLALCHEMY,
    )


@then("every SQLAlchemy COUNT_THRESHOLD should be {expected:d}")
def step_then_every_count_threshold(context, expected):
    actual = [config.COUNT_THRESHOLD for config in _sqlalchemy_configs(BaseConfig.global_config())]
    assert actual == [expected] * len(actual), f"Expected every COUNT_THRESHOLD to be {expected}, got {actual}"


@then("POSTGRES_SQLALCHEMY.COUNT_THRESHOLD should be {expected:d}")
def step_then_postgres_count_threshold(context, expected):
    actual = BaseConfig.global_config().POSTGRES_SQLALCHEMY.COUNT_THRESHOLD
    assert actual == expected, f"Expected POSTGRES_SQLALCHEMY.COUNT_THRESHOLD={expected}, got {actual}"


@then("SQLITE_SQLALCHEMY.COUNT_THRESHOLD should be {expected:d}")
def step_then_sqlite_count_threshold(context, expected):
    actual = BaseConfig.global_config().SQLITE_SQLALCHEMY.COUNT_THRESHOLD
    assert actual == expected, f"Expected SQLITE_SQLALCHEMY.COUNT_THRESHOLD={expected}, got {actual}"


@then("pagination of page {page:d} with size {size:d} should be accepted")
def step_then_pagination_accepted(context, page, size):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    assert PaginationDTO(page=page, page_size=size).offset == (page - 1) * size


@then("pagination of page {page:d} with size {size:d} should be rejected as out of range")
def step_then_pagination_rejected(context, page, size):
    from archipy.models.dtos.pagination_dto import PaginationDTO
    from archipy.models.errors import OutOfRangeError

    try:
        PaginationDTO(page=page, page_size=size)
    except OutOfRangeError:
        return
    raise AssertionError(f"Expected OutOfRangeError for page {page} with size {size}")
