from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.common_dtos import KeycloakImpersonationDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakFederatedIdentityRequestDTO
from archipy.models.dtos.keycloak.user_profile_dtos import KeycloakUserProfileConfigDTO, KeycloakUserProfileMetadataDTO

HTTP_INTERNAL_ERROR = 500


@then('the users are counted and filtered, and the user "{username}" has credentials, no consents and no unmanaged attributes using {adapter_type} adapter')
async def step_users_counted_and_credentials(context: Context, username: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    assert await _adapter_call(adapter, is_async, "count_users") >= 1
    assert await _adapter_call(adapter, is_async, "count_users", {"username": username, "exact": True}) == 1
    users = await _adapter_call(adapter, is_async, "get_users", {"username": username, "exact": True})
    assert [u.id for u in users] == [user_id], users
    credentials = await _adapter_call(adapter, is_async, "get_user_credentials", user_id)
    assert [c.type for c in credentials] == ["password"], credentials
    await _adapter_call(adapter, is_async, "move_user_credential_to_first", user_id, credentials[0].id)
    types = await _adapter_call(adapter, is_async, "get_user_configured_credential_types", user_id)
    assert isinstance(types, list), types
    assert await _adapter_call(adapter, is_async, "get_user_consents", user_id) == []
    assert await _adapter_call(adapter, is_async, "get_user_unmanaged_attributes", user_id) == {}


@when('I add user "{username}" to a new group "{group}" using {adapter_type} adapter')
async def step_add_user_to_new_group(context: Context, username: str, group: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    group_id = await _adapter_call(adapter, is_async, "create_group", KeycloakGroupRequestDTO(name=group), skip_exists=True)
    await _adapter_call(adapter, is_async, "group_user_add", user_id=sc.get(f"user_id_{username}"), group_id=group_id)
    sc.store("extra_group_id", group_id)


@then('the user "{username}" lists and counts the group "{group}" using {adapter_type} adapter')
async def step_user_groups(context: Context, username: str, group: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    groups = await _adapter_call(adapter, is_async, "get_user_groups", user_id)
    assert group in [g.name for g in groups], groups
    count = await _adapter_call(adapter, is_async, "count_user_groups", user_id)
    assert count.count == len(groups), count


@when('I link user "{username}" to the identity provider "{alias}" as "{external}" using {adapter_type} adapter')
async def step_link_user_federated_identity(
    context: Context, username: str, alias: str, external: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    payload = {
        "alias": alias,
        "providerId": "oidc",
        "enabled": True,
        "config": {
            "clientId": "external",
            "clientSecret": "secret",
            "authorizationUrl": "https://idp.example.com/auth",
            "tokenUrl": "https://idp.example.com/token",
        },
    }
    if is_async:
        await adapter.admin_adapter.a_create_idp(payload)
    else:
        adapter.admin_adapter.create_idp(payload)
    link = KeycloakFederatedIdentityRequestDTO(identity_provider=alias, user_id=f"ext-{external}", user_name=external)
    await _adapter_call(adapter, is_async, "add_user_federated_identity", sc.get(f"user_id_{username}"), alias, link)


@then('the user "{username}" lists the link to "{alias}" and removes it using {adapter_type} adapter')
async def step_user_federated_identities(context: Context, username: str, alias: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    links = await _adapter_call(adapter, is_async, "get_user_federated_identities", user_id)
    assert alias in [link.identity_provider for link in links], links
    await _adapter_call(adapter, is_async, "remove_user_federated_identity", user_id, alias)
    assert await _adapter_call(adapter, is_async, "get_user_federated_identities", user_id) == []


@then('the user "{username}" with password "{password}" has a session, can be impersonated and the user profile is readable using {adapter_type} adapter')
async def step_user_sessions_profile(context: Context, username: str, password: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    await _adapter_call(adapter, is_async, "get_token", username, password)
    sessions = await _adapter_call(adapter, is_async, "get_user_sessions", user_id)
    assert sessions and sessions[0].username == username, sessions
    client_uuid = await _adapter_call(adapter, is_async, "get_client_id", adapter.configs.CLIENT_ID)
    offline = await _adapter_call(adapter, is_async, "get_user_offline_sessions", user_id, client_uuid)
    assert offline == [], offline
    impersonation = await _adapter_call(adapter, is_async, "impersonate_user", user_id)
    assert isinstance(impersonation, KeycloakImpersonationDTO) and impersonation.redirect, impersonation
    config = await _adapter_call(adapter, is_async, "get_user_profile_config")
    metadata = await _adapter_call(adapter, is_async, "get_user_profile_metadata")
    assert isinstance(config, KeycloakUserProfileConfigDTO) and config.attributes, config
    assert isinstance(metadata, KeycloakUserProfileMetadataDTO), metadata


@then('the email actions for user "{username}" reach Keycloak and report the missing SMTP setup using {adapter_type} adapter')
async def step_user_email_actions(context: Context, username: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    user_id = sc.get(f"user_id_{username}")
    calls = (
        ("execute_user_actions_email", (user_id, ["UPDATE_PASSWORD"])),
        ("send_user_verify_email", (user_id,)),
        ("send_user_reset_password_email", (user_id,)),
    )
    for operation, args in calls:
        try:
            await _adapter_call(adapter, is_async, operation, *args)
        except Exception as e:  # noqa: BLE001 - without SMTP Keycloak answers a server error
            assert e.additional_data.get("response_code") in (HTTP_INTERNAL_ERROR, 400), f"{operation}: {e!r}"
