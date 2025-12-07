from behave import given, then, when

from archipy.helpers.utils.file_utils import FileUtils
from archipy.models.errors import BaseError
from features.test_helpers import get_current_scenario_context


@given('a valid file path "{file_path}"')
def step_given_valid_file_path(context, file_path):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("file_path", file_path)


@given("an empty file path")
def step_given_empty_file_path(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("file_path", "")


@given('a valid file path "{file_path}" and negative minutes')
def step_given_negative_minutes(context, file_path):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("file_path", file_path)
    scenario_context.store("minutes", -5)


@when("a secure link is created")
def step_when_secure_link_created(context):
    scenario_context = get_current_scenario_context(context)
    file_path = scenario_context.get("file_path")

    secure_link = FileUtils.create_secure_link(file_path)
    scenario_context.store("secure_link", secure_link)


@when("a secure link creation is attempted")
def step_when_secure_link_attempted(context):
    scenario_context = get_current_scenario_context(context)
    file_path = scenario_context.get("file_path")
    minutes = scenario_context.get("minutes")

    try:
        secure_link = FileUtils.create_secure_link(file_path, minutes)
        scenario_context.store("secure_link", secure_link)
    except BaseError as e:
        # Get English message by temporarily setting language to EN
        from archipy.models.types.language_type import LanguageType

        original_lang = e.lang
        e.lang = LanguageType.EN
        scenario_context.store("exception_message", e.get_message())
        e.lang = original_lang


@then("the secure link should contain a hash and expiration timestamp")
def step_then_secure_link_contains_hash(context):
    scenario_context = get_current_scenario_context(context)
    secure_link = scenario_context.get("secure_link")

    assert "?md5=" in secure_link and "&expires_at=" in secure_link


@given('a file name "{file_name}"')
def step_given_file_name(context, file_name):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("file_name", file_name)


@when("the file name is validated")
def step_when_file_validated(context):
    scenario_context = get_current_scenario_context(context)
    file_name = scenario_context.get("file_name")

    is_valid = FileUtils.validate_file_name(file_name)
    scenario_context.store("is_valid", is_valid)
