---
title: Keycloak Adapter Tutorial
description: Practical examples for using the ArchiPy Keycloak adapter.
---

# Keycloak Adapter Tutorial

The Keycloak adapter provides an interface for interacting with Keycloak's API to manage authentication and
authorization. ArchiPy offers both synchronous and asynchronous implementations.

## Installation

```bash
uv add "archipy[keycloak]"
```

For full API reference, see the [Keycloak Adapters API Documentation](../../api_reference/adapters/keycloak.md).

## Configuration

Configure the Keycloak adapter via environment variables or a `KeycloakConfig` object.

### Environment Variables

!!! warning
    Keep `KEYCLOAK__CLIENT_SECRET_KEY` out of source control. Load it from the environment or a secrets store, and keep
    `KEYCLOAK__VERIFY_SSL=true` outside local development.

```bash
KEYCLOAK__SERVER_URL=https://keycloak.example.com
KEYCLOAK__REALM_NAME=my-realm
KEYCLOAK__CLIENT_ID=my-client
KEYCLOAK__CLIENT_SECRET_KEY=client-secret
KEYCLOAK__VERIFY_SSL=true  # true, false, or the path of a CA bundle for a private CA
KEYCLOAK__TIMEOUT=10  # seconds, fractions allowed (2.5)
KEYCLOAK__TOKEN_LEEWAY_SECONDS=0  # clock-skew tolerance when validating token expiry
KEYCLOAK__EXPECTED_ISSUER=https://keycloak.example.com/realms/my-realm  # enforce the iss claim (and typ=Bearer) of locally verified tokens
KEYCLOAK__EXPECTED_AUDIENCE=my-client  # enforce the aud claim (and typ=Bearer) of locally verified tokens
KEYCLOAK__REMOTE_CACHE_TTL_SECONDS=0  # opt-in cache for the keycloak auth guards' UserInfo/permission lookups (0 = off)
```

!!! warning "Token claim checks"
    Local verification (`validate_token`, `get_token_info`, role checks) always checks the signature and expiry. Set
    `KEYCLOAK__EXPECTED_ISSUER` and/or `KEYCLOAK__EXPECTED_AUDIENCE` to also require the `iss` / `aud` claims and
    `typ == "Bearer"`; mismatching tokens are rejected (`validate_token` returns `False`, `get_token_info` raises
    `InvalidTokenError`). Without these settings a mismatch only emits a `DeprecationWarning`, and enforcement becomes
    the default in 6.0.

### Connection Options

Optional settings for private CAs, mutual TLS, retries, pooling, proxies and extra headers. The defaults keep the
previous behaviour.

| Setting            | Default | Meaning                                                                          |
|--------------------|---------|----------------------------------------------------------------------------------|
| `VERIFY_SSL`       | `true`  | `true`/`false`, or a CA bundle path to verify the server against                 |
| `TIMEOUT`          | `10`    | Request timeout in seconds, fractions allowed                                    |
| `CLIENT_CERT_FILE` | none    | Client certificate (PEM) for mutual TLS; a combined cert and key file needs no key |
| `CLIENT_KEY_FILE`  | none    | Private key of `CLIENT_CERT_FILE` (requires `CLIENT_CERT_FILE`)                  |
| `MAX_RETRIES`      | `1`     | Total times a request to Keycloak is retried                                     |
| `POOL_MAXSIZE`     | none    | Maximum connections kept in the pool                                             |
| `PROXIES`          | none    | Proxy URL by URL pattern, e.g. `{"https://": "http://proxy:3128"}`               |
| `CUSTOM_HEADERS`   | none    | Extra headers sent with every request                                            |

```bash
KEYCLOAK__VERIFY_SSL=/etc/ssl/private-ca.pem
KEYCLOAK__CLIENT_CERT_FILE=/etc/ssl/client.pem
KEYCLOAK__CLIENT_KEY_FILE=/etc/ssl/client.key
KEYCLOAK__PROXIES='{"https://": "http://proxy:3128"}'
KEYCLOAK__CUSTOM_HEADERS='{"X-Tenant": "acme"}'
```

