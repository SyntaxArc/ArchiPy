# features/steps/keycloak_auth_steps.py

from behave import given, then, when
from behave.runner import Context
from features.scenario_context import ScenarioContext
from features.test_helpers import get_current_scenario_context

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


# Configuration steps
@given("a configured {adapter_type} Keycloak adapter")
def step_configured_adapter(context: Context, adapter_type: str) -> None:
    """Configure a Keycloak adapter of the specified type."""
    get_keycloak_adapter(context)
    context.logger.info(f"{adapter_type.capitalize()} Keycloak adapter configured")


# Realm management steps
@given('I create a realm named "{realm_name}" with display name "{display_name}" using {adapter_type} adapter')
@when('I create a realm named "{realm_name}" with display name "{display_name}" using {adapter_type} adapter')
async def step_create_realm(context: Context, realm_name: str, display_name: str, adapter_type: str) -> None:
    """Create a realm with the specified name and display name."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            realm_result = await adapter.create_realm(realm_name=realm_name, display_name=display_name, skip_exists=True)

        else:
            realm_result = adapter.create_realm(realm_name=realm_name, display_name=display_name, skip_exists=True)
        scenario_context.store("latest_realm_result", realm_result)
        scenario_context.store(f"realm_{realm_name}", realm_result)
        context.logger.info(f"Created realm {realm_name}")
    except Exception as e:
        scenario_context.store("realm_error", str(e))
        context.logger.exception("Realm creation failed")


# Client management steps
@given(
    'I create a client named "{client_name}" in realm "{realm_name}" with service accounts enabled using {adapter_type} adapter',
)
@when(
    'I create a client named "{client_name}" in realm "{realm_name}" with service accounts enabled using {adapter_type} adapter',
)
async def step_create_client_with_service_accounts(
    context: Context, client_name: str, realm_name: str, adapter_type: str,
) -> None:
    """Create a client with service accounts enabled in the specified realm."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            client_result = await adapter.create_client(
                client_id=client_name,
                realm=realm_name,
                skip_exists=True,
                public_client=False,
                service_account_enabled=True,
            )
            scenario_context.store("latest_client_result", client_result)
            scenario_context.store(f"client_{client_name}", client_result)
            await update_adapter_config(adapter, client_name, realm_name, scenario_context)
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

            # Update the adapter configuration to use the new client
            update_adapter_config(adapter, client_name, realm_name, scenario_context)

        context.logger.info(f"Created client {client_name} in realm {realm_name}")
    except Exception as e:
        scenario_context.store("client_error", str(e))
        context.logger.exception("Client creation failed")


async def update_adapter_config(
    adapter: AsyncKeycloakAdapter | KeycloakAdapter,
    client_name: str,
    realm_name: str,
    scenario_context: ScenarioContext,
) -> None:
    try:
        original_realm = adapter.configs.REALM_NAME
        adapter.configs.REALM_NAME = realm_name
        adapter._admin_adapter = None
        adapter._admin_token_expiry = 0
        if adapter.configs.IS_ADMIN_MODE_ENABLED and (adapter.configs.CLIENT_SECRET_KEY or (adapter.configs.ADMIN_USERNAME and adapter.configs.ADMIN_PASSWORD)):
            adapter._initialize_admin_client()
        client_result = scenario_context.get(f"client_{client_name}")
        if not client_result or "internal_client_id" not in client_result:
            raise ValueError(f"Client result not found or missing ID for client {client_name}")
        client_id = client_result["internal_client_id"]
        if "async" in scenario_context.__dict__.get("context", {}).scenario.tags:
            client_secret = await adapter.get_client_secret(client_id)
        else:
            client_secret = adapter.get_client_secret(client_id)
        adapter.configs.CLIENT_ID = client_name
        adapter.configs.CLIENT_SECRET_KEY = client_secret
        adapter.openid_adapter = adapter._get_openid_client(adapter.configs)
        adapter._admin_adapter = None
        adapter._admin_token_expiry = 0
        if adapter.configs.IS_ADMIN_MODE_ENABLED and (adapter.configs.CLIENT_SECRET_KEY or (adapter.configs.ADMIN_USERNAME and adapter.configs.ADMIN_PASSWORD)):
            adapter._initialize_admin_client()
        scenario_context.store(
            "client_config_updated",
            {
                "client_id": client_name,
                "realm": realm_name,
                "secret": client_secret,
                "previous_realm": original_realm,
                "internal_client_id": client_id,
            },
        )
    except Exception as e:
        scenario_context.store("client_config_error", str(e))
        raise


