# features/steps/keycloak_auth_steps.py
from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context, safe_run_async

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter


def get_keycloak_adapter(context: Context) -> AsyncKeycloakAdapter | KeycloakAdapter:
    """Get or initialize the appropriate Keycloak adapter based on scenario tags."""
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:
        if not hasattr(scenario_context, "async_adapter") or scenario_context.async_adapter is None:
            test_config = scenario_context.get("test_config")
            scenario_context.async_adapter = AsyncKeycloakAdapter(test_config.KEYCLOAK)
        return scenario_context.async_adapter
    if not hasattr(scenario_context, "adapter") or scenario_context.adapter is None:
        test_config = scenario_context.get("test_config")
        scenario_context.adapter = KeycloakAdapter(test_config.KEYCLOAK)
    return scenario_context.adapter


@given('a Keycloak realm "{realm}" exists')
def step_realm_exists(context: Context, realm: str) -> None:
    """Assume a Keycloak realm exists."""
    context.logger.info(f"Assuming Keycloak realm '{realm}' exists")


@given('a client "{client_id}" exists')
def step_client_exists(context: Context, client_id: str) -> None:
    """Assume a client exists in Keycloak."""
    context.logger.info(f"Assuming client '{client_id}' exists")


@given('the "VERIFY_PROFILE" required action is disabled in realm "{realm}"')
def step_verify_profile_disabled(context: Context, realm: str) -> None:
    """Assume the VERIFY_PROFILE required action is disabled in the specified realm."""
    context.logger.info(f"Assuming 'VERIFY_PROFILE' required action is disabled in realm '{realm}'")


@given('client "{client_id}" has client authentication enabled')
def step_client_auth_enabled(context: Context, client_id: str) -> None:
    """Assume a client has client authentication enabled."""
    context.logger.info(f"Assuming client '{client_id}' has client authentication enabled")


@given('client "{client_id}" has service accounts roles enabled')
def step_service_accounts_enabled(context: Context, client_id: str) -> None:
    """Assume a client has service accounts roles enabled."""
    context.logger.info(f"Assuming client '{client_id}' has service accounts roles enabled")


@given('client "{client_id}" has "{role1}" and "{role2}" service account role access')
def step_service_account_roles(context: Context, client_id: str, role1: str, role2: str) -> None:
    """Assume a client has the specified service account role access."""
    context.logger.info(f"Assuming client '{client_id}' has '{role1}' and '{role2}' service account role access")


@given("a configured {adapter_type} Keycloak adapter")
def step_configured_adapter(context: Context, adapter_type: str) -> None:
    """Configure a Keycloak adapter of the specified type."""
    get_keycloak_adapter(context)
    context.logger.info(f"{adapter_type.capitalize()} Keycloak adapter configured")


@given('a user exists with username "{username}" and password "{password}"')
def step_user_exists(context: Context, username: str, password: str) -> None:
    """Create a user with the specified username and password if it doesn't already exist."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_data = {
        "username": username,
        "enabled": True,
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }

    try:
        if is_async:

            async def create_user_async(context: Context) -> None:
                user = await adapter.get_user_by_username(username)
                if user:
                    await adapter.delete_user(user["id"])
                user_id = await adapter.create_user(user_data)
                scenario_context.store(f"user_id_{username}", user_id)

            safe_run_async(create_user_async)(context)
        else:
            user = adapter.get_user_by_username(username)
            if user:
                adapter.delete_user(user["id"])
            user_id = adapter.create_user(user_data)
            scenario_context.store(f"user_id_{username}", user_id)
        context.logger.info(f"Created user {username} with ID {scenario_context.get(f'user_id_{username}')}")
    except Exception:
        context.logger.exception(f"Failed to create user {username}")
        raise


@given('I have a valid token for "{username}" with password "{password}" using {adapter_type} adapter')
def step_have_valid_token(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Obtain a valid token for the specified username and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        async def get_token_async(context: Context) -> None:
            token_response = await adapter.get_token(username, password)
            scenario_context.store(f"token_response_{username}", token_response)

        safe_run_async(get_token_async)(context)
    else:
        token_response = adapter.get_token(username, password)
        scenario_context.store(f"token_response_{username}", token_response)
    context.logger.info(f"Obtained initial token for {username}")


# Action steps
@when('I request a token with username "{username}" and password "{password}" using {adapter_type} adapter')
def step_request_token(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Request a token with the specified username and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            async def request_token_async(context: Context) -> None:
                token_response = await adapter.get_token(username, password)
                scenario_context.store("latest_token_response", token_response)

            safe_run_async(request_token_async)(context)
        else:
            token_response = adapter.get_token(username, password)
            scenario_context.store("latest_token_response", token_response)
        context.logger.info(f"Requested token for {username}")
    except Exception as e:
        scenario_context.store("token_error", str(e))
        context.logger.exception("Token request failed")


@when("I refresh the token using {adapter_type} adapter")
def step_refresh_token(context: Context, adapter_type: str) -> None:
    """Refresh the token using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next(s for s in reversed(context.scenario.steps) if "have a valid token" in s.name)
    username = prev_step.name.split('"')[1]
    refresh_token = scenario_context.get(f"token_response_{username}")["refresh_token"]

    if is_async:

        async def refresh_token_async(context: Context) -> None:
            new_token = await adapter.refresh_token(refresh_token)
            scenario_context.store("latest_token_response", new_token)

        safe_run_async(refresh_token_async)(context)
    else:
        new_token = adapter.refresh_token(refresh_token)
        scenario_context.store("latest_token_response", new_token)
    context.logger.info(f"Refreshed token for {username}")


