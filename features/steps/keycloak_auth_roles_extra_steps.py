from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.required_action_dtos import KeycloakRequiredActionProviderRequestDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleRequestDTO

HTTP_NOT_IMPLEMENTED = 501


@then("the authenticator, form and client authenticator providers are listed using {adapter_type} adapter")
async def step_provider_listings(context: Context, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    for operation in ("get_client_authenticator_providers", "get_form_action_providers", "get_form_providers"):
        providers = await _adapter_call(adapter, is_async, operation)
        assert providers and all(p.id for p in providers), f"{operation}: {providers}"
    described = await _adapter_call(adapter, is_async, "get_per_client_config_description")
    assert described and all(isinstance(v, list) for v in described.values()), described


@then("the required actions are listed, updated and reordered, and their settings are described using {adapter_type} adapter")
async def step_required_actions(context: Context, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    actions = await _adapter_call(adapter, is_async, "get_required_actions")
    assert actions, actions
    alias = "UPDATE_PASSWORD"
    one = await _adapter_call(adapter, is_async, "get_required_action", alias)
    assert one.alias == alias and one.provider_id, one
    await _adapter_call(
        adapter, is_async, "update_required_action", alias,
        KeycloakRequiredActionProviderRequestDTO(alias=alias, name=one.name, provider_id=one.provider_id, enabled=True, default_action=False),
    )
    await _adapter_call(adapter, is_async, "raise_required_action_priority", alias)
    await _adapter_call(adapter, is_async, "lower_required_action_priority", alias)
    unregistered = await _adapter_call(adapter, is_async, "get_unregistered_required_actions")
    assert isinstance(unregistered, list)
    try:
        await _adapter_call(adapter, is_async, "get_required_action_config_description", alias)
    except Exception as e:  # noqa: BLE001 - not every required action has settings
        assert e.additional_data.get("response_code") in (400, 404, HTTP_NOT_IMPLEMENTED), repr(e)


@when('I manage the realm role "{role}" and the client role "{client_role}" of client "{client}" by name using {adapter_type} adapter')
async def step_roles_by_name(context: Context, role: str, client_role: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    sc.store("by_name_client_uuid", uuid)
    await _adapter_call(adapter, is_async, "create_realm_role", role)
    await _adapter_call(adapter, is_async, "create_realm_role", f"{role}-child")
    await _adapter_call(adapter, is_async, "create_client_role", client, client_role)
    await _adapter_call(adapter, is_async, "update_realm_role", role, KeycloakRoleRequestDTO(name=role, description="updated"))
    await _adapter_call(adapter, is_async, "update_client_role", uuid, client_role, KeycloakRoleRequestDTO(name=client_role, description="client updated"))


@then('the roles "{role}" and "{client_role}" are listed with composites, users and groups using {adapter_type} adapter')
async def step_roles_listings(context: Context, role: str, client_role: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = sc.get("by_name_client_uuid")
    realm_roles = await _adapter_call(adapter, is_async, "get_realm_roles_filtered", {"search": role})
    assert role in [r.name for r in realm_roles], realm_roles
    client_roles = await _adapter_call(adapter, is_async, "get_client_roles_filtered", uuid)
    assert client_role in [r.name for r in client_roles], client_roles
    fetched = await _adapter_call(adapter, is_async, "get_client_role_by_name", uuid, client_role)
    assert fetched.description == "client updated", fetched
    child = await _adapter_call(adapter, is_async, "get_realm_role", f"{role}-child")
    await _adapter_call(adapter, is_async, "add_realm_role_composites", role, [child])
    await _adapter_call(adapter, is_async, "add_client_role_composites", uuid, client_role, [child])
    for names in (
        await _adapter_call(adapter, is_async, "get_realm_role_composites", role),
        await _adapter_call(adapter, is_async, "get_realm_role_realm_composites", role),
        await _adapter_call(adapter, is_async, "get_client_role_composites", uuid, client_role),
        await _adapter_call(adapter, is_async, "get_client_role_realm_composites", uuid, client_role),
    ):
        assert f"{role}-child" in [r.name for r in names], names
    assert await _adapter_call(adapter, is_async, "get_realm_role_client_composites", role, uuid) == []
    assert await _adapter_call(adapter, is_async, "get_client_role_client_composites", uuid, client_role, uuid) == []
    for operation, args in (
        ("get_users_with_realm_role", (role,)),
        ("get_groups_with_realm_role", (role,)),
        ("get_users_with_client_role", (uuid, client_role)),
        ("get_groups_with_client_role", (uuid, client_role)),
    ):
        assert isinstance(await _adapter_call(adapter, is_async, operation, *args), list), operation
    for operation, args in (("get_realm_role_management_permissions", (role,)), ("get_client_role_management_permissions", (uuid, client_role))):
        try:
            await _adapter_call(adapter, is_async, operation, *args)
        except Exception as e:  # noqa: BLE001 - fine-grained admin permissions v1 may be disabled
            assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, f"{operation}: {e!r}"
    await _adapter_call(adapter, is_async, "delete_realm_role_composites", role, [child])
    await _adapter_call(adapter, is_async, "delete_client_role_composites", uuid, client_role, [child])
    assert await _adapter_call(adapter, is_async, "get_realm_role_composites", role) == []
    await _adapter_call(adapter, is_async, "delete_client_role", uuid, client_role)
    assert client_role not in [r.name for r in await _adapter_call(adapter, is_async, "get_client_roles_filtered", uuid)]
