# Keycloak Adapter Usage Guide

The Keycloak adapter provides an interface for interacting with Keycloak's API to manage authentication and
authorization. ArchiPy offers both synchronous and asynchronous implementations.

For full API reference, see the [Keycloak Adapters API Documentation](../../api_reference/adapters.md#keycloak).

## Configuration

First, configure your Keycloak settings in your application config:

```python
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import KeycloakConfig

class AppConfig(BaseConfig):
    # Keycloak configuration
    KEYCLOAK = KeycloakConfig(
        SERVER_URL="https://keycloak.example.com",
        REALM_NAME="my-realm",
        CLIENT_ID="my-client",
        CLIENT_SECRET_KEY="client-secret",  # Optional, required for admin operations
        VERIFY_SSL=True,
        TIMEOUT=10
    )
```

## Synchronous Adapter

The synchronous adapter provides a blocking API for Keycloak operations.

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.errors import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    InternalError
)

# Configure logging
logger = logging.getLogger(__name__)

# Using global configuration
keycloak = KeycloakAdapter()

# Or with custom configuration
custom_config = KeycloakConfig(
    SERVER_URL="https://keycloak.example.com",
    REALM_NAME="another-realm",
    CLIENT_ID="another-client",
    CLIENT_SECRET_KEY="client-secret"
)
keycloak = KeycloakAdapter(custom_config)

# Authentication
try:
    # Get token with username/password
    token = keycloak.get_token("username", "password")
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e}")
    raise
else:
    access_token = token["access_token"]
    refresh_token = token["refresh_token"]
    logger.info("Authentication successful")

try:
    # Refresh an existing token
    new_token = keycloak.refresh_token(refresh_token)
except AuthenticationError as e:
    logger.error(f"Token refresh failed: {e}")
    raise
else:
    logger.info("Token refreshed successfully")

try:
    # Validate a token
    is_valid = keycloak.validate_token(access_token)
except AuthenticationError as e:
    logger.error(f"Token validation failed: {e}")
    raise
else:
    logger.info(f"Token valid: {is_valid}")

try:
    # Get user info from token
    user_info = keycloak.get_userinfo(access_token)
except (AuthenticationError, InternalError) as e:
    logger.error(f"Failed to get user info: {e}")
    raise
else:
    logger.info(f"User info retrieved: {user_info.get('preferred_username')}")

try:
    # Get token using client credentials
    client_token = keycloak.get_client_credentials_token()
except AuthenticationError as e:
    logger.error(f"Client credentials authentication failed: {e}")
    raise
else:
    logger.info("Client token obtained")

try:
    # Logout (invalidate refresh token)
    keycloak.logout(refresh_token)
except InternalError as e:
    logger.error(f"Logout failed: {e}")
    raise
else:
    logger.info("Logout successful")

# User operations (requires admin privileges)
try:
    # Get user by ID
    user = keycloak.get_user_by_id("user-uuid")
except NotFoundError as e:
    logger.error(f"User not found: {e}")
    raise
except PermissionDeniedError as e:
    logger.error(f"Permission denied: {e}")
    raise
else:
    logger.info(f"User retrieved: {user.get('username')}")

try:
    # Get user by username
    user = keycloak.get_user_by_username("johndoe")
except NotFoundError as e:
    logger.error(f"User not found: {e}")
    raise
else:
    logger.info(f"User retrieved by username: {user.get('username')}")

try:
    # Get user by email
    user = keycloak.get_user_by_email("john@example.com")
except NotFoundError as e:
    logger.error(f"User not found by email: {e}")
    raise
else:
    logger.info(f"User retrieved by email: {user.get('username')}")

try:
    # Create a new user
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "enabled": True,
        "firstName": "New",
        "lastName": "User",
        "credentials": [{
            "type": "password",
            "value": "initial-password",
            "temporary": True
        }]
    }
    user_id = keycloak.create_user(user_data)
except PermissionDeniedError as e:
    logger.error(f"Permission denied to create user: {e}")
    raise
except InternalError as e:
    logger.error(f"Failed to create user: {e}")
    raise
else:
    logger.info(f"User created with ID: {user_id}")

try:
    # Update a user
    update_data = {"firstName": "Updated", "email": "updated@example.com"}
    keycloak.update_user(user_id, update_data)