@when("I request user info with the token using {adapter_type} adapter")
def step_request_user_info(context: Context, adapter_type: str) -> None:
    """Request user info using the token and the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next(s for s in reversed(context.scenario.steps) if "have a valid token" in s.name)
    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        async def get_userinfo_async(context: Context) -> None:
            user_info = await adapter.get_userinfo(access_token)
            scenario_context.store("latest_user_info", user_info)

        safe_run_async(get_userinfo_async)(context)
    else:
        user_info = adapter.get_userinfo(access_token)
        scenario_context.store("latest_user_info", user_info)
    context.logger.info(f"Requested user info for {username}")


@when("I logout the user using {adapter_type} adapter")
def step_logout_user(context: Context, adapter_type: str) -> None:
    """Logout the user using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next(s for s in reversed(context.scenario.steps) if "have a valid token" in s.name)
    username = prev_step.name.split('"')[1]
    refresh_token = scenario_context.get(f"token_response_{username}")["refresh_token"]

    if is_async:

        async def logout_async(context: Context) -> None:
            result = await adapter.logout(refresh_token)
            scenario_context.store("logout_result", result)

        safe_run_async(logout_async)(context)
    else:
        result = adapter.logout(refresh_token)
        scenario_context.store("logout_result", result)
    context.logger.info(f"Logged out user {username}")


@when("I validate the token using {adapter_type} adapter")
def step_validate_token(context: Context, adapter_type: str) -> None:
    """Validate the token using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next(s for s in reversed(context.scenario.steps) if "have a valid token" in s.name)
    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        async def validate_async(context: Context) -> None:
            result = await adapter.introspect_token(access_token)
            scenario_context.store("validation_result", result)

        safe_run_async(validate_async)(context)
    else:
        result = adapter.introspect_token(access_token)
        scenario_context.store("validation_result", result)
    context.logger.info(f"Validated token for {username}")


# Verification steps
@then("the {adapter_type} token request should succeed")
def step_token_request_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the token request succeeded."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert token_response is not None, f"{adapter_type.capitalize()} token request failed"
    assert "access_token" in token_response, "Access token missing"
    context.logger.info(f"{adapter_type.capitalize()} token request verified")


@then("the {adapter_type} token refresh should succeed")
def step_token_refresh_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the token refresh succeeded."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert token_response is not None, f"{adapter_type.capitalize()} token refresh failed"
    assert "access_token" in token_response, "Refreshed access token missing"
    context.logger.info(f"{adapter_type.capitalize()} token refresh verified")


@then('the {adapter_type} token response should contain "{field1}" and "{field2}"')
def step_token_response_contains(context: Context, adapter_type: str, field1: str, field2: str) -> None:
    """Verify that the token response contains the specified fields."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert field1 in token_response, f"{field1} missing from {adapter_type} token response"
    assert field2 in token_response, f"{field2} missing from {adapter_type} token response"
    context.logger.info(f"{adapter_type.capitalize()} token response fields verified")


