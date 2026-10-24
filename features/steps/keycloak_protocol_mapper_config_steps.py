from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from pydantic import ValidationError

from archipy.models.dtos.keycloak.protocol_mapper_config_dtos import (
    PROTOCOL_MAPPER_CONFIGS,
    parse_protocol_mapper_config,
)


def _config_class(mapper):
    return PROTOCOL_MAPPER_CONFIGS[mapper]


def _non_default_values(dto_class):
    values = {}
    for name, field in dto_class.model_fields.items():
        if field.annotation is bool or field.annotation == (bool | None):
            values[name] = not field.default if field.default is not None else True
        else:
            values[name] = f"custom-{name}"
    return values


@given("the {mapper} config DTO with every property set to a non-default value")
def step_non_default(context, mapper):
    sc = get_current_scenario_context(context)
    sc.store("mapper", mapper)
    sc.store("config_dto", _config_class(mapper)(**_non_default_values(_config_class(mapper))))


@given("the {mapper} config DTO with default values")
def step_defaults(context, mapper):
    sc = get_current_scenario_context(context)
    sc.store("mapper", mapper)
    sc.store("config_dto", _config_class(mapper)())


@given("the {mapper} config DTO with {attribute} set to {value}")
def step_attribute_set(context, mapper, attribute, value):
    sc = get_current_scenario_context(context)
    sc.store("mapper", mapper)
    sc.store("config_dto", _config_class(mapper)(**{attribute: value == "True"}))


@when("the config is serialized and parsed back")
def step_round_trip(context):
    sc = get_current_scenario_context(context)
    original = sc.get("config_dto")
    sc.store("parsed", parse_protocol_mapper_config(sc.get("mapper"), original.to_config()))


@then("the parsed config equals the original")
def step_parsed_equals(context):
    sc = get_current_scenario_context(context)
    assert sc.get("parsed") == sc.get("config_dto"), (sc.get("parsed"), sc.get("config_dto"))


@then('the serialized config has "{prop}" set to "{value}"')
def step_serialized_has(context, prop, value):
    config = get_current_scenario_context(context).get("config_dto").to_config()
    assert config.get(prop) == value, config


@then('the serialized config has no "{prop}" key')
def step_serialized_lacks(context, prop):
    config = get_current_scenario_context(context).get("config_dto").to_config()
    assert prop not in config, config


@when('the {mapper} config DTO is built with an unknown field "{field}"')
def step_build_unknown(context, mapper, field):
    sc = get_current_scenario_context(context)
    try:
        _config_class(mapper).model_validate({field: "value"})
    except ValidationError as e:
        sc.store("validation_error", e)
    else:
        sc.store("validation_error", None)


@then("the config DTO build is rejected as invalid")
def step_build_fails(context):
    assert get_current_scenario_context(context).get("validation_error") is not None


@when('a mapper named "{name}" is built from the config')
def step_to_mapper(context, name):
    sc = get_current_scenario_context(context)
    sc.store("mapper_request", sc.get("config_dto").to_mapper(name))


@then('the mapper request has protocol "{protocol}" and protocol mapper "{mapper}"')
def step_mapper_fields(context, protocol, mapper):
    request = get_current_scenario_context(context).get("mapper_request")
    assert request.protocol == protocol and request.protocol_mapper == mapper, request
    assert request.to_payload()["protocolMapper"] == mapper


@then("the mapper request config equals the serialized config")
def step_mapper_config(context):
    sc = get_current_scenario_context(context)
    assert sc.get("mapper_request").config == sc.get("config_dto").to_config()


def _wire_config(text):
    return dict(pair.split("=", 1) for pair in text.split(","))


@when("the wire config {config} of {mapper} is parsed")
def step_parse(context, config, mapper):
    sc = get_current_scenario_context(context)
    sc.store("parsed", parse_protocol_mapper_config(mapper, _wire_config(config)))


@then('the parsed config has {attribute} equal to "{value}"')
def step_parsed_attribute(context, attribute, value):
    parsed = get_current_scenario_context(context).get("parsed")
    assert str(getattr(parsed, attribute)) == value, parsed


@then("no typed config is returned")
def step_no_config(context):
    assert get_current_scenario_context(context).get("parsed") is None
