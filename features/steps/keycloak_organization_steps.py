from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts
from features.test_helpers import get_current_scenario_context

from archipy.models.dtos.keycloak.group_dtos import KeycloakGroupRequestDTO
from archipy.models.dtos.keycloak.identity_provider_dtos import (
    KeycloakIdentityProviderDTO,
    KeycloakOrganizationIdentityProviderLinkRequestDTO,
)
from archipy.models.dtos.keycloak.organization_dtos import KeycloakOrganizationInvitationDTO, KeycloakOrganizationMemberDTO


def _org_id(context: Context) -> str:
    org_id = get_current_scenario_context(context).get("latest_organization_id")
    assert org_id, "No organization id in context (create an organization first)"
    return org_id


@when('I create the identity provider "{alias}" using {adapter_type} adapter')
async def step_create_identity_provider(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
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
    admin = adapter.admin_adapter
    if is_async:
        await admin.a_create_idp(payload)
    else:
        admin.create_idp(payload)


@when('I link the identity provider "{alias}" to the organization using {adapter_type} adapter')
async def step_link_identity_provider(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    sc.store("idp_link_result", await _adapter_call(adapter, is_async, "organization_idp_add", _org_id(context), alias))


@then('the organization lists the identity provider "{alias}" and returns it by alias using {adapter_type} adapter')
async def step_organization_lists_identity_provider(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    org_id = _org_id(context)
    idps = await _adapter_call(adapter, is_async, "get_organization_idps", org_id)
    assert alias in [idp.alias for idp in idps], idps
    assert all(isinstance(idp, KeycloakIdentityProviderDTO) for idp in idps)
    one = await _adapter_call(adapter, is_async, "get_organization_idp", org_id, alias)
    assert isinstance(one, KeycloakIdentityProviderDTO) and one.alias == alias, one


@when('I enable auto membership for the identity provider "{alias}" of the organization using {adapter_type} adapter')
async def step_update_identity_provider_link(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    link = KeycloakOrganizationIdentityProviderLinkRequestDTO(auto_membership=False)
    sc.store("idp_update_result", await _adapter_call(adapter, is_async, "update_organization_idp", _org_id(context), alias, link))


@when('I unlink the identity provider "{alias}" from the organization using {adapter_type} adapter')
async def step_unlink_identity_provider(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    sc.store("idp_unlink_result", await _adapter_call(adapter, is_async, "organization_idp_remove", _org_id(context), alias))


@then('the organization no longer lists the identity provider "{alias}" using {adapter_type} adapter')
async def step_organization_no_identity_provider(context: Context, alias: str, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    idps = await _adapter_call(adapter, is_async, "get_organization_idps", _org_id(context))
    assert alias not in [idp.alias for idp in idps], idps


@then("the organization count includes the organization and a search for it counts 1 using {adapter_type} adapter")
async def step_organization_count(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    total = await _adapter_call(adapter, is_async, "get_organizations_count")
    assert isinstance(total, int) and total >= 1, total
    name = sc.get("latest_organization_creation")["name"]
    searched = await _adapter_call(adapter, is_async, "get_organizations_count", {"search": name, "exact": True})
    assert searched == 1, searched


@then('the organization returns member "{username}" by id and accepts a membership type change using {adapter_type} adapter')
async def step_organization_member(context: Context, username: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id = _org_id(context)
    user_id = sc.get(f"user_id_{username}")
    member = await _adapter_call(adapter, is_async, "get_organization_member", org_id, user_id)
    assert isinstance(member, KeycloakOrganizationMemberDTO) and member.username == username, member
    result = await _adapter_call(
        adapter, is_async, "update_organization_member_membership_type", org_id, user_id, "UNMANAGED",
    )
    assert result is not None


@then("the organization has no invitations and an unknown invitation is not found using {adapter_type} adapter")
async def step_organization_invitations(context: Context, adapter_type: str) -> None:
    adapter, is_async, _ = _adapter_parts(context)
    org_id = _org_id(context)
    invitations = await _adapter_call(adapter, is_async, "get_organization_invitations", org_id)
    assert invitations == [], invitations
    assert all(isinstance(i, KeycloakOrganizationInvitationDTO) for i in invitations)
    for operation in ("get_organization_invitation", "delete_organization_invitation", "resend_organization_invitation"):
        try:
            await _adapter_call(adapter, is_async, operation, org_id, "00000000-0000-0000-0000-000000000000")
        except Exception as e:  # noqa: BLE001 - assert on the mapped error type below
            assert type(e).__name__ == "ResourceNotFoundError", f"{operation}: {e!r}"
        else:
            raise AssertionError(f"{operation} accepted an unknown invitation id")


# --- organization groups ---


@when('I create the organization group "{name}" and the subgroup "{child}" using {adapter_type} adapter')
async def step_create_organization_groups(context: Context, name: str, child: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id = _org_id(context)
    group = await _adapter_call(adapter, is_async, "create_organization_group", org_id, KeycloakGroupRequestDTO(name=name))
    sc.store("org_group_create", group)
    sc.store("org_group_id", group.id)
    sub = await _adapter_call(
        adapter, is_async, "create_organization_subgroup", org_id, group.id, KeycloakGroupRequestDTO(name=child),
    )
    sc.store("org_subgroup_create", sub)


@then('the organization groups report their ids and are found by path, list and children using {adapter_type} adapter')
async def step_organization_groups_found(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id = _org_id(context)
    group_id = sc.get("org_group_id")
    assert sc.get("org_group_create").id == group_id and group_id, sc.get("org_group_create")
    assert sc.get("org_subgroup_create").id, sc.get("org_subgroup_create")
    groups = await _adapter_call(adapter, is_async, "get_organization_groups", org_id)
    assert group_id in [g.id for g in groups], groups
    fetched = await _adapter_call(adapter, is_async, "get_organization_group", org_id, group_id)
    by_path = await _adapter_call(adapter, is_async, "get_organization_group_by_path", org_id, f"/{fetched.name}")
    assert by_path.id == group_id
    children = await _adapter_call(adapter, is_async, "get_organization_group_children", org_id, group_id)
    assert [c.id for c in children] == [sc.get("org_subgroup_create").id], children


@when('I add user "{username}" to the organization group and assign realm role "{role}" using {adapter_type} adapter')
async def step_organization_group_membership_and_roles(
    context: Context, username: str, role: str, adapter_type: str,
) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id, group_id = _org_id(context), sc.get("org_group_id")
    user_id = sc.get(f"user_id_{username}")
    await _adapter_call(adapter, is_async, "add_user_to_organization_group", org_id, group_id, user_id)
    realm_role = await _adapter_call(adapter, is_async, "get_realm_role", role)
    sc.store("org_group_role", realm_role)
    result = await _adapter_call(adapter, is_async, "assign_organization_group_realm_roles", org_id, group_id, [realm_role])
    sc.store("org_group_assign_result", result)


@then('the organization group lists member "{username}" and role "{role}" in every role view using {adapter_type} adapter')
async def step_organization_group_listings(context: Context, username: str, role: str, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id, group_id = _org_id(context), sc.get("org_group_id")
    user_id = sc.get(f"user_id_{username}")
    members = await _adapter_call(adapter, is_async, "get_organization_group_members", org_id, group_id)
    assert username in [m.username for m in members], members
    member_groups = await _adapter_call(adapter, is_async, "get_organization_member_groups", org_id, user_id)
    assert group_id in [g.id for g in member_groups], member_groups
    realm_roles = await _adapter_call(adapter, is_async, "get_organization_group_realm_roles", org_id, group_id)
    assert role in [r.name for r in realm_roles], realm_roles
    mappings = await _adapter_call(adapter, is_async, "get_organization_group_role_mappings", org_id, group_id)
    assert role in [r.name for r in mappings.realm_mappings or []], mappings
    composite = await _adapter_call(adapter, is_async, "get_organization_group_realm_roles_composite", org_id, group_id)
    assert role in [r.name for r in composite], composite
    available = await _adapter_call(adapter, is_async, "get_organization_group_realm_roles_available", org_id, group_id)
    assert role not in [r.name for r in available], available


@when("I remove the role and the member, then update and delete the organization group using {adapter_type} adapter")
async def step_organization_group_cleanup(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id, group_id = _org_id(context), sc.get("org_group_id")
    await _adapter_call(
        adapter, is_async, "delete_organization_group_realm_roles", org_id, group_id, [sc.get("org_group_role")],
    )
    members = await _adapter_call(adapter, is_async, "get_organization_group_members", org_id, group_id)
    for member in members:
        await _adapter_call(adapter, is_async, "remove_user_from_organization_group", org_id, group_id, member.id)
    await _adapter_call(
        adapter, is_async, "update_organization_group", org_id, group_id, KeycloakGroupRequestDTO(name="renamed-group"),
    )
    sc.store("org_group_renamed", await _adapter_call(adapter, is_async, "get_organization_group", org_id, group_id))
    await _adapter_call(adapter, is_async, "delete_organization_group", org_id, group_id)


@then("the organization group was renamed, emptied and no longer exists using {adapter_type} adapter")
async def step_organization_group_gone(context: Context, adapter_type: str) -> None:
    adapter, is_async, sc = _adapter_parts(context)
    org_id, group_id = _org_id(context), sc.get("org_group_id")
    assert sc.get("org_group_renamed").name == "renamed-group"
    groups = await _adapter_call(adapter, is_async, "get_organization_groups", org_id)
    assert group_id not in [g.id for g in groups], groups