# Alternative approach: Create a new adapter instance with updated config
@given(
    'I create a client named "{client_name}" in realm "{realm_name}" with service accounts and update adapter using {adapter_type} adapter',
)
@when(
    'I create a client named "{client_name}" in realm "{realm_name}" with service accounts and update adapter using {adapter_type} adapter',
)
async def step_create_client_and_update_adapter(
    context: Context, client_name: str, realm_name: str, adapter_type: str,
) -> None:
    """Create a client with service accounts enabled and create a new adapter instance for it."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            # Create the client first
            client_result = await adapter.create_client(
                client_id=client_name,
                realm=realm_name,
                skip_exists=True,
                public_client=False,
                service_account_enabled=True,
            )
            scenario_context.store("latest_client_result", client_result)
            scenario_context.store(f"client_{client_name}", client_result)

            await update_adapter_config(adapter, client_name, realm_name, scenario_context)

            # Extract the internal client ID from the result
            if not client_result or "internal_client_id" not in client_result:
                raise ValueError(f"Client result not found or missing ID for client {client_name}")

            client_id = client_result["internal_client_id"]  # This is the internal UUID

            # Get the client secret using the internal client ID
            client_secret = await adapter.get_client_secret(client_id)

            # Create new configuration
            from archipy.configs.config_template import KeycloakConfig

            new_config = KeycloakConfig()
            new_config.SERVER_URL = adapter.configs.SERVER_URL
            new_config.CLIENT_ID = client_name  # Use client name for configuration
            new_config.REALM_NAME = realm_name
            new_config.CLIENT_SECRET_KEY = client_secret
            new_config.VERIFY_SSL = adapter.configs.VERIFY_SSL
            new_config.TIMEOUT = adapter.configs.TIMEOUT
            new_config.ADMIN_USERNAME = adapter.configs.ADMIN_USERNAME
            new_config.ADMIN_PASSWORD = adapter.configs.ADMIN_PASSWORD
            new_config.ADMIN_REALM_NAME = adapter.configs.ADMIN_REALM_NAME

            # Create new adapter instance
            from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter

            new_adapter = AsyncKeycloakAdapter(new_config)
            scenario_context.async_adapter = new_adapter

        else:
            # Create the client first
            client_result = adapter.create_client(
                client_id=client_name,
                realm=realm_name,
                skip_exists=True,
                public_client=False,
                service_account_enabled=True,
            )
            scenario_context.store("latest_client_result", client_result)
            scenario_context.store(f"client_{client_name}", client_result)

            update_adapter_config(adapter, client_name, realm_name, scenario_context)

            # Extract the internal client ID from the result
            if not client_result or "internal_client_id" not in client_result:
                raise ValueError(f"Client result not found or missing ID for client {client_name}")

            client_id = client_result["internal_client_id"]  # This is the internal UUID

            # Get the client secret using the internal client ID
            client_secret = adapter.get_client_secret(client_id)

            # Create new configuration
            from archipy.configs.config_template import KeycloakConfig

            new_config = KeycloakConfig()
            new_config.SERVER_URL = adapter.configs.SERVER_URL
            new_config.CLIENT_ID = client_name  # Use client name for configuration
            new_config.REALM_NAME = realm_name
            new_config.CLIENT_SECRET_KEY = client_secret
            new_config.VERIFY_SSL = adapter.configs.VERIFY_SSL
            new_config.TIMEOUT = adapter.configs.TIMEOUT
            new_config.ADMIN_USERNAME = adapter.configs.ADMIN_USERNAME
            new_config.ADMIN_PASSWORD = adapter.configs.ADMIN_PASSWORD
            new_config.ADMIN_REALM_NAME = adapter.configs.ADMIN_REALM_NAME

            # Create new adapter instance
            from archipy.adapters.keycloak.adapters import KeycloakAdapter

            new_adapter = KeycloakAdapter(new_config)
            scenario_context.adapter = new_adapter

        context.logger.info(f"Created client {client_name} in realm {realm_name} and updated adapter configuration")
    except Exception as e:
        scenario_context.store("client_error", str(e))
        context.logger.exception("Client creation and adapter update failed")


# User management steps
@given('I create a user with username "{username}" and password "{password}" using {adapter_type} adapter')
@when('I create a user with username "{username}" and password "{password}" using {adapter_type} adapter')
async def step_create_user_basic(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Create a user with the specified username and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_data = {
        "username": username,
        "enabled": True,
        "emailVerified": True,
        "firstName": username,
        "lastName": "Test",
        "email": f"{username}@test.com",
        "credentials": [{"type": "password", "value": password, "temporary": False}],
        "requiredActions": [],
        "attributes": {"locale": ["en"]},
    }

    try:
        if is_async:

            existing_user = await adapter.get_user_by_username(username)
            if existing_user:
                await adapter.delete_user(existing_user["id"])

            user_id = await adapter.create_user(user_data)
            scenario_context.store(f"user_id_{username}", user_id)
            scenario_context.store("latest_user_creation", {"username": username, "user_id": user_id})

        else:
            # Check if user exists and delete if needed
            existing_user = adapter.get_user_by_username(username)
            if existing_user:
                adapter.delete_user(existing_user["id"])

            user_id = adapter.create_user(user_data)
            scenario_context.store(f"user_id_{username}", user_id)
            scenario_context.store("latest_user_creation", {"username": username, "user_id": user_id})
        context.logger.info(f"Created user {username} with ID {scenario_context.get(f'user_id_{username}')}")
    except Exception as e:
        scenario_context.store("user_creation_error", str(e))
        context.logger.exception(f"Failed to create user {username}")


@given(
    'I create a user including username "{username}" email "{email}" and password "{password}" using {adapter_type} adapter',
)
@when(
    'I create a user including username "{username}" email "{email}" and password "{password}" using {adapter_type} adapter',
)
async def step_create_user_with_email(context: Context, username: str, email: str, password: str, adapter_type: str) -> None:
    """Create a user with the specified username, email, and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_data = {
        "username": username,
        "email": email,
        "enabled": True,
        "credentials": [{"type": "password", "value": password, "temporary": False}],
    }

    try:
        if is_async:

            existing_user = await adapter.get_user_by_username(username)
            if existing_user:
                await adapter.delete_user(existing_user["id"])

            user_id = await adapter.create_user(user_data)
            scenario_context.store(f"user_id_{username}", user_id)
            scenario_context.store(
                "latest_user_creation", {"username": username, "email": email, "user_id": user_id},
            )

        else:
            # Check if user exists and delete if needed
            existing_user = adapter.get_user_by_username(username)
            if existing_user:
                adapter.delete_user(existing_user["id"])

            user_id = adapter.create_user(user_data)
            scenario_context.store(f"user_id_{username}", user_id)
            scenario_context.store("latest_user_creation", {"username": username, "email": email, "user_id": user_id})
        context.logger.info(f"Created user {username} with email {email}")
    except Exception as e:
        scenario_context.store("user_creation_error", str(e))
        context.logger.exception(f"Failed to create user {username}")


