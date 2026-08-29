"""Behave steps for OpenTelemetry tracing and metrics decorators."""

from __future__ import annotations

import logging

from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context
from opentelemetry import trace
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import (
    async_trace_span,
    count_calls,
    measure_duration,
    trace_class,
    trace_root,
    trace_span,
)
from archipy.helpers.utils.error_utils import ErrorUtils
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import NotFoundError


def _setup_otel_testing(context: Context) -> None:
    """Enable OTel and install in-memory exporters for the current scenario."""
    scenario_context = get_current_scenario_context(context)
    OtelUtils.reset_for_testing()

    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False

    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    OtelUtils.configure_for_testing(span_exporter=span_exporter, metric_reader=metric_reader)

    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("metric_reader", metric_reader)
    scenario_context.store("otel_enabled_for_test", True)


def _close_open_test_spans(scenario_context) -> None:
    """End ambient/manual spans left open if a scenario failed mid-way."""
    for span_key, cm_key in (
        ("ambient_parent_span", "ambient_parent_context_cm"),
        ("manual_span", "manual_span_cm"),
    ):
        span = scenario_context.get(span_key)
        cm = scenario_context.get(cm_key)
        if span is not None:
            try:
                if span.is_recording():
                    span.end()
            except Exception:
                pass
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
        scenario_context.store(span_key, None)
        scenario_context.store(cm_key, None)


def teardown_otel_testing(context: Context) -> None:
    """Reset OTel providers and restore the master switch after a scenario.

    Called from ``features/environment.py`` ``after_scenario`` (Behave only
    loads hooks from environment, not step modules).
    """
    try:
        scenario_context = get_current_scenario_context(context)
    except AttributeError:
        return

    if not scenario_context.get("otel_enabled_for_test", False):
        return

    _close_open_test_spans(scenario_context)
    OtelUtils.reset_for_testing()
    try:
        config = BaseConfig.global_config()
        config.OTEL.IS_ENABLED = False
        config.OTEL.TRACES_ENABLED = False
        config.OTEL.METRICS_ENABLED = False
    except AssertionError:
        pass
    scenario_context.store("otel_enabled_for_test", False)


def _finished_spans(context: Context) -> list:
    scenario_context = get_current_scenario_context(context)
    exporter: InMemorySpanExporter = scenario_context.get("span_exporter")
    return list(exporter.get_finished_spans())


def _span_by_name(context: Context, name: str):
    spans = [span for span in _finished_spans(context) if span.name == name]
    assert spans, f"No finished span named '{name}'. Found: {[s.name for s in _finished_spans(context)]}"
    return spans[-1]


def _metric_datapoints(context: Context, instrument_name: str) -> list:
    scenario_context = get_current_scenario_context(context)
    reader: InMemoryMetricReader = scenario_context.get("metric_reader")
    metrics_data = reader.get_metrics_data()
    points: list = []
    if metrics_data is None:
        return points
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != instrument_name:
                    continue
                points.extend(list(metric.data.data_points))
    return points


def _span_has_exception_event(span) -> bool:
    return any(event.name == "exception" for event in span.events)


@given("OpenTelemetry is configured for testing")
def step_given_otel_configured(context):
    _setup_otel_testing(context)


@given("OpenTelemetry is disabled for testing")
def step_given_otel_disabled(context):
    """Flip the master switch off after Background setup (decorator no-op path)."""
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = False
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = False
    # Keep exporters/flag so after_scenario still resets providers
    scenario_context.store("otel_enabled_for_test", True)


@given('a sync function decorated with trace_span named "{span_name}"')
def step_given_trace_span(context, span_name):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name=span_name)
    def traced_sync() -> str:
        return "ok"

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", span_name)


@given('an async function decorated with async_trace_span named "{span_name}"')
def step_given_async_trace_span(context, span_name):
    scenario_context = get_current_scenario_context(context)

    @async_trace_span(name=span_name)
    async def traced_async() -> str:
        return "ok"

    scenario_context.store("traced_async", traced_async)
    scenario_context.store("expected_span_name", span_name)


