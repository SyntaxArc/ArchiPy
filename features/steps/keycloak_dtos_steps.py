import importlib
import warnings

from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from pydantic import ValidationError

from archipy.adapters.keycloak.base import to_mutation_result, to_request_payload, with_created_id

from archipy.models.dtos.keycloak.common_dtos import KeycloakMutationResultDTO
from archipy.models.dtos.keycloak import authz_dtos, common_dtos, client_scope_dtos, component_dtos, group_dtos, role_dtos, user_dtos
from archipy.models.dtos.keycloak import organization_dtos, token_dtos, uma_dtos

_MODULES = (
    common_dtos,
    authz_dtos,
    client_scope_dtos,
    component_dtos,
    group_dtos,
    organization_dtos,
    role_dtos,
    token_dtos,
    uma_dtos,
    user_dtos,
)


def _dto_class(name):
    for module in _MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AssertionError(f"unknown Keycloak DTO {name}")


@given('a Keycloak {dto} response with an unknown field "{field}"')
def step_response_with_unknown_field(context, dto, field):
    sc = get_current_scenario_context(context)
    sc.store("response", _dto_class(dto).model_validate({field: "value"}))


@then('the {dto} response keeps "{field}" in its extra fields')
def step_response_keeps_extra(context, dto, field):
    response = get_current_scenario_context(context).get("response")
    assert response.model_extra == {field: "value"}, response.model_extra


@when('a Keycloak {dto} is built with an unknown field "{field}"')
def step_build_with_unknown_field(context, dto, field):
    sc = get_current_scenario_context(context)
    try:
        _dto_class(dto).model_validate({field: "value"})
    except ValidationError as e:
        sc.store("validation_error", e)
    else:
        sc.store("validation_error", None)


@then("building the {dto} fails with a validation error")
def step_build_fails(context, dto):
    assert get_current_scenario_context(context).get("validation_error") is not None


@given('a Keycloak request DTO {dto} with {attribute} set to "{value}"')
def step_request_with_attribute(context, dto, attribute, value):
    sc = get_current_scenario_context(context)
    sc.store("request", _dto_class(dto)(**{attribute: value}))


@then('its payload has "{wire_name}" set to "{value}"')
def step_payload_has(context, wire_name, value):
    payload = get_current_scenario_context(context).get("request").to_payload()
    assert payload == {wire_name: value}, payload


@given('a Keycloak KeycloakRoleDTO response with name "{name}"')
def step_role_response(context, name):
    get_current_scenario_context(context).store("response", role_dtos.KeycloakRoleDTO(name=name))


@when("the response is read with {access}")
def step_read_response(context, access):
    sc = get_current_scenario_context(context)
    response = sc.get("response")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = response["name"] if access == "brackets" else response.get("name")
    sc.store("value", value)
    sc.store("warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then("a dict-style access deprecation warning is raised")
def step_dict_warning(context):
    caught = get_current_scenario_context(context).get("warnings")
    assert len(caught) == 1 and "dict-style access" in str(caught[0].message), caught


@then('the value read is "{value}"')
def step_value_read(context, value):
    assert get_current_scenario_context(context).get("value") == value


@given("a Keycloak KeycloakTokenClaimsDTO response without claims")
def step_empty_claims(context):
    get_current_scenario_context(context).store("response", token_dtos.KeycloakTokenClaimsDTO())


@then("the response is falsy")
def step_response_falsy(context):
    assert not get_current_scenario_context(context).get("response")


@when("a {kind} payload is converted for the Keycloak adapter")
def step_convert_payload(context, kind):
    sc = get_current_scenario_context(context)
    value = group_dtos.KeycloakGroupRequestDTO(name="ops") if kind == "DTO" else {"name": "ops"}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("adapter_payload", to_request_payload(value))
    sc.store("warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then('the adapter payload is {{"name": "ops"}}')
def step_adapter_payload(context):
    assert get_current_scenario_context(context).get("adapter_payload") == {"name": "ops"}


@then("the dict deprecation warning is {state}")
def step_dict_deprecation_state(context, state):
    caught = get_current_scenario_context(context).get("warnings")
    assert bool(caught) == (state == "raised"), caught


_MUTATION_BODIES = {
    "an empty dict": {},
    "empty bytes": b"",
    "a skip-exists dict": {"msg": "Already exists"},
    "JSON bytes with a field": b'{"futureField": 1}',
    "non-JSON bytes": b"<html>created</html>",
}


@when("the Keycloak mutation body {body} is converted")
def step_convert_mutation_body(context, body):
    get_current_scenario_context(context).store("mutation_result", to_mutation_result(KeycloakMutationResultDTO, _MUTATION_BODIES[body]))


@then("the mutation result message is {message}")
def step_mutation_message(context, message):
    result = get_current_scenario_context(context).get("mutation_result")
    assert result.msg == (None if message == "none" else message), result


@then("the mutation result extra fields are {extra}")
def step_mutation_extra(context, extra):
    result = get_current_scenario_context(context).get("mutation_result")
    expected = {} if extra == "none" else {extra: 1}
    assert (result.model_extra or {}) == expected, result.model_extra


@when("the Keycloak mutation body {body} is converted to {result_dto}")
def step_convert_mutation_body_to(context, body, result_dto):
    get_current_scenario_context(context).store(
        "mutation_result",
        to_mutation_result(_dto_class(result_dto), _MUTATION_BODIES[body]),
    )


@then("the result is a {result_dto} and a KeycloakMutationResultDTO")
def step_result_is_subclass(context, result_dto):
    result = get_current_scenario_context(context).get("mutation_result")
    assert type(result) is _dto_class(result_dto)
    assert isinstance(result, KeycloakMutationResultDTO)


@given("a Keycloak create result with message {message}")
def step_create_result_with_message(context, message):
    msg = None if message == "none" else message
    get_current_scenario_context(context).store("create_result", common_dtos.KeycloakCreateResultDTO(msg=msg))


@when('the id of the created resource is looked up as "{created_id}"')
def step_lookup_created_id(context, created_id):
    sc = get_current_scenario_context(context)
    calls = []

    def lookup():
        calls.append(1)
        return created_id

    sc.store("create_result", with_created_id(sc.get("create_result"), lookup))
    sc.store("lookup_calls", len(calls))


@then("the create result id is {expected}")
def step_create_result_id(context, expected):
    result = get_current_scenario_context(context).get("create_result")
    assert result.id == (None if expected == "none" else expected), result


@then("the lookup ran {ran}")
def step_lookup_ran(context, ran):
    assert (get_current_scenario_context(context).get("lookup_calls") == 1) == (ran == "yes")


@when('the deprecated module "{old_module}" is read for "{name}"')
def step_read_deprecated_module(context, old_module, name):
    sc = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("old_object", getattr(importlib.import_module(old_module), name))
    sc.store("warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then('it is the same object as "{new_module}" "{name}"')
def step_same_object(context, new_module, name):
    old = get_current_scenario_context(context).get("old_object")
    assert old is getattr(importlib.import_module(new_module), name)


@then('a deprecation warning names "{old_module}"')
def step_warning_names_module(context, old_module):
    caught = get_current_scenario_context(context).get("warnings")
    assert any(old_module in str(w.message) and "6.0.0" in str(w.message) for w in caught), caught