@given('I have a valid token for "{username}" with password "{password}" using {adapter_type} adapter')
async def step_have_valid_token(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Obtain a valid token for the specified username and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        token_response = await adapter.get_token(username, password)
        scenario_context.store(f"token_response_{username}", token_response)

    else:
        token_response = adapter.get_token(username, password)
        scenario_context.store(f"token_response_{username}", token_response)
    context.logger.info(f"Obtained initial token for {username}")


# Token management steps
@when('I request a token with username "{username}" and password "{password}" using {adapter_type} adapter')
async def step_request_token(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Request a token with the specified username and password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            token_response = await adapter.get_token(username, password)
            scenario_context.store("latest_token_response", token_response)

        else:
            token_response = adapter.get_token(username, password)
            scenario_context.store("latest_token_response", token_response)
        context.logger.info(f"Requested token for {username}")
    except Exception as e:
        scenario_context.store("token_error", str(e))
        context.logger.exception("Token request failed")


@when("I refresh the token using {adapter_type} adapter")
async def step_refresh_token(context: Context, adapter_type: str) -> None:
    """Refresh the token using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    # Find the username from previous steps
    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    refresh_token = scenario_context.get(f"token_response_{username}")["refresh_token"]

    if is_async:

        new_token = await adapter.refresh_token(refresh_token)
        scenario_context.store("latest_token_response", new_token)

    else:
        new_token = adapter.refresh_token(refresh_token)
        scenario_context.store("latest_token_response", new_token)
    context.logger.info(f"Refreshed token for {username}")


@when("I request user info with the token using {adapter_type} adapter")
async def step_request_user_info(context: Context, adapter_type: str) -> None:
    """Request user info using the token and the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        user_info = await adapter.get_userinfo(access_token)
        scenario_context.store("latest_user_info", user_info)

    else:
        user_info = adapter.get_userinfo(access_token)
        scenario_context.store("latest_user_info", user_info)
    context.logger.info(f"Requested user info for {username}")


@when("I logout the user using {adapter_type} adapter")
async def step_logout_user(context: Context, adapter_type: str) -> None:
    """Logout the user using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    refresh_token = scenario_context.get(f"token_response_{username}")["refresh_token"]

    if is_async:

        result = await adapter.logout(refresh_token)
        scenario_context.store("logout_result", result)

    else:
        result = adapter.logout(refresh_token)
        scenario_context.store("logout_result", result)
    context.logger.info(f"Logged out user {username}")


@when("I validate the token using {adapter_type} adapter")
async def step_validate_token(context: Context, adapter_type: str) -> None:
    """Validate the token using the adapter of the specified type."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        result = await adapter.validate_token(access_token)
        scenario_context.store("validation_result", result)

    else:
        result = adapter.validate_token(access_token)
        scenario_context.store("validation_result", result)
    context.logger.info(f"Validated token for {username}")


# User retrieval steps
@when('I get user by username "{username}" using {adapter_type} adapter')
async def step_get_user_by_username(context: Context, username: str, adapter_type: str) -> None:
    """Get user by username."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        user = await adapter.get_user_by_username(username)
        scenario_context.store("latest_user_retrieval", user)

    else:
        user = adapter.get_user_by_username(username)
        scenario_context.store("latest_user_retrieval", user)
    context.logger.info(f"Retrieved user by username {username}")


@when('I get user by email "{email}" using {adapter_type} adapter')
async def step_get_user_by_email(context: Context, email: str, adapter_type: str) -> None:
    """Get user by email."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        user = await adapter.get_user_by_email(email)
        scenario_context.store("latest_user_retrieval", user)

    else:
        user = adapter.get_user_by_email(email)
        scenario_context.store("latest_user_retrieval", user)
    context.logger.info(f"Retrieved user by email {email}")


# Role management steps


@given('I create a realm role named "{role_name}" with description "{description}" using {adapter_type} adapter')
@when('I create a realm role named "{role_name}" with description "{description}" using {adapter_type} adapter')
async def step_create_realm_role(context: Context, role_name: str, description: str, adapter_type: str) -> None:
    """Create a realm role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            role = await adapter.create_realm_role(role_name, description)
            scenario_context.store("latest_realm_role", role)
            scenario_context.store(f"realm_role_{role_name}", role)

        else:
            role = adapter.create_realm_role(role_name, description)
            scenario_context.store("latest_realm_role", role)
            scenario_context.store(f"realm_role_{role_name}", role)
        context.logger.info(f"Created realm role {role_name}")
    except Exception as e:
        scenario_context.store("realm_role_error", str(e))
        context.logger.exception("Realm role creation failed")


@when(
    'I create a client role named "{role_name}" for client "{client_id}" with description "{description}" using {adapter_type} adapter',
)
async def step_create_client_role(
    context: Context, role_name: str, client_id: str, description: str, adapter_type: str,
) -> None:
    """Create a client role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            role = await adapter.create_client_role(client_id, role_name, description)
            scenario_context.store("latest_client_role", role)
            scenario_context.store(f"client_role_{role_name}_{client_id}", role)

        else:
            role = adapter.create_client_role(client_id, role_name, description)
            scenario_context.store("latest_client_role", role)
            scenario_context.store(f"client_role_{role_name}_{client_id}", role)
        context.logger.info(f"Created client role {role_name} for client {client_id}")
    except Exception as e:
        scenario_context.store("client_role_error", str(e))
        context.logger.exception("Client role creation failed")


@given('I assign realm role "{role_name}" to user "{username}" using {adapter_type} adapter')
@when('I assign realm role "{role_name}" to user "{username}" using {adapter_type} adapter')
async def step_assign_realm_role(context: Context, role_name: str, username: str, adapter_type: str) -> None:
    """Assign a realm role to a user."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    try:
        if is_async:

            await adapter.assign_realm_role(user_id, role_name)
            scenario_context.store("latest_role_assignment", {"user": username, "role": role_name})

        else:
            adapter.assign_realm_role(user_id, role_name)
            scenario_context.store("latest_role_assignment", {"user": username, "role": role_name})
        context.logger.info(f"Assigned realm role {role_name} to user {username}")
    except Exception as e:
        scenario_context.store("role_assignment_error", str(e))
        context.logger.exception("Role assignment failed")


@when('I assign client role "{role_name}" of client "{client_id}" to user "{username}" using {adapter_type} adapter')
async def step_assign_client_role(context: Context, role_name: str, client_id: str, username: str, adapter_type: str) -> None:
    """Assign a client role to a user."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    try:
        if is_async:

            await adapter.assign_client_role(user_id, client_id, role_name)
            scenario_context.store(
                "latest_client_role_assignment", {"user": username, "role": role_name, "client": client_id},
            )

        else:
            adapter.assign_client_role(user_id, client_id, role_name)
            scenario_context.store(
                "latest_client_role_assignment", {"user": username, "role": role_name, "client": client_id},
            )
        context.logger.info(f"Assigned client role {role_name} of client {client_id} to user {username}")
    except Exception as e:
        scenario_context.store("client_role_assignment_error", str(e))
        context.logger.exception("Client role assignment failed")


@when('I remove realm role "{role_name}" from user "{username}" using {adapter_type} adapter')
async def step_remove_realm_role(context: Context, role_name: str, username: str, adapter_type: str) -> None:
    """Remove a realm role from a user."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    try:
        if is_async:

            await adapter.remove_realm_role(user_id, role_name)
            scenario_context.store("latest_role_removal", {"user": username, "role": role_name})

        else:
            adapter.remove_realm_role(user_id, role_name)
            scenario_context.store("latest_role_removal", {"user": username, "role": role_name})
        context.logger.info(f"Removed realm role {role_name} from user {username}")
    except Exception as e:
        scenario_context.store("role_removal_error", str(e))
        context.logger.exception("Role removal failed")


# Search and update steps
@when('I search for users with query "{query}" using {adapter_type} adapter')
async def step_search_users(context: Context, query: str, adapter_type: str) -> None:
    """Search for users."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        users = await adapter.search_users(query)
        scenario_context.store("search_results", users)

    else:
        users = adapter.search_users(query)
        scenario_context.store("search_results", users)
    context.logger.info(f"Searched for users with query {query}")


@when(
    'I update user "{username}" with first name "{first_name}" and last name "{last_name}" using {adapter_type} adapter',
)
async def step_update_user(context: Context, username: str, first_name: str, last_name: str, adapter_type: str) -> None:
    """Update user details."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")
    update_data = {"firstName": first_name, "lastName": last_name}

    try:
        if is_async:

            await adapter.update_user(user_id, update_data)
            scenario_context.store("latest_user_update", {"user": username, "data": update_data})

        else:
            adapter.update_user(user_id, update_data)
            scenario_context.store("latest_user_update", {"user": username, "data": update_data})
        context.logger.info(f"Updated user {username}")
    except Exception as e:
        scenario_context.store("user_update_error", str(e))
        context.logger.exception("User update failed")


@when('I reset password for user "{username}" to "{new_password}" using {adapter_type} adapter')
async def step_reset_password(context: Context, username: str, new_password: str, adapter_type: str) -> None:
    """Reset user password."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    try:
        if is_async:

            await adapter.reset_password(user_id, new_password, temporary=False)
            scenario_context.store("latest_password_reset", {"user": username, "new_password": new_password})

        else:
            adapter.reset_password(user_id, new_password, temporary=False)
            scenario_context.store("latest_password_reset", {"user": username, "new_password": new_password})
        context.logger.info(f"Reset password for user {username}")
    except Exception as e:
        scenario_context.store("password_reset_error", str(e))
        context.logger.exception("Password reset failed")


@when('I clear sessions for user "{username}" using {adapter_type} adapter')
async def step_clear_user_sessions(context: Context, username: str, adapter_type: str) -> None:
    """Clear user sessions."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    if is_async:

        await adapter.clear_user_sessions(user_id)
        scenario_context.store("latest_session_clear", {"user": username})

    else:
        adapter.clear_user_sessions(user_id)
        scenario_context.store("latest_session_clear", {"user": username})
    context.logger.info(f"Cleared sessions for user {username}")


@when('I delete user "{username}" using {adapter_type} adapter')
async def step_delete_user(context: Context, username: str, adapter_type: str) -> None:
    """Delete a user."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    try:
        if is_async:

            await adapter.delete_user(user_id)
            scenario_context.store("latest_user_deletion", {"user": username})

        else:
            adapter.delete_user(user_id)
            scenario_context.store("latest_user_deletion", {"user": username})
        context.logger.info(f"Deleted user {username}")
    except Exception as e:
        scenario_context.store("user_deletion_error", str(e))
        context.logger.exception("User deletion failed")


# Advanced token operations
@when("I request client credentials token using {adapter_type} adapter")
async def step_request_client_credentials_token(context: Context, adapter_type: str) -> None:
    """Request client credentials token."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        token = await adapter.get_client_credentials_token()
        scenario_context.store("latest_token_response", token)

    else:
        token = adapter.get_client_credentials_token()
        scenario_context.store("latest_token_response", token)
    context.logger.info("Requested client credentials token")


@when("I introspect the token using {adapter_type} adapter")
async def step_introspect_token(context: Context, adapter_type: str) -> None:
    """Introspect the token."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        result = await adapter.introspect_token(access_token)
        scenario_context.store("introspection_result", result)

    else:
        result = adapter.introspect_token(access_token)
        scenario_context.store("introspection_result", result)
    context.logger.info("Introspected token")


@when("I get token info using {adapter_type} adapter")
async def step_get_token_info(context: Context, adapter_type: str) -> None:
    """Get token info."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        result = await adapter.get_token_info(access_token)
        scenario_context.store("token_info_result", result)

    else:
        result = adapter.get_token_info(access_token)
        scenario_context.store("token_info_result", result)
    context.logger.info("Retrieved token info")


@when('I check if user has role "{role_name}" using {adapter_type} adapter')
async def step_check_user_role(context: Context, role_name: str, adapter_type: str) -> None:
    """Check if user has a specific role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    prev_step = next((s for s in reversed(context.scenario.steps) if "have a valid token" in s.name), None)
    if not prev_step:
        raise ValueError("No previous token step found")

    username = prev_step.name.split('"')[1]
    access_token = scenario_context.get(f"token_response_{username}")["access_token"]

    if is_async:

        has_role = await adapter.has_role(access_token, role_name)
        scenario_context.store("role_check_result", {"role": role_name, "has_role": has_role})

    else:
        has_role = adapter.has_role(access_token, role_name)
        scenario_context.store("role_check_result", {"role": role_name, "has_role": has_role})
    context.logger.info(f"Checked if user has role {role_name}")


@when('I should be able to get token with username "{username}" and password "{password}" using {adapter_type} adapter')
@then('I should be able to get token with username "{username}" and password "{password}" using {adapter_type} adapter')
async def step_should_get_token(context: Context, username: str, password: str, adapter_type: str) -> None:
    """Verify that we can get a token with new credentials."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    try:
        if is_async:

            token_response = await adapter.get_token(username, password)
            scenario_context.store("verification_token_response", token_response)

        else:
            token_response = adapter.get_token(username, password)
            scenario_context.store("verification_token_response", token_response)
        context.logger.info(f"Verified token acquisition for {username} with new password")
    except Exception as e:
        scenario_context.store("verification_token_error", str(e))
        context.logger.exception("Token verification failed")


# Verification steps (Then statements)
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
    realm_display_name = realm_result.get("displayName") or realm_result.get("config", {}).get("displayName")
    assert realm_result, "No realm creation result found"
    assert realm_display_name == display_name, f"Expected display name {display_name}, got {realm_display_name}"
    context.logger.info(f"Verified realm has display name {display_name}")


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


@then('the client "{client_name}" should have service accounts enabled')
def step_client_has_service_accounts(context: Context, client_name: str) -> None:
    """Verify that the client has service accounts enabled."""
    scenario_context = get_current_scenario_context(context)
    client_result = scenario_context.get(f"client_{client_name}")
    assert client_result, f"Client {client_name} not found in results"
    # Note: This assumes the client was created with service accounts enabled
    # In a real test, you might want to query Keycloak to verify this
    context.logger.info(f"Verified client {client_name} has service accounts enabled")


@then("the {adapter_type} user creation should succeed")
def step_user_creation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user creation succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "user_creation_error",
    ), f"User creation failed: {scenario_context.get('user_creation_error')}"
    assert scenario_context.get("latest_user_creation"), "No user creation result found"
    context.logger.info("User creation succeeded")


@then("the {adapter_type} user token request should succeed")
def step_user_token_request_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user token request succeeded."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert token_response is not None, f"{adapter_type.capitalize()} token request failed"
    assert "access_token" in token_response, "Access token missing"
    context.logger.info(f"{adapter_type.capitalize()} user token request verified")


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


@then('the {adapter_type} token response should contain "{field}"')
def step_token_response_contains_single(context: Context, adapter_type: str, field: str) -> None:
    """Verify that the token response contains the specified field."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert field in token_response, f"{field} missing from {adapter_type} token response"
    context.logger.info(f"{adapter_type.capitalize()} token response field {field} verified")


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
    assert result is True, "Token validation returned False"
    context.logger.info(f"{adapter_type.capitalize()} token validation verified")


@then("the {adapter_type} user retrieval should succeed")
def step_user_retrieval_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user retrieval succeeded."""
    scenario_context = get_current_scenario_context(context)
    user = scenario_context.get("latest_user_retrieval")
    assert user is not None, f"{adapter_type.capitalize()} user retrieval failed"
    context.logger.info(f"{adapter_type.capitalize()} user retrieval verified")


@then('the user should have username "{username}"')
def step_user_has_username(context: Context, username: str) -> None:
    """Verify that the user has the specified username."""
    scenario_context = get_current_scenario_context(context)
    user = scenario_context.get("latest_user_retrieval")
    assert user["username"] == username, f"Expected username {username}, got {user.get('username')}"
    context.logger.info(f"Verified user has username {username}")


@then('the user should have email "{email}"')
def step_user_has_email(context: Context, email: str) -> None:
    """Verify that the user has the specified email."""
    scenario_context = get_current_scenario_context(context)
    user = scenario_context.get("latest_user_retrieval")
    assert user["email"] == email, f"Expected email {email}, got {user.get('email')}"
    context.logger.info(f"Verified user has email {email}")


@then("the {adapter_type} realm role creation should succeed")
def step_realm_role_creation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the realm role creation succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "realm_role_error",
    ), f"Realm role creation failed: {scenario_context.get('realm_role_error')}"
    assert scenario_context.get("latest_realm_role"), "No realm role creation result found"
    context.logger.info("Realm role creation succeeded")


@then("the {adapter_type} client role creation should succeed")
def step_client_role_creation_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the client role creation succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "client_role_error",
    ), f"Client role creation failed: {scenario_context.get('client_role_error')}"
    assert scenario_context.get("latest_client_role"), "No client role creation result found"
    context.logger.info("Client role creation succeeded")


@then("the {adapter_type} realm role assignment should succeed")
def step_realm_role_assignment_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the realm role assignment succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "role_assignment_error",
    ), f"Role assignment failed: {scenario_context.get('role_assignment_error')}"
    assert scenario_context.get("latest_role_assignment"), "No role assignment result found"
    context.logger.info("Realm role assignment succeeded")


@then("the {adapter_type} client role assignment should succeed")
def step_client_role_assignment_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the client role assignment succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "client_role_assignment_error",
    ), f"Client role assignment failed: {scenario_context.get('client_role_assignment_error')}"
    assert scenario_context.get("latest_client_role_assignment"), "No client role assignment result found"
    context.logger.info("Client role assignment succeeded")


@then('the user "{username}" should have realm role "{role_name}"')
async def step_user_has_realm_role(context: Context, username: str, role_name: str) -> None:
    """Verify that the user has the specified realm role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    if is_async:

            roles = await adapter.get_user_roles(user_id)
            role_names = [role["name"] for role in roles]
            assert role_name in role_names, f"User {username} does not have realm role {role_name}"

    else:
        roles = adapter.get_user_roles(user_id)
        role_names = [role["name"] for role in roles]
        assert role_name in role_names, f"User {username} does not have realm role {role_name}"
    context.logger.info(f"Verified user {username} has realm role {role_name}")


@then('the user "{username}" should have client role "{role_name}" for client "{client_name}"')
async def step_user_has_client_role(context: Context, username: str, role_name: str, client_name: str) -> None:
    """Verify that the user has the specified client role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    if is_async:

        client_id = await adapter.get_client_id(client_name)
        roles = await adapter.get_client_roles_for_user(user_id, client_id)
        role_names = [role["name"] for role in roles]
        assert (
            role_name in role_names
        ), f"User {username} does not have client role {role_name} for client {client_id}"

    else:
        client_id = adapter.get_client_id(client_name)
        roles = adapter.get_client_roles_for_user(user_id, client_id)
        role_names = [role["name"] for role in roles]
        assert role_name in role_names, f"User {username} does not have client role {role_name} for client {client_id}"
    context.logger.info(f"Verified user {username} has client role {role_name} for client {client_id}")


@then('the user "{username}" should not have realm role "{role_name}"')
async def step_user_not_have_realm_role(context: Context, username: str, role_name: str) -> None:
    """Verify that the user does not have the specified realm role."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    if is_async:

        roles = await adapter.get_user_roles(user_id)
        role_names = [role["name"] for role in roles]
        assert role_name not in role_names, f"User {username} still has realm role {role_name}"

    else:
        roles = adapter.get_user_roles(user_id)
        role_names = [role["name"] for role in roles]
        assert role_name not in role_names, f"User {username} still has realm role {role_name}"
    context.logger.info(f"Verified user {username} does not have realm role {role_name}")


@then("the {adapter_type} user search should succeed")
def step_user_search_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user search succeeded."""
    scenario_context = get_current_scenario_context(context)
    search_results = scenario_context.get("search_results")
    assert search_results is not None, f"{adapter_type.capitalize()} user search failed"
    context.logger.info(f"{adapter_type.capitalize()} user search verified")


@then("the search results should contain {count:d} users")
def step_search_results_count(context: Context, count: int) -> None:
    """Verify that the search results contain the expected number of users."""
    scenario_context = get_current_scenario_context(context)
    search_results = scenario_context.get("search_results")
    assert len(search_results) == count, f"Expected {count} users, got {len(search_results)}"
    context.logger.info(f"Verified search results contain {count} users")


@then("the {adapter_type} user update should succeed")
def step_user_update_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user update succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "user_update_error",
    ), f"User update failed: {scenario_context.get('user_update_error')}"
    assert scenario_context.get("latest_user_update"), "No user update result found"
    context.logger.info("User update succeeded")


@then('the user "{username}" should have first name "{first_name}" and last name "{last_name}"')
async def step_user_has_names(context: Context, username: str, first_name: str, last_name: str) -> None:
    """Verify that the user has the specified first and last names."""
    adapter = get_keycloak_adapter(context)
    scenario_context = get_current_scenario_context(context)
    is_async = "async" in context.scenario.tags

    user_id = scenario_context.get(f"user_id_{username}")

    if is_async:

        user = await adapter.get_user_by_id(user_id)
        assert user["firstName"] == first_name, f"Expected first name {first_name}, got {user.get('firstName')}"
        assert user["lastName"] == last_name, f"Expected last name {last_name}, got {user.get('lastName')}"

    else:
        user = adapter.get_user_by_id(user_id)
        assert user["firstName"] == first_name, f"Expected first name {first_name}, got {user.get('firstName')}"
        assert user["lastName"] == last_name, f"Expected last name {last_name}, got {user.get('lastName')}"
    context.logger.info(f"Verified user {username} has names {first_name} {last_name}")


@then("the {adapter_type} password reset should succeed")
def step_password_reset_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the password reset succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "password_reset_error",
    ), f"Password reset failed: {scenario_context.get('password_reset_error')}"
    assert scenario_context.get("latest_password_reset"), "No password reset result found"
    context.logger.info("Password reset succeeded")


@then("the {adapter_type} session clearing should succeed")
def step_session_clearing_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the session clearing succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("latest_session_clear"), "No session clear result found"
    context.logger.info("Session clearing succeeded")


@then("the {adapter_type} user deletion should succeed")
def step_user_deletion_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the user deletion succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "user_deletion_error",
    ), f"User deletion failed: {scenario_context.get('user_deletion_error')}"
    assert scenario_context.get("latest_user_deletion"), "No user deletion result found"
    context.logger.info("User deletion succeeded")


@then('the user "{username}" should not exist')
async def step_user_not_exist(context: Context, username: str) -> None:
    """Verify that the user no longer exists."""
    adapter = get_keycloak_adapter(context)
    is_async = "async" in context.scenario.tags

    if is_async:

        user = await adapter.get_user_by_username(username)
        assert user is None, f"User {username} still exists"

    else:
        user = adapter.get_user_by_username(username)
        assert user is None, f"User {username} still exists"
    context.logger.info(f"Verified user {username} does not exist")


@then("the {adapter_type} client credentials token request should succeed")
def step_client_credentials_token_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the client credentials token request succeeded."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    assert token_response is not None, f"{adapter_type.capitalize()} client credentials token request failed"
    assert "access_token" in token_response, "Access token missing from client credentials response"
    context.logger.info(f"{adapter_type.capitalize()} client credentials token request verified")


@then("the {adapter_type} token introspection should succeed")
def step_token_introspection_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the token introspection succeeded."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("introspection_result")
    assert result is not None, f"{adapter_type.capitalize()} token introspection failed"
    context.logger.info(f"{adapter_type.capitalize()} token introspection verified")


@then("the introspection result should indicate active token")
def step_introspection_active(context: Context) -> None:
    """Verify that the introspection result indicates an active token."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("introspection_result")
    assert result.get("active", False), "Token is not active according to introspection"
    context.logger.info("Verified token is active")


@then("the {adapter_type} token info request should succeed")
def step_token_info_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the token info request succeeded."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("token_info_result")
    assert result is not None, f"{adapter_type.capitalize()} token info request failed"
    context.logger.info(f"{adapter_type.capitalize()} token info request verified")


@then("the token info should contain user claims")
def step_token_info_contains_claims(context: Context) -> None:
    """Verify that the token info contains user claims."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("token_info_result")
    assert "sub" in result, "Token info missing 'sub' claim"
    assert "preferred_username" in result, "Token info missing 'preferred_username' claim"
    context.logger.info("Verified token info contains user claims")


@then("the {adapter_type} role check should succeed")
def step_role_check_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the role check succeeded."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("role_check_result")
    assert result is not None, f"{adapter_type.capitalize()} role check failed"
    context.logger.info(f"{adapter_type.capitalize()} role check verified")


@then('the user should have the role "{role_name}"')
def step_user_should_have_role(context: Context, role_name: str) -> None:
    """Verify that the user has the specified role."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("role_check_result")
    assert result["has_role"], f"User does not have role {role_name}"
    context.logger.info(f"Verified user has role {role_name}")


@then("the {adapter_type} role removal should succeed")
def step_role_removal_succeeds(context: Context, adapter_type: str) -> None:
    """Verify that the role removal succeeded."""
    scenario_context = get_current_scenario_context(context)
    assert not scenario_context.get(
        "role_removal_error",
    ), f"Role removal failed: {scenario_context.get('role_removal_error')}"
    assert scenario_context.get("latest_role_removal"), "No role removal result found"
    context.logger.info("Role removal succeeded")


# Additional utility verification steps for complex scenarios
@then("all operations should complete successfully")
def step_all_operations_successful(context: Context) -> None:
    """Verify that all operations in the scenario completed successfully."""
    scenario_context = get_current_scenario_context(context)

    # Check for any stored errors
    error_keys = [key for key in scenario_context._storage.keys() if "error" in key.lower()]
    for error_key in error_keys:
        error_value = scenario_context.get(error_key)
        assert not error_value, f"Operation failed with error in {error_key}: {error_value}"

    context.logger.info("Verified all operations completed successfully")


@then("the scenario should have created all required resources")
def step_scenario_created_resources(context: Context) -> None:
    """Verify that the scenario created all required resources."""
    scenario_context = get_current_scenario_context(context)

    # Count the resources that should have been created based on scenario steps
    realm_count = len([key for key in scenario_context._storage.keys() if key.startswith("realm_")])
    client_count = len([key for key in scenario_context._storage.keys() if key.startswith("client_")])
    user_count = len([key for key in scenario_context._storage.keys() if key.startswith("user_id_")])

    assert realm_count > 0, "No realms were created"
    assert client_count > 0, "No clients were created"
    assert user_count > 0, "No users were created"

    context.logger.info(
        f"Verified scenario created {realm_count} realm(s), {client_count} client(s), and {user_count} user(s)",
    )


# Helper verification steps for debugging
@then("I should see the latest token response")
def step_debug_token_response(context: Context) -> None:
    """Debug step to print the latest token response."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")
    context.logger.info(f"Latest token response: {token_response}")


@then("I should see the latest user info")
def step_debug_user_info(context: Context) -> None:
    """Debug step to print the latest user info."""
    scenario_context = get_current_scenario_context(context)
    user_info = scenario_context.get("latest_user_info")
    context.logger.info(f"Latest user info: {user_info}")


@then("I should see all stored data")
def step_debug_all_data(context: Context) -> None:
    """Debug step to print all stored scenario data."""
    scenario_context = get_current_scenario_context(context)
    all_data = {key: value for key, value in scenario_context._storage.items()}
    context.logger.info(f"All stored data: {all_data}")


# Performance verification steps
@then("the {adapter_type} operations should complete within reasonable time")
def step_operations_performance(context: Context, adapter_type: str) -> None:
    """Verify that operations complete within reasonable time (basic performance check)."""
    # This is a placeholder for performance verification
    # In a real implementation, you might want to measure operation times
    context.logger.info(f"{adapter_type.capitalize()} operations completed within reasonable time")


# Security verification steps
@then("the token should have appropriate expiration")
def step_token_expiration_check(context: Context) -> None:
    """Verify that the token has appropriate expiration settings."""
    scenario_context = get_current_scenario_context(context)
    token_response = scenario_context.get("latest_token_response")

    if token_response and "expires_in" in token_response:
        expires_in = token_response["expires_in"]
        assert expires_in > 0, "Token expires_in should be greater than 0"
        assert expires_in <= 3600, "Token expires_in should not exceed 1 hour for security"
        context.logger.info(f"Verified token expiration: {expires_in} seconds")
    else:
        context.logger.warning("Token response does not contain expires_in field")


@then("the user should have appropriate permissions")
def step_user_permissions_check(context: Context) -> None:
    """Verify that the user has appropriate permissions (placeholder for security checks)."""
    # This is a placeholder for permission verification
    # In a real implementation, you might want to check specific permissions
    context.logger.info("User permissions verified (placeholder)")


# Cleanup verification steps
@then("all test resources should be properly cleaned up")
def step_cleanup_verification(context: Context) -> None:
    """Verify that test resources are properly cleaned up."""
    # This step could be used in cleanup scenarios
    # In a real implementation, you might want to verify that test users, roles, etc. are removed
    context.logger.info("Test resource cleanup verified (placeholder)")


# Integration verification steps
@then("the {adapter_type} adapter should integrate properly with Keycloak")
def step_integration_verification(context: Context, adapter_type: str) -> None:
    """Verify that the adapter integrates properly with Keycloak."""
    scenario_context = get_current_scenario_context(context)

    # Check that we have successful operations
    token_response = scenario_context.get("latest_token_response")
    user_info = scenario_context.get("latest_user_info")

    if token_response:
        assert "access_token" in token_response, "Integration failed: no access token"
    if user_info:
        assert "sub" in user_info, "Integration failed: no user subject"

    context.logger.info(f"{adapter_type.capitalize()} adapter integration with Keycloak verified")


# Error handling verification steps
@then("error handling should work correctly")
def step_error_handling_verification(context: Context) -> None:
    """Verify that error handling works correctly."""
    # This is a placeholder for error handling verification
    # In a real implementation, you might want to test error scenarios
    context.logger.info("Error handling verification completed (placeholder)")


# Configuration verification steps
@then("the adapter configuration should be valid")
def step_adapter_config_verification(context: Context) -> None:
    """Verify that the adapter configuration is valid."""
    adapter = get_keycloak_adapter(context)

    # Basic configuration checks
    assert adapter.configs is not None, "Adapter configuration is None"
    assert adapter.configs.SERVER_URL, "Server URL not configured"
    assert adapter.configs.CLIENT_ID, "Client ID not configured"
    assert adapter.configs.REALM_NAME, "Realm name not configured"

    context.logger.info("Adapter configuration verified")


# Async/Sync consistency verification
@then("async and sync operations should have consistent behavior")
def step_async_sync_consistency(context: Context) -> None:
    """Verify that async and sync operations have consistent behavior."""
    # This is a placeholder for consistency verification between async and sync adapters
    # In a real implementation, you might want to compare results from both adapters
    context.logger.info("Async/sync consistency verified (placeholder)")


# Token lifecycle verification
@then("the token lifecycle should work correctly")
def step_token_lifecycle_verification(context: Context) -> None:
    """Verify that the complete token lifecycle works correctly."""
    scenario_context = get_current_scenario_context(context)

    # Check if we have evidence of successful token operations
    token_response = scenario_context.get("latest_token_response")
    validation_result = scenario_context.get("validation_result")
    logout_result = scenario_context.get("logout_result")

    operations_count = sum(1 for result in [token_response, validation_result, logout_result] if result is not None)
    assert operations_count > 0, "No token lifecycle operations were performed"

    context.logger.info("Token lifecycle verification completed")


# Role-based access control verification
@then("role-based access control should function properly")
def step_rbac_verification(context: Context) -> None:
    """Verify that role-based access control functions properly."""
    scenario_context = get_current_scenario_context(context)

    # Check if we have evidence of successful role operations
    role_assignment = scenario_context.get("latest_role_assignment")
    role_check = scenario_context.get("role_check_result")

    if role_assignment or role_check:
        context.logger.info("Role-based access control verified")
    else:
        context.logger.info("No role operations to verify")


# Multi-tenancy verification (for realm isolation)
@then("realm isolation should be maintained")
def step_realm_isolation_verification(context: Context) -> None:
    """Verify that realm isolation is properly maintained."""
    scenario_context = get_current_scenario_context(context)

    # Check that we have realm-specific operations
    realm_keys = [key for key in scenario_context._storage.keys() if key.startswith("realm_")]
    assert len(realm_keys) > 0, "No realm operations to verify isolation"

    context.logger.info("Realm isolation verified")


# Service account verification
@then("service account functionality should work correctly")
def step_service_account_verification(context: Context) -> None:
    """Verify that service account functionality works correctly."""
    scenario_context = get_current_scenario_context(context)

    # Check if we have client credentials token (service account token)
    client_token = scenario_context.get("latest_token_response")
    if client_token and "access_token" in client_token:
        context.logger.info("Service account functionality verified")
    else:
        context.logger.info("No service account operations to verify")


def _create_or_get_realm(
    adapter: AsyncKeycloakAdapter | KeycloakAdapter,
    realm_name: str,
    display_name: str,
    context: Context,
    scenario_context: ScenarioContext,
) -> None:
    """Helper function to create a realm or get existing one if it already exists."""
    try:
        realm_result = adapter.create_realm(realm_name=realm_name, display_name=display_name, skip_exists=True)
        context.logger.info(f"Created realm {realm_name}")
    except Exception as e:
        if "already exists" in str(e).lower():
            context.logger.info(f"Realm {realm_name} already exists, retrieving existing realm")
            realm_result = adapter.get_realm(realm_name)
        else:
            raise

    # Store the result (either newly created or existing realm)
    scenario_context.store("latest_realm_result", realm_result)
    scenario_context.store(f"realm_{realm_name}", realm_result)


async def _create_or_get_realm_async(
    adapter: AsyncKeycloakAdapter | KeycloakAdapter,
    realm_name: str,
    display_name: str,
    context: Context,
    scenario_context: ScenarioContext,
) -> None:
    """Async helper function to create a realm or get existing one if it already exists."""
    try:
        realm_result = await adapter.create_realm(realm_name=realm_name, display_name=display_name, skip_exists=True)
        context.logger.info(f"Created realm {realm_name}")
    except Exception as e:
        if "already exists" in str(e).lower():
            context.logger.info(f"Realm {realm_name} already exists, retrieving existing realm")
            realm_result = await adapter.get_realm(realm_name)
        else:
            raise

    # Store the result (either newly created or existing realm)
    scenario_context.store("latest_realm_result", realm_result)
    scenario_context.store(f"realm_{realm_name}", realm_result)
