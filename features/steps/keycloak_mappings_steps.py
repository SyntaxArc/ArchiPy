from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts
from features.test_helpers import get_current_scenario_context

from archipy.models.dtos.keycloak.client_dtos import KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeRequestDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleDTO


async def _exercise_family(
    context: Context,
    subject: str,
    noun: str,
    subject_id: str,
    owner_uuid: str,
    realm_role,
    client_role,
    all_name: str,
    include_client_roles: bool = True,
) -> None:
    """Add, list, find as available and effective, and remove a realm role and a client role for one subject."""
    adapter, is_async, _ = _adapter_parts(context)

    async def call(name: str, *args):
        return await _adapter_call(adapter, is_async, name, *args)

    realm_available = await call(f"get_{subject}_realm_{noun}_available", subject_id)
    assert realm_role.name in [r.name for r in realm_available], f"{subject} realm available: {realm_available}"
    await call(f"add_{subject}_realm_{noun}", subject_id, [realm_role])
    assert realm_role.name in [r.name for r in await call(f"get_{subject}_realm_{noun}", subject_id)]
    assert realm_role.name in [r.name for r in await call(f"get_{subject}_realm_{noun}_composite", subject_id)]
    assert realm_role.name not in [r.name for r in await call(f"get_{subject}_realm_{noun}_available", subject_id)]

    if include_client_roles:
        client_available = await call(f"get_{subject}_client_{noun}_available", subject_id, owner_uuid)
        assert client_role.name in [r.name for r in client_available], f"{subject} client available: {client_available}"
        await call(f"add_{subject}_client_{noun}", subject_id, owner_uuid, [client_role])
        assert client_role.name in [r.name for r in await call(f"get_{subject}_client_{noun}", subject_id, owner_uuid)]
        assert client_role.name in [r.name for r in await call(f"get_{subject}_client_{noun}_composite", subject_id, owner_uuid)]

    mappings = await call(all_name, subject_id)
    assert realm_role.name in [r.name for r in mappings.realm_mappings or []], mappings
    if include_client_roles:
        assert owner_uuid in (mappings.client_mappings or {}) or any(
            m.id == owner_uuid for m in (mappings.client_mappings or {}).values()
        ), mappings

    await call(f"delete_{subject}_realm_{noun}", subject_id, [realm_role])
    assert realm_role.name not in [r.name for r in await call(f"get_{subject}_realm_{noun}", subject_id)]
    if include_client_roles:
        await call(f"delete_{subject}_client_{noun}", subject_id, owner_uuid, [client_role])
        assert client_role.name not in [r.name for r in await call(f"get_{subject}_client_{noun}", subject_id, owner_uuid)]


@when('I create the realm role "{realm_role}" and the client role "{client_role}" of client "{client}" using {adapter_type} adapter')
async def step_create_mapping_roles(
    context: Context, realm_role: str, client_role: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    await _adapter_call(adapter, is_async, "create_realm_role", realm_role)
    await _adapter_call(adapter, is_async, "create_client_role", client, client_role)
    sc.store("mapping_realm_role", await _adapter_call(adapter, is_async, "get_realm_role", realm_role))
    uuid = await _adapter_call(adapter, is_async, "get_client_id", client)
    sc.store("mapping_client_uuid", uuid)
    sc.store("mapping_client_role_name", client_role)


async def _client_role(context: Context):
    adapter, is_async, sc = _adapter_parts(context)
    uuid = sc.get("mapping_client_uuid")
    admin = adapter.admin_adapter
    name = sc.get("mapping_client_role_name")
    raw = await admin.a_get_client_role(uuid, name) if is_async else admin.get_client_role(uuid, name)
    return KeycloakRoleDTO.model_validate(raw)


@then('the user "{username}" gets, lists and loses the realm and client roles through role mappings using {adapter_type} adapter')
async def step_user_role_mappings(context: Context, username: str, adapter_type: str) -> None:
    sc = get_current_scenario_context(context)
    await _exercise_family(
        context, "user", "role_mappings", sc.get(f"user_id_{username}"), sc.get("mapping_client_uuid"),
        sc.get("mapping_realm_role"), await _client_role(context), "get_user_role_mappings",
    )


@then('the group "{group}" lists the role mappings it lacked before using {adapter_type} adapter')
async def step_group_role_mappings(context: Context, group: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    group_id = await _adapter_call(adapter, is_async, "create_group", KeycloakGroupRequestDTO(name=group), skip_exists=True)
    realm_role = sc.get("mapping_realm_role")
    await _adapter_call(adapter, is_async, "assign_group_realm_roles", group_id, [realm_role])
    mappings = await _adapter_call(adapter, is_async, "get_group_role_mappings", group_id)
    assert realm_role.name in [r.name for r in mappings.realm_mappings or []], mappings
    composite = await _adapter_call(adapter, is_async, "get_group_realm_role_mappings_composite", group_id)
    assert realm_role.name in [r.name for r in composite], composite
    available = await _adapter_call(adapter, is_async, "get_group_realm_role_mappings_available", group_id)
    assert realm_role.name not in [r.name for r in available], available
    client_available = await _adapter_call(
        adapter, is_async, "get_group_client_role_mappings_available", group_id, sc.get("mapping_client_uuid"),
    )
    assert isinstance(client_available, list)


@then('the client scope "{scope}" and the client map scopes to the realm and client roles using {adapter_type} adapter')
async def step_scope_mappings(context: Context, scope: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    scope_id = await _adapter_call(
        adapter, is_async, "create_client_scope", KeycloakClientScopeRequestDTO(name=scope, protocol="openid-connect"), skip_exists=True,
    )
    client_role = await _client_role(context)
    uuid = sc.get("mapping_client_uuid")
    await _exercise_family(
        context, "client_scope", "scope_mappings", scope_id, uuid, sc.get("mapping_realm_role"), client_role,
        "get_client_scope_scope_mappings",
    )
    # a client with full scope allowed has every role in scope, so nothing is "available" to map
    await _adapter_call(adapter, is_async, "update_client", uuid, KeycloakClientRequestDTO(full_scope_allowed=False))
    await _exercise_family(
        context, "client", "scope_mappings", uuid, uuid, sc.get("mapping_realm_role"), client_role,
        "get_client_scope_mappings",
        include_client_roles=False,  # a client's own roles are always in its scope
    )