@then("the {adapter_type} user info request should succeed")
def step_user_info_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user info request succeeded."""
    scenario_context = get_current_scenario_context(context)
    user_info = scenario_context.get("latest_user_info")
    assert user_info is not None, f"{adapter_type.capitalize()} user info request failed"
    context.logger.info(f"{adapter_type.capitalize()} user info request verified")


@then('the {adapter_type} user info should contain "{field1}" and "{field2}"')
def step_user_info_contains(context: Context, adapter_type: str, field1: str, field2: str) -> None:
    """Verify that the user info contains the specified fields."""
    scenario_context = get_current_scenario_context(context)
    user_info = scenario_context.get("latest_user_info")
    assert field1 in user_info, f"{field1} missing from {adapter_type} user info"
    assert field2 in user_info, f"{field2} missing from {adapter_type} user info"
    context.logger.info(f"{adapter_type.capitalize()} user info fields verified")


@then("the {adapter_type} logout operation should succeed")
def step_logout_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the logout operation succeeded."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("logout_result")
    assert result is True or result is None, f"{adapter_type.capitalize()} logout failed"
    context.logger.info(f"{adapter_type.capitalize()} logout verified")


@then("the {adapter_type} token validation should succeed")
def step_token_validation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the token validation succeeded."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("validation_result")
    assert result is not None, f"{adapter_type.capitalize()} token validation failed"
    assert result.get("active", False), "Token is not active"
    context.logger.info(f"{adapter_type.capitalize()} token validation verified")


# Create realm steps
@when('I create a realm named "{realm_name}" with display name "{display_name}" using {adapter_type} adapter')
def step_create_realm(context: Context, realm_name: str, display_name: str, adapter_type: str) -> None:
    """Create a realm with the specified name and display name."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            async def create_realm_async(context: Context) -> None:
                realm_result = await adapter.create_realm(
                    realm_name=realm_name, display_name=display_name, skip_exists=True
                )
                scenario_context.store("latest_realm_result", realm_result)
                scenario_context.store(f"realm_{realm_name}", realm_result)

            safe_run_async(create_realm_async)(context)
        else:
            realm_result = adapter.create_realm(realm_name=realm_name, display_name=display_name, skip_exists=True)
            scenario_context.store("latest_realm_result", realm_result)
            scenario_context.store(f"realm_{realm_name}", realm_result)
        context.logger.info(f"Created realm {realm_name}")
    except Exception as e:
        scenario_context.store("realm_error", str(e))
        context.logger.exception("Realm creation failed")


@then("the {adapter_type} realm creation should succeed")
def step_realm_creation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the realm creation succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get("realm_error"), f"Realm creation failed: {scenario_context.get('realm_error')}"
    assert scenario_context.get("latest_realm_result"), "No realm creation result found"
    context.logger.info("Realm creation succeeded")


@then('the realm "{realm_name}" should exist')
def step_realm_exists_after_creation(context: Context, realm_name: str) -> None:
    """Verify that the realm exists after creation."""
    scenario_context = get_current_scenario_context(context)
    realm_result = scenario_context.get(f"realm_{realm_name}")
    assert realm_result, f"Realm {realm_name} not found in results"
    assert realm_result["realm"] == realm_name, f"Expected realm name {realm_name}, got {realm_result['realm']}"
    context.logger.info(f"Verified realm {realm_name} exists")


@then('the realm should have display name "{display_name}"')
def step_realm_has_display_name(context: Context, display_name: str) -> None:
    """Verify that the realm has the specified display name."""
    scenario_context = get_current_scenario_context(context)
    realm_result = scenario_context.get("latest_realm_result")
    assert realm_result, "No realm creation result found"
    assert (
        realm_result["config"]["displayName"] == display_name
    ), f"Expected display name {display_name}, got {realm_result['config']['displayName']}"
    context.logger.info(f"Verified realm has display name {display_name}")


# Create client steps
@when('I create a client named "{client_name}" in realm "{realm_name}" using {adapter_type} adapter')
def step_create_client(context: Context, client_name: str, realm_name: str, adapter_type: str) -> None:
    """Create a client with the specified name in the specified realm."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            async def create_client_async(context: Context) -> None:
                client_result = await adapter.create_client(
                    client_id=client_name,
                    realm=realm_name,
                    skip_exists=True,
                    public_client=False,
                    service_account_enabled=True,
                )
                scenario_context.store("latest_client_result", client_result)
                scenario_context.store(f"client_{client_name}", client_result)

            safe_run_async(create_client_async)(context)
        else:
            client_result = adapter.create_client(
                client_id=client_name,
                realm=realm_name,
                skip_exists=True,
                public_client=False,
                service_account_enabled=True,
            )
            scenario_context.store("latest_client_result", client_result)
            scenario_context.store(f"client_{client_name}", client_result)
        context.logger.info(f"Created client {client_name} in realm {realm_name}")
    except Exception as e:
        scenario_context.store("client_error", str(e))
        context.logger.exception("Client creation failed")


@then("the {adapter_type} client creation should succeed")
def step_client_creation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the client creation succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get("client_error"), f"Client creation failed: {scenario_context.get('client_error')}"
    assert scenario_context.get("latest_client_result"), "No client creation result found"
    context.logger.info("Client creation succeeded")


@then('the client "{client_name}" should exist in realm "{realm_name}"')
def step_client_exists_in_realm(context: Context, client_name: str, realm_name: str) -> None:
    """Verify that the client exists in the specified realm."""
    scenario_context = get_current_scenario_context(context)
    client_result = scenario_context.get(f"client_{client_name}")
    assert client_result, f"Client {client_name} not found in results"
    assert (
        client_result["client_id"] == client_name
    ), f"Expected client name {client_name}, got {client_result['client_id']}"
    assert client_result["realm"] == realm_name, f"Expected realm {realm_name}, got {client_result['realm']}"
    context.logger.info(f"Verified client {client_name} exists in realm {realm_name}")
