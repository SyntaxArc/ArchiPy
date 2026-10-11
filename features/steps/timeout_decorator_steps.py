import signal
import time

from behave import given, then, when

from archipy.helpers.decorators.timeout import timeout_decorator
from archipy.models.errors import DeadlineExceededError
from features.test_helpers import get_current_scenario_context


def _build(context, behavior, limit):
    sc = get_current_scenario_context(context)

    @timeout_decorator(limit)
    def slow_function(a=0, b=0):
        behavior()
        return "done" if (a, b) == (0, 0) else f"done:{a + b}"

    sc.store("timeout_function", slow_function)


@given("a timeout-decorated function that sleeps {sleep:f} seconds with a {limit:d} second limit")
def step_given_timeout_sleeping(context, sleep, limit):
    _build(context, lambda: time.sleep(sleep), limit)


@given("a timeout-decorated function that raises ValueError with a {limit:d} second limit")
def step_given_timeout_raising(context, limit):
    def fail():
        raise ValueError("boom")

    _build(context, fail, limit)


def _run(context, *args):
    sc = get_current_scenario_context(context)
    previous_handler = signal.getsignal(signal.SIGALRM)
    context.add_cleanup(signal.signal, signal.SIGALRM, previous_handler)
    start = time.monotonic()
    try:
        sc.store("timeout_result", sc.get("timeout_function")(*args))
        sc.store("timeout_error", None)
    except Exception as e:
        sc.store("timeout_error", e)
    sc.store("timeout_elapsed", time.monotonic() - start)


@when("the timeout-decorated function is called")
def step_when_timeout_called(context):
    _run(context)


@when("the timeout-decorated function is called with arguments {a:d} and {b:d}")
def step_when_timeout_called_args(context, a, b):
    _run(context, a, b)


@then('the timeout-decorated function returns "{expected}"')
def step_then_timeout_returns(context, expected):
    sc = get_current_scenario_context(context)
    assert sc.get("timeout_error") is None, f"Unexpected error: {sc.get('timeout_error')!r}"
    assert sc.get("timeout_result") == expected


@then("the timeout-decorated function raises DeadlineExceededError")
def step_then_timeout_raises(context):
    error = get_current_scenario_context(context).get("timeout_error")
    assert isinstance(error, DeadlineExceededError), f"Got {error!r}"


@then("the timeout-decorated function raises ValueError")
def step_then_timeout_raises_value_error(context):
    error = get_current_scenario_context(context).get("timeout_error")
    assert isinstance(error, ValueError), f"Got {error!r}"


@then('the timeout error names operation "{operation}"')
def step_then_timeout_operation(context, operation):
    error = get_current_scenario_context(context).get("timeout_error")
    assert error.additional_data.get("operation") == operation


@then('the timeout error has code "{code}"')
def step_then_timeout_code(context, code):
    error = get_current_scenario_context(context).get("timeout_error")
    assert error.code == code


@then("the timeout-decorated function was interrupted before {seconds:d} seconds")
def step_then_timeout_interrupted(context, seconds):
    elapsed = get_current_scenario_context(context).get("timeout_elapsed")
    assert elapsed < seconds, f"Elapsed {elapsed}"


@then("no timeout alarm remains pending")
def step_then_timeout_no_alarm(context):
    assert signal.alarm(0) == 0


@then('the timeout-decorated function keeps its name "{name}"')
def step_then_timeout_name(context, name):
    assert get_current_scenario_context(context).get("timeout_function").__name__ == name
