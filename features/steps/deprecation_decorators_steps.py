import warnings

from behave import given, then, when

from archipy.helpers.decorators.deprecation_exception import class_deprecation_error, method_deprecation_error
from archipy.helpers.decorators.deprecation_warnings import class_deprecation_warning, method_deprecation_warning
from archipy.models.errors import DeprecationError
from archipy.models.types.language_type import LanguageType
from features.test_helpers import get_current_scenario_context


def _kwargs(**kwargs):
    return {k: v for k, v in kwargs.items() if v is not None}


# ---- warnings ----


@given("a method decorated with method_deprecation_warning without a message")
def step_given_warning_method_default(context):
    _build_warning_method(context, None)


@given('a method decorated with method_deprecation_warning with message "{message}"')
def step_given_warning_method_custom(context, message):
    _build_warning_method(context, message)


def _build_warning_method(context, message):
    class Service:
        @method_deprecation_warning(message)
        def old_method(self):
            return "old-result"

    get_current_scenario_context(context).store("warning_target", Service())


@given("a class decorated with class_deprecation_warning without a message")
def step_given_warning_class_default(context):
    _build_warning_class(context, None)


@given('a class decorated with class_deprecation_warning with message "{message}"')
def step_given_warning_class_custom(context, message):
    _build_warning_class(context, message)


def _build_warning_class(context, message):
    @class_deprecation_warning(message)
    class OldClass:
        def __init__(self, value):
            self.value = value

    get_current_scenario_context(context).store("warning_target", OldClass)


def _record(context, action):
    sc = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("deprecation_result", action(sc.get("warning_target")))
    sc.store("deprecation_warnings", list(caught))


@when("the deprecated-warning method is called")
def step_when_warning_method(context):
    _record(context, lambda target: target.old_method())


@when("the deprecated-warning method is called {count:d} times")
def step_when_warning_method_times(context, count):
    def call_many(target):
        for _ in range(count):
            target.old_method()

    _record(context, call_many)


@when("the deprecated-warning class is instantiated with value {value:d}")
def step_when_warning_class(context, value):
    _record(context, lambda target: target(value))


@then('the deprecation result is "{expected}"')
def step_then_deprecation_result(context, expected):
    assert get_current_scenario_context(context).get("deprecation_result") == expected


@then("the deprecated-warning instance holds value {value:d}")
def step_then_warning_instance_value(context, value):
    assert get_current_scenario_context(context).get("deprecation_result").value == value


@then("exactly one DeprecationWarning was emitted")
def step_then_one_warning(context):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert len(caught) == 1, f"Got {len(caught)} warnings"
    assert issubclass(caught[0].category, DeprecationWarning)


@then("{count:d} DeprecationWarnings were emitted")
def step_then_n_warnings(context, count):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert len(caught) == count
    assert all(issubclass(w.category, DeprecationWarning) for w in caught)


@then('the deprecation warning text is "{text}"')
def step_then_warning_text(context, text):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert str(caught[0].message) == text, str(caught[0].message)


@then("the deprecation warning points at the calling code")
def step_then_warning_location(context):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert caught[0].filename.endswith("deprecation_decorators_steps.py"), caught[0].filename


# ---- errors ----


def _lang(name):
    return LanguageType[name]


@given("a method decorated with method_deprecation_error without arguments")
def step_given_error_method_default(context):
    _build_error_method(context, {})


@given('a method decorated with method_deprecation_error with operation "{operation}" and language {lang}')
def step_given_error_method_custom(context, operation, lang):
    _build_error_method(context, {"operation": operation, "lang": _lang(lang)})


def _build_error_method(context, kwargs):
    sc = get_current_scenario_context(context)
    ran = {"value": False}

    class Service:
        @method_deprecation_error(**kwargs)
        def legacy_method(self):
            ran["value"] = True

    sc.store("error_target", Service())
    sc.store("error_body_ran", ran)


@given("a class decorated with class_deprecation_error without arguments")
def step_given_error_class_default(context):
    _build_error_class(context, {})


@given('a class decorated with class_deprecation_error with operation "{operation}" and language {lang}')
def step_given_error_class_custom(context, operation, lang):
    _build_error_class(context, {"operation": operation, "lang": _lang(lang)})


def _build_error_class(context, kwargs):
    sc = get_current_scenario_context(context)
    ran = {"value": False}

    @class_deprecation_error(**kwargs)
    class LegacyClass:
        def __init__(self):
            ran["value"] = True

    sc.store("error_target", LegacyClass)
    sc.store("error_body_ran", ran)


def _capture(context, action):
    sc = get_current_scenario_context(context)
    try:
        action(sc.get("error_target"))
        sc.store("deprecation_error", None)
    except Exception as e:
        sc.store("deprecation_error", e)


@when("the deprecated-error method is called")
def step_when_error_method(context):
    _capture(context, lambda target: target.legacy_method())


@when("the deprecated-error class is instantiated")
def step_when_error_class(context):
    _capture(context, lambda target: target())


@then("the deprecated-error method body did not run")
def step_then_error_body_not_run(context):
    assert get_current_scenario_context(context).get("error_body_ran")["value"] is False


@then("a DeprecationError is raised")
def step_then_deprecation_error(context):
    error = get_current_scenario_context(context).get("deprecation_error")
    assert isinstance(error, DeprecationError), f"Got {error!r}"


@then('the deprecation error code is "{code}"')
def step_then_deprecation_error_code(context, code):
    assert get_current_scenario_context(context).get("deprecation_error").code == code


@then('the deprecation error names feature "{feature}"')
def step_then_deprecation_error_feature(context, feature):
    error = get_current_scenario_context(context).get("deprecation_error")
    assert error.additional_data.get("deprecated_feature") == feature


@then('the deprecation error message is "{message}"')
def step_then_deprecation_error_message(context, message):
    assert get_current_scenario_context(context).get("deprecation_error").get_message() == message
