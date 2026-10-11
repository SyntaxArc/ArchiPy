import time

from behave import given, then, when

from archipy.helpers.decorators.retry import retry_decorator
from archipy.models.errors import ResourceExhaustedError
from features.test_helpers import get_current_scenario_context

_EXCEPTIONS = {"ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError}


@given("a retry config with max_retries {max_retries:d} and delay {delay:f}")
def step_given_retry_config(context, max_retries, delay):
    sc = get_current_scenario_context(context)
    sc.store("retry_max_retries", max_retries)
    sc.store("retry_delay", delay)


@given('a retry resource type "{resource_type}"')
def step_given_retry_resource_type(context, resource_type):
    get_current_scenario_context(context).store("retry_resource_type", resource_type)


@given("a retry config retrying only on {name}")
def step_given_retry_on(context, name):
    get_current_scenario_context(context).store("retry_on", (_EXCEPTIONS[name],))


@given("a retry config ignoring {name}")
def step_given_retry_ignore(context, name):
    get_current_scenario_context(context).store("retry_ignore", (_EXCEPTIONS[name],))


@given("a retry-decorated function that raises {name} on the first {fails:d} calls")
def step_given_retry_function(context, name, fails):
    sc = get_current_scenario_context(context)
    calls = {"count": 0}
    exc_type = _EXCEPTIONS[name]

    @retry_decorator(
        max_retries=sc.get("retry_max_retries"),
        delay=sc.get("retry_delay"),
        retry_on=sc.get("retry_on"),
        ignore=sc.get("retry_ignore"),
        resource_type=sc.get("retry_resource_type"),
    )
    def flaky_function(a=0, b=0):
        calls["count"] += 1
        if calls["count"] <= fails:
            raise exc_type("transient failure")
        return "ok" if (a, b) == (0, 0) else f"ok:{a + b}"

    sc.store("retry_function", flaky_function)
    sc.store("retry_calls", calls)


def _run_retry_function(context, *args):
    sc = get_current_scenario_context(context)
    func = sc.get("retry_function")
    start = time.monotonic()
    try:
        sc.store("retry_result", func(*args))
        sc.store("retry_error", None)
    except Exception as e:
        sc.store("retry_error", e)
    sc.store("retry_elapsed", time.monotonic() - start)


@when("the retry-decorated function is called")
def step_when_retry_called(context):
    _run_retry_function(context)


@when("the retry-decorated function is called with arguments {a:d} and {b:d}")
def step_when_retry_called_args(context, a, b):
    _run_retry_function(context, a, b)


@then('the retry-decorated function returns "{expected}"')
def step_then_retry_returns(context, expected):
    sc = get_current_scenario_context(context)
    assert sc.get("retry_error") is None, f"Unexpected error: {sc.get('retry_error')!r}"
    assert sc.get("retry_result") == expected, f"Got {sc.get('retry_result')!r}"


@then("the retry-decorated function raises ResourceExhaustedError")
def step_then_retry_raises_exhausted(context):
    error = get_current_scenario_context(context).get("retry_error")
    assert isinstance(error, ResourceExhaustedError), f"Got {error!r}"


@then("the retry-decorated function raises built-in error {name}")
def step_then_retry_raises(context, name):
    error = get_current_scenario_context(context).get("retry_error")
    assert type(error) is _EXCEPTIONS[name], f"Got {error!r}"


@then("the retry-decorated function was invoked {count:d} times")
def step_then_retry_invocations(context, count):
    calls = get_current_scenario_context(context).get("retry_calls")
    assert calls["count"] == count, f"Invoked {calls['count']} times"


@then('the retry error carries resource type "{resource_type}"')
def step_then_retry_error_resource_type(context, resource_type):
    error = get_current_scenario_context(context).get("retry_error")
    assert error.additional_data.get("resource_type") == resource_type


@then("the retry elapsed time is at least {seconds:f} seconds")
def step_then_retry_elapsed_min(context, seconds):
    elapsed = get_current_scenario_context(context).get("retry_elapsed")
    assert elapsed >= seconds, f"Elapsed {elapsed}"


@then("the retry elapsed time is below {seconds:f} seconds")
def step_then_retry_elapsed_max(context, seconds):
    elapsed = get_current_scenario_context(context).get("retry_elapsed")
    assert elapsed < seconds, f"Elapsed {elapsed}"


@then('the retry-decorated function keeps its name "{name}"')
def step_then_retry_name(context, name):
    func = get_current_scenario_context(context).get("retry_function")
    assert func.__name__ == name
