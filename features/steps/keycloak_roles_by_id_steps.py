from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts

from archipy.models.dtos.keycloak.management_permission_dtos import KeycloakManagementPermissionDTO
from archipy.models.dtos.keycloak.role_dtos import KeycloakRoleRequestDTO


HTTP_NOT_IMPLEMENTED = 501


async def _role_id(context: Context, name: str) -> str:
    adapter, is_async, _ = _adapter_parts(context)
    role = await _adapter_call(adapter, is_async, "get_realm_role", name)
    return role.id


@when('I update the role "{role}" by its id and add "{child}" as a composite using {adapter_type} adapter')
async def step_update_role_by_id(context: Context, role: str, child: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    role_id = await _role_id(context, role)
    sc.store("role_by_id_before", await _adapter_call(adapter, is_async, "get_role_by_id", role_id))
    await _adapter_call(
        adapter, is_async, "update_role_by_id", role_id, KeycloakRoleRequestDTO(name=role, description="updated"),
    )
    child_role = await _adapter_call(adapter, is_async, "get_realm_role", child)
    sc.store("role_by_id_add_result", await _adapter_call(adapter, is_async, "add_role_composites_by_id", role_id, [child_role]))


@then('the role "{role}" by id has description "{description}" and lists "{child}" as composite using {adapter_type} adapter')
async def step_role_by_id_state(context: Context, role: str, description: str, child: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    role_id = await _role_id(context, role)
    assert sc.get("role_by_id_before").id == role_id
    fetched = await _adapter_call(adapter, is_async, "get_role_by_id", role_id)
    assert fetched.description == description and fetched.composite is True, fetched
    composites = await _adapter_call(adapter, is_async, "get_role_composites_by_id", role_id)
    assert child in [c.name for c in composites], composites
    realm_composites = await _adapter_call(adapter, is_async, "get_role_realm_composites_by_id", role_id)
    assert child in [c.name for c in realm_composites], realm_composites
    client_composites = await _adapter_call(adapter, is_async, "get_role_client_composites_by_id", role_id, await _adapter_call(adapter, is_async, "get_client_id", "test-client" if not is_async else "async-test-client"))
    assert client_composites == [], client_composites


@then('the management permissions of the role "{role}" by id are readable or report the disabled feature using {adapter_type} adapter')
async def step_role_management_permissions(context: Context, role: str, adapter_type: str) -> None:
    """Fine-grained admin permissions v1 is a server feature; without it Keycloak answers 501 ``Feature not enabled``."""
    adapter, is_async, _ = _adapter_parts(context)
    role_id = await _role_id(context, role)
    try:
        permissions = await _adapter_call(adapter, is_async, "get_role_management_permissions_by_id", role_id)
    except Exception as e:  # noqa: BLE001 - the feature may be disabled on the server under test
        assert e.additional_data.get("response_code") == HTTP_NOT_IMPLEMENTED, repr(e)
    else:
        assert isinstance(permissions, KeycloakManagementPermissionDTO), permissions


@when('I remove "{child}" from the composite "{role}" and delete the role "{role}" by its id using {adapter_type} adapter')
async def step_remove_composite_and_delete(context: Context, child: str, role: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    role_id = await _role_id(context, role)
    child_role = await _adapter_call(adapter, is_async, "get_realm_role", child)
    await _adapter_call(adapter, is_async, "delete_role_composites_by_id", role_id, [child_role])
    remaining = await _adapter_call(adapter, is_async, "get_role_composites_by_id", role_id)
    sc.store("role_composites_after_remove", remaining)
    await _adapter_call(adapter, is_async, "delete_role_by_id", role_id)
    sc.store("deleted_role_id", role_id)


@then("the composite was removed and the role no longer exists by id using {adapter_type} adapter")
async def step_role_deleted(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    assert sc.get("role_composites_after_remove") == [], sc.get("role_composites_after_remove")
    try:
        await _adapter_call(adapter, is_async, "get_role_by_id", sc.get("deleted_role_id"))
    except Exception as e:  # noqa: BLE001 - assert on the mapped error type
        assert type(e).__name__ == "ResourceNotFoundError", repr(e)
    else:
        raise AssertionError("the deleted role is still readable by id")
