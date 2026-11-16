"""Exercise ownership through the public auth API without external services."""

from uuid import UUID

from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from pydantic import ValidationError

from archipy.adapters.keycloak import auth
from archipy.models.dtos.keycloak.auth_dtos import AuthenticatedUserDTO
from archipy.models.errors import BaseError


@given('an ownership context with scope "{scope}" and organizations "{organizations}" and selection "{selection}"')
def ownership_context(context, scope, organizations, selection):
    organization_id = "22222222-2222-4222-8222-222222222222"
    other_id = "33333333-3333-4333-8333-333333333333"
    claims = {
        "none": {},
        "selected": {"acme": {"id": organization_id}},
        "aliases": {"acme": {}},
        "multiple": {"acme": {"id": organization_id}, "other": {"id": other_id}},
        "mixed": {"acme": {"id": organization_id}, "other": {}},
    }[organizations]
    selected = {
        "none": None,
        "selected": {"id": organization_id},
        "other": {"id": other_id},
        "missing-id": {},
    }[selection]
    caller = AuthenticatedUserDTO(
        user_id="11111111-1111-4111-8111-111111111111",
        username="owner",
        email="",
        roles=[],
        token="unused",
        raw_user_info={"sub": "11111111-1111-4111-8111-111111111111"},
        token_info={"scope": scope},
        organizations=claims,
        selected_organization=selected,
    )
    get_current_scenario_context(context).store("ownership_context", caller)


@when("I resolve the authenticated owner explicitly")
def resolve_explicit_owner(context):
    scenario = get_current_scenario_context(context)
    try:
        scenario.store("resolved_owner", auth.resolve_owner(scenario.get("ownership_context")))
    except BaseError as error:
        scenario.store("ownership_error", error)


@then('the resolved owner is "{owner_type}" with UUID "{owner_uuid}"')
def resolved_owner(context, owner_type, owner_uuid):
    owner = get_current_scenario_context(context).get("resolved_owner")
    assert owner.type.value == owner_type
    assert owner.uuid == UUID(owner_uuid)
    assert owner.model_dump(mode="json") == {"uuid": owner_uuid, "type": owner_type}


@then('ownership resolution fails with "{code}"')
def ownership_error(context, code):
    error = get_current_scenario_context(context).get("ownership_error")
    assert error is not None and error.code == code, error


@given("the ownership context has an impersonating actor")
def ownership_actor(context):
    scenario = get_current_scenario_context(context)
    caller = scenario.get("ownership_context")
    scenario.store(
        "ownership_context",
        AuthenticatedUserDTO.model_validate(
            {
                **caller.model_dump(),
                "actor_chain": [{"id": "44444444-4444-4444-8444-444444444444", "type": "USER"}],
            },
        ),
    )


@given("only raw UserInfo contains an organization claim")
def ownership_raw_claim(context):
    scenario = get_current_scenario_context(context)
    caller = scenario.get("ownership_context")
    scenario.store(
        "ownership_context",
        AuthenticatedUserDTO.model_validate(
            {
                **caller.model_dump(),
                "raw_user_info": {"organization": ["acme"]},
            },
        ),
    )


@when("I resolve the owner through the request context")
def resolve_request_owner(context):
    scenario = get_current_scenario_context(context)
    token = auth.AuthContextManager.set_auth_context(scenario.get("ownership_context"))
    try:
        scenario.store("resolved_owner", auth.get_authenticated_owner())
    except BaseError as error:
        scenario.store("ownership_error", error)
    finally:
        auth.AuthContextManager.clear_auth_context(token)


@then("the resolved owner is immutable")
def immutable_owner(context):
    owner = get_current_scenario_context(context).get("resolved_owner")
    try:
        owner.uuid = UUID("44444444-4444-4444-8444-444444444444")
    except ValidationError as error:
        assert error.errors()[0]["type"] == "frozen_instance"
        return
    raise AssertionError("Owner was mutable")


@then("the authenticated user ID is a UUID and serializes as a string")
def ownership_user_uuid(context):
    caller = get_current_scenario_context(context).get("ownership_context")
    assert isinstance(caller.user_id, UUID)
    assert caller.model_dump(mode="json")["user_id"] == "11111111-1111-4111-8111-111111111111"


@when('I construct an ownership context with malformed "{field}"')
def malformed_owner_context(context, field):
    values = dict(
        user_id="11111111-1111-4111-8111-111111111111",
        username="owner",
        email="",
        roles=[],
        token="unused",
        raw_user_info={},
    )
    if field == "user UUID":
        values["user_id"] = "invalid"
    elif field == "organization UUID":
        values["organizations"] = {"acme": {"id": "invalid"}}
    else:
        values["selected_organization"] = {"id": "invalid"}
    try:
        AuthenticatedUserDTO(**values)
    except ValidationError as error:
        get_current_scenario_context(context).store("ownership_validation_error", error)


@then("the ownership context fails UUID validation")
def ownership_validation_failure(context):
    error = get_current_scenario_context(context).get("ownership_validation_error")
    assert isinstance(error, ValidationError)
    assert any(item["type"] == "uuid_parsing" for item in error.errors())
