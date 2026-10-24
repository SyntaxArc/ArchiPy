from behave import then
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.authz_dtos import KeycloakAuthzScopeRequestDTO, KeycloakAuthzSettingsRequestDTO
from archipy.models.dtos.keycloak.authz_evaluation_dtos import KeycloakAuthzPolicyEvaluationRequestRequestDTO
from archipy.models.dtos.keycloak.client_scope_dtos import KeycloakClientScopeRequestDTO
from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.protocol_mapper_config_dtos import PROTOCOL_MAPPER_CONFIGS

HTTP_NOT_IMPLEMENTED = 501
SERVER_ERRORS = (400, 404, 500, 501)


@then('the resource "{resource}" and scope "{scope}" of client "{client}" are found, filtered, searched and described using {adapter_type} adapter')
async def step_authz_queries(context: Context, resource: str, scope: str, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = await _adapter_call(adapter, is_async, "get_client_id", client)
    filtered = await _adapter_call(adapter, is_async, "get_client_authz_resources_filtered", cid, {"name": resource})
    assert [r.name for r in filtered] == [resource], filtered
    found = await _adapter_call(adapter, is_async, "search_client_authz_resource", cid, resource)
    assert found.name == resource, found
    resource_id = found.internal_id
    assert isinstance(await _adapter_call(adapter, is_async, "get_client_authz_resource_attributes", cid, resource_id), dict)
    permissions = await _adapter_call(adapter, is_async, "get_client_authz_resource_permissions", cid, resource_id)
    assert any(p.name == f"{resource}-{scope}" for p in permissions), permissions
    scopes = await _adapter_call(adapter, is_async, "get_client_authz_resource_scopes", cid, resource_id)
    assert scope in [s.name for s in scopes], scopes
    scope_found = await _adapter_call(adapter, is_async, "search_client_authz_scope", cid, scope)
    assert scope in [s.name for s in await _adapter_call(adapter, is_async, "get_client_authz_scopes_filtered", cid, {"name": scope})]
    one = await _adapter_call(adapter, is_async, "get_client_authz_scope", cid, scope_found.id)
    assert one.name == scope, one
    await _adapter_call(adapter, is_async, "update_client_authz_scope", cid, scope_found.id, KeycloakAuthzScopeRequestDTO(name=scope, display_name="Reading"))
    assert (await _adapter_call(adapter, is_async, "get_client_authz_scope", cid, scope_found.id)).display_name == "Reading"
    assert any(p.name == f"{resource}-{scope}" for p in await _adapter_call(adapter, is_async, "get_client_authz_scope_permissions", cid, scope_found.id))
    assert resource in [r.name for r in await _adapter_call(adapter, is_async, "get_client_authz_scope_resources", cid, scope_found.id)]
    extra = await _adapter_call(adapter, is_async, "create_client_authz_scopes", cid, KeycloakAuthzScopeRequestDTO(name="disposable"))
    await _adapter_call(adapter, is_async, "delete_client_authz_scope", cid, extra.id)
    assert "disposable" not in [s.name for s in await _adapter_call(adapter, is_async, "get_client_authz_scopes", cid)]
    sc.store("authz_extra_client_uuid", cid)
    sc.store("authz_extra_resource", resource)


@then('the policies and permissions of client "{client}" are found, searched, listed by provider and evaluated for user "{username}" using {adapter_type} adapter')
async def step_authz_policy_queries(context: Context, client: str, username: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    cid = sc.get("authz_extra_client_uuid")
    policy_name = f"{sc.get('authz_extra_resource')}-offline_access-policy"
    policies = await _adapter_call(adapter, is_async, "get_client_authz_policies_filtered", cid, {"name": policy_name})
    assert [p.name for p in policies] == [policy_name], policies
    assert (await _adapter_call(adapter, is_async, "search_client_authz_policy", cid, policy_name)).name == policy_name
    permission_name = next(p.name for p in await _adapter_call(adapter, is_async, "get_client_authz_permissions", cid) if p.name.endswith("-read"))
    assert (await _adapter_call(adapter, is_async, "search_client_authz_permission", cid, permission_name)).name == permission_name
    assert permission_name in [p.name for p in await _adapter_call(adapter, is_async, "get_client_authz_permissions_filtered", cid, {"name": permission_name})]
    for operation in ("get_client_authz_policy_providers", "get_client_authz_permission_providers"):
        providers = await _adapter_call(adapter, is_async, operation, cid)
        assert providers and all(p.type for p in providers), f"{operation}: {providers}"
    request = KeycloakAuthzPolicyEvaluationRequestRequestDTO(user_id=sc.get(f"user_id_{username}"), client_id=cid, entitlements=False)
    for operation in ("evaluate_client_authz_policies", "evaluate_client_authz_permissions"):
        outcome = await _adapter_call(adapter, is_async, operation, cid, request)
        assert outcome.results, f"{operation}: {outcome}"
    settings = await _adapter_call(adapter, is_async, "get_client_authz_settings", cid)
    await _adapter_call(adapter, is_async, "update_client_authz_settings", cid, KeycloakAuthzSettingsRequestDTO(policy_enforcement_mode="PERMISSIVE", allow_remote_resource_management=True, decision_strategy=settings.decision_strategy))
    assert (await _adapter_call(adapter, is_async, "get_client_authz_settings", cid)).policy_enforcement_mode == "PERMISSIVE"


@then('the client scope "{scope}" lists, bulk-adds and reads protocol mappers by id and protocol, and the group "{group}" and a component report their settings using {adapter_type} adapter')
async def step_mappers_groups_components(context: Context, scope: str, group: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    scope_id = await _adapter_call(adapter, is_async, "create_client_scope", KeycloakClientScopeRequestDTO(name=scope, protocol="openid-connect"), skip_exists=True)
    mappers = [
        PROTOCOL_MAPPER_CONFIGS["oidc-allowed-origins-mapper"]().to_mapper("origins"),
        PROTOCOL_MAPPER_CONFIGS["oidc-sub-mapper"]().to_mapper("subject"),
    ]
    result = await _adapter_call(adapter, is_async, "add_client_scope_protocol_mappers", scope_id, mappers)
    assert result is not None
    listed = await _adapter_call(adapter, is_async, "get_client_scope_protocol_mappers_by_protocol", scope_id, "openid-connect")
    assert {"origins", "subject"} <= {m.name for m in listed}, listed
    one = await _adapter_call(adapter, is_async, "get_client_scope_protocol_mapper", scope_id, next(m.id for m in listed if m.name == "origins"))
    assert one.protocol_mapper == "oidc-allowed-origins-mapper", one
    group_id = await _adapter_call(adapter, is_async, "create_group", KeycloakGroupRequestDTO(name=group), skip_exists=True)
    for operation, args in (("get_group_management_permissions", (group_id,)),):
        try:
            await _adapter_call(adapter, is_async, operation, *args)
        except Exception as e:  # noqa: BLE001 - fine-grained admin permissions v1 may be disabled
            assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, repr(e)
    components = await _adapter_call(adapter, is_async, "get_components")
    assert components, components
    try:
        await _adapter_call(adapter, is_async, "get_component_sub_types", components[0].id, "org.keycloak.keys.KeyProvider")
    except Exception as e:  # noqa: BLE001 - not every component has sub-component types
        assert e.additional_data.get("response_code") in SERVER_ERRORS, repr(e)
