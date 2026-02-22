from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.models.dtos.base_dtos import BaseDTO, FieldStr
from archipy.models.dtos.pagination_dto import PaginationDTO


@given('a DTO subclass with fields "name" and "email"')
def step_given_dto_subclass(context):
    scenario_context = get_current_scenario_context(context)

    class SampleDTO(BaseDTO):
        name: str
        email: str

    scenario_context.store("dto_class", SampleDTO)


@when("I access the field names as class attributes")
def step_when_access_field_names(context):
    scenario_context = get_current_scenario_context(context)
    dto_class = scenario_context.get("dto_class")
    scenario_context.store("name_attr", dto_class.name)
    scenario_context.store("email_attr", dto_class.email)


@then("each attribute should be a FieldStr instance")
def step_then_attributes_are_fieldstr(context):
    scenario_context = get_current_scenario_context(context)
    assert isinstance(scenario_context.get("name_attr"), FieldStr)
    assert isinstance(scenario_context.get("email_attr"), FieldStr)


@then("each attribute value should match its field name")
def step_then_values_match_field_names(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("name_attr") == "name"
    assert scenario_context.get("email_attr") == "email"


@when('I create an instance with name "{name}" and email "{email}"')
def step_when_create_instance(context, name, email):
    scenario_context = get_current_scenario_context(context)
    dto_class = scenario_context.get("dto_class")
    instance = dto_class(name=name, email=email)
    scenario_context.store("instance", instance)


@then('instance attribute "{attr}" should return "{expected}"')
def step_then_instance_attr_returns(context, attr, expected):
    scenario_context = get_current_scenario_context(context)
    instance = scenario_context.get("instance")
    assert getattr(instance, attr) == expected


@then('class attribute "{attr}" should still return FieldStr "{expected}"')
def step_then_class_attr_still_fieldstr(context, attr, expected):
    scenario_context = get_current_scenario_context(context)
    dto_class = scenario_context.get("dto_class")
    class_attr = getattr(dto_class, attr)
    assert isinstance(class_attr, FieldStr)
    assert class_attr == expected


@when("I use a FieldStr class attribute as a dictionary key")
def step_when_use_fieldstr_as_dict_key(context):
    scenario_context = get_current_scenario_context(context)
    dto_class = scenario_context.get("dto_class")
    test_dict = {dto_class.name: "Alice", dto_class.email: "alice@example.com"}
    scenario_context.store("test_dict", test_dict)


@then("the dictionary should be accessible with the equivalent plain string")
def step_then_dict_accessible_with_plain_string(context):
    scenario_context = get_current_scenario_context(context)
    test_dict = scenario_context.get("test_dict")
    assert test_dict["name"] == "Alice"
    assert test_dict["email"] == "alice@example.com"


@when("I compare the FieldStr class attribute to a plain string")
def step_when_compare_fieldstr(context):
    scenario_context = get_current_scenario_context(context)
    dto_class = scenario_context.get("dto_class")
    scenario_context.store("match_result", dto_class.name == "name")
    scenario_context.store("no_match_result", dto_class.name == "other")


@then("the comparison should return true for matching strings")
def step_then_comparison_true(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("match_result") is True


@then("the comparison should return false for non-matching strings")
def step_then_comparison_false(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("no_match_result") is False


@given('a parent DTO with field "base_field" and a child DTO with field "child_field"')
def step_given_parent_child_dto(context):
    scenario_context = get_current_scenario_context(context)

    class ParentDTO(BaseDTO):
        base_field: str

    class ChildDTO(ParentDTO):
        child_field: str

    scenario_context.store("parent_class", ParentDTO)
    scenario_context.store("child_class", ChildDTO)


@when("I access field names on the child class")
def step_when_access_child_fields(context):
    pass


@then('the child should have FieldStr for "{field_name}"')
def step_then_child_has_fieldstr(context, field_name):
    scenario_context = get_current_scenario_context(context)
    child_class = scenario_context.get("child_class")
    attr = getattr(child_class, field_name)
    assert isinstance(attr, FieldStr)
    assert attr == field_name


@given("the PaginationDTO class")
def step_given_pagination_dto(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("pagination_class", PaginationDTO)


@when("I access its field name class attributes")
def step_when_access_pagination_fields(context):
    pass


@then('"{field_name}" should be a FieldStr with value "{expected}"')
def step_then_field_is_fieldstr_with_value(context, field_name, expected):
    scenario_context = get_current_scenario_context(context)
    pagination_class = scenario_context.get("pagination_class")
    attr = getattr(pagination_class, field_name)
    assert isinstance(attr, FieldStr), f"Expected FieldStr but got {type(attr).__name__}"
    assert attr == expected, f"Expected '{expected}' but got '{attr}'"