@given('a sync function decorated with trace_span that captures arg "{arg_name}"')
def step_given_trace_span_capture_args(context, arg_name):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name="capture_args_span", capture_args=[arg_name])
    def traced_sync(user_id: int) -> int:
        return user_id

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", "capture_args_span")
    scenario_context.store("capture_arg_name", arg_name)


@given("a sync function decorated with trace_span that raises an error")
def step_given_trace_span_raises(context):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name="failing_span")
    def traced_sync() -> None:
        raise RuntimeError("otel test failure")

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", "failing_span")


@given("a sync function decorated with trace_span that raises NotFoundError")
def step_given_trace_span_raises_not_found(context):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name="client_error_span")
    def traced_sync() -> None:
        raise NotFoundError(resource_type="user")

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", "client_error_span")


@given("an ambient parent span is active")
def step_given_ambient_parent(context):
    scenario_context = get_current_scenario_context(context)
    tracer = OtelUtils.get_tracer(__name__)
    parent_span = tracer.start_span("ambient_parent")
    # Keep parent open so child spans see it as ambient context
    context_cm = trace.use_span(parent_span, end_on_exit=False)
    context_cm.__enter__()
    scenario_context.store("ambient_parent_span", parent_span)
    scenario_context.store("ambient_parent_context_cm", context_cm)
    scenario_context.store("ambient_parent_trace_id", parent_span.get_span_context().trace_id)


@given('a sync function decorated with trace_root named "{span_name}"')
def step_given_trace_root(context, span_name):
    scenario_context = get_current_scenario_context(context)

    @trace_root(name=span_name)
    def traced_root() -> str:
        return "root"

    scenario_context.store("traced_root", traced_root)
    scenario_context.store("expected_span_name", span_name)


@given("a class decorated with trace_class")
def step_given_trace_class(context):
    scenario_context = get_current_scenario_context(context)

    @trace_class()
    class TracedService:
        def public_method(self) -> str:
            return "public"

        def _private_method(self) -> str:
            return "private"

    scenario_context.store("traced_service", TracedService())


@given('a sync function decorated with measure_duration named "{instrument_name}"')
def step_given_measure_duration(context, instrument_name):
    scenario_context = get_current_scenario_context(context)

    @measure_duration(name=instrument_name)
    def measured_sync() -> str:
        return "timed"

    scenario_context.store("measured_sync", measured_sync)
    scenario_context.store("expected_instrument_name", instrument_name)


@given('a sync function decorated with count_calls named "{instrument_name}"')
def step_given_count_calls(context, instrument_name):
    scenario_context = get_current_scenario_context(context)

    @count_calls(name=instrument_name)
    def counted_sync() -> str:
        return "counted"

    scenario_context.store("counted_sync", counted_sync)
    scenario_context.store("expected_instrument_name", instrument_name)


@given('an active recording span named "{span_name}"')
def step_given_active_recording_span(context, span_name):
    scenario_context = get_current_scenario_context(context)
    tracer = OtelUtils.get_tracer(__name__)
    span = tracer.start_span(span_name)
    cm = trace.use_span(span, end_on_exit=False)
    cm.__enter__()
    scenario_context.store("manual_span", span)
    scenario_context.store("manual_span_cm", cm)
    scenario_context.store("expected_span_name", span_name)


