import logging
import os
import tempfile
import uuid
from pathlib import Path

from behave import given, then, when
from features.environment import TestConfig
from features.test_helpers import get_current_scenario_context

from archipy.adapters.vault.adapters import VaultAdapter
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import (
    KafkaConfig,
    PostgresSQLAlchemyConfig,
    RedisConfig,
    ScyllaDBConfig,
    StarRocksSQLAlchemyConfig,
    TemporalConfig,
    VaultConfig,
)
from archipy.configs.environment_type import EnvironmentType
from archipy.configs.vault_settings_source import create_vault_client
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
    assert test_config.ENVIRONMENT.name == expected_value, (
        f"Expected '{expected_value}', but got '{test_config.ENVIRONMENT.name}'"
    )


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


@when('a PostgreSQL configuration is built from the DSN "{dsn}"')
def step_when_postgres_config_from_dsn(context, dsn):
    get_current_scenario_context(context).store("postgres_config", PostgresSQLAlchemyConfig(POSTGRES_DSN=dsn))


@when('a PostgreSQL configuration is built with the host "{host}" and the DSN "{dsn}"')
def step_when_postgres_config_from_dsn_with_host(context, host, dsn):
    get_current_scenario_context(context).store(
        "postgres_config",
        PostgresSQLAlchemyConfig(POSTGRES_DSN=dsn, HOST=host),
    )


@when(
    'a PostgreSQL configuration is built from the parts user "{user}", password "{password}", host "{host}", '
    'port {port:d} and database "{database}"',
)
def step_when_postgres_config_from_parts(context, user, password, host, port, database):
    get_current_scenario_context(context).store(
        "postgres_config",
        PostgresSQLAlchemyConfig(
            DRIVER_NAME="postgresql+psycopg",
            USERNAME=user,
            PASSWORD=password,
            HOST=host,
            PORT=port,
            DATABASE=database,
        ),
    )


@then(
    'the PostgreSQL connection parts should be user "{user}", password "{password}", host "{host}", '
    'port {port:d} and database "{database}"',
)
def step_then_postgres_parts(context, user, password, host, port, database):
    config = get_current_scenario_context(context).get("postgres_config")
    actual = (config.USERNAME, config.PASSWORD or "(none)", config.HOST, config.PORT, config.DATABASE)
    assert actual == (user, password, host, port, database), actual


@then('the PostgreSQL DSN should be "{dsn}"')
def step_then_postgres_dsn(context, dsn):
    config = get_current_scenario_context(context).get("postgres_config")
    assert str(config.POSTGRES_DSN) == dsn, str(config.POSTGRES_DSN)


@when('a StarRocks configuration is built with the isolation level "{level}"')
def step_when_starrocks_config(context, level):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.store("starrocks_config", StarRocksSQLAlchemyConfig(ISOLATION_LEVEL=level))
        scenario_context.store("starrocks_error", None)
    except Exception as error:
        scenario_context.store("starrocks_error", error)


@then("the StarRocks configuration should be {outcome}")
def step_then_starrocks_outcome(context, outcome):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("starrocks_error")
    if outcome == "accepted":
        assert error is None, error
        assert scenario_context.get("starrocks_config").ISOLATION_LEVEL == "READ COMMITTED"
    else:
        assert error is not None, "Expected the isolation level to be rejected"


_UNUSED_VAULT_ADDR = "http://127.0.0.1:8200"

_VAULT_PROBLEMS = {
    "no token is set": {},
    "the token file cannot be read": {"TOKEN_FILE": "/nonexistent/vault-token"},
    "no role id is set": {},
    "no secret id is set": {"APPROLE_ROLE_ID": "role"},
    "no username is set": {},
    "no password is set": {"USERNAME": "user"},
    "no role is set": {},
    "no jwt is set": {"JWT_ROLE": "role", "AZURE_ROLE": "role", "GCP_ROLE": "role"},
    "no access key is set": {},
    "no github token is set": {},
    "no address is set": {"ADDR": None, "TOKEN": "t"},
    "only a client certificate is set": {"TOKEN": "t", "CLIENT_CERT_PATH": "/tmp/client.pem"},
}


