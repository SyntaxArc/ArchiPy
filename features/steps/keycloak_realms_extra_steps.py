from behave import then
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.event_dtos import KeycloakRealmEventsConfigRequestDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.management_permission_dtos import KeycloakManagementPermissionDTO
from archipy.models.dtos.keycloak.partial_import_dtos import KeycloakPartialImportRequestDTO
from archipy.models.dtos.keycloak.user_dtos import KeycloakUserRequestDTO

HTTP_NOT_IMPLEMENTED = 501
SERVER_ERRORS = (400, 500, 501)


@then('the realm "{realm}" is listed and its event settings, client policies, profiles and types round-trip using {adapter_type} adapter')
async def step_realm_listing_and_settings(context: Context, realm: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    realms = await _adapter_call(adapter, is_async, "get_realms")
    assert realm in [r.realm for r in realms], realms
    brief = await _adapter_call(adapter, is_async, "get_realms", brief_representation=True)
    assert realm in [r.realm for r in brief], brief
    config = await _adapter_call(adapter, is_async, "get_realm_events_config", realm)
    await _adapter_call(
        adapter, is_async, "update_realm_events_config", realm,
        KeycloakRealmEventsConfigRequestDTO(events_enabled=True, admin_events_enabled=True, events_expiration=3600),
    )
    updated = await _adapter_call(adapter, is_async, "get_realm_events_config", realm)
    assert updated.events_enabled is True and updated.admin_events_enabled is True, (config, updated)
    policies = await _adapter_call(adapter, is_async, "get_realm_client_policies", realm, include_global_policies=True)
    await _adapter_call(adapter, is_async, "update_realm_client_policies", realm, {"policies": policies.policies or []})
    profiles = await _adapter_call(adapter, is_async, "get_realm_client_profiles", realm, include_global_profiles=True)
    await _adapter_call(adapter, is_async, "update_realm_client_profiles", realm, {"profiles": profiles.profiles or []})
    try:
        types = await _adapter_call(adapter, is_async, "get_realm_client_types", realm)
    except Exception as e:  # noqa: BLE001 - client types are a preview feature the server may not enable
        assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, repr(e)
    else:
        assert types.global_client_types is not None, types
    stats = await _adapter_call(adapter, is_async, "get_realm_client_session_stats", realm)
    registrators = await _adapter_call(adapter, is_async, "get_realm_credential_registrators", realm)
    assert isinstance(stats, list) and isinstance(registrators, list)


@then('the realm "{realm}" records and clears events and admin events using {adapter_type} adapter')
async def step_realm_events(context: Context, realm: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    await _adapter_call(adapter, is_async, "create_group", KeycloakGroupRequestDTO(name="event-group"), skip_exists=True)
    admin_events = await _adapter_call(adapter, is_async, "get_realm_admin_events", realm)
    assert any(e.resource_type == "GROUP" for e in admin_events), admin_events
    events = await _adapter_call(adapter, is_async, "get_realm_events", realm)
    assert isinstance(events, list)
    await _adapter_call(adapter, is_async, "delete_realm_admin_events", realm)
    await _adapter_call(adapter, is_async, "delete_realm_events", realm)
    assert await _adapter_call(adapter, is_async, "get_realm_admin_events", realm) == []


@then('the realm "{realm}" manages default groups and localization texts using {adapter_type} adapter')
async def step_realm_defaults_localization(context: Context, realm: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    group_id = await _adapter_call(adapter, is_async, "create_group", KeycloakGroupRequestDTO(name="default-group"), skip_exists=True)
    await _adapter_call(adapter, is_async, "add_realm_default_group", realm, group_id)
    defaults = await _adapter_call(adapter, is_async, "get_realm_default_groups", realm)
    assert group_id in [g.id for g in defaults], defaults
    await _adapter_call(adapter, is_async, "remove_realm_default_group", realm, group_id)
    assert group_id not in [g.id for g in await _adapter_call(adapter, is_async, "get_realm_default_groups", realm)]
    await _adapter_call(adapter, is_async, "update_realm_localization_texts", realm, "en", {"greeting": "hello", "farewell": "bye"})
    assert "en" in await _adapter_call(adapter, is_async, "get_realm_localization_locales", realm)
    texts = await _adapter_call(adapter, is_async, "get_realm_localization_texts", realm, "en")
    assert texts == {"greeting": "hello", "farewell": "bye"}, texts
    await _adapter_call(adapter, is_async, "delete_realm_localization_text", realm, "en", "farewell")
    assert await _adapter_call(adapter, is_async, "get_realm_localization_texts", realm, "en") == {"greeting": "hello"}
    await _adapter_call(adapter, is_async, "delete_realm_localization", realm, "en")


@then('the realm "{realm}" exports, imports, logs everyone out and pushes revocation using {adapter_type} adapter')
async def step_realm_export_import(context: Context, realm: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    exported = await _adapter_call(adapter, is_async, "partial_export_realm", realm, export_clients=True, export_groups_and_roles=True)
    assert exported.realm == realm and exported.clients, exported
    payload = KeycloakPartialImportRequestDTO(if_resource_exists="SKIP", users=[KeycloakUserRequestDTO(username="imported-user")])
    result = await _adapter_call(adapter, is_async, "partial_import_realm", realm, payload)
    assert result.added == 1, result
    users = await _adapter_call(adapter, is_async, "get_users", {"username": "imported-user", "exact": True})
    assert len(users) == 1, users
    for operation in ("logout_all_realm_sessions", "push_realm_revocation"):
        outcome = await _adapter_call(adapter, is_async, operation, realm)
        assert outcome is not None, operation


@then('the realm "{realm}" deletes a session, reports SMTP and permission settings and can be deleted using {adapter_type} adapter')
async def step_realm_sessions_smtp_delete(context: Context, realm: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    try:
        await _adapter_call(adapter, is_async, "test_realm_smtp_connection", realm, {"host": "localhost", "port": "1", "from": "a@b.c"})
    except Exception as e:  # noqa: BLE001 - there is no SMTP server to reach
        assert e.additional_data.get("response_code") in SERVER_ERRORS, repr(e)
    try:
        permissions = await _adapter_call(adapter, is_async, "get_realm_users_management_permissions", realm)
    except Exception as e:  # noqa: BLE001 - fine-grained admin permissions v1 may be disabled
        assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, repr(e)
    else:
        assert isinstance(permissions, KeycloakManagementPermissionDTO)
    await _adapter_call(adapter, is_async, "delete_realm", realm)
    realms = await _adapter_call(adapter, is_async, "get_realms")
    assert realm not in [r.realm for r in realms], realms
