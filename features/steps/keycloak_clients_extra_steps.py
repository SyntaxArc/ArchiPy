from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.client_dtos import KeycloakClientRequestDTO
from archipy.models.dtos.keycloak.management_permission_dtos import KeycloakManagementPermissionDTO
from archipy.models.dtos.keycloak.token_dtos import KeycloakTokenClaimsDTO, KeycloakUserInfoDTO

HTTP_NOT_IMPLEMENTED = 501
SERVER_ERRORS = (400, 500, 501)


async def _uuid(context: Context, client_name: str) -> str:
    adapter, is_async, _ = _adapter_parts(context)
    return await _adapter_call(adapter, is_async, "get_client_id", client_name)


@when('I list, read and update the client "{client}" by its UUID using {adapter_type} adapter')
async def step_client_crud(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = await _uuid(context, client)
    listed = await _adapter_call(adapter, is_async, "get_clients", {"clientId": client})
    sc.store("clients_listed", listed)
    sc.store("client_read", await _adapter_call(adapter, is_async, "get_client", uuid))
    await _adapter_call(adapter, is_async, "update_client", uuid, KeycloakClientRequestDTO(client_id=client, description="updated"))
    sc.store("client_updated", await _adapter_call(adapter, is_async, "get_client", uuid))


@then('the client "{client}" is found by client id and carries the new description using {adapter_type} adapter')
async def step_client_crud_result(context: Context, client: str, adapter_type: str) -> None:
    _, _, sc = _adapter_parts(context)
    assert [c.client_id for c in sc.get("clients_listed")] == [client], sc.get("clients_listed")
    assert sc.get("client_read").client_id == client
    assert sc.get("client_updated").description == "updated", sc.get("client_updated")


@then('the client "{client}" has a secret that can be regenerated and rotated using {adapter_type} adapter')
async def step_client_secret(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    uuid = await _uuid(context, client)
    before = await _adapter_call(adapter, is_async, "get_client_secret_credential", uuid)
    assert before.value, before
    after = await _adapter_call(adapter, is_async, "regenerate_client_secret", uuid)
    assert after.value and after.value != before.value, after
    for operation in ("get_client_rotated_secret", "invalidate_client_rotated_secret"):
        try:
            await _adapter_call(adapter, is_async, operation, uuid)
        except Exception as e:  # noqa: BLE001 - without a secret rotation policy Keycloak answers 404
            assert type(e).__name__ == "ResourceNotFoundError", f"{operation}: {e!r}"
    token = await _adapter_call(adapter, is_async, "regenerate_client_registration_access_token", uuid)
    assert token.registration_access_token, token
    account = await _adapter_call(adapter, is_async, "get_client_service_account_user", uuid)
    assert account.username.startswith("service-account-"), account


@then('the client "{client}" evaluates example tokens, mappers, scope roles and installation config using {adapter_type} adapter')
async def step_client_evaluation(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    uuid = await _uuid(context, client)
    account = await _adapter_call(adapter, is_async, "get_client_service_account_user", uuid)
    query = {"userId": account.id}
    access = await _adapter_call(adapter, is_async, "get_client_example_access_token", uuid, query)
    id_token = await _adapter_call(adapter, is_async, "get_client_example_id_token", uuid, query)
    userinfo = await _adapter_call(adapter, is_async, "get_client_example_userinfo", uuid, query)
    assert isinstance(access, KeycloakTokenClaimsDTO) and isinstance(id_token, KeycloakTokenClaimsDTO)
    assert isinstance(userinfo, KeycloakUserInfoDTO)
    mappers = await _adapter_call(adapter, is_async, "evaluate_client_protocol_mappers", uuid)
    assert isinstance(mappers, list), mappers
    granted = await _adapter_call(adapter, is_async, "get_client_granted_scope_roles", uuid, uuid)
    not_granted = await _adapter_call(adapter, is_async, "get_client_not_granted_scope_roles", uuid, uuid)
    assert isinstance(granted, list) and isinstance(not_granted, list)
    config = await _adapter_call(adapter, is_async, "get_client_installation_provider", uuid, "keycloak-oidc-keycloak-json")
    assert client in config, config


@then('the client "{client}" counts sessions, registers a node and reports management permissions using {adapter_type} adapter')
async def step_client_sessions_nodes(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    uuid = await _uuid(context, client)
    for operation in ("get_client_session_count", "get_client_offline_session_count"):
        counted = await _adapter_call(adapter, is_async, operation, uuid)
        assert isinstance(counted.count, int), counted
    for operation in ("get_client_user_sessions", "get_client_offline_sessions"):
        assert isinstance(await _adapter_call(adapter, is_async, operation, uuid), list)
    await _adapter_call(adapter, is_async, "register_client_node", uuid, "node1.example.com")
    registered = await _adapter_call(adapter, is_async, "get_client", uuid)
    assert "node1.example.com" in (registered.registered_nodes or {}), registered.registered_nodes
    await _adapter_call(adapter, is_async, "unregister_client_node", uuid, "node1.example.com")
    for operation in ("push_client_revocation", "test_client_nodes_available"):
        try:
            await _adapter_call(adapter, is_async, operation, uuid)
        except Exception as e:  # noqa: BLE001 - the client has no admin URL, so Keycloak may refuse
            assert e.additional_data.get("response_code") in SERVER_ERRORS, f"{operation}: {e!r}"
    try:
        permissions = await _adapter_call(adapter, is_async, "get_client_management_permissions", uuid)
    except Exception as e:  # noqa: BLE001 - fine-grained admin permissions v1 may be disabled
        assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, repr(e)
    else:
        assert isinstance(permissions, KeycloakManagementPermissionDTO)


@when('I delete the client "{client}" by its UUID using {adapter_type} adapter')
async def step_client_delete(context: Context, client: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    uuid = await _uuid(context, client)
    await _adapter_call(adapter, is_async, "delete_client", uuid)
    sc.store("deleted_client_uuid", uuid)


@then("the deleted client is no longer found using {adapter_type} adapter")
async def step_client_deleted(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    try:
        await _adapter_call(adapter, is_async, "get_client", sc.get("deleted_client_uuid"))
    except Exception as e:  # noqa: BLE001 - assert on the mapped error type
        assert type(e).__name__ == "ResourceNotFoundError", repr(e)
    else:
        raise AssertionError("the deleted client is still readable")
