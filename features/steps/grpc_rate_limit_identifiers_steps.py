from types import SimpleNamespace
from uuid import uuid4

from behave import given, then, when
from pydantic import SecretStr

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.rate_limit.identifiers import (
    extract_bearer_token_from_metadata,
    invocation_metadata_to_dict,
    resolve_jwt_access_token_sub_from_metadata,
)
from archipy.helpers.utils.jwt_utils import JWTUtils
from features.test_helpers import get_current_scenario_context

_ITEMS_KEY = "identifier_metadata_items"


def _items(context) -> list:
    scenario_context = get_current_scenario_context(context)
    items = scenario_context.get(_ITEMS_KEY)
    if items is None:
        items = []
        scenario_context.store(_ITEMS_KEY, items)
    return items


def _bearer(token: str) -> list:
    return [("authorization", f"Bearer {token}")]


@given("identifier metadata that is empty")
def step_identifier_metadata_empty(context):
    get_current_scenario_context(context).store(_ITEMS_KEY, [])


@given("identifier metadata with tuple entries:")
def step_identifier_metadata_tuples(context):
    _items(context).extend((row["key"], row["value"]) for row in context.table)


@given("identifier metadata with attribute entries:")
def step_identifier_metadata_attrs(context):
    _items(context).extend(SimpleNamespace(key=row["key"], value=row["value"]) for row in context.table)


@given('identifier metadata with list-style pair "{key}" and "{value}"')
def step_identifier_metadata_list_pair(context, key, value):
    _items(context).append([key, value])


@given('identifier metadata with a three-item tuple "{key}", "{value}" and "{extra}"')
def step_identifier_metadata_three_tuple(context, key, value, extra):
    _items(context).append((key, value, extra))


@given('identifier metadata with a one-item tuple "{item}"')
def step_identifier_metadata_one_tuple(context, item):
    _items(context).append((item,))


@given('identifier metadata with a bare string entry "{item}"')
def step_identifier_metadata_bare(context, item):
    _items(context).append(item)


@given('identifier metadata with bytes value "{text}" followed by invalid byte under key "{key}"')
def step_identifier_metadata_bytes(context, text, key):
    _items(context).append((key, text.encode("utf-8") + b"\xff"))


@given('identifier metadata with integer value {number:d} under key "{key}"')
def step_identifier_metadata_int(context, number, key):
    _items(context).append((key, number))


@given('identifier metadata with header "{header}" and value "{value}"')
def step_identifier_metadata_header(context, header, value):
    _items(context).append((header, value))


@given('identifier metadata with bytes header "{header}" and value "{value}"')
def step_identifier_metadata_bytes_header(context, header, value):
    _items(context).append((header, value.encode("utf-8")))


@given("identifier metadata with a valid access token for a new user")
def step_identifier_metadata_valid_access(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = uuid4()
    token = JWTUtils.create_access_token(user_uuid, auth_config=BaseConfig.global_config().AUTH)
    scenario_context.store("identifier_user_uuid", user_uuid)
    _items(context).extend(_bearer(token))


@given("identifier metadata with a refresh token for a new user")
def step_identifier_metadata_refresh(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = uuid4()
    token = JWTUtils.create_refresh_token(user_uuid, auth_config=BaseConfig.global_config().AUTH)
    scenario_context.store("identifier_user_uuid", user_uuid)
    _items(context).extend(_bearer(token))


@given("identifier metadata with an expired access token for a new user")
def step_identifier_metadata_expired(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = uuid4()
    token = JWTUtils.create_access_token(
        user_uuid,
        additional_claims={"exp": 1},
        auth_config=BaseConfig.global_config().AUTH,
    )
    scenario_context.store("identifier_user_uuid", user_uuid)
    _items(context).extend(_bearer(token))


@given("identifier metadata with an access token signed with another key")
def step_identifier_metadata_other_key(context):
    scenario_context = get_current_scenario_context(context)
    user_uuid = uuid4()
    other_auth = BaseConfig.global_config().AUTH.model_copy(
        update={"SECRET_KEY": SecretStr("another-secret-key-that-is-long-enough-for-hs256")},
    )
    token = JWTUtils.create_access_token(user_uuid, auth_config=other_auth)
    scenario_context.store("identifier_user_uuid", user_uuid)
    scenario_context.store("identifier_other_auth", other_auth)
    _items(context).extend(_bearer(token))


@when("identifier metadata is normalized")
def step_identifier_normalize(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("identifier_normalized", invocation_metadata_to_dict(_items(context)))


@when("the bearer token is extracted from identifier metadata")
def step_identifier_extract(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("identifier_bearer", extract_bearer_token_from_metadata(_items(context)))


@when("the subject is resolved from identifier metadata")
def step_identifier_resolve(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("identifier_sub", resolve_jwt_access_token_sub_from_metadata(_items(context)))


@when("the subject is resolved from identifier metadata using that other key configuration")
def step_identifier_resolve_with_config(context):
    scenario_context = get_current_scenario_context(context)
    sub = resolve_jwt_access_token_sub_from_metadata(
        _items(context),
        auth_config=scenario_context.get("identifier_other_auth"),
    )
    scenario_context.store("identifier_sub", sub)


@then("the normalized identifier metadata has {count:d} entries")
def step_identifier_count(context, count):
    normalized = get_current_scenario_context(context).get("identifier_normalized")
    assert len(normalized) == count, f"Expected {count} entries, got {normalized}"


@then('the normalized identifier metadata maps "{key}" to "{value}"')
def step_identifier_maps(context, key, value):
    normalized = get_current_scenario_context(context).get("identifier_normalized")
    assert normalized.get(key) == value, f"Expected {key}={value!r}, got {normalized}"


@then('the extracted identifier bearer token is "{token}"')
def step_identifier_bearer_is(context, token):
    actual = get_current_scenario_context(context).get("identifier_bearer")
    assert actual == token, f"Expected {token!r}, got {actual!r}"


@then("no identifier bearer token is extracted")
def step_identifier_bearer_none(context):
    actual = get_current_scenario_context(context).get("identifier_bearer")
    assert actual is None, f"Expected None, got {actual!r}"


@then("the resolved identifier subject is the user UUID")
def step_identifier_sub_is_uuid(context):
    scenario_context = get_current_scenario_context(context)
    expected = str(scenario_context.get("identifier_user_uuid"))
    actual = scenario_context.get("identifier_sub")
    assert actual == expected, f"Expected {expected}, got {actual!r}"


@then("no identifier subject is resolved")
def step_identifier_sub_none(context):
    actual = get_current_scenario_context(context).get("identifier_sub")
    assert actual is None, f"Expected None, got {actual!r}"