@when("I call the traced sync function")
def step_when_call_traced_sync(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("traced_sync")()
    scenario_context.store("result", result)


@when("I call the traced async function")
async def step_when_call_traced_async(context):
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.get("traced_async")()
    scenario_context.store("result", result)


@when("I call the traced sync function with user_id {user_id:d}")
def step_when_call_traced_sync_with_user_id(context, user_id):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("traced_sync")(user_id=user_id)
    scenario_context.store("result", result)
    scenario_context.store("expected_user_id", user_id)


@when("I call the traced sync function and it fails")
def step_when_call_traced_sync_fails(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.get("traced_sync")()
    except RuntimeError as exc:
        scenario_context.store("raised_exception", exc)
    else:
        raise AssertionError("Expected RuntimeError was not raised")


@when("I call the traced sync function and it fails with NotFoundError")
def step_when_call_traced_sync_fails_not_found(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.get("traced_sync")()
    except NotFoundError as exc:
        scenario_context.store("raised_exception", exc)
    else:
        raise AssertionError("Expected NotFoundError was not raised")


@when("I call the traced root function under the ambient parent")
def step_when_call_traced_root(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("traced_root")()
    scenario_context.store("result", result)

    parent_span = scenario_context.get("ambient_parent_span")
    cm = scenario_context.get("ambient_parent_context_cm")
    parent_span.end()
    cm.__exit__(None, None, None)
    scenario_context.store("ambient_parent_span", None)
    scenario_context.store("ambient_parent_context_cm", None)


@when("I call the public method and the private method on the traced class")
def step_when_call_traced_class_methods(context):
    scenario_context = get_current_scenario_context(context)
    service = scenario_context.get("traced_service")
    scenario_context.store("public_result", service.public_method())
    scenario_context.store("private_result", service._private_method())


@when("I call the measured sync function")
def step_when_call_measured_sync(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("measured_sync")()
    scenario_context.store("result", result)


@when("I call the counted sync function")
def step_when_call_counted_sync(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("counted_sync")()
    scenario_context.store("result", result)


@when("I capture an exception on the current span")
def step_when_capture_exception(context):
    scenario_context = get_current_scenario_context(context)
    error_logger = logging.getLogger("archipy.helpers.utils.error_utils")
    previous_level = error_logger.level
    error_logger.setLevel(logging.CRITICAL)
    try:
        ErrorUtils.capture_exception(RuntimeError("captured for otel"))
    finally:
        error_logger.setLevel(previous_level)
    span = scenario_context.get("manual_span")
    cm = scenario_context.get("manual_span_cm")
    span.end()
    cm.__exit__(None, None, None)
    scenario_context.store("manual_span", None)
    scenario_context.store("manual_span_cm", None)


@then('a span named "{span_name}" should be recorded')
def step_then_span_named(context, span_name):
    _span_by_name(context, span_name)


@then('no span named "{span_name}" should be recorded')
def step_then_no_span_named(context, span_name):
    names = [span.name for span in _finished_spans(context)]
    assert span_name not in names, f"Unexpected span '{span_name}' recorded. Found: {names}"


@then('the recorded span should have attribute "{attr_name}" equal to {attr_value:d}')
def step_then_span_attribute(context, attr_name, attr_value):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.attributes is not None, "Span has no attributes"
    assert span.attributes.get(attr_name) == attr_value, (
        f"Expected {attr_name}={attr_value}, got {span.attributes.get(attr_name)}"
    )


@then("the recorded span status should be ERROR")
def step_then_span_status_error(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.status.status_code == StatusCode.ERROR, f"Expected ERROR status, got {span.status.status_code}"


@then("the recorded span status should be OK")
def step_then_span_status_ok(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.status.status_code == StatusCode.OK, f"Expected OK status, got {span.status.status_code}"


@then("the recorded span should include an exception event")
def step_then_span_has_exception_event(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert _span_has_exception_event(span), f"Span '{span.name}' has no exception event"


@then("the root span trace id should differ from the ambient parent trace id")
def step_then_root_trace_differs(context):
    scenario_context = get_current_scenario_context(context)
    root_span = _span_by_name(context, scenario_context.get("expected_span_name"))
    ambient_trace_id = scenario_context.get("ambient_parent_trace_id")
    root_trace_id = root_span.context.trace_id
    assert root_trace_id != ambient_trace_id, (
        f"Expected different trace ids, both were {ambient_trace_id:032x}"
    )


@then('a histogram metric named "{instrument_name}" should have datapoints')
def step_then_histogram_datapoints(context, instrument_name):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No histogram datapoints for '{instrument_name}'"


@then('a counter metric named "{instrument_name}" should have datapoints')
def step_then_counter_datapoints(context, instrument_name):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No counter datapoints for '{instrument_name}'"
    assert any(getattr(point, "value", 0) >= 1 for point in points), (
        f"Counter '{instrument_name}' datapoints have no positive values"
    )