!!! note
    python-keycloak has no separate connect and read timeouts, so `TIMEOUT` is one value. The async admin and UMA
    clients do not take `PROXIES` (python-keycloak accepts no proxies for them); the async OpenID client and every
    synchronous client do.

### Direct Configuration

```python
from archipy.configs.config_template import KeycloakConfig

config = KeycloakConfig(
    SERVER_URL="https://keycloak.example.com",
    REALM_NAME="my-realm",
    CLIENT_ID="my-client",
    CLIENT_SECRET_KEY="client-secret",  # noqa: S105
    VERIFY_SSL=True,
    TIMEOUT=10,
)
```

## Basic Usage

The Keycloak adapter provides both synchronous and asynchronous implementations. Use the synchronous adapter for
standard request-response flows and the asynchronous adapter with `async/await` patterns.

### Synchronous Adapter

The synchronous adapter provides a blocking API for Keycloak operations.

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.configs.config_template import KeycloakConfig
from archipy.models.dtos.keycloak.user_dtos import KeycloakCredentialRequestDTO, KeycloakUserRequestDTO
from archipy.models.errors import (
    InternalError,
    InvalidCredentialsError,
    ResourceNotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
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
    CLIENT_SECRET_KEY="client-secret",  # noqa: S105
)
keycloak = KeycloakAdapter(custom_config)

# Authentication
try:
    # Get token with username/password
    token = keycloak.get_token("username", "password")
except InvalidCredentialsError as e:
    logger.error(f"Authentication failed: {e}")
    raise
else:
    access_token = token.access_token
    refresh_token = token.refresh_token
    logger.info("Authentication successful")

try:
    # Refresh an existing token
    new_token = keycloak.refresh_token(refresh_token)
except (UnauthenticatedError, InvalidCredentialsError) as e:
    logger.error(f"Token refresh failed: {e}")
    raise
else:
    logger.info("Token refreshed successfully")

try:
    # Validate a token
    is_valid = keycloak.validate_token(access_token)
except UnauthenticatedError as e:
    logger.error(f"Token validation failed: {e}")
    raise
else:
    logger.info(f"Token valid: {is_valid}")

try:
    # Get user info from token
    user_info = keycloak.get_userinfo(access_token)
except (UnauthenticatedError, InternalError) as e:
    logger.error(f"Failed to get user info: {e}")
    raise
else:
    logger.info(f"User info retrieved: {user_info.preferred_username}")

try:
    # Get token using client credentials
    client_token = keycloak.get_client_credentials_token()
except InvalidCredentialsError as e:
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
except ResourceNotFoundError as e:
    logger.error(f"User not found: {e}")
    raise
except PermissionDeniedError as e:
    logger.error(f"Permission denied: {e}")
    raise
else:
    logger.info(f"User retrieved: {user.username}")

try:
    # Get user by username
    user = keycloak.get_user_by_username("johndoe")
except ResourceNotFoundError as e:
    logger.error(f"User not found: {e}")
    raise
else:
    logger.info(f"User retrieved by username: {user.username}")

try:
    # Get user by email
    user = keycloak.get_user_by_email("john@example.com")
except ResourceNotFoundError as e:
    logger.error(f"User not found by email: {e}")
    raise
else:
    logger.info(f"User retrieved by email: {user.username}")

try:
    # Create a new user
    user_data = KeycloakUserRequestDTO(
        username="newuser",
        email="newuser@example.com",
        enabled=True,
        first_name="New",
        last_name="User",
        credentials=[
            KeycloakCredentialRequestDTO(type="password", value="initial-password", temporary=True),
        ],
    )
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
    keycloak.update_user(user_id, KeycloakUserRequestDTO(first_name="Updated", email="updated@example.com"))
