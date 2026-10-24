from behave import then, when
from behave.runner import Context
from features.steps.keycloak_adapter_steps import _adapter_call, _adapter_parts
from features.test_helpers import get_current_scenario_context

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