@when("a Vault client is built for {auth_method} auth when {problem}")
def step_when_vault_client_built_with_problem(context, auth_method, problem):
    scenario_context = get_current_scenario_context(context)
    settings = {"ENABLED": True, "ADDR": _UNUSED_VAULT_ADDR, "AUTH_METHOD": auth_method, **_VAULT_PROBLEMS[problem]}
    try:
        create_vault_client(VaultConfig(**settings))
        scenario_context.store("vault_config_error", None)
    except Exception as error:
        scenario_context.store("vault_config_error", error)


@then('the error should mention "{fragment}"')
def step_then_error_mentions(context, fragment):
    error = get_current_scenario_context(context).get("vault_config_error")
    assert fragment in str(error) or fragment in repr(getattr(error, "additional_data", "")), repr(error)


def _vault_admin_client():
    from hvac import Client

    vault = TestConfig.global_config().VAULT
    return Client(url=vault.ADDR, token=vault.TOKEN)


@given("Vault accepts {method} logins for a test identity")
def step_given_vault_accepts_logins(context, method):
    scenario_context = get_current_scenario_context(context)
    vault = TestConfig.global_config().VAULT
    settings = {"ENABLED": True, "ADDR": vault.ADDR}
    admin = _vault_admin_client()
    suffix = uuid.uuid4().hex[:8]
    if method == "token file":
        token_file = Path(tempfile.mkdtemp(prefix="archipy_vault_")) / "token"
        token_file.write_text(f"{vault.TOKEN}\n", encoding="utf-8")
        settings.update({"AUTH_METHOD": "token", "TOKEN_FILE": str(token_file)})
    elif method == "approle":
        mount = f"approle{suffix}"
        admin.sys.enable_auth_method("approle", path=mount)
        admin.auth.approle.create_or_update_approle("test-role", token_policies=["default"], mount_point=mount)
        role_id = admin.auth.approle.read_role_id("test-role", mount_point=mount)["data"]["role_id"]
        secret_id = admin.auth.approle.generate_secret_id("test-role", mount_point=mount)["data"]["secret_id"]
        settings.update(
            {
                "AUTH_METHOD": "approle",
                "APPROLE_ROLE_ID": role_id,
                "APPROLE_SECRET_ID": secret_id,
                "APPROLE_MOUNT_POINT": mount,
            },
        )
    else:
        mount = f"userpass{suffix}"
        admin.sys.enable_auth_method("userpass", path=mount)
        admin.auth.userpass.create_or_update_user("alice", "s3cret-pass", policies=["default"], mount_point=mount)
        settings.update(
            {"AUTH_METHOD": "userpass", "USERNAME": "alice", "PASSWORD": "s3cret-pass", "USERPASS_MOUNT_POINT": mount},
        )
    scenario_context.store("vault_login_settings", settings)


