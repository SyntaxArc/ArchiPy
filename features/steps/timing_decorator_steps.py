import logging
import time

from behave import given, then, when

from archipy.helpers.decorators.timing import timing_decorator
from features.test_helpers import get_current_scenario_context

_TIMING_LOGGER = "archipy.helpers.decorators.timing"


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


@given("a timing-decorated function that sleeps {sleep:f} seconds")
def step_given_timing_function(context, sleep):
    sc = get_current_scenario_context(context)

    @timing_decorator
    def slow_work(a=0, b=0):
        time.sleep(sleep)
        return "result" if (a, b) == (0, 0) else f"result:{a + b}"

    sc.store("timing_function", slow_work)


@given("a timing-decorated function that raises ValueError")
def step_given_timing_raising_function(context):
    sc = get_current_scenario_context(context)

    @timing_decorator
    def slow_work():
        raise ValueError("boom")

    sc.store("timing_function", slow_work)


@given("the root logging level is {level}")
def step_given_timing_root_level(context, level):
    sc = get_current_scenario_context(context)
    root = logging.getLogger()
    timing_logger = logging.getLogger(_TIMING_LOGGER)
    handler = _ListHandler()
    previous_level = root.level
    timing_logger.addHandler(handler)
    root.setLevel(getattr(logging, level))

    def restore():
        root.setLevel(previous_level)
        timing_logger.removeHandler(handler)

    context.add_cleanup(restore)
    sc.store("timing_handler", handler)


def _run(context, *args):
    sc = get_current_scenario_context(context)
    try:
        sc.store("timing_result", sc.get("timing_function")(*args))
        sc.store("timing_error", None)
    except Exception as e:
        sc.store("timing_error", e)


@when("the timing-decorated function is called")
def step_when_timing_called(context):
    _run(context)


@when("the timing-decorated function is called with arguments {a:d} and {b:d}")
def step_when_timing_called_args(context, a, b):
    _run(context, a, b)


@then('the timing-decorated function returns "{expected}"')
def step_then_timing_returns(context, expected):
    sc = get_current_scenario_context(context)
    assert sc.get("timing_error") is None, f"Unexpected error: {sc.get('timing_error')!r}"
    assert sc.get("timing_result") == expected


@then("the timing-decorated function raises ValueError")
def step_then_timing_raises(context):
    assert isinstance(get_current_scenario_context(context).get("timing_error"), ValueError)


@then('one timing log message is recorded for "{name}"')
def step_then_timing_one_message(context, name):
    messages = get_current_scenario_context(context).get("timing_handler").messages
    assert len(messages) == 1, f"Got {messages}"
    assert messages[0].startswith(f"{name} took ") and messages[0].endswith(" seconds to execute."), messages[0]


@then("the timing log message reports at least {seconds:f} seconds")
def step_then_timing_duration(context, seconds):
    message = get_current_scenario_context(context).get("timing_handler").messages[0]
    reported = float(message.split(" took ")[1].split(" seconds")[0])
    assert reported >= seconds, f"Reported {reported}"


@then("no timing log message is recorded")
def step_then_timing_no_message(context):
    messages = get_current_scenario_context(context).get("timing_handler").messages
    assert messages == [], f"Got {messages}"


@then('the timing-decorated function keeps its name "{name}"')
def step_then_timing_name(context, name):
    assert get_current_scenario_context(context).get("timing_function").__name__ == name