except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to update user: {e}")
    raise
else:
    logger.info(f"User updated: {user_id}")

try:
    # Reset password
    keycloak.reset_password(user_id, "new-password", temporary=True)
except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
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
except (ResourceNotFoundError, InternalError) as e:
    logger.error(f"Failed to clear sessions: {e}")
    raise
else:
    logger.info(f"Sessions cleared for user: {user_id}")

try:
    # Delete a user
    keycloak.delete_user(user_id)
except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Failed to delete user: {e}")
    raise
else:
    logger.info(f"User deleted: {user_id}")

# Role operations
try:
    # Get user roles
    roles = keycloak.get_user_roles(user_id)
except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
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
except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Keycloak role operation failed: {e}")
    raise

# Client operations
try:
    # Get client ID from name
    client_id = keycloak.get_client_id("client-name")

    # Get client secret
    secret = keycloak.get_client_secret(client_id)

    # Get service account ID
    service_account_id = keycloak.get_service_account_id()
except (ResourceNotFoundError, InternalError) as e:
    logger.error(f"Keycloak client operation failed: {e}")
    raise

# System operations
try:
    # Get public key for token verification
    public_key = keycloak.get_public_key()

    # Get well-known OpenID configuration
    config = keycloak.get_well_known_config()

    # Get JWT certificates
    certs = keycloak.get_certs()
except InternalError as e:
    logger.error(f"Keycloak system operation failed: {e}")
    raise

# Authorization
try:
    # Exchange authorization code for token
    token = keycloak.get_token_from_code("auth-code", "https://my-app.example.com/callback")

    # Check permissions
    has_permission = keycloak.check_permissions(access_token, "resource-name", "view")
except (UnauthenticatedError, PermissionDeniedError, InternalError) as e:
    logger.error(f"Keycloak authorization operation failed: {e}")
    raise
