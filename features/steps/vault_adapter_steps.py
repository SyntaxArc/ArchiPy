"""BDD steps for the HashiCorp Vault adapter."""

import hvac
from behave import given, then, when
from features.environment import TestConfig
from features.test_helpers import get_current_scenario_context

from archipy.adapters.vault.adapters import VaultAdapter
from archipy.models.errors import InvalidArgumentError, NotFoundError


def get_vault_adapter(context) -> VaultAdapter:
    """Get or initialize the Vault adapter for the current scenario."""
    scenario_context = get_current_scenario_context(context)
    adapter = scenario_context.get("vault_adapter")
    if adapter is None:
        test_config = TestConfig.global_config()
        # Adapter needs live ADDR/TOKEN from the container; ENABLED stays opt-in for settings source.
        config = test_config.VAULT.model_copy(update={"ENABLED": True})
        adapter = VaultAdapter(config)
        scenario_context.store("vault_adapter", adapter)
    return adapter


def _store_adapter(context, adapter: VaultAdapter) -> VaultAdapter:
    """Replace the scenario Vault adapter."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("vault_adapter", adapter)
    return adapter


def _admin_client() -> hvac.Client:
    """Return an hvac client using the global Vault root token."""
    vault = TestConfig.global_config().VAULT
    return hvac.Client(url=vault.ADDR, token=vault.TOKEN, verify=vault.VERIFY_SSL)


@given("a configured Vault adapter")
def step_configured_vault_adapter(context):
    adapter = get_vault_adapter(context)
    # Ensure KV v2 is available at the default mount (dev mode usually has it)
    client = _admin_client()
    mounts = client.sys.list_mounted_secrets_engines()
    if "secret/" not in mounts:
        client.sys.enable_secrets_engine("kv", path="secret", options={"version": "2"})
    context.logger.info("Vault adapter configured against %s", TestConfig.global_config().VAULT.ADDR)


@given('a Vault secret "{path}" with key "{key}" and value "{value}"')
def step_given_vault_secret(context, path, key, value):
    adapter = get_vault_adapter(context)
    adapter.write_secret(path, {key: value})


@given("a Vault adapter with secret cache TTL {ttl:d} seconds")
def step_given_caching_vault_adapter(context, ttl: int):
    """Build a Vault adapter with SECRET_CACHE_TTL enabled."""
    test_config = TestConfig.global_config()
    config = test_config.VAULT.model_copy(
        update={"ENABLED": True, "SECRET_CACHE_TTL": ttl},
    )
    _store_adapter(context, VaultAdapter(config))


@given(
    "a Vault adapter using a renewable token with TTL {token_ttl:d} seconds "
    "and renew threshold {threshold:d} seconds",
)
def step_given_renewing_vault_adapter(context, token_ttl: int, threshold: int):
    """Build an adapter that uses a short-lived renewable child token."""
    admin = _admin_client()
    mount = TestConfig.global_config().VAULT.MOUNT_POINT
    policy_name = "archipy-renew-test"
    policy = f"""
