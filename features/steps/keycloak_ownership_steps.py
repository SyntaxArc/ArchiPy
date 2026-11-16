"""Exercise ownership through the public auth API without external services."""

from uuid import UUID

from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from pydantic import ValidationError

from archipy.adapters.keycloak import auth
from archipy.models.dtos.keycloak.auth_dtos import AuthenticatedUserDTO
from archipy.models.dtos.keycloak.owner_dto import OwnerDTO
from archipy.models.errors import BaseError


@given('the acting chain is "{kind}"')
def acting_chain(context, kind):
    scenario = get_current_scenario_context(context)
    caller = scenario.get("ownership_context")
    chains = {
        "direct": [],
        "user": [{"id": "44444444-4444-4444-8444-444444444444", "type": "USER"}],
        "client": [{"id": "service-client", "type": "CLIENT"}],
        "nested": [
            {"id": "service-client", "type": "CLIENT"},
            {"id": "44444444-4444-4444-8444-444444444444", "type": "USER"},
        ],
    }
    scenario.store(
        "ownership_context", AuthenticatedUserDTO.model_validate({
            **caller.model_dump(), "actor_chain": chains[kind],
        }),
    )


@when("I resolve the authenticated actor")
def resolve_request_actor(context):
    scenario = get_current_scenario_context(context)
    token = auth.AuthContextManager.set_auth_context(scenario.get("ownership_context"))
    try:
        scenario.store("resolved_actor", auth.get_authenticated_actor())
    except BaseError as error:
        scenario.store("ownership_error", error)
    finally:
        auth.AuthContextManager.clear_auth_context(token)


@when("I resolve the authenticated actor and owner together")
def resolve_request_actor_and_owner(context):
    scenario = get_current_scenario_context(context)
    token = auth.AuthContextManager.set_auth_context(scenario.get("ownership_context"))
    try:
        actor, owner = auth.get_authenticated_actor_and_owner()
        scenario.store("resolved_actor", actor)
        scenario.store("resolved_owner", owner)
    except BaseError as error:
        scenario.store("ownership_error", error)
        assert scenario.get("resolved_actor") is None and scenario.get("resolved_owner") is None
    finally:
        auth.AuthContextManager.clear_auth_context(token)


@then('the actor is "{actor_type}" with identifier "{identifier}"')
def resolved_actor(context, actor_type, identifier):
    actor = get_current_scenario_context(context).get("resolved_actor")
    assert actor.type.value == actor_type
    assert actor.id == identifier


@when('I construct a "{owner_type}" owner with "{claims}" claim details')
def construct_inconsistent_owner(context, owner_type, claims):
    owner_uuid = "11111111-1111-4111-8111-111111111111"
    other_uuid = "22222222-2222-4222-8222-222222222222"
    details = {
        "different user": {"user": {"sub": other_uuid}},
        "organization": {"organization": {"id": owner_uuid}},
        "user": {"user": {"sub": owner_uuid}},
        "different organization": {"organization": {"id": other_uuid}},
        "malformed user subject": {"user": {"sub": "not-a-uuid"}},
    }[claims]
    try:
        OwnerDTO(owner_uuid=owner_uuid, type=owner_type, **details)
    except ValidationError as error:
        get_current_scenario_context(context).store("owner_claims_error", error)


@then("the owner rejects inconsistent claim details")
def inconsistent_owner_rejected(context):
    error = get_current_scenario_context(context).get("owner_claims_error")
    assert isinstance(error, ValidationError), error
    assert any(item["type"] == "value_error" for item in error.errors())


@then("the public owner DTO has documented fields and no legacy alias")
def owner_dto_public_schema(context):
    from archipy.models.dtos import keycloak
    from archipy.models.dtos.keycloak import owner_dto

    model = getattr(keycloak, "OwnerDTO", None)
    assert model is not None, "OwnerDTO is missing from public DTO exports"
    owner = get_current_scenario_context(context).get("resolved_owner")
    assert isinstance(owner, model)
    assert not hasattr(keycloak, "Owner")
    assert not hasattr(owner_dto, "Owner")
    schema = model.model_json_schema()
    assert schema["title"] == "OwnerDTO"
    assert all(schema["properties"][field]["description"] for field in ("owner_uuid", "type", "user", "organization"))


@given('an ownership context with scope "{scope}" and organizations "{organizations}" and selection "{selection}"')
def ownership_context(context, scope, organizations, selection):
    organization_id = "22222222-2222-4222-8222-222222222222"
    other_id = "33333333-3333-4333-8333-333333333333"
    claims = {
        "none": {},
        "selected": {"acme": {"id": organization_id, "domain": "acme.test", "plan": ["team"]}},
        "aliases": {"acme": {}},
        "multiple": {"acme": {"id": organization_id}, "other": {"id": other_id}},
        "mixed": {"acme": {"id": organization_id}, "other": {}},
    }[organizations]
    selected = {
        "none": None,
        "selected": {"id": organization_id, "domain": "acme.test", "plan": ["team"]},
        "other": {"id": other_id},
        "missing-id": {},
    }[selection]
    caller = AuthenticatedUserDTO(
        user_uuid="11111111-1111-4111-8111-111111111111",
        username="owner",
        email="",
        roles=[],
        token="unused",
        raw_user_info={
            "sub": "11111111-1111-4111-8111-111111111111",
            "preferred_username": "owner",
            "email": "owner@example.com",
            "identity_verified": True,
        },
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
    assert owner.owner_uuid == UUID(owner_uuid)
    assert not hasattr(owner, "uuid")
    expected_predicates = {"USER": (True, False), "ORGANIZATION": (False, True)}
    assert (owner.is_user, owner.is_organization) == expected_predicates[owner_type]
    payload = owner.model_dump(mode="json")
    assert payload["owner_uuid"] == owner_uuid and payload["type"] == owner_type
    assert "is_user" not in payload and "is_organization" not in payload
    assert "uuid" not in payload
    if owner_type == "USER":
        assert owner.organization is None and payload["organization"] is None
        assert owner.user.user_uuid == owner_uuid
        assert payload["user"]["sub"] == owner_uuid
        assert "user_uuid" not in payload["user"]
        assert owner.user.preferred_username == "owner"
        assert owner.user.email == "owner@example.com"
        assert payload["user"]["identity_verified"] is True
    else:
        assert owner.user is None and payload["user"] is None
        assert owner.organization.id == UUID(owner_uuid)
        assert owner.organization.domain == "acme.test"
        assert payload["organization"]["plan"] == ["team"]


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
        owner.owner_uuid = UUID("44444444-4444-4444-8444-444444444444")
    except ValidationError as error:
        assert error.errors()[0]["type"] == "frozen_instance"
        return
    raise AssertionError("Owner was mutable")


@then("the authenticated user ID is a UUID and serializes as a string")
def ownership_user_uuid(context):
    caller = get_current_scenario_context(context).get("ownership_context")
    assert isinstance(caller.user_uuid, UUID)
    assert caller.model_dump(mode="json")["user_uuid"] == "11111111-1111-4111-8111-111111111111"
    assert not hasattr(caller, "user_id")
    assert "user_id" not in caller.model_dump(mode="json")


@when('I construct an ownership context with malformed "{field}"')
def malformed_owner_context(context, field):
    values = dict(
        user_uuid="11111111-1111-4111-8111-111111111111",
        username="owner",
        email="",
        roles=[],
        token="unused",
        raw_user_info={},
    )
    if field == "user UUID":
        values["user_uuid"] = "invalid"
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