```

### Asynchronous Adapter

The asynchronous adapter provides a non-blocking API using `async/await` syntax:

```python
import asyncio
import logging

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserRequestDTO
from archipy.models.errors import (
    InternalError,
    InvalidCredentialsError,
    ResourceNotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    # Initialize with global config
    keycloak = AsyncKeycloakAdapter()

    try:
        # Get token
        token = await keycloak.get_token("username", "password")
        access_token = token.access_token
    except InvalidCredentialsError as e:
        logger.error(f"Authentication failed: {e}")
        raise
    else:
        logger.info("Authentication successful")

    try:
        # Get user info
        user_info = await keycloak.get_userinfo(access_token)
        logger.info(f"Logged in as: {user_info.preferred_username}")

        # Check if user has role
        if await keycloak.has_role(access_token, "admin"):
            logger.info("User has admin role")
    except (UnauthenticatedError, InternalError) as e:
        logger.error(f"Failed to get user info or check role: {e}")
        raise

    try:
        # Search for users
        users = await keycloak.search_users("john")
        logger.info(f"Found {len(users)} users matching 'john'")

        # Create a new user
        user_data = KeycloakUserRequestDTO(username="async_user", email="async@example.com", enabled=True)
        user_id = await keycloak.create_user(user_data)
        logger.info(f"Created user with ID: {user_id}")

        # Delete the user
        await keycloak.delete_user(user_id)
        logger.info(f"Deleted user: {user_id}")
    except (ResourceNotFoundError, PermissionDeniedError, InternalError) as e:
        logger.error(f"User management operation failed: {e}")
        raise


# Run the async function
asyncio.run(main())
```

## Advanced Features

### Groups

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

group_id = keycloak.create_group(payload=KeycloakGroupRequestDTO(name="engineering"), skip_exists=True)
groups = keycloak.get_groups()
logger.info("Group %s created; realm has %d groups", group_id, len(groups))
```

### Authentication Flows

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

flows = keycloak.get_authentication_flows()
browser_flow = next(flow for flow in flows if flow.alias == "browser")
logger.info("Browser flow id: %s", browser_flow.id)
```

### Client Scopes

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

scopes = keycloak.get_client_scopes()
scope_id = keycloak.create_client_scope(
    payload=KeycloakClientScopeRequestDTO(name="custom-audience", protocol="openid-connect"),
    skip_exists=True,
)
default_scopes = keycloak.get_default_default_client_scopes()
logger.info("Created scope %s; realm has %d default scopes", scope_id, len(default_scopes))
```

### Authorization Services

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzResourceRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

client_id = keycloak.get_client_id("my-client")
settings = keycloak.get_client_authz_settings(client_id=client_id)
resource = keycloak.create_client_authz_resource(
    client_id=client_id,
    payload=KeycloakAuthzResourceRequestDTO(name="Account", display_name="Account", uris=["/account/*"]),
    skip_exists=True,
)
policies = keycloak.get_client_authz_policies(client_id=client_id)
logger.info("Authz enabled=%s; created resource %s", settings.allow_remote_resource_management, resource.id)
```

### UMA Resource Sets

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.uma_dtos import KeycloakUmaResourceRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

resource = keycloak.resource_set_create(
    payload=KeycloakUmaResourceRequestDTO(name="Protected API", scopes=["read", "write"], type="api"),
)
resource_sets = keycloak.resource_set_list()
logger.info("UMA resource %s; total sets=%d", resource.internal_id, len(resource_sets))
```

### Components

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.component_dtos import KeycloakComponentRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

components = keycloak.get_components(query={"type": "org.keycloak.storage.UserStorageProvider"})
component_id = keycloak.create_component(
    payload=KeycloakComponentRequestDTO(
        name="ldap",
        provider_id="ldap",
        provider_type="org.keycloak.storage.UserStorageProvider",
    ),
)
logger.info("Listed %d components; created component %s", len(components), component_id)
```

### DTOs

Every Keycloak adapter method takes and returns pydantic DTOs from `archipy.models.dtos.keycloak`:

- **Responses** (`KeycloakUserDTO`, `KeycloakRoleDTO`, `KeycloakTokenDTO`, ...) use snake_case attributes and keep
  fields unknown to ArchiPy in `model_extra`, so a newer Keycloak never breaks parsing.
- **Requests** (`KeycloakUserRequestDTO`, `KeycloakGroupRequestDTO`, ...) reject unknown fields, so a typo fails before
  the call instead of as a Keycloak `400`.
- `to_payload()` returns the camelCase JSON Keycloak receives.

```python
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO

group_id = keycloak.create_group(payload=KeycloakGroupRequestDTO(name="engineering"))
group = keycloak.get_group(group_id)
logger.info("Group %s at %s", group.name, group.path)
```

!!! warning "Deprecated: dicts"
    Passing a `dict` payload and reading results with `result["key"]` or `result.get("key")` still work but emit a
    `DeprecationWarning`. Both are removed in 6.0.0. See [Create Results and Ids](#create-results-and-ids).

### Resources Overview

Both adapters expose one method group per Keycloak resource area. Every method exists on `KeycloakAdapter` and, as a
coroutine, on `AsyncKeycloakAdapter`.

| Area                       | Example methods                                                                                            |
|----------------------------|------------------------------------------------------------------------------------------------------------|
| Realms                     | `create_realm`, `get_realm`, `get_realm_events`, `partial_export_realm`, `partial_import_realm`            |
| Users                      | `create_user`, `get_users`, `get_user_credentials`, `get_user_sessions`, `impersonate_user`                |
| Groups                     | `create_group`, `get_group_by_path`, `get_group_members`, `assign_group_realm_roles`                       |
| Roles                      | `create_realm_role`, `create_client_role`, `add_realm_roles_to_composite`, `has_role`                      |
| Roles by id                | `get_role_by_id`, `update_role_by_id`, `get_role_composites_by_id`                                         |
| Role mappings              | `get_user_role_mappings`, `add_user_realm_role_mappings`, `get_group_role_mappings`                        |
| Scope mappings             | `get_client_scope_mappings`, `add_client_realm_scope_mappings`, `get_client_scope_scope_mappings`          |
| Clients                    | `create_client`, `regenerate_client_secret`, `get_client_example_access_token`, `get_client_user_sessions` |
| Client scopes              | `create_client_scope`, `add_client_default_client_scope`, `get_default_optional_client_scopes`             |
| Protocol mappers           | `add_mapper_to_client`, `get_mappers_from_client_scope`, `update_client_mapper`                            |
| Organizations              | `create_organization`, `organization_user_add`, `organization_idp_add`, `get_organization_invitations`     |
| Organization groups        | `create_organization_group`, `create_organization_subgroup`, `assign_organization_group_realm_roles`       |
| Identity providers         | `create_identity_provider`, `create_identity_provider_mapper`, `export_identity_provider`                  |
| Authentication flows       | `copy_authentication_flow`, `get_authentication_flow_executions`, `create_execution_config`                |
| Required actions           | register, enable and reorder required actions of the realm                                                 |
| Authorization services     | `create_client_authz_resource`, `create_client_authz_policy`, `get_client_authz_settings`                  |
| UMA                        | `resource_set_create`, `policy_query`, `permission_ticket_create`, `permissions_check`                     |
| Components                 | `create_component`, `get_components`, `update_component`                                                   |
| Keys                       | `get_realm_keys`                                                                                           |
| Attack detection           | `get_user_brute_force_status`, `clear_user_brute_force`, `clear_all_brute_force`                           |
| Client initial access      | `create_client_initial_access`, `get_client_initial_access_tokens`, `delete_client_initial_access`         |
| Client certificates        | `get_client_certificate`, `generate_client_certificate`, `download_client_keystore`                        |
| Client registration policy | `get_client_registration_policy_providers`                                                                 |

```python
import logging

from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.client_initial_access_dtos import KeycloakClientInitialAccessCreateRequestDTO

logger = logging.getLogger(__name__)
keycloak = KeycloakAdapter()

keys = keycloak.get_realm_keys()
user = keycloak.get_user_by_username("johndoe")
status = keycloak.get_user_brute_force_status(user.id)
initial_access = keycloak.create_client_initial_access(
    KeycloakClientInitialAccessCreateRequestDTO(expiration=3600, count=5),
)
logger.info("Realm keys: %s; brute force status: %s; token: %s", keys, status, initial_access.token)
```

The same calls work asynchronously:

```python
from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter


async def lock_status(username: str):
    keycloak = AsyncKeycloakAdapter()
    user = await keycloak.get_user_by_username(username)
    return await keycloak.get_user_brute_force_status(user.id)
```

!!! note "Exact signatures"
    Method names and signatures live in the port classes of
    [`archipy.adapters.keycloak.ports`](../../api_reference/adapters/keycloak.md). Many of these calls go through the
    admin connection because `python-keycloak` has no helper for them.

### Token Exchange

`token_exchange` takes a `KeycloakTokenExchangeRequestDTO` and returns a `KeycloakTokenExchangeResponseDTO` (the issued
token in `access_token`, its type in `issued_token_type`). It covers the standard
token exchange V2, the delegation preview (the issued token carries an `act` claim naming the actor), and the legacy
fields of V1.

```python
from archipy.adapters.keycloak.adapters import KeycloakAdapter
from archipy.models.dtos.keycloak.token_exchange_dtos import KeycloakTokenExchangeRequestDTO

keycloak = KeycloakAdapter()

exchanged = keycloak.token_exchange(
    KeycloakTokenExchangeRequestDTO(subject_token=access_token, audience="downstream-service"),
)
```

The older `exchange_token(subject_token, requested_subject=..., audience=..., scope=...)` stays available for simple
impersonation.

!!! warning "Server features"
    Delegation is a Keycloak preview feature, and the legacy fields need the legacy exchange feature on the server.
    Enable them in Keycloak before relying on them.

### JWT Bearer Grant

`jwt_bearer_grant` sends an assertion JWT to the token endpoint (RFC 7523). ID-JAG (identity assertion authorization
grant) and chaining across domains are two separate primitives: use `token_exchange` to obtain the assertion at the
first domain, then `jwt_bearer_grant` to redeem it at the second.

```python
assertion = keycloak.token_exchange(
    KeycloakTokenExchangeRequestDTO(
        subject_token=access_token,
        audience="https://keycloak.example.com/realms/domainb",
        scope="access-domainb",
    ),
).access_token
token = second_domain_keycloak.jwt_bearer_grant(assertion, scope="profile")
```

The token returned by the second realm has no refresh token. The client must be confidential and allowed to use the
identity provider that represents the first realm.

### RPT Requests

`request_rpt` asks the token endpoint for a requesting party token (RPT) that carries the permissions the policies
grant to the given access token.

```python
rpt = keycloak.request_rpt(access_token, audience="my-resource-server")
```

### AuthZEN

!!! warning "Experimental"
    AuthZEN needs the server `authzen` feature enabled. Keycloak requires the resource `type` in practice, so always
    set it.

`get_authzen_configuration` reads the discovery document. `authzen_evaluation` answers one access question and
`authzen_evaluations` answers several in one call.

```python
from archipy.models.dtos.keycloak.authzen_dtos import (
    KeycloakAuthzenActionDTO,
    KeycloakAuthzenEvaluationRequestDTO,
    KeycloakAuthzenResourceDTO,
    KeycloakAuthzenSubjectDTO,
)

config = keycloak.get_authzen_configuration()
decision = keycloak.authzen_evaluation(
    client_access_token,  # a token issued to a client with authorization enabled
    KeycloakAuthzenEvaluationRequestDTO(
        subject=KeycloakAuthzenSubjectDTO(type="user", id="alice"),
        resource=KeycloakAuthzenResourceDTO(type="document", id="quarterly-report"),
        action=KeycloakAuthzenActionDTO(name="read"),
    ),
)
print(decision.decision)
```

`authzen_evaluations(token, KeycloakAuthzenEvaluationsRequestDTO(...))` takes the same token and a batch whose top-level
`subject`, `resource`, `action` and `context` are defaults for each entry in `evaluations`.

The request and response DTOs live in `archipy.models.dtos.keycloak.authzen_dtos`.

### Create Results and Ids

Keycloak answers creates with an empty body. Calls that return `KeycloakCreateResultDTO` look the new resource up, so
`result.id` is set when the adapter can find it. With `skip_exists=True` an existing resource gives
`msg == "Already exists"` and `id is None`. Updates, deletes and assignments return `KeycloakUpdateResultDTO`,
`KeycloakDeleteResultDTO` and `KeycloakAssignResultDTO`. All four live in `archipy.models.dtos.keycloak.common_dtos`.

```python
result = keycloak.create_identity_provider(identity_provider_request)
if result.id is None:
    logger.info("Provider skipped: %s", result.msg)
```

!!! warning "Deprecated: dicts"
    Dict payloads and dict-style reads (`result["id"]`, `result.get("id")`) still work but emit a `DeprecationWarning`.
    They are removed in 6.0.0. Use the request DTOs and the attributes of the response DTOs.

### Error Mapping

The adapter maps Keycloak failures to ArchiPy errors, chained with `from`. A `404` raises `ResourceNotFoundError`,
bad credentials raise `InvalidCredentialsError`, and a forbidden call raises `InsufficientPermissionsError`.
A `409` raises the `*AlreadyExistsError` of the resource the operation works on (or `ConflictError` when it names none),
a `429` raises `RateLimitExceededError`, and a `5xx` raises `KeycloakServiceUnavailableError` (`502`, `503`, `504`) or
`InternalError`. The status code decides before any message text is read. Keycloak's own message reaches callers in
`additional_data["original_error"]` for `4xx` answers only; a `5xx` or connection failure is logged and its message
is left out, since it can carry internals such as database URLs.

```python
from archipy.models.errors import ResourceNotFoundError

try:
    keycloak.get_organization("missing-id")
except ResourceNotFoundError:
    logger.warning("Organization does not exist")
```

### Not Supported

The adapter does not wrap these Keycloak endpoints:

- Workflows: the server answers with YAML.
- Endpoints with `text/plain`, multipart or form-encoded bodies: credential label, localization of a single text, the
  client description converter, certificate upload, and the organization `invite-user` and `invite-existing-user`
  calls.

### Caching

Both adapters use TTL (Time-To-Live) caching for appropriate operations to improve performance. Cache durations are
configured for each method based on how frequently the data typically changes:

- Public keys and certificate information: 1 hour
- Realm JWKS used for local token verification: 1 hour, fetched again (at most every 10 seconds) when a token names an unknown `kid`, so a rotated signing key is picked up
- User information from tokens: 30 seconds
- User details and role information: 5 minutes

!!! note
    Token validation is never cached. If Keycloak cannot be reached while its JWKS is fetched, `validate_token` and `get_token_info` raise `ServiceUnavailableError` instead of reporting an invalid token. Write operations such as user creation and updates clear the relevant caches.

You can clear all caches if needed. `clear_all_caches()` works with or without admin mode: it never builds the admin
client or logs in to Keycloak.

=== "Sync"

    ```python
    from archipy.adapters.keycloak.adapters import KeycloakAdapter

    keycloak = KeycloakAdapter()
    keycloak.clear_all_caches()
    ```

=== "Async"

    ```python
    from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter

    async_keycloak = AsyncKeycloakAdapter()
    async_keycloak.clear_all_caches()
    ```

## Security Considerations

!!! warning
    `KEYCLOAK__REMOTE_CACHE_TTL_SECONDS` trades freshness for fewer Keycloak calls. While it is set above `0`, a revoked
    token or a changed permission stays accepted until the cached entry expires.

- Token validation is performed without caching to ensure security.
- The adapter automatically refreshes admin tokens before they expire.
- Write operations (like user creation/updates) automatically clear relevant caches.
- For production use, prefer the authorization code flow over direct username/password authentication.
- The auth guards' role checks read `realm_access` and `resource_access` from the UserInfo response. Stock Keycloak
  omits them there, so enable "Add to userinfo" on the realm roles and client roles mappers of the `roles` client scope.
- Token expiry is checked locally with `KEYCLOAK__TOKEN_LEEWAY_SECONDS` (default `0`) of clock-skew tolerance; raise it
  only if your servers' clocks drift.
- The auth guards call Keycloak for UserInfo (and UMA permissions) on every request. Set
  `KEYCLOAK__REMOTE_CACHE_TTL_SECONDS` to a few seconds to cache those lookups per access token. A revoked token or a
  changed permission then stays accepted for up to that long, so it is off (`0`) by default.
  `clear_keycloak_remote_cache()` drops the cache.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Keycloak configuration setup
- [BDD Testing](../testing_strategy.md) — Testing Keycloak operations
- [Keycloak Utils](../helpers/utils.md#keycloak-utils) — Authentication utilities with Keycloak
- BDD feature files — [`keycloak_adapter.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/keycloak_adapter.feature), [`keycloak_adapter_apm.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/keycloak_adapter_apm.feature), [`keycloak_adapter_management.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/keycloak_adapter_management.feature), [`keycloak_adapter_tokens_orgs.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/keycloak_adapter_tokens_orgs.feature)
- [API Reference](../../api_reference/adapters/keycloak.md) — Full Keycloak adapter API documentation