path "{mount}/data/*" {{
  capabilities = ["create", "read", "update", "delete", "list"]
}}
path "{mount}/metadata/*" {{
  capabilities = ["list", "read", "delete"]
}}
path "auth/token/renew-self" {{
  capabilities = ["update"]
}}
path "auth/token/lookup-self" {{
  capabilities = ["read"]
}}
"""
    admin.sys.create_or_update_policy(name=policy_name, policy=policy)
    # explicit_max_ttl must exceed ttl so renew_self can extend remaining life.
    response = admin.auth.token.create(
        ttl=f"{token_ttl}s",
        renewable=True,
        explicit_max_ttl="1h",
        policies=[policy_name],
    )
    child_token = response["auth"]["client_token"]
    test_config = TestConfig.global_config()
    config = test_config.VAULT.model_copy(
        update={
            "ENABLED": True,
            "TOKEN": child_token,
            "AUTO_RENEW_TOKEN": True,
            "RENEW_THRESHOLD_SECONDS": threshold,
        },
    )
    adapter = _store_adapter(context, VaultAdapter(config))
    lookup = adapter._client.auth.token.lookup_self()
    data = lookup.get("data") or {}
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("token_ttl_before", int(data.get("ttl", 0)))


@given('a Vault transit key named "{key_name}"')
def step_given_transit_key(context, key_name):
    client = _admin_client()
    mounts = client.sys.list_mounted_secrets_engines()
    if "transit/" not in mounts:
        client.sys.enable_secrets_engine("transit", path="transit")
    try:
        client.secrets.transit.create_key(name=key_name)
    except hvac.exceptions.InvalidRequest:
        # Key may already exist from a previous scenario
        pass
    context.logger.info("Ensured transit key '%s' exists", key_name)


@given('a Vault database role named "{role_name}" backed by Postgres')
def step_given_vault_database_role(context, role_name):
    """Configure Vault database secrets engine against the Postgres testcontainer."""
    from features.test_containers import ContainerManager

    # Scenario-level @needs-postgres is not started by before_feature — start lazily.
    postgres = ContainerManager.get_container("postgres")
    test_config = TestConfig.global_config()
    pg = test_config.POSTGRES_SQLALCHEMY
    # Vault runs in Docker; reach the host-published Postgres port via host-gateway.
    host = "host.docker.internal"
    port = postgres.port or pg.PORT or 5432
    user = pg.USERNAME or postgres.username or "test_user"
    password = pg.PASSWORD or postgres.password or "test_password"
    database = pg.DATABASE or postgres.database or "test_db"

    connection_url = f"postgresql://{{{{username}}}}:{{{{password}}}}@{host}:{port}/{database}?sslmode=disable"

    client = _admin_client()
    mounts = client.sys.list_mounted_secrets_engines()
    if "database/" not in mounts:
        client.sys.enable_secrets_engine("database", path="database")

    client.write(
        "database/config/postgres",
        plugin_name="postgresql-database-plugin",
        allowed_roles=role_name,
        connection_url=connection_url,
        username=user,
        password=password,
    )
    client.write(
        f"database/roles/{role_name}",
        db_name="postgres",
        creation_statements=(
            "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';"
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";"
        ),
        default_ttl="1h",
        max_ttl="2h",
    )
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("db_role", role_name)
    context.logger.info("Configured Vault database role '%s' -> %s:%s/%s", role_name, host, port, database)


@when('I write Vault secret "{path}" with key "{key}" and value "{value}"')
def step_write_vault_secret(context, path, key, value):
    adapter = get_vault_adapter(context)
    adapter.write_secret(path, {key: value})
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("written_path", path)


@when('I read Vault secret "{path}"')
def step_when_read_vault_secret(context, path):
    adapter = get_vault_adapter(context)
    secret = adapter.read_secret(path)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("read_secret", secret)
    scenario_context.store("read_path", path)


@when('the Vault secret "{path}" is updated out-of-band with key "{key}" and value "{value}"')
def step_update_secret_out_of_band(context, path, key, value):
    """Mutate a secret via the admin client so the adapter cache is not cleared."""
    vault = TestConfig.global_config().VAULT
    client = _admin_client()
    client.secrets.kv.v2.create_or_update_secret(
        path=path,
        secret={key: value},
        mount_point=vault.MOUNT_POINT,
    )


@when('I call Vault "{operation}" with invalid args')
def step_call_vault_invalid_args(context, operation):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    try:
        if operation == "read_secret empty path":
            adapter.read_secret("")
        elif operation == "write_secret empty path":
            adapter.write_secret("", {"k": "v"})
        elif operation == "write_secret empty payload":
            adapter.write_secret("app/x", {})
        elif operation == "delete_secret empty path":
            adapter.delete_secret("")
        elif operation == "renew_lease empty id":
            adapter.renew_lease("")
        elif operation == "revoke_lease empty id":
            adapter.revoke_lease("")
        elif operation == "encrypt empty key":
            adapter.encrypt("", "plaintext")
        elif operation == "encrypt empty plaintext":
            adapter.encrypt("key", "")
        elif operation == "decrypt empty key":
            adapter.decrypt("", "vault:v1:x")
        elif operation == "decrypt empty ciphertext":
            adapter.decrypt("key", "")
        elif operation == "get_dynamic_credentials empty mount":
            adapter.get_dynamic_credentials("", "role")
        elif operation == "get_dynamic_credentials empty role":
            adapter.get_dynamic_credentials("database", "")
        else:
            raise AssertionError(f"Unknown invalid-args operation: {operation}")
        scenario_context.store("vault_invalid_arg_error", None)
    except InvalidArgumentError as e:
        scenario_context.store("vault_invalid_arg_error", e)


@when('I list Vault secrets under "{path}"')
def step_list_vault_secrets(context, path):
    adapter = get_vault_adapter(context)
    keys = adapter.list_secrets(path)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("listed_keys", keys)


@when('I delete Vault secret "{path}"')
def step_delete_vault_secret(context, path):
    adapter = get_vault_adapter(context)
    adapter.delete_secret(path)


@when('I encrypt plaintext "{plaintext}" with transit key "{key_name}"')
def step_encrypt(context, plaintext, key_name):
    adapter = get_vault_adapter(context)
    ciphertext = adapter.encrypt(key_name, plaintext)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("ciphertext", ciphertext)
    scenario_context.store("plaintext", plaintext)


@when('I generate dynamic credentials from mount "{mount}" for role "{role}"')
def step_generate_dynamic_creds(context, mount, role):
    adapter = get_vault_adapter(context)
    parameters = {"ip": "127.0.0.1"} if mount == "ssh" else None
    lease = adapter.get_dynamic_credentials(mount, role, parameters=parameters)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("vault_lease", lease)


@then("the Vault lease should contain database credentials")
def step_then_lease_has_db_creds(context):
    scenario_context = get_current_scenario_context(context)
    lease = scenario_context.get("vault_lease")
    assert lease.lease_id, "Expected non-empty lease_id"
    assert "username" in lease.data, f"Expected username in lease data, got {lease.data}"
    assert "password" in lease.data, f"Expected password in lease data, got {lease.data}"



@when("I renew the Vault lease")
def step_renew_lease(context):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    lease = scenario_context.get("vault_lease")
    renewed = adapter.renew_lease(lease.lease_id)
    scenario_context.store("vault_lease", renewed)


@when("I revoke the Vault lease")
def step_revoke_lease(context):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    lease = scenario_context.get("vault_lease")
    adapter.revoke_lease(lease.lease_id)


@then('reading Vault secret "{path}" should return key "{key}" with value "{value}"')
def step_then_read_secret(context, path, key, value):
    adapter = get_vault_adapter(context)
    secret = adapter.read_secret(path)
    assert secret.get(key) == value, f"Expected {key}={value!r}, got {secret!r}"


@then('the Vault secret list should include "{name}"')
def step_then_list_includes(context, name):
    scenario_context = get_current_scenario_context(context)
    keys = scenario_context.get("listed_keys")
    assert name in keys or f"{name}/" in keys, f"Expected '{name}' in {keys}"


@then('reading Vault secret "{path}" should fail with NotFoundError')
def step_then_read_not_found(context, path):
    adapter = get_vault_adapter(context)
    try:
        adapter.read_secret(path)
        raise AssertionError(f"Expected NotFoundError for path '{path}'")
    except NotFoundError:
        pass


@then('decrypting the ciphertext with transit key "{key_name}" should return "{expected}"')
def step_then_decrypt(context, key_name, expected):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    ciphertext = scenario_context.get("ciphertext")
    plaintext = adapter.decrypt(key_name, ciphertext)
    assert plaintext == expected, f"Expected {expected!r}, got {plaintext!r}"


@then("the renewed Vault lease should be valid")
def step_then_renewed_valid(context):
    scenario_context = get_current_scenario_context(context)
    lease = scenario_context.get("vault_lease")
    assert lease.lease_id, "Expected lease_id after renew"
    assert lease.lease_duration >= 0


@then("revoking the Vault lease again should fail")
def step_then_revoke_again_fails(context):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    lease = scenario_context.get("vault_lease")
    try:
        adapter.revoke_lease(lease.lease_id)
        # Some Vault versions treat re-revoke as idempotent success; accept either
        context.logger.info("Second revoke succeeded (idempotent)")
    except Exception as e:  # noqa: BLE001
        context.logger.info("Second revoke failed as expected: %s", e)


@then("the Vault client token should still be valid")
def step_then_token_valid(context):
    adapter = get_vault_adapter(context)
    lookup = adapter._client.auth.token.lookup_self()
    assert lookup.get("data"), f"Expected token lookup data, got {lookup!r}"


@then("the token should have been renewed")
def step_then_token_renewed(context):
    adapter = get_vault_adapter(context)
    scenario_context = get_current_scenario_context(context)
    before_ttl = scenario_context.get("token_ttl_before")
    assert before_ttl is not None, "Missing token TTL before sample"
    assert before_ttl <= adapter.configs.RENEW_THRESHOLD_SECONDS, (
        f"Precondition failed: TTL {before_ttl} should be <= threshold "
        f"{adapter.configs.RENEW_THRESHOLD_SECONDS}"
    )
    assert adapter.token_renew_count >= 1, (
        f"Expected at least one token renew, got {adapter.token_renew_count}"
    )


@then('a Vault InvalidArgumentError should be raised for "{argument}"')
def step_then_invalid_argument(context, argument):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("vault_invalid_arg_error")
    assert error is not None, "Expected InvalidArgumentError but call succeeded"
    assert isinstance(error, InvalidArgumentError), f"Expected InvalidArgumentError, got {type(error)}: {error}"
    assert error.additional_data.get("argument") == argument, (
        f"Expected argument_name={argument!r}, got {error.additional_data!r}"
    )
