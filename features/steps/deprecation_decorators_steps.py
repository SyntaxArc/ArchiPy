import importlib
import inspect
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
            """Store the value."""
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
            """Mark the body as run."""
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


@then("the warning class constructor keeps its docstring")
def step_then_warning_class_doc(context):
    target = get_current_scenario_context(context).get("warning_target")
    assert target.__init__.__doc__ == "Store the value.", f"Got {target.__init__.__doc__!r}"


@then("the error class constructor keeps its docstring")
def step_then_error_class_doc(context):
    target = get_current_scenario_context(context).get("error_target")
    assert target.__init__.__doc__ == "Mark the body as run.", f"Got {target.__init__.__doc__!r}"


# ---- renamed decorators ----

_OLD_NAME_CALLS = {
    "retry_decorator": lambda fn: fn(max_retries=2),
    "timeout_decorator": lambda fn: fn(1),
    "timing_decorator": lambda fn: fn(lambda: None),
    "singleton_decorator": lambda fn: fn(),
    "ttl_cache_decorator": lambda fn: fn(ttl_seconds=1),
    "grpc_rate_limit_decorator": lambda fn: fn(calls_count=1, seconds=1),
    "sqlalchemy_atomic_decorator": lambda fn: fn("sqlite"),
}


def _call_old_name(fn, name):
    call = _OLD_NAME_CALLS.get(name, lambda f: f())
    return call(fn)


@when('the old decorator name "{old_name}" is applied')
def step_when_old_name_applied(context, old_name):
    from archipy.helpers import decorators

    sc = get_current_scenario_context(context)
    fn = getattr(decorators, old_name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("old_name_result", _call_old_name(fn, old_name))
    sc.store("deprecation_warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then('exactly one DeprecationWarning should name "{replacement}"')
def step_then_one_warning_names(context, replacement):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert len(caught) == 1, f"Got {[str(w.message) for w in caught]}"
    assert f"use {replacement} instead" in str(caught[0].message), str(caught[0].message)


@then("the DeprecationWarning should point at the calling code")
def step_then_warning_points_at_caller(context):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert caught[0].filename.endswith("deprecation_decorators_steps.py"), caught[0].filename


@when('the new decorator name "{new_name}" is imported from the decorators package')
def step_when_new_name_imported(context, new_name):
    from archipy.helpers import decorators

    sc = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("imported_object", getattr(decorators, new_name))
    sc.store("deprecation_warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@when('the decorator name "{name}" is imported from the module "{module}"')
def step_when_name_imported_from_module(context, name, module):
    sc = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("imported_object", getattr(importlib.import_module(module), name))
    sc.store("deprecation_warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then("it should be a function and not a module")
def step_then_function_not_module(context):
    imported = get_current_scenario_context(context).get("imported_object")
    assert callable(imported) and not inspect.ismodule(imported), f"Got {imported!r}"


@then("no DeprecationWarning should have been emitted")
def step_then_no_deprecation_warning(context):
    caught = get_current_scenario_context(context).get("deprecation_warnings")
    assert caught == [], f"Got {[str(w.message) for w in caught]}"


@when('"{name}" is imported from the old module path "{module}"')
def step_when_imported_from_old_path(context, name, module):
    imported = importlib.import_module(f"archipy.helpers.decorators.{module}")
    get_current_scenario_context(context).store("old_path_object", getattr(imported, name))


@then("the old module path should resolve to a callable")
def step_then_old_path_callable(context):
    assert callable(get_current_scenario_context(context).get("old_path_object"))