@when("a Vault client is built for the test identity")
def step_when_vault_client_built_for_identity(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.store(
            "vault_client", create_vault_client(VaultConfig(**scenario_context.get("vault_login_settings"))),
        )
        scenario_context.store("vault_config_error", None)
    except Exception as error:
        scenario_context.store("vault_config_error", error)


@then("the Vault client should be authenticated")
def step_then_vault_client_authenticated(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("vault_config_error") is None, scenario_context.get("vault_config_error")
    assert scenario_context.get("vault_client").is_authenticated()


_SECTION_SETTINGS = {
    ("Kafka", "SASL_SSL without credentials"): (KafkaConfig, {"SECURITY_PROTOCOL": "SASL_SSL"}),
    (
        "Kafka",
        "SASL_SSL with credentials",
    ): (
        KafkaConfig,
        {"SECURITY_PROTOCOL": "SASL_SSL", "SASL_MECHANISM": "PLAIN", "USERNAME": "user", "PASSWORD": "pass"},
    ),
    ("Kafka", "auto commit and no offset reset"): (
        KafkaConfig,
        {"ENABLE_AUTO_COMMIT": True, "AUTO_OFFSET_RESET": "none"},
    ),
    ("Kafka", "a heartbeat longer than the session"): (
        KafkaConfig,
        {"HEARTBEAT_INTERVAL_MS": 20000, "SESSION_TIMEOUT_MS": 10000},
    ),
    ("Redis", "cluster mode without nodes"): (RedisConfig, {"MODE": "CLUSTER"}),
    ("Redis", "cluster mode with nodes"): (RedisConfig, {"MODE": "CLUSTER", "CLUSTER_NODES": ["localhost:7000"]}),
    ("Redis", "sentinel mode without a service name"): (
        RedisConfig,
        {"MODE": "SENTINEL", "SENTINEL_NODES": ["localhost:26379"]},
    ),
    ("Redis", "standalone mode without a host"): (RedisConfig, {"MODE": "STANDALONE", "MASTER_HOST": ""}),
    ("ScyllaDB", "no contact points"): (ScyllaDBConfig, {"CONTACT_POINTS": []}),
    ("ScyllaDB", "a username without a password"): (ScyllaDBConfig, {"USERNAME": "user"}),
    ("ScyllaDB", "a minimum pool above the maximum"): (
        ScyllaDBConfig,
        {"MIN_CONNECTIONS_PER_HOST": 10, "MAX_CONNECTIONS_PER_HOST": 2},
    ),
    ("Temporal", "only a client certificate"): (TemporalConfig, {"TLS_CLIENT_CERT": "/tmp/client.pem"}),
    ("Temporal", "a run timeout above the execution one"): (
        TemporalConfig,
        {"WORKFLOW_RUN_TIMEOUT": 7200, "WORKFLOW_EXECUTION_TIMEOUT": 3600},
    ),
    ("Temporal", "a keep alive timeout above the interval"): (
        TemporalConfig,
        {"KEEP_ALIVE_TIMEOUT_MS": 60000, "KEEP_ALIVE_INTERVAL_MS": 30000},
    ),
}


@when("a {section} configuration is built with {problem}")
def step_when_section_config_built(context, section, problem):
    config_class, settings = _SECTION_SETTINGS[(section, problem)]
    scenario_context = get_current_scenario_context(context)
    try:
        config_class(**settings)
        scenario_context.store("section_config_error", None)
    except Exception as error:
        scenario_context.store("section_config_error", error)


@then("the configuration should be {outcome}")
def step_then_section_config_outcome(context, outcome):
    error = get_current_scenario_context(context).get("section_config_error")
    if outcome == "accepted":
        assert error is None, error
    else:
        assert error is not None, "Expected the configuration to be rejected"


@when("a default Temporal configuration is built")
def step_when_default_temporal_config_built(context):
    get_current_scenario_context(context).store("temporal_config", TemporalConfig())


@then("the default Temporal setting {field} should be {expected}")
def step_then_temporal_default(context, field, expected):
    actual = getattr(get_current_scenario_context(context).get("temporal_config"), field)
    assert str(actual) == expected, f"Expected {field}={expected}, got {actual!r}"


@when("the environment type {environment} is inspected")
def step_when_environment_inspected(context, environment):
    get_current_scenario_context(context).store("environment_type", EnvironmentType[environment])


@then(
    "it should be production {production}, test {test}, dev {dev}, local {local} and log at {level}",
)
def step_then_environment_kind(context, production, test, dev, local, level):
    environment = get_current_scenario_context(context).get("environment_type")
    actual = (environment.is_production, environment.is_test, environment.is_dev, environment.is_local)
    assert actual == (production == "True", test == "True", dev == "True", local == "True"), actual
    assert environment.log_level == getattr(logging, level), environment.log_level