except (NotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to update user: {e}")
    raise
else:
    logger.info(f"User updated: {user_id}")

try:
    # Reset password
    keycloak.reset_password(user_id, "new-password", temporary=True)
except (NotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to reset password: {e}")
    raise
else:
    logger.info(f"Password reset for user: {user_id}")

try:
    # Search for users
    users = keycloak.search_users("john", max_results=10)
except InternalError as e:
    logger.error(f"Failed to search users: {e}")
    raise
else:
    logger.info(f"Found {len(users)} users")

try:
    # Clear all user sessions
    keycloak.clear_user_sessions(user_id)
except (NotFoundError, InternalError) as e:
    logger.error(f"Failed to clear sessions: {e}")
    raise
else:
    logger.info(f"Sessions cleared for user: {user_id}")

try:
    # Delete a user
    keycloak.delete_user(user_id)
except (NotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to delete user: {e}")
    raise
else:
    logger.info(f"User deleted: {user_id}")

# Role operations
try:
    # Get user roles
    roles = keycloak.get_user_roles(user_id)
except (NotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to get user roles: {e}")
    raise
else:
    logger.info(f"User has {len(roles)} roles")

try:

    # Get client roles for user
    client_roles = keycloak.get_client_roles_for_user(user_id, "client-id")

    # Check if user has role
    has_role = keycloak.has_role(access_token, "admin")

    # Check if user has any of the specified roles
    has_any = keycloak.has_any_of_roles(access_token, {"admin", "manager"})

    # Check if user has all specified roles
    has_all = keycloak.has_all_roles(access_token, {"user", "viewer"})

    # Assign realm role
    keycloak.assign_realm_role(user_id, "admin")

    # Remove realm role
    keycloak.remove_realm_role(user_id, "admin")

    # Assign client role
    keycloak.assign_client_role(user_id, "client-id", "client-admin")

    # Remove client role
    keycloak.remove_client_role(user_id, "client-id", "client-admin")

    # Get realm roles
    all_roles = keycloak.get_realm_roles()

    # Get a specific realm role
    role = keycloak.get_realm_role("admin")

    # Create a realm role
    new_role = keycloak.create_realm_role("new-role", "A new role description")

    # Delete a realm role
    keycloak.delete_realm_role("new-role")
except ValueError as e:
    print(f"Keycloak error: {e}")

# Client operations
try:
    # Get client ID from name
    client_id = keycloak.get_client_id("client-name")

    # Get client secret
    secret = keycloak.get_client_secret(client_id)

    # Get service account ID
    service_account_id = keycloak.get_service_account_id()
except ValueError as e:
    print(f"Keycloak error: {e}")

# System operations
try:
    # Get public key for token verification
    public_key = keycloak.get_public_key()

    # Get well-known OpenID configuration
    config = keycloak.get_well_known_config()

    # Get JWT certificates
    certs = keycloak.get_certs()
except ValueError as e:
    print(f"Keycloak error: {e}")

# Authorization
try:
    # Exchange authorization code for token
    token = keycloak.get_token_from_code("auth-code", "https://my-app.example.com/callback")

    # Check permissions
    has_permission = keycloak.check_permissions(access_token, "resource-name", "view")
except ValueError as e:
    print(f"Keycloak error: {e}")
```

## Asynchronous Adapter

The asynchronous adapter provides a non-blocking API using `async/await` syntax:

```python
import asyncio
from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter

async def main():
    # Initialize with global config
    keycloak = AsyncKeycloakAdapter()

    try:
        # Get token
        token = await keycloak.get_token("username", "password")
        access_token = token["access_token"]

        # Get user info
        user_info = await keycloak.get_userinfo(access_token)
        print(f"Logged in as: {user_info.get('preferred_username')}")

        # Check if user has role
        if await keycloak.has_role(access_token, "admin"):
            print("User has admin role")

        # Search for users
        users = await keycloak.search_users("john")
        print(f"Found {len(users)} users matching 'john'")

        # Create a new user
        user_data = {
            "username": "async_user",
            "email": "async@example.com",
            "enabled": True,
        }
        user_id = await keycloak.create_user(user_data)
        print(f"Created user with ID: {user_id}")

        # Delete the user
        await keycloak.delete_user(user_id)
    except ValueError as e:
        print(f"Keycloak error: {e}")

# Run the async function
asyncio.run(main())
```

## Caching

Both adapters use TTL (Time-To-Live) caching for appropriate operations to improve performance. Cache durations are
configured for each method based on how frequently the data typically changes:

- Public keys and certificate information: 1 hour
- User information from tokens: 30 seconds
- User details and role information: 5 minutes

You can clear all caches if needed:

```python
# Sync adapter
keycloak = KeycloakAdapter()
keycloak.clear_all_caches()

# Async adapter
async_keycloak = AsyncKeycloakAdapter()
async_keycloak.clear_all_caches()
```

## Security Considerations

- Token validation is performed without caching to ensure security.
- The adapter automatically refreshes admin tokens before they expire.
- Write operations (like user creation/updates) automatically clear relevant caches.
- For production use, prefer the authorization code flow over direct username/password authentication.

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - Keycloak configuration setup
- [BDD Testing](../bdd_testing.md) - Testing Keycloak operations
- [Keycloak Adapter Feature](../../features/keycloak_adapter.feature) - BDD test scenarios for Keycloak
- [Keycloak Utils](../helpers/utils.md#keycloak-utils) - Authentication utilities with Keycloak
- [API Reference](../../api_reference/adapters.md) - Full Keycloak adapter API documentation
