from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts
from keycloak.uma_permissions import UMAPermission

from archipy.models.dtos.keycloak.authz_dtos import (
    KeycloakAuthzPolicyRequestDTO,
    KeycloakAuthzResourceRequestDTO,
    KeycloakAuthzScopeRequestDTO,
)
from archipy.models.dtos.keycloak.authz_policy_dtos import (
    KeycloakAuthzClientPolicyRequestDTO,
    KeycloakAuthzPolicyRoleDTO,
    KeycloakAuthzRolePolicyRequestDTO,
)
from archipy.models.dtos.keycloak.uma_dtos import KeycloakUmaPolicyRequestDTO, KeycloakUmaResourceRequestDTO


async def _client_uuid(adapter, is_async: bool, client_name: str) -> str:
    return await _adapter_call(adapter, is_async, "get_client_id", client_name)


# --- authorization services ---


@when('I create the authorization scope "{scope}" for client "{client}" using {adapter_type} adapter')
async def step_create_authz_scope(context: Context, scope: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    created = await _adapter_call(adapter, is_async, "create_client_authz_scopes", cid, KeycloakAuthzScopeRequestDTO(name=scope))
    sc.store(f"authz_scope_{scope}", created)


@when(
    'I create the authorization resource "{resource}" with scope "{scope}" for client "{client}" '
    "using {adapter_type} adapter",
)
async def step_create_authz_resource(
    context: Context, resource: str, scope: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    payload = KeycloakAuthzResourceRequestDTO(name=resource, scopes=[KeycloakAuthzScopeRequestDTO(name=scope)])
    sc.store(f"authz_resource_{resource}", await _adapter_call(adapter, is_async, "create_client_authz_resource", cid, payload))


@when(
    'I create the role policy "{policy}" for realm role "{role}" on client "{client}" using {adapter_type} adapter',
)
async def step_create_role_policy(context: Context, policy: str, role: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    realm_role = await _adapter_call(adapter, is_async, "get_realm_role", role)
    payload = KeycloakAuthzRolePolicyRequestDTO(
        name=policy,
        logic="POSITIVE",
        decision_strategy="UNANIMOUS",
        roles=[KeycloakAuthzPolicyRoleDTO(id=realm_role.id, required=False)],
    )
    sc.store(
        f"authz_policy_{policy}",
        await _adapter_call(adapter, is_async, "create_client_authz_role_based_policy", cid, payload),
    )


@when('I create the client policy "{policy}" for client "{client}" using {adapter_type} adapter')
async def step_create_client_policy(context: Context, policy: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    payload = KeycloakAuthzClientPolicyRequestDTO(
        name=policy,
        logic="POSITIVE",
        decision_strategy="UNANIMOUS",
        clients=[cid],
    )
    sc.store(
        f"authz_policy_{policy}",
        await _adapter_call(adapter, is_async, "create_client_authz_client_policy", payload, cid),
    )


@when(
    'I create the scope permission "{permission}" on resource "{resource}" scope "{scope}" policy "{policy}" '
    'for client "{client}" using {adapter_type} adapter',
)
async def step_create_scope_permission(
    context: Context, permission: str, resource: str, scope: str, policy: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    payload = KeycloakAuthzPolicyRequestDTO(
        name=permission,
        type="scope",
        logic="POSITIVE",
        decision_strategy="UNANIMOUS",
        resources=[sc.get(f"authz_resource_{resource}").internal_id],
        scopes=[sc.get(f"authz_scope_{scope}").id],
        policies=[sc.get(f"authz_policy_{policy}").id],
    )
    created = await _adapter_call(adapter, is_async, "create_client_authz_scope_permission", payload, cid)
    sc.store(f"authz_permission_{permission}", created)


@then(
    'the authorization objects of client "{client}" are listed as scope "{scope}", resource "{resource}", '
    'policies "{policies}" and permission "{permission}" using {adapter_type} adapter',
)
async def step_authz_objects_listed(
    context: Context, client: str, scope: str, resource: str, policies: str, permission: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    scopes = await _adapter_call(adapter, is_async, "get_client_authz_scopes", cid)
    resources = await _adapter_call(adapter, is_async, "get_client_authz_resources", cid)
    all_policies = await _adapter_call(adapter, is_async, "get_client_authz_policies", cid)
    permissions = await _adapter_call(adapter, is_async, "get_client_authz_permissions", cid)
    assert scope in [s.name for s in scopes], scopes
    assert resource in [r.name for r in resources], resources
    for policy in policies.split(","):
        assert policy in [p.name for p in all_policies], all_policies
    assert permission in [p.name for p in permissions], permissions
    role_policy = sc.get(f"authz_policy_{policies.split(',')[0]}")
    assert role_policy.roles, f"role policy create response has no roles: {role_policy!r}"
    client_policies = await _adapter_call(adapter, is_async, "get_client_authz_client_policies", cid)
    assert client_policies and client_policies[0].clients == [cid], client_policies
    settings = await _adapter_call(adapter, is_async, "get_client_authz_settings", cid)
    assert resource in [r.name for r in settings.resources or []], settings


@when(
    'I set the description of scope permission "{permission}" to "{description}" for client "{client}" '
    "using {adapter_type} adapter",
)
async def step_update_scope_permission(
    context: Context, permission: str, description: str, client: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    perm_id = sc.get(f"authz_permission_{permission}").id
    payload = KeycloakAuthzPolicyRequestDTO(
        id=perm_id,
        name=permission,
        type="scope",
        logic="POSITIVE",
        decision_strategy="UNANIMOUS",
        description=description,
    )
    result = await _adapter_call(adapter, is_async, "update_client_authz_scope_permission", payload, cid, perm_id)
    sc.store("authz_update_result", result)


@then(
    'the scope permission "{permission}" of client "{client}" has description "{description}" and its policies '
    "and scopes are readable using {adapter_type} adapter",
)
async def step_scope_permission_description(
    context: Context, permission: str, client: str, description: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    perm_id = sc.get(f"authz_permission_{permission}").id
    fetched = await _adapter_call(adapter, is_async, "get_client_authz_scope_permission", cid, perm_id)
    assert fetched.description == description, fetched
    associated = await _adapter_call(adapter, is_async, "get_client_authz_permission_associated_policies", cid, perm_id)
    assert associated, "scope permission has no associated policies"
    scopes = await _adapter_call(adapter, is_async, "get_client_authz_policy_scopes", cid, perm_id)
    resources = await _adapter_call(adapter, is_async, "get_client_authz_policy_resources", cid, perm_id)
    assert scopes and resources, (scopes, resources)


@when('I delete the authorization policy "{policy}" and resource "{resource}" of client "{client}" using {adapter_type} adapter')
async def step_delete_authz(context: Context, policy: str, resource: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    sc.store(
        "authz_delete_policy_result",
        await _adapter_call(adapter, is_async, "delete_client_authz_policy", cid, sc.get(f"authz_policy_{policy}").id),
    )
    sc.store(
        "authz_delete_resource_result",
        await _adapter_call(
            adapter, is_async, "delete_client_authz_resource", cid, sc.get(f"authz_resource_{resource}").internal_id,
        ),
    )


@then('the policy "{policy}" and resource "{resource}" of client "{client}" no longer exist using {adapter_type} adapter')
async def step_authz_deleted(context: Context, policy: str, resource: str, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    cid = await _client_uuid(adapter, is_async, client)
    policies = await _adapter_call(adapter, is_async, "get_client_authz_policies", cid)
    resources = await _adapter_call(adapter, is_async, "get_client_authz_resources", cid)
    assert policy not in [p.name for p in policies], policies
    assert resource not in [r.name for r in resources], resources


# --- UMA ---


@when('I create the UMA resource set "{name}" with scope "{scope}" using {adapter_type} adapter')
async def step_uma_create_resource(context: Context, name: str, scope: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    payload = KeycloakUmaResourceRequestDTO(name=name, scopes=[scope], type="document", owner_managed_access=True)
    sc.store(f"uma_resource_{name}", await _adapter_call(adapter, is_async, "resource_set_create", payload))


@then('the UMA resource set "{name}" is typed, owned by the client and listed using {adapter_type} adapter')
async def step_uma_resource_listed(context: Context, name: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    created = sc.get(f"uma_resource_{name}")
    assert created.internal_id and created.owner and created.owner.id, created
    assert [s.name for s in created.scopes or []] == ["view"], created
    assert created.owner_managed_access is True, created
    read = await _adapter_call(adapter, is_async, "resource_set_read", created.internal_id)
    assert read.name == name and read.type == "document", read
    ids = await _adapter_call(adapter, is_async, "resource_set_list_ids")
    assert created.internal_id in ids, ids
    listed = await _adapter_call(adapter, is_async, "resource_set_list")
    assert name in [r.name for r in listed], listed


@when('I create the UMA policy "{policy}" for realm role "{role}" on resource set "{name}" using {adapter_type} adapter')
async def step_uma_create_policy(context: Context, policy: str, role: str, name: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    resource_id = sc.get(f"uma_resource_{name}").internal_id
    payload = KeycloakUmaPolicyRequestDTO(name=policy, description="viewers", scopes=["view"], roles=[role])
    sc.store(f"uma_policy_{policy}", await _adapter_call(adapter, is_async, "policy_resource_create", resource_id, payload))


@when(
    'I set the description of UMA policy "{policy}" on resource set "{name}" to "{description}" '
    "using {adapter_type} adapter",
)
async def step_uma_update_policy(context: Context, policy: str, name: str, description: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    created = sc.get(f"uma_policy_{policy}")
    payload = KeycloakUmaPolicyRequestDTO(name=policy, description=description, scopes=["view"], roles=created.roles)
    sc.store("uma_policy_update_result", await _adapter_call(adapter, is_async, "policy_update", created.id, payload))


@then(
    'querying UMA policies of resource set "{name}" returns "{policy}" with description "{description}" '
    "using {adapter_type} adapter",
)
async def step_uma_query_policy(context: Context, name: str, policy: str, description: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    resource_id = sc.get(f"uma_resource_{name}").internal_id
    policies = await _adapter_call(adapter, is_async, "policy_query", resource=resource_id)
    match = next((p for p in policies if p.name == policy), None)
    assert match is not None, policies
    assert match.description == description and match.scopes == ["view"], match
    assert match.owner, match


@then('a UMA permission ticket for resource "{name}" scope "{scope}" is issued using {adapter_type} adapter')
async def step_uma_ticket(context: Context, name: str, scope: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    ticket = await _adapter_call(adapter, is_async, "permission_ticket_create", [UMAPermission(resource=name, scope=scope)])
    assert ticket.ticket, ticket


@when('I delete the UMA policy "{policy}" and resource set "{name}" using {adapter_type} adapter')
async def step_uma_delete(context: Context, policy: str, name: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    await _adapter_call(adapter, is_async, "policy_delete", sc.get(f"uma_policy_{policy}").id)
    await _adapter_call(adapter, is_async, "resource_set_delete", sc.get(f"uma_resource_{name}").internal_id)


@then('the UMA resource set "{name}" no longer exists using {adapter_type} adapter')
async def step_uma_deleted(context: Context, name: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    ids = await _adapter_call(adapter, is_async, "resource_set_list_ids")
    assert sc.get(f"uma_resource_{name}").internal_id not in ids, ids
