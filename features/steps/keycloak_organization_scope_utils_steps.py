from uuid import UUID, uuid4

from behave import given, then, when

from archipy.helpers.utils.keycloak_utils import KeycloakUtils
from archipy.models.errors import PermissionDeniedError
from features.test_helpers import get_current_scenario_context

WILDCARD_SCOPE = "organization:*"


def _organization_claim(count: int) -> tuple[dict[str, dict[str, str]], set[UUID]]:
    uuids = {uuid4() for _ in range(count)}
    claim = {f"org-{index}": {"id": str(organization_uuid)} for index, organization_uuid in enumerate(uuids)}
    return claim, uuids


def _malformed_claim(case: str) -> object:
    claims = {
        "non-mapping": ["not", "a", "mapping"],
        "entry without id": {"acme": {"name": "Acme"}},
        "invalid uuid": {"acme": {"id": "not-a-uuid"}},
    }
    return claims[case]


def _store_claims(context, token_info, expected_uuids=None) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("token_info", token_info)
    scenario_context.store("expected_uuids", expected_uuids or set())


@given('token claims of kind "{kind}"')
def step_given_claims_of_kind(context, kind):
    if kind == "none":
        _store_claims(context, None)
    elif kind == "no organization":
        _store_claims(context, {"scope": "openid profile"})
    else:
        scope = "openid organization:*" if kind == "one organization with wildcard" else "openid"
        claim, uuids = _organization_claim(1)
        _store_claims(context, {"organization": claim, "scope": scope}, uuids)


@given('token claims with {count:d} organizations and scope "{scope}"')
def step_given_claims_with_organizations(context, count, scope):
    claim, uuids = _organization_claim(count)
    _store_claims(context, {"organization": claim, "scope": scope}, uuids)


@given('token claims with a malformed organization claim "{case}" and scope "{scope}"')
def step_given_claims_with_malformed_organization(context, case, scope):
    _store_claims(context, {"organization": _malformed_claim(case), "scope": scope})


@given("token claims with {count:d} organizations and a scope claim that is {scope_kind}")
def step_given_claims_with_non_string_scope(context, count, scope_kind):
    claim, uuids = _organization_claim(count)
    token_info = {"organization": claim}
    if scope_kind == "a list":
        token_info["scope"] = ["openid", WILDCARD_SCOPE]
    elif scope_kind == "None":
        token_info["scope"] = None
    _store_claims(context, token_info, uuids)


def _run(context, action) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("result", None)
    scenario_context.store("error", None)
    try:
        scenario_context.store("result", action(scenario_context.get("token_info")))
    except PermissionDeniedError as e:
        scenario_context.store("error", e)


@when("the selected organization is resolved")
def step_when_resolved(context):
    _run(context, KeycloakUtils.resolve_selected_organization_uuid)


@when("the selected organization is required")
def step_when_required(context):
    _run(context, KeycloakUtils.require_selected_organization_uuid)


@when("the organization uuids are parsed")
def step_when_parsed(context):
    _run(context, KeycloakUtils.parse_organization_uuids)


@then('the resolution outcome should be "{outcome}"')
def step_then_outcome(context, outcome):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    if outcome == "denied":
        assert isinstance(error, PermissionDeniedError), f"expected PermissionDeniedError, got {error!r}"
        return
    assert error is None, error
    if outcome == "none":
        assert scenario_context.get("result") is None
    else:
        assert scenario_context.get("result") in scenario_context.get("expected_uuids")


@then("no organization uuids should be parsed")
def step_then_no_uuids(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("result") == set()


@then('a permission denied error should be raised with reason "{reason}"')
def step_then_permission_denied(context, reason):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    assert isinstance(error, PermissionDeniedError), f"expected PermissionDeniedError, got {error!r}"
    assert error.additional_data.get("reason") == reason


@then("the error should report an organization count of {count:d}")
def step_then_error_count(context, count):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("error").additional_data.get("organization_count") == count
