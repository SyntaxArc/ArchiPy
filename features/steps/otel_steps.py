"""Behave steps for OpenTelemetry tracing and metrics decorators."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from collections.abc import Callable
from unittest.mock import patch

import httpx2
from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context
from features.test_helpers_otel import CollectorTelemetry, reset_otel_for_testing
from opentelemetry import trace
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OtelLogsExporter, OtelMetricsExporter
from archipy.helpers.decorators import (
    count_calls,
    measure_duration,
    trace_class,
    trace_root,
    trace_span,
)
from archipy.helpers.errors import capture_exception
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import ConfigurationError, NotFoundError


def _reset_otel_config_defaults() -> None:
    """Restore mutable OTEL fields so prior scenarios cannot leak exporter mode."""
    config = BaseConfig.global_config()
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.OTLP
    config.OTEL.LOGS_EXPORTER = OtelLogsExporter.CONSOLE
    config.OTEL.SYSTEM_METRICS_ENABLED = True
    config.OTEL.METRICS_PULL_HOST = "127.0.0.1"
    config.OTEL.METRICS_PULL_PORT = 8200
    config.OTEL.METRICS_PUSHGATEWAY_URL = None
    config.OTEL.METRICS_PUSHGATEWAY_JOB = None
    config.OTEL.METRICS_PUSHGATEWAY_INTERVAL_SECONDS = 60
    config.OTEL.METRICS_PUSHGATEWAY_TIMEOUT_SECONDS = 10.0
    config.OTEL.METRICS_PUSHGATEWAY_GROUPING_KEY = {}
    config.OTEL.METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.LOGS_LEVEL = "INFO"
    config.OTEL.FASTAPI_LOGS_ENABLED = False


# OTEL fields scenarios may change; they are restored after every scenario.
_OTEL_FIELDS_TO_RESTORE = (
    "IS_ENABLED",
    "TRACES_ENABLED",
    "METRICS_ENABLED",
    "LOGS_ENABLED",
    "LOGS_EXPORTER",
    "LOGS_LEVEL",
    "SERVICE_NAME",
    "ENVIRONMENT",
    "PROTOCOL",
    "OTLP_ENDPOINT",
    "OTLP_HEADERS",
    "METRIC_EXPORT_INTERVAL_MS",
    "TRACES_SAMPLE_RATIO",
    "SYSTEM_METRICS_ENABLED",
    "FASTAPI_LOGS_ENABLED",
    "METRICS_EXPORTER",
    "METRICS_PULL_HOST",
    "METRICS_PULL_PORT",
    "METRICS_PUSHGATEWAY_URL",
    "METRICS_PUSHGATEWAY_JOB",
    "METRICS_PUSHGATEWAY_INTERVAL_SECONDS",
    "METRICS_PUSHGATEWAY_TIMEOUT_SECONDS",
    "METRICS_PUSHGATEWAY_GROUPING_KEY",
    "METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN",
    "INSTRUMENTATION_SKIP_DEP_CHECK",
)


def _snapshot_otel_config(scenario_context) -> None:
    """Remember the OTEL config once per scenario so teardown can put it back."""
    if scenario_context.get("otel_config_snapshot") is not None:
        return
    otel = BaseConfig.global_config().OTEL
    scenario_context.store("otel_config_snapshot", {name: getattr(otel, name) for name in _OTEL_FIELDS_TO_RESTORE})


def _restore_otel_config(scenario_context) -> None:
    snapshot = scenario_context.get("otel_config_snapshot")
    if snapshot is None:
        return
    otel = BaseConfig.global_config().OTEL
    for name, value in snapshot.items():
        setattr(otel, name, value)
    scenario_context.store("otel_config_snapshot", None)


def _setup_otel_testing(context: Context) -> None:
    """Enable OTel and install in-memory exporters for the current scenario."""
    scenario_context = get_current_scenario_context(context)
    _snapshot_otel_config(scenario_context)
    reset_otel_for_testing()

    config = BaseConfig.global_config()
    _reset_otel_config_defaults()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False

    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    OtelUtils.configure_for_testing(span_exporter=span_exporter, metric_reader=metric_reader)

    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("metric_reader", metric_reader)
    scenario_context.store("collector_telemetry", None)
    scenario_context.store("otel_enabled_for_test", True)


def _setup_collector_otel(
    context: Context,
    *,
    traces: bool = True,
    metrics: bool = True,
    logs: bool = False,
    sample_ratio: float = 1.0,
    service_name: str | None = None,
    environment: str | None = None,
    protocol: str = "grpc",
    before_init: Callable[[], None] | None = None,
    otlp_endpoint: str | None = None,
) -> CollectorTelemetry:
    """Initialize the real OTel providers so they export over OTLP/gRPC to the collector test container.

    ``before_init`` runs after the reset and before ArchiPy initializes, to play another library that registers a
    provider first. ``otlp_endpoint`` sends the telemetry somewhere else than the collector (Elastic APM Server).

    Every scenario gets its own ``service.name`` so the readers only see this scenario's telemetry.
    """
    scenario_context = get_current_scenario_context(context)
    _snapshot_otel_config(scenario_context)
    collector = scenario_context.get("test_containers").get_container("otel-collector")
    reset_otel_for_testing()

    config = BaseConfig.global_config()
    _reset_otel_config_defaults()
    otel = config.OTEL
    otel.IS_ENABLED = True
    otel.TRACES_ENABLED = traces
    otel.METRICS_ENABLED = metrics
    otel.LOGS_ENABLED = logs
    otel.LOGS_EXPORTER = OtelLogsExporter.OTLP if logs else OtelLogsExporter.CONSOLE
    otel.METRICS_EXPORTER = OtelMetricsExporter.OTLP
    otel.PROTOCOL = protocol
    otel.OTLP_ENDPOINT = otlp_endpoint or (
        collector.http_endpoint if protocol == "http/protobuf" else collector.grpc_endpoint
    )
    # Metrics leave the process only when a scenario flushes, so every read sees a complete snapshot.
    otel.METRIC_EXPORT_INTERVAL_MS = 60_000
    otel.SYSTEM_METRICS_ENABLED = False
    otel.TRACES_SAMPLE_RATIO = sample_ratio
    otel.SERVICE_NAME = service_name or f"archipy-bdd-{uuid.uuid4().hex[:8]}"
    if environment is not None:
        otel.ENVIRONMENT = environment

    if before_init is not None:
        before_init()
    OtelUtils.init_otel_if_needed(config)
    assert OtelUtils._initialized, "OpenTelemetry did not initialize against the collector"

    telemetry = CollectorTelemetry(collector, otel.SERVICE_NAME)
    scenario_context.store("collector_telemetry", telemetry)
    scenario_context.store("span_exporter", None)
    scenario_context.store("metric_reader", None)
    scenario_context.store("otel_enabled_for_test", True)
    return telemetry


def _telemetry(context: Context) -> CollectorTelemetry | None:
    """Return the collector reader of the current scenario, or None when it uses in-memory exporters."""
    return get_current_scenario_context(context).get("collector_telemetry")


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

    # Always attempt server cleanup when scenario stored any (even if OTel flag off).
    _cleanup_otel_integration_resources(scenario_context)

    if not scenario_context.get("otel_enabled_for_test", False):
        return

    _restore_captured_log_streams(scenario_context)
    _close_open_test_spans(scenario_context)
    blocker = scenario_context.get("metrics_pull_blocker")
    if blocker is not None:
        try:
            blocker.close()
        except OSError:
            pass
        scenario_context.store("metrics_pull_blocker", None)
    reset_otel_for_testing()
    try:
        config = BaseConfig.global_config()
        config.OTEL.IS_ENABLED = False
        config.OTEL.TRACES_ENABLED = False
        config.OTEL.METRICS_ENABLED = False
        _reset_otel_config_defaults()
        _restore_otel_config(scenario_context)
    except AssertionError:
        pass
    scenario_context.store("collector_telemetry", None)
    scenario_context.store("otel_enabled_for_test", False)


def _restore_captured_log_streams(scenario_context) -> None:
    """Restore ``sys.stdout`` / ``sys.stderr`` after console-log exporter scenarios."""
    import sys

    test_logger = scenario_context.get("console_test_logger")
    if test_logger is not None:
        test_logger.handlers.clear()
        test_logger.propagate = True
        scenario_context.store("console_test_logger", None)

    original_stdout = scenario_context.get("original_stdout")
    original_stderr = scenario_context.get("original_stderr")
    if original_stdout is not None:
        sys.stdout = original_stdout
        scenario_context.store("original_stdout", None)
    if original_stderr is not None:
        sys.stderr = original_stderr
        scenario_context.store("original_stderr", None)


def _finished_spans(context: Context) -> list:
    telemetry = _telemetry(context)
    if telemetry is not None:
        telemetry.flush()
        return telemetry.spans()
    scenario_context = get_current_scenario_context(context)
    exporter: InMemorySpanExporter = scenario_context.get("span_exporter")
    return list(exporter.get_finished_spans())


def _span_by_name(context: Context, name: str):
    telemetry = _telemetry(context)
    if telemetry is not None:
        telemetry.flush()
        spans = telemetry.wait_for(lambda: [span for span in telemetry.spans() if span.name == name])
        assert spans, f"No finished span named '{name}'. Found: {[s.name for s in telemetry.spans()]}"
        return spans[-1]
    spans = [span for span in _finished_spans(context) if span.name == name]
    assert spans, f"No finished span named '{name}'. Found: {[s.name for s in _finished_spans(context)]}"
    return spans[-1]


def _metric_datapoints(context: Context, instrument_name: str) -> list:
    telemetry = _telemetry(context)
    if telemetry is not None:
        telemetry.flush()
        metric = telemetry.wait_for(lambda: telemetry.metrics().get(instrument_name))
        return list(metric.data.data_points) if metric else []
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


@given("OpenTelemetry is configured with the collector")
def step_given_otel_collector(context):
    _setup_collector_otel(context)


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


@given('an async function decorated with trace_span named "{span_name}"')
def step_given_async_trace_span(context, span_name):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name=span_name)
    async def traced_async() -> str:
        return "ok"

    scenario_context.store("traced_async", traced_async)
    scenario_context.store("expected_span_name", span_name)


@given('a sync function decorated with trace_span that captures arg "{arg_name}"')
def step_given_trace_span_capture_args(context, arg_name):
    scenario_context = get_current_scenario_context(context)

    if arg_name == "password":

        @trace_span(name="capture_args_span", capture_args=[arg_name])
        def traced_sync(password: str) -> str:
            return password
    else:

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
        capture_exception(RuntimeError("captured for otel"))
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


@then("the recorded span status should be UNSET")
def step_then_span_status_unset(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.status.status_code == StatusCode.UNSET, f"Expected UNSET status, got {span.status.status_code}"


@then("the recorded span should include an exception event")
def step_then_span_has_exception_event(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert _span_has_exception_event(span), f"Span '{span.name}' has no exception event"


@then("the recorded span should have exactly {count:d} exception event")
@then("the recorded span should have exactly {count:d} exception events")
def step_then_span_exception_event_count(context, count):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    events = [event for event in span.events if event.name == "exception"]
    assert len(events) == count, f"Expected {count} exception event(s), got {len(events)}"


@then("the root span trace id should differ from the ambient parent trace id")
def step_then_root_trace_differs(context):
    scenario_context = get_current_scenario_context(context)
    root_span = _span_by_name(context, scenario_context.get("expected_span_name"))
    ambient_trace_id = scenario_context.get("ambient_parent_trace_id")
    root_trace_id = root_span.context.trace_id
    assert root_trace_id != ambient_trace_id, f"Expected different trace ids, both were {ambient_trace_id:032x}"


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


@when("I reset and reconfigure OpenTelemetry for testing")
def step_when_reset_reconfigure_otel(context):
    _setup_otel_testing(context)


@when("I call the measured sync function again")
def step_when_call_measured_sync_again(context):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("measured_sync")()
    scenario_context.store("result", result)


@when('I call the traced sync function with password "{password}"')
def step_when_call_traced_sync_with_password(context, password):
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.get("traced_sync")(password=password)
    scenario_context.store("result", result)


@then('the recorded span attribute "{attr_name}" should end with "{suffix}"')
def step_then_span_attribute_suffix(context, attr_name, suffix):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    value = str((span.attributes or {}).get(attr_name, ""))
    assert value.endswith(suffix), f"Expected {attr_name} to end with {suffix!r}, got {value!r}"


@then('the recorded span should have attribute "{attr_name}" equal to "{attr_value}"')
def step_then_span_attribute_string(context, attr_name, attr_value):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.attributes is not None, "Span has no attributes"
    assert span.attributes.get(attr_name) == attr_value, (
        f"Expected {attr_name}={attr_value!r}, got {span.attributes.get(attr_name)!r}"
    )


_OTEL_DECORATORS = {
    "measure_duration": lambda: measure_duration(name="test.async.duration"),
    "count_calls": lambda: count_calls(name="test.async.calls"),
    "trace_span": lambda: trace_span(name="async_span"),
    "trace_root": lambda: trace_root(name="async_root"),
}


@when("I apply {decorator_name} to an async function and call it")
def step_when_apply_to_async_and_call(context, decorator_name):
    scenario_context = get_current_scenario_context(context)

    @_OTEL_DECORATORS[decorator_name]()
    async def work() -> str:
        return "async-result"

    scenario_context.store("async_result", asyncio.run(work()))


@then("the async function should return its result")
def step_then_async_function_result(context):
    assert get_current_scenario_context(context).get("async_result") == "async-result"


@when('I resolve OTLP endpoints for protocol "{protocol}" with base "{base}"')
def step_when_resolve_endpoints(context, protocol, base):
    scenario_context = get_current_scenario_context(context)
    from archipy.configs.config_template import OpentelemetryConfig

    otel = OpentelemetryConfig(PROTOCOL=protocol, OTLP_ENDPOINT=base)
    scenario_context.store("resolved_traces", OtelUtils._resolve_otlp_endpoint(otel, "traces", None))
    scenario_context.store("resolved_metrics", OtelUtils.resolve_metrics_endpoint(otel))
    scenario_context.store("resolved_logs", OtelUtils._resolve_otlp_endpoint(otel, "logs", None))


@when(
    'I resolve OTLP metrics endpoint for protocol "{protocol}" with base "{base}" overridden to "{override}"',
)
def step_when_resolve_endpoints_with_override(context, protocol, base, override):
    scenario_context = get_current_scenario_context(context)
    from archipy.configs.config_template import OpentelemetryConfig

    otel = OpentelemetryConfig(PROTOCOL=protocol, OTLP_ENDPOINT=base, METRICS_ENDPOINT=override)
    scenario_context.store("resolved_traces", OtelUtils._resolve_otlp_endpoint(otel, "traces", otel.TRACES_ENDPOINT))
    scenario_context.store("resolved_metrics", OtelUtils.resolve_metrics_endpoint(otel))
    scenario_context.store("resolved_logs", OtelUtils._resolve_otlp_endpoint(otel, "logs", otel.LOGS_ENDPOINT))


@then('the traces endpoint should be "{endpoint}"')
def step_then_traces_endpoint(context, endpoint):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("resolved_traces") == endpoint


@then('the metrics endpoint should be "{endpoint}"')
def step_then_metrics_endpoint(context, endpoint):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("resolved_metrics") == endpoint


@then('the logs endpoint should be "{endpoint}"')
def step_then_logs_endpoint(context, endpoint):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("resolved_logs") == endpoint


@given('OpenTelemetry providers are built with service name "{service_name}" and environment "{environment}"')
def step_given_providers_with_resource(context, service_name, environment):
    scenario_context = get_current_scenario_context(context)
    _setup_collector_otel(context, metrics=False, service_name=service_name, environment=environment)
    scenario_context.store("expected_service_name", service_name)
    scenario_context.store("expected_environment", environment)


@then('the tracer provider resource should include "{attr_name}" equal to "{attr_value}"')
def step_then_resource_attr(context, attr_name, attr_value):
    with OtelUtils.get_tracer(__name__).start_as_current_span("resource_probe"):
        pass
    span = _span_by_name(context, "resource_probe")
    value = span.resource.attributes.get(attr_name)
    assert value == attr_value, f"Expected {attr_name}={attr_value!r}, got {value!r}"


@given("OpenTelemetry is configured for testing with sample ratio {ratio:f}")
def step_given_otel_with_sample_ratio(context, ratio):
    _setup_collector_otel(context, metrics=False, sample_ratio=ratio)


@when("I run a traced function inside a worker thread under an ambient parent")
def step_when_traced_in_worker_thread(context):
    from concurrent.futures import ThreadPoolExecutor

    from opentelemetry.instrumentation.threading import ThreadingInstrumentor

    scenario_context = get_current_scenario_context(context)
    if "threading" not in OtelUtils._instrumented_libraries:
        ThreadingInstrumentor().instrument(tracer_provider=OtelUtils.tracer_provider())
        OtelUtils._instrumented_libraries.add("threading")

    tracer = OtelUtils.get_tracer(__name__)
    parent_span = tracer.start_span("ambient_parent")
    parent_cm = trace.use_span(parent_span, end_on_exit=False)
    parent_cm.__enter__()
    ambient_trace_id = parent_span.get_span_context().trace_id

    @trace_span(name="worker_span")
    def worker() -> str:
        return "done"

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        result = future.result(timeout=5)

    parent_span.end()
    parent_cm.__exit__(None, None, None)
    scenario_context.store("result", result)
    scenario_context.store("ambient_parent_trace_id", ambient_trace_id)
    scenario_context.store("expected_span_name", "worker_span")


@then("the worker span should share the ambient parent trace id")
def step_then_worker_shares_trace(context):
    scenario_context = get_current_scenario_context(context)
    worker_span = _span_by_name(context, "worker_span")
    ambient_trace_id = scenario_context.get("ambient_parent_trace_id")
    assert worker_span.context.trace_id == ambient_trace_id, (
        f"Expected shared trace id {ambient_trace_id:032x}, got {worker_span.context.trace_id:032x}"
    )


# ---------------------------------------------------------------------------
# FastAPI / gRPC / Temporal integration + distributed tracing
# ---------------------------------------------------------------------------


def _ensure_httpx_instrumented() -> None:
    """Instrument httpx once for outbound HTTP context propagation."""
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    instrumentor = HTTPXClientInstrumentor()
    if not instrumentor.is_instrumented_by_opentelemetry:
        instrumentor.instrument(tracer_provider=OtelUtils.tracer_provider())


def _uninstrument_httpx() -> None:
    from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor, HTTPXClientInstrumentor

    for instrumentor in (HTTPXClientInstrumentor(), HTTPX2ClientInstrumentor()):
        if instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.uninstrument()


def _import_test_proto():
    import sys
    from pathlib import Path

    proto_dir = Path(__file__).resolve().parents[1] / "proto"
    if str(proto_dir) not in sys.path:
        sys.path.insert(0, str(proto_dir))
    import test_service_pb2
    import test_service_pb2_grpc

    return test_service_pb2, test_service_pb2_grpc


def _free_port() -> int:
    import socket

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _start_uvicorn(app, port: int):
    import threading
    import time

    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    assert server.started, f"uvicorn failed to start on port {port}"
    return server, thread


def _stop_uvicorn(server) -> None:
    if server is not None:
        server.should_exit = True


def _start_grpc_test_server(config, servicer):
    from archipy.helpers.utils.app_utils import AppUtils

    _pb2, pb2_grpc = _import_test_proto()
    server = AppUtils.create_grpc_app(config)
    pb2_grpc.add_TestServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    return server, port


def _grpc_stub(port: int):
    import grpc

    _pb2, pb2_grpc = _import_test_proto()
    config = BaseConfig.global_config()
    channel = grpc.insecure_channel(f"localhost:{port}")
    if config.OTEL.IS_ENABLED and config.OTEL.TRACES_ENABLED and not OtelUtils.import_failed():
        from opentelemetry.instrumentation.grpc import intercept_channel as otel_intercept_channel

        channel = otel_intercept_channel(
            channel,
            *OtelUtils.grpc_client_interceptors(),
        )
    return pb2_grpc.TestServiceStub(channel), channel


def _store_server_cleanup(scenario_context, **servers) -> None:
    cleanup = scenario_context.get("otel_server_cleanup") or []
    cleanup.append(servers)
    scenario_context.store("otel_server_cleanup", cleanup)


def _cleanup_otel_servers(scenario_context) -> None:
    for entry in scenario_context.get("otel_server_cleanup") or []:
        if entry.get("uvicorn") is not None:
            _stop_uvicorn(entry["uvicorn"])
        if entry.get("grpc") is not None:
            try:
                entry["grpc"].stop(None)
            except Exception:
                pass
        if entry.get("channel") is not None:
            try:
                entry["channel"].close()
            except Exception:
                pass
    scenario_context.store("otel_server_cleanup", [])
    _uninstrument_httpx()


def _cleanup_otel_integration_resources(scenario_context) -> None:
    """Tear down uvicorn/gRPC servers and httpx instrumentation from integration scenarios."""
    _cleanup_otel_servers(scenario_context)


@when('I create an instrumented FastAPI app and GET "{path}"')
def step_when_fastapi_get(context, path):
    from fastapi.testclient import TestClient

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    app = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

    @app.get(path)
    def otel_ping():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 200, response.text
    scenario_context.store("expected_span_name", f"GET {path}")
    scenario_context.store("fastapi_response", response.json())


@then("an HTTP server duration metric should have datapoints")
def step_then_http_server_duration(context):
    points = _metric_datapoints(context, "http.server.request.duration")
    assert points, "No http.server.request.duration datapoints"


@when("I call an instrumented gRPC TestMethod")
def step_when_call_instrumented_grpc(context):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    pb2, pb2_grpc = _import_test_proto()

    class Servicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            return pb2.TestResponse(result="ok")

    server, port = _start_grpc_test_server(config, Servicer())
    stub, channel = _grpc_stub(port)
    try:
        result = stub.TestMethod(pb2.TestRequest(data="hi"))
        assert result.result == "ok"
    finally:
        channel.close()
        server.stop(None)
    scenario_context.store("expected_span_name", "/test.TestService/TestMethod")


@when("I call an instrumented async gRPC TestMethod")
async def step_when_call_instrumented_async_grpc(context):
    import grpc

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    pb2, pb2_grpc = _import_test_proto()

    class AsyncServicer(pb2_grpc.TestServiceServicer):
        async def TestMethod(self, request, context_):
            return pb2.TestResponse(result="ok")

    server = AppUtils.create_async_grpc_app(config)
    pb2_grpc.add_TestServiceServicer_to_server(AsyncServicer(), server)
    port = server.add_insecure_port("localhost:0")
    await server.start()
    channel_kwargs: dict = {}
    if config.OTEL.IS_ENABLED and config.OTEL.TRACES_ENABLED and not OtelUtils.import_failed():
        channel_kwargs["interceptors"] = OtelUtils.async_grpc_client_interceptors()
    channel = grpc.aio.insecure_channel(f"localhost:{port}", **channel_kwargs)
    try:
        stub = pb2_grpc.TestServiceStub(channel)
        result = await stub.TestMethod(pb2.TestRequest(data="hi"))
        assert result.result == "ok"
    finally:
        await channel.close()
        await server.stop(None)
    scenario_context.store("expected_span_name", "/test.TestService/TestMethod")


@when("I setup the gRPC OTel interceptor on a list with a sentinel interceptor")
def step_when_setup_grpc_otel_with_sentinel(context):
    from archipy.helpers.utils.app_utils import GrpcAPIUtils

    scenario_context = get_current_scenario_context(context)
    sentinel = object()
    interceptors = [sentinel]
    GrpcAPIUtils.setup_otel_interceptor(BaseConfig.global_config(), interceptors)
    scenario_context.store("grpc_interceptors", interceptors)
    scenario_context.store("grpc_sentinel", sentinel)


@when("I setup the async gRPC OTel interceptor on a list with a sentinel interceptor")
def step_when_setup_async_grpc_otel_with_sentinel(context):
    from archipy.helpers.utils.app_utils import AsyncGrpcAPIUtils

    scenario_context = get_current_scenario_context(context)
    sentinel = object()
    interceptors = [sentinel]
    AsyncGrpcAPIUtils.setup_otel_interceptor(BaseConfig.global_config(), interceptors)
    scenario_context.store("grpc_interceptors", interceptors)
    scenario_context.store("grpc_sentinel", sentinel)


@then("the OTel interceptor should be first and the sentinel should remain")
def step_then_grpc_otel_prepended(context):
    scenario_context = get_current_scenario_context(context)
    interceptors = scenario_context.get("grpc_interceptors")
    sentinel = scenario_context.get("grpc_sentinel")
    assert len(interceptors) >= 2, f"Expected at least 2 interceptors, got {len(interceptors)}"
    assert interceptors[-1] is sentinel
    assert interceptors[0] is not sentinel
    assert any("Otel" in type(item).__name__ or "OpenTelemetry" in type(item).__name__ for item in interceptors[:-1])


@then("the owned tracer and meter providers should be Temporal replay-safe providers")
def step_then_providers_replay_safe(context):
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeMeterProvider, ReplaySafeTracerProvider
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return

    for provider, expected in (
        (OtelUtils.tracer_provider(), ReplaySafeTracerProvider),
        (OtelUtils.meter_provider(), ReplaySafeMeterProvider),
    ):
        assert isinstance(provider, expected), f"{type(provider).__name__} is not a {expected.__name__}"


@when("a console logger provider is built with an in-memory log exporter")
def step_when_console_logger_provider_built(context):
    from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter

    from archipy.configs.config_template import OpentelemetryConfig
    from archipy.helpers.utils._otel.providers import build_logger_provider

    otel = OpentelemetryConfig(LOGS_EXPORTER=OtelLogsExporter.CONSOLE)
    exporter = InMemoryLogRecordExporter()
    provider = build_logger_provider(otel, OtelUtils._create_resource(otel), console_exporter_factory=lambda: exporter)
    context.add_cleanup(provider.shutdown)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("built_logger_provider", provider)
    scenario_context.store("in_memory_log_exporter", exporter)


@then("the logger provider should be a Temporal replay-safe provider")
def step_then_logger_provider_replay_safe(context):
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeLoggerProvider
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return

    provider = get_current_scenario_context(context).get("built_logger_provider")
    assert isinstance(provider, ReplaySafeLoggerProvider), f"{type(provider).__name__} is not a ReplaySafeLoggerProvider"


@then("a log record emitted outside a workflow should reach the exporter")
def step_then_log_record_reaches_exporter(context):
    from opentelemetry._logs import LogRecord

    scenario_context = get_current_scenario_context(context)
    provider = scenario_context.get("built_logger_provider")
    provider.get_logger("archipy-replay-safe-bdd").emit(LogRecord(body="outside a workflow"))
    bodies = [item.log_record.body for item in scenario_context.get("in_memory_log_exporter").get_finished_logs()]
    assert bodies == ["outside a workflow"], bodies


@given("another library registered a replay-safe tracer provider before ArchiPy initialized OpenTelemetry")
def step_given_other_library_replay_safe(context):
    try:
        from temporalio.contrib.opentelemetry import create_tracer_provider
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return
    reset_otel_for_testing()
    provider = create_tracer_provider()
    trace.set_tracer_provider(provider)
    get_current_scenario_context(context).store("other_library_provider", provider)


@when("ArchiPy initializes OpenTelemetry")
def step_when_archipy_initializes(context):
    if context.scenario.status == "skipped":
        return
    OtelUtils.init_otel_if_needed(BaseConfig.global_config())


@then("ArchiPy should use that tracer provider")
def step_then_archipy_uses_provider(context):
    if context.scenario.status == "skipped":
        return
    assert OtelUtils.tracer_provider() is get_current_scenario_context(context).get("other_library_provider")


@when("I reset OpenTelemetry for testing and initialize it again")
def step_when_reset_and_init(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("previous_global_tracer_provider", trace.get_tracer_provider())
    reset_otel_for_testing()
    OtelUtils.init_otel_if_needed(BaseConfig.global_config())


@given("OpenTelemetry was initialized with traces disabled")
def step_given_otel_traces_disabled(context):
    reset_otel_for_testing()
    BaseConfig.global_config().OTEL.TRACES_ENABLED = False
    OtelUtils.init_otel_if_needed(BaseConfig.global_config())
    assert isinstance(trace.get_tracer_provider(), trace.ProxyTracerProvider), "a tracer provider was published"
    assert OtelUtils.tracer_provider() is None


@when("traces are enabled and OpenTelemetry initializes again")
def step_when_traces_enabled_later(context):
    OtelUtils.reset_for_testing()
    BaseConfig.global_config().OTEL.TRACES_ENABLED = True
    OtelUtils.init_otel_if_needed(BaseConfig.global_config())


@then("the global tracer provider should be the one ArchiPy owns")
def step_then_global_is_owned(context):
    owned = OtelUtils.tracer_provider()
    assert owned is not None, "ArchiPy did not build a tracer provider"
    assert trace.get_tracer_provider() is owned, "the owned tracer provider was not published globally"


@given("temporalio cannot be imported")
def step_given_temporalio_missing(context):
    import sys

    blocked = patch.dict(
        sys.modules,
        {"temporalio": None, "temporalio.contrib": None, "temporalio.contrib.opentelemetry": None},
    )
    blocked.start()
    context.add_cleanup(blocked.stop)


@then("the owned tracer and meter providers should be plain SDK providers")
def step_then_plain_sdk_providers(context):
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider

    assert type(OtelUtils.tracer_provider()) is TracerProvider, type(OtelUtils.tracer_provider())
    assert type(OtelUtils.meter_provider()) is MeterProvider, type(OtelUtils.meter_provider())


@when("the Temporal tracing plugin configures a sandboxed worker")
def step_when_plugin_configures_sandbox(context):
    try:
        from temporalio.client import Client
        from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

        from archipy.adapters.temporal.tracing import MessagingOpenTelemetryPlugin
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return
    # A lazy client never dials the server; the plugin only reads its interceptors while configuring the worker.
    client = asyncio.run(Client.connect("localhost:7233", lazy=True))
    configured = MessagingOpenTelemetryPlugin().configure_worker(
        {"client": client, "workflow_runner": SandboxedWorkflowRunner()},
    )
    get_current_scenario_context(context).store("configured_workflow_runner", configured["workflow_runner"])


@then("the workflow sandbox should pass opentelemetry through")
def step_then_sandbox_passthrough(context):
    if context.scenario.status == "skipped":
        return
    runner = get_current_scenario_context(context).get("configured_workflow_runner")
    assert "opentelemetry" in runner.restrictions.passthrough_modules, runner.restrictions.passthrough_modules


@when("the stock OpenTelemetry plugin and the Temporal tracing plugin configure the same client")
def step_when_both_plugins_configure_client(context):
    try:
        from temporalio.contrib.opentelemetry import OpenTelemetryPlugin

        from archipy.adapters.temporal.tracing import MessagingOpenTelemetryPlugin
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return
    stock = OpenTelemetryPlugin()
    ours = MessagingOpenTelemetryPlugin()
    config = ours.configure_client(stock.configure_client({"interceptors": []}))
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("plugin_names", (stock.name(), ours.name()))
    scenario_context.store("client_interceptors", config["interceptors"])


@then("the plugin names should differ and the client should carry both interceptors")
def step_then_both_plugins_coexist(context):
    if context.scenario.status == "skipped":
        return
    from archipy.adapters.temporal.tracing import MessagingOpenTelemetryInterceptor

    scenario_context = get_current_scenario_context(context)
    stock_name, our_name = scenario_context.get("plugin_names")
    assert stock_name != our_name, stock_name
    interceptors = scenario_context.get("client_interceptors")
    assert len(interceptors) == 2, interceptors
    assert sum(isinstance(item, MessagingOpenTelemetryInterceptor) for item in interceptors) == 1, interceptors


@when("I append the Temporal tracing plugin to connect kwargs that already have a sentinel")
def step_when_temporal_append_with_sentinel(context):
    try:
        from archipy.adapters.temporal.adapters import TemporalAdapter
    except ImportError:
        context.scenario.skip("temporalio is not installed")
        return

    scenario_context = get_current_scenario_context(context)

    class _SentinelInterceptor:
        pass

    sentinel = _SentinelInterceptor()
    connect_kwargs = {"plugins": [sentinel]}
    TemporalAdapter._append_tracing_plugin(connect_kwargs)
    scenario_context.store("temporal_connect_kwargs", connect_kwargs)
    scenario_context.store("temporal_sentinel", sentinel)


@then("the Temporal connect kwargs should keep the sentinel and include the tracing plugin")
def step_then_temporal_append_preserved(context):
    if context.scenario.status == "skipped":
        return
    from archipy.adapters.temporal.tracing import MessagingOpenTelemetryPlugin

    scenario_context = get_current_scenario_context(context)
    kwargs = scenario_context.get("temporal_connect_kwargs")
    sentinel = scenario_context.get("temporal_sentinel")
    plugins = kwargs["plugins"]
    assert plugins[0] is sentinel
    assert isinstance(plugins[1], MessagingOpenTelemetryPlugin)


@then("all finished spans should share one trace id")
def step_then_single_trace_id(context):
    spans = _finished_spans(context)
    assert spans, "No finished spans"
    trace_ids = {span.context.trace_id for span in spans}
    assert len(trace_ids) == 1, f"Expected 1 trace id, got {len(trace_ids)}: {[f'{t:032x}' for t in trace_ids]}"


@then('the span named "{child_name}" should descend from span "{ancestor_name}"')
def step_then_span_descends_from(context, child_name, ancestor_name):
    """Assert ``child`` is in the parent chain of ``ancestor`` (same distributed hop)."""
    spans = _finished_spans(context)
    by_span_id = {span.context.span_id: span for span in spans}
    child = _span_by_name(context, child_name)
    ancestor = _span_by_name(context, ancestor_name)
    assert child.context.trace_id == ancestor.context.trace_id, (
        f"Expected shared trace id between {child_name!r} and {ancestor_name!r}"
    )
    current = child
    seen: set[int] = set()
    while current.parent is not None and current.parent.span_id not in seen:
        parent_id = current.parent.span_id
        seen.add(parent_id)
        if parent_id == ancestor.context.span_id:
            return
        parent = by_span_id.get(parent_id)
        if parent is None:
            break
        current = parent
    chain = []
    current = child
    while current is not None:
        chain.append(current.name)
        if current.parent is None:
            break
        current = by_span_id.get(current.parent.span_id)
    raise AssertionError(
        f"Expected {child_name!r} to descend from {ancestor_name!r}; parent chain: {chain}",
    )


@then('at least {count:d} spans named "{span_name}" should be recorded')
def step_then_at_least_n_spans(context, count, span_name):
    matches = [span for span in _finished_spans(context) if span.name == span_name]
    assert len(matches) >= count, f"Expected >= {count} spans named '{span_name}', got {len(matches)}"


@when("FastAPI upstream calls FastAPI downstream over HTTP")
def step_when_fa_calls_fa(context):
    import httpx
    from fastapi.testclient import TestClient

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    _ensure_httpx_instrumented()

    downstream = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

    @downstream.get("/downstream")
    def downstream_handler():
        return {"from": "downstream"}

    down_port = _free_port()
    uvicorn_server, _thread = _start_uvicorn(downstream, down_port)
    _store_server_cleanup(scenario_context, uvicorn=uvicorn_server)

    upstream = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

    @upstream.get("/call-fa")
    def call_fa():
        response = httpx.get(f"http://127.0.0.1:{down_port}/downstream")
        response.raise_for_status()
        return {"status": response.status_code, "body": response.json()}

    with TestClient(upstream) as client:
        response = client.get("/call-fa")
    assert response.status_code == 200, response.text
    _stop_uvicorn(uvicorn_server)


@when("FastAPI upstream calls gRPC TestMethod")
def step_when_fa_calls_grpc(context):
    from fastapi.testclient import TestClient

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    pb2, pb2_grpc = _import_test_proto()

    class Servicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            return pb2.TestResponse(result="grpc-ok")

    grpc_server, grpc_port = _start_grpc_test_server(config, Servicer())
    _store_server_cleanup(scenario_context, grpc=grpc_server)

    upstream = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

    @upstream.get("/call-grpc")
    def call_grpc():
        stub, channel = _grpc_stub(grpc_port)
        try:
            result = stub.TestMethod(pb2.TestRequest(data="hi"))
            return {"result": result.result}
        finally:
            channel.close()

    with TestClient(upstream) as client:
        response = client.get("/call-grpc")
    assert response.status_code == 200, response.text
    assert response.json()["result"] == "grpc-ok"
    grpc_server.stop(None)


@when("gRPC upstream calls gRPC downstream TestMethod")
def step_when_grpc_calls_grpc(context):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    pb2, pb2_grpc = _import_test_proto()

    class DownstreamServicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            return pb2.TestResponse(result="leaf")

    down_server, down_port = _start_grpc_test_server(config, DownstreamServicer())
    _store_server_cleanup(scenario_context, grpc=down_server)

    class UpstreamServicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            stub, channel = _grpc_stub(down_port)
            try:
                resp = stub.TestMethod(pb2.TestRequest(data=request.data))
                return pb2.TestResponse(result=f"up:{resp.result}")
            finally:
                channel.close()

    up_server, up_port = _start_grpc_test_server(config, UpstreamServicer())
    _store_server_cleanup(scenario_context, grpc=up_server)

    stub, channel = _grpc_stub(up_port)
    try:
        result = stub.TestMethod(pb2.TestRequest(data="x"))
        assert result.result == "up:leaf"
    finally:
        channel.close()
        up_server.stop(None)
        down_server.stop(None)


@when("gRPC upstream calls FastAPI downstream over HTTP")
def step_when_grpc_calls_fa(context):
    import httpx

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    _ensure_httpx_instrumented()
    pb2, pb2_grpc = _import_test_proto()

    downstream = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

    @downstream.get("/from-grpc")
    def from_grpc():
        return {"ok": True}

    fa_port = _free_port()
    uvicorn_server, _thread = _start_uvicorn(downstream, fa_port)
    _store_server_cleanup(scenario_context, uvicorn=uvicorn_server)

    class GrpcToFaServicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            response = httpx.get(f"http://127.0.0.1:{fa_port}/from-grpc")
            return pb2.TestResponse(result=str(response.status_code))

    grpc_server, grpc_port = _start_grpc_test_server(config, GrpcToFaServicer())
    _store_server_cleanup(scenario_context, grpc=grpc_server)

    stub, channel = _grpc_stub(grpc_port)
    try:
        result = stub.TestMethod(pb2.TestRequest(data="x"))
        assert result.result == "200"
    finally:
        channel.close()
        grpc_server.stop(None)
        _stop_uvicorn(uvicorn_server)


# ---------------------------------------------------------------------------
# Lifecycle / signal / failure-path scenarios
# ---------------------------------------------------------------------------


@given("OpenTelemetry metrics-only mode for testing")
def step_given_metrics_only(context):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.IS_ENABLED = True
    scenario_context.store("otel_enabled_for_test", True)


@given("a sync function decorated with trace_span that captures a broken repr arg")
def step_given_broken_repr_capture(context):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name="broken_repr_span", capture_args=["payload"])
    def traced_sync(payload: object) -> str:
        return "ok"

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", "broken_repr_span")


@when("I call the traced sync function with a broken repr object")
def step_when_call_broken_repr(context):
    scenario_context = get_current_scenario_context(context)

    class BrokenRepr:
        def __repr__(self) -> str:
            raise RuntimeError("repr boom")

    result = scenario_context.get("traced_sync")(BrokenRepr())
    scenario_context.store("result", result)


@given('a sync function decorated with trace_span and static attribute password "{password}"')
def step_given_static_password_attr(context, password):
    scenario_context = get_current_scenario_context(context)

    @trace_span(name="static_secret_span", attributes={"password": password})
    def traced_sync() -> str:
        return "ok"

    scenario_context.store("traced_sync", traced_sync)
    scenario_context.store("expected_span_name", "static_secret_span")


@given('an async function decorated with measure_duration named "{instrument_name}"')
def step_given_async_measure_duration(context, instrument_name):
    scenario_context = get_current_scenario_context(context)
    import asyncio

    @measure_duration(name=instrument_name)
    async def measured_async() -> str:
        await asyncio.sleep(60)
        return "done"

    scenario_context.store("measured_async", measured_async)
    scenario_context.store("expected_instrument_name", instrument_name)


@when("I cancel the measured async function")
async def step_when_cancel_measured_async(context):
    import asyncio

    scenario_context = get_current_scenario_context(context)
    task = asyncio.create_task(scenario_context.get("measured_async")())
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        scenario_context.store("cancelled", True)


@then('a histogram metric named "{instrument_name}" should have status "{status}"')
def step_then_histogram_status(context, instrument_name, status):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No datapoints for histogram '{instrument_name}'"
    statuses = [point.attributes.get("status") for point in points]
    assert status in statuses, f"Expected status {status!r} in {statuses!r}"


@then('a histogram metric named "{instrument_name}" should have gRPC status code "{code}"')
def step_then_histogram_grpc_status_code(context, instrument_name, code):
    points = _metric_datapoints(context, instrument_name)
    codes = [point.attributes.get("rpc.response.status_code") for point in points]
    assert code in codes, f"Expected gRPC status code {code!r} in {codes!r}"


@then(
    'the "{instrument_name}" histogram has the attributes rpc.system.name "{system}", rpc.method "{method}" '
    'and rpc.response.status_code "{code}"',
)
def step_then_rpc_attributes(context, instrument_name, system, method, code):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No datapoints for histogram '{instrument_name}'"
    attributes = dict(points[0].attributes)
    assert attributes.get("rpc.system.name") == system, attributes
    assert attributes.get("rpc.method") == method, attributes
    assert attributes.get("rpc.response.status_code") == code, attributes


@then('the "{instrument_name}" histogram has none of the attributes "{names}"')
def step_then_histogram_lacks_attributes(context, instrument_name, names):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No datapoints for histogram '{instrument_name}'"
    unwanted = {name.strip() for name in names.split(",")}
    for point in points:
        assert not unwanted & set(point.attributes), dict(point.attributes)


@then('a histogram metric named "{instrument_name}" should have error type "{error_type}"')
def step_then_histogram_error_type(context, instrument_name, error_type):
    points = _metric_datapoints(context, instrument_name)
    types = [point.attributes.get("error.type") for point in points]
    assert error_type in types, f"Expected error.type {error_type!r} in {types!r}"


@then('a histogram metric named "{instrument_name}" should not have an error type')
def step_then_histogram_no_error_type(context, instrument_name):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No datapoints for histogram '{instrument_name}'"
    assert all("error.type" not in point.attributes for point in points), [dict(p.attributes) for p in points]


@then('the "{instrument_name}" histogram should have {expected:d} datapoint for method "{method}"')
def step_then_histogram_datapoint_count_for_method(context, instrument_name, expected, method):
    points = [
        p
        for p in _metric_datapoints(context, instrument_name)
        if str(p.attributes.get("rpc.method", "")).endswith(f"/{method}")
    ]
    recorded = sum(point.count for point in points)
    assert recorded == expected, f"Expected {expected} recording(s) for method {method!r}, got {recorded}"


@when("I cancel the traced async function")
async def step_when_cancel_traced_async(context):
    import asyncio

    scenario_context = get_current_scenario_context(context)

    @trace_span(name=scenario_context.get("expected_span_name") or "cancel_span")
    async def cancellable() -> str:
        await asyncio.sleep(60)
        return "done"

    # Re-wrap if Background already stored a different async fn without sleep
    if scenario_context.get("traced_async") is not None:
        # Prefer the named cancel_span from the Given step; redefine with sleep
        span_name = scenario_context.get("expected_span_name") or "cancel_span"

        @trace_span(name=span_name)
        async def cancellable_named() -> str:
            await asyncio.sleep(60)
            return "done"

        target = cancellable_named
    else:
        target = cancellable

    task = asyncio.create_task(target())
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        scenario_context.store("cancelled", True)


@when("I force flush OpenTelemetry providers")
def step_when_force_flush(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("force_flush_ok", OtelUtils.force_flush(timeout_millis=1000))


@then("OpenTelemetry force flush should succeed")
def step_then_force_flush_ok(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("force_flush_ok") is True


@when("I shut down OpenTelemetry providers twice")
def step_when_shutdown_twice(context):
    OtelUtils.shutdown()
    OtelUtils.shutdown()
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("otel_enabled_for_test", True)


@then("OpenTelemetry tracer provider should be absent")
def step_then_no_tracer_provider(context):
    assert OtelUtils.tracer_provider() is None


@given("OpenTelemetry is configured for testing with a borrowed tracer provider")
def step_given_borrowed_tracer(context):
    scenario_context = get_current_scenario_context(context)
    # Background already configured providers; mark tracer as borrowed (not owned).
    external = OtelUtils.tracer_provider()
    assert external is not None
    OtelUtils._owns_tracer = False
    scenario_context.store("external_tracer_provider", external)
    scenario_context.store("otel_enabled_for_test", True)

    def _release_borrowed_provider() -> None:
        # Nothing else owns it, and a live global provider would be adopted by later scenarios.
        external.shutdown()
        OtelUtils._mark_provider_shutdown(external)

    context.add_cleanup(_release_borrowed_provider)


@when("I shut down OpenTelemetry providers")
def step_when_shutdown_once(context):
    OtelUtils.shutdown()
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("otel_enabled_for_test", True)


@then("the borrowed TracerProvider should still be usable")
def step_then_borrowed_still_usable(context):
    scenario_context = get_current_scenario_context(context)
    external = scenario_context.get("external_tracer_provider")
    assert external is not None
    tracer = external.get_tracer("borrowed-check")
    with tracer.start_as_current_span("borrowed_span"):
        pass
    assert OtelUtils.tracer_provider() is None
    assert OtelUtils._owns_tracer is False


@given("an external TracerProvider is installed as the global provider")
def step_given_external_tracer(context):
    # Kept for compatibility; prefer borrowed-provider scenario above.
    step_given_borrowed_tracer(context)


@when("I initialize OpenTelemetry adopting the external provider")
def step_when_init_adopting(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("adopted_provider", OtelUtils.tracer_provider())


@then("the external TracerProvider should still be usable")
def step_then_external_still_usable(context):
    step_then_borrowed_still_usable(context)


@when("OpenTelemetry initialization fails while creating the metric exporter")
def step_when_init_metric_exporter_fails(context):
    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False
    config = BaseConfig.global_config()
    _reset_otel_config_defaults()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.OTLP
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://localhost:4318"

    def _boom(_otel):
        raise RuntimeError("metric exporter boom")

    with patch.object(OtelUtils.runtime(), "_create_metric_exporter", _boom):
        OtelUtils.init_otel_if_needed(config)
    scenario_context.store("otel_enabled_for_test", True)


@then("OpenTelemetry should not be marked initialized")
def step_then_not_initialized(context):
    assert OtelUtils._initialized is False


@then("OpenTelemetry should be marked initialized")
def step_then_initialized(context):
    assert OtelUtils._initialized is True


@then("OpenTelemetry meter provider should be absent")
def step_then_no_meter_provider(context):
    assert OtelUtils.meter_provider() is None


@given("OpenTelemetry import failure is simulated")
def step_given_import_failed(context):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    OtelUtils._import_failed = True
    OtelUtils._initialized = False
    scenario_context.store("otel_enabled_for_test", True)


@then('the traced sync function result should be "{value}"')
def step_then_traced_result(context, value):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("result") == value


@given("OpenTelemetry is configured for testing with log export")
def step_given_otel_with_logs(context):
    _setup_collector_otel(context, logs=True)


@when('I emit an INFO log message "{message}"')
def step_when_emit_log(context, message):
    logging.getLogger("archipy.otel.test").info(message)


@when('I emit a WARNING log message "{message}"')
def step_when_emit_warning_log(context, message):
    logging.getLogger("archipy.otel.test").warning(message)


def _exported_logs_containing(context, message: str) -> list:
    telemetry = _telemetry(context)
    telemetry.flush()
    return telemetry.wait_for(lambda: [record for record in telemetry.logs() if message in str(record.body)])


@then('a log record containing "{message}" should be exported')
def step_then_log_exported(context, message):
    records = _exported_logs_containing(context, message)
    assert records, f"Expected {message!r} in {[str(record.body) for record in _telemetry(context).logs()]!r}"


@then('a log record containing "{message}" should carry the ambient parent trace id and span id')
def step_then_log_carries_ambient_context(context, message):
    scenario_context = get_current_scenario_context(context)
    ambient_span = scenario_context.get("ambient_parent_span")
    assert ambient_span is not None, "No ambient parent span in scenario context"
    ambient_ctx = ambient_span.get_span_context()
    matches = _exported_logs_containing(context, message)
    assert matches, f"No log record containing {message!r}"
    for log_record in matches:
        assert log_record.trace_id == ambient_ctx.trace_id, (
            f"Expected log trace_id {ambient_ctx.trace_id:032x}, got {log_record.trace_id:032x}"
        )
        assert log_record.span_id == ambient_ctx.span_id, (
            f"Expected log span_id {ambient_ctx.span_id:016x}, got {log_record.span_id:016x}"
        )


@given("OpenTelemetry is configured for console log export with captured streams")
def step_given_console_logs_captured(context):
    """Install console split exporter against StringIO streams (avoids OTel global lock)."""
    import io
    import sys

    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor
    from opentelemetry.sdk.resources import Resource

    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    scenario_context.store("original_stdout", sys.stdout)
    scenario_context.store("original_stderr", sys.stderr)
    # Exporters bind streams at construction time.
    sys.stdout = stdout_buf
    sys.stderr = stderr_buf
    scenario_context.store("captured_stdout", stdout_buf)
    scenario_context.store("captured_stderr", stderr_buf)

    exporter = OtelUtils._create_console_log_exporter()
    provider = LoggerProvider(resource=Resource.create({"service.name": "archipy-console-logs-bdd"}))
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    OtelUtils._logger_provider = provider
    OtelUtils._owns_logger = True
    OtelUtils._initialized = True

    # Prefer owned provider handler; also wire named test logger explicitly.
    OtelUtils._attach_logging_handler_unlocked(logging.INFO)
    test_logger = logging.getLogger("archipy.otel.test")
    test_logger.handlers.clear()
    test_logger.addHandler(LoggingHandler(level=logging.INFO, logger_provider=provider))
    test_logger.setLevel(logging.INFO)
    test_logger.propagate = False
    scenario_context.store("console_test_logger", test_logger)
    scenario_context.store("otel_enabled_for_test", True)


@when('I build OpentelemetryConfig with LOGS_EXPORTER "{exporter}"')
def step_when_build_bad_logs_exporter(context, exporter):
    from pydantic import ValidationError

    from archipy.configs.config_template import OpentelemetryConfig

    scenario_context = get_current_scenario_context(context)
    try:
        OpentelemetryConfig(
            IS_ENABLED=True,
            TRACES_ENABLED=False,
            METRICS_ENABLED=False,
            LOGS_ENABLED=True,
            LOGS_EXPORTER=exporter,
        )
        scenario_context.store("validation_error", None)
    except ValidationError as exc:
        scenario_context.store("validation_error", exc)


@then('the captured stdout should contain "{needle}"')
def step_then_stdout_contains(context, needle):
    scenario_context = get_current_scenario_context(context)
    OtelUtils.force_flush(timeout_millis=2000)
    body = scenario_context.get("captured_stdout").getvalue()
    assert needle in body, f"Expected {needle!r} in stdout:\n{body!r}"


@then('the captured stderr should contain "{needle}"')
def step_then_stderr_contains(context, needle):
    scenario_context = get_current_scenario_context(context)
    OtelUtils.force_flush(timeout_millis=2000)
    body = scenario_context.get("captured_stderr").getvalue()
    assert needle in body, f"Expected {needle!r} in stderr:\n{body!r}"


@then('the captured stdout should not contain "{needle}"')
def step_then_stdout_not_contains(context, needle):
    scenario_context = get_current_scenario_context(context)
    OtelUtils.force_flush(timeout_millis=2000)
    body = scenario_context.get("captured_stdout").getvalue()
    assert needle not in body, f"Did not expect {needle!r} in stdout:\n{body!r}"


@then('the captured stderr should not contain "{needle}"')
def step_then_stderr_not_contains(context, needle):
    scenario_context = get_current_scenario_context(context)
    OtelUtils.force_flush(timeout_millis=2000)
    body = scenario_context.get("captured_stderr").getvalue()
    assert needle not in body, f"Did not expect {needle!r} in stderr:\n{body!r}"


@when("I simulate a process fork after OpenTelemetry init")
def step_when_simulate_fork(context):
    import os

    assert OtelUtils._initialized is True
    # Pretend we are in a child process with a different PID.
    OtelUtils._init_pid = os.getpid() + 10_000_000


@when("I re-initialize OpenTelemetry after the simulated fork")
def step_when_reinit_after_fork(context):
    import os

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False

    # Exercise fork detection under the init lock, then install in-memory providers
    # (avoid constructing real OTLP exporters in BDD).
    with OtelUtils._lock:
        if OtelUtils._initialized and OtelUtils._init_pid is not None and OtelUtils._init_pid != os.getpid():
            OtelUtils._reset_after_fork()
    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    OtelUtils.configure_for_testing(span_exporter=span_exporter, metric_reader=metric_reader)
    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("metric_reader", metric_reader)
    scenario_context.store("otel_enabled_for_test", True)


@when("I build OpentelemetryConfig with IS_ENABLED true and all signals false")
def step_when_build_no_signals(context):
    from archipy.configs.config_template import OpentelemetryConfig

    scenario_context = get_current_scenario_context(context)
    try:
        OpentelemetryConfig(
            IS_ENABLED=True,
            TRACES_ENABLED=False,
            METRICS_ENABLED=False,
            LOGS_ENABLED=False,
        )
        scenario_context.store("config_error", None)
    except ConfigurationError as exc:
        scenario_context.store("config_error", exc)


@when('I build OpentelemetryConfig with LOGS_LEVEL "{level}"')
def step_when_build_bad_logs_level(context, level):
    from archipy.configs.config_template import OpentelemetryConfig

    scenario_context = get_current_scenario_context(context)
    try:
        OpentelemetryConfig(LOGS_LEVEL=level)
        scenario_context.store("config_error", None)
    except ConfigurationError as exc:
        scenario_context.store("config_error", exc)


@then('a ConfigurationError should be raised for operation "{operation}"')
def step_then_config_error(context, operation):
    scenario_context = get_current_scenario_context(context)
    err = scenario_context.get("config_error")
    assert isinstance(err, ConfigurationError), f"Expected ConfigurationError, got {err!r}"
    assert err.additional_data.get("operation") == operation


@when("I call the measured sync function from {n:d} threads concurrently")
def step_when_concurrent_measure(context, n):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    scenario_context = get_current_scenario_context(context)
    measured = scenario_context.get("measured_sync")

    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(measured) for _ in range(n)]
        for future in as_completed(futures):
            assert future.result() == "timed"


@then("the interceptor list should contain only the sentinel")
def step_then_only_sentinel(context):
    scenario_context = get_current_scenario_context(context)
    interceptors = scenario_context.get("grpc_interceptors")
    sentinel = scenario_context.get("grpc_sentinel")
    assert interceptors == [sentinel], f"Expected only sentinel, got {interceptors!r}"


@when("I run FastAPI lifespan startup and shutdown")
def step_when_fastapi_lifespan_cycle(context):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    from archipy.helpers.utils.app_utils import AppUtils

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    assert OtelUtils.tracer_provider() is not None

    user_ran = {"value": False}

    @asynccontextmanager
    async def user_lifespan(app):
        user_ran["value"] = True
        with OtelUtils.get_tracer("lifespan-test").start_as_current_span("lifespan-span"):
            pass
        yield

    app = AppUtils.create_fastapi_app(
        config,
        configure_exception_handlers=False,
        lifespan=user_lifespan,
    )
    with TestClient(app):
        assert user_ran["value"] is True
    # Providers must remain usable after TestClient lifespan exit.
    assert OtelUtils.tracer_provider() is not None
    scenario_context.store("otel_enabled_for_test", True)


@then("the span created during the lifespan should reach the collector without an explicit flush")
def step_then_lifespan_flush(context):
    """The batch processor only sends every few seconds, so a quick arrival proves the lifespan exit flushed."""
    telemetry: CollectorTelemetry = get_current_scenario_context(context).get("collector_telemetry")
    spans = telemetry.wait_for(
        lambda: [span for span in telemetry.spans() if span.name == "lifespan-span"],
        timeout=2.0,
    )
    assert spans, f"lifespan-span never reached the collector. Exported: {[s.name for s in telemetry.spans()]}"


def _free_tcp_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _configure_pull_metrics(context) -> None:
    """Reset Background providers and prepare real init with metrics pull scrape."""
    from archipy.configs.config_template import OtelMetricsExporter

    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False

    port = _free_tcp_port()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.PULL
    config.OTEL.METRICS_PULL_HOST = "127.0.0.1"
    config.OTEL.METRICS_PULL_PORT = port
    config.OTEL.SYSTEM_METRICS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://127.0.0.1:4318"
    config.OTEL.SERVICE_NAME = "archipy-pull-bdd"

    scenario_context.store("metrics_pull_port", port)
    scenario_context.store("otel_enabled_for_test", True)


@given("OpenTelemetry is configured for pull-only metrics on an ephemeral port")
def step_given_pull_only(context):
    _configure_pull_metrics(context)


@given("OpenTelemetry is configured for OTLP-only metrics with pull port reserved")
def step_given_otlp_only_reserved_port(context):
    from archipy.configs.config_template import OtelMetricsExporter

    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False

    port = _free_tcp_port()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.OTLP
    config.OTEL.METRICS_PULL_HOST = "127.0.0.1"
    config.OTEL.METRICS_PULL_PORT = port
    config.OTEL.SYSTEM_METRICS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://127.0.0.1:4318"
    config.OTEL.SERVICE_NAME = "archipy-otlp-bdd"

    scenario_context.store("metrics_pull_port", port)
    scenario_context.store("otel_enabled_for_test", True)


@given("OpenTelemetry is configured for production init with system metrics disabled")
def step_given_system_metrics_off(context):
    from archipy.configs.config_template import OtelMetricsExporter

    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False

    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.OTLP
    config.OTEL.SYSTEM_METRICS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://127.0.0.1:4318"
    config.OTEL.SERVICE_NAME = "archipy-sysmetrics-bdd"
    scenario_context.store("otel_enabled_for_test", True)


@when("I initialize OpenTelemetry providers from config")
def step_when_init_from_config(context):
    OtelUtils.init_otel_if_needed(BaseConfig.global_config())
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("otel_enabled_for_test", True)


@when("I initialize OpenTelemetry providers from config twice")
def step_when_init_from_config_twice(context):
    config = BaseConfig.global_config()
    OtelUtils.init_otel_if_needed(config)
    OtelUtils.init_otel_if_needed(config)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("otel_enabled_for_test", True)


@when('I call a measured sync function named "{instrument_name}"')
def step_when_call_named_measured(context, instrument_name):
    scenario_context = get_current_scenario_context(context)

    @measure_duration(name=instrument_name)
    def measured() -> str:
        return "ok"

    assert measured() == "ok"
    scenario_context.store("measured_sync", measured)


@given('a sync function decorated with measure_duration named "{instrument_name}" that raises NotFoundError')
def step_given_measure_not_found(context, instrument_name):
    scenario_context = get_current_scenario_context(context)

    @measure_duration(name=instrument_name)
    def measured() -> str:
        raise NotFoundError(resource_type="user")

    scenario_context.store("measured_sync", measured)


@given('a sync function decorated with measure_duration named "{instrument_name}" that raises RuntimeError')
def step_given_measure_runtime_error(context, instrument_name):
    scenario_context = get_current_scenario_context(context)

    @measure_duration(name=instrument_name)
    def measured() -> str:
        raise RuntimeError("measured failure")

    scenario_context.store("measured_sync", measured)


@when("I call the measured sync function and it fails with RuntimeError")
def step_when_measured_fails_runtime_error(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.get("measured_sync")()
    except RuntimeError as exc:
        scenario_context.store("measured_error", exc)
    else:
        raise AssertionError("Expected RuntimeError was not raised")


@when("I call the measured sync function and it fails with NotFoundError")
def step_when_measured_fails_not_found(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.get("measured_sync")()
    except NotFoundError as exc:
        scenario_context.store("measured_error", exc)
    else:
        scenario_context.store("measured_error", None)
    assert isinstance(scenario_context.get("measured_error"), NotFoundError)


@when('I build OpentelemetryConfig with METRICS_EXPORTER "{exporter}"')
def step_when_build_bad_metrics_exporter(context, exporter):
    from pydantic import ValidationError

    from archipy.configs.config_template import OpentelemetryConfig

    scenario_context = get_current_scenario_context(context)
    try:
        OpentelemetryConfig(
            IS_ENABLED=True,
            TRACES_ENABLED=False,
            METRICS_ENABLED=True,
            LOGS_ENABLED=False,
            METRICS_EXPORTER=exporter,
        )
        scenario_context.store("validation_error", None)
    except ValidationError as exc:
        scenario_context.store("validation_error", exc)


@then('a ValidationError should be raised for field "{field_name}"')
def step_then_validation_error_for_field(context, field_name):
    scenario_context = get_current_scenario_context(context)
    err = scenario_context.get("validation_error")
    assert err is not None, "Expected ValidationError"
    locations = [str(loc) for error in err.errors() for loc in error.get("loc", ())]
    assert field_name in locations, f"Expected field {field_name!r} in {locations!r}"


@then('the metrics pull scrape endpoint should return 200 containing "{needle}"')
def step_then_scrape_contains(context, needle):
    scenario_context = get_current_scenario_context(context)
    port = scenario_context.get("metrics_pull_port")
    response = httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=2)
    assert response.status_code == 200
    body = response.text
    assert needle in body, f"Expected {needle!r} in scrape body:\n{body[:2000]}"


@then("the metrics pull scrape endpoint should return 200")
def step_then_scrape_200(context):
    scenario_context = get_current_scenario_context(context)
    port = scenario_context.get("metrics_pull_port")
    response = httpx2.get(f"http://127.0.0.1:{port}/metrics", timeout=2)
    assert response.status_code == 200


@then("the metrics pull scrape port should refuse connections")
def step_then_scrape_refused(context):
    import socket

    scenario_context = get_current_scenario_context(context)
    port = scenario_context.get("metrics_pull_port")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(("127.0.0.1", port))
    assert result != 0, f"Expected port {port} closed, but connect succeeded"


@then("system CPU metric instruments should be absent")
def step_then_no_system_metrics(context):
    assert "system_metrics" not in OtelUtils._instrumented_libraries


@given("OpenTelemetry is configured for pull metrics on a busy port with traces enabled")
def step_given_pull_busy_port_with_traces(context):
    import socket

    from archipy.configs.config_template import OtelMetricsExporter

    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False

    port = _free_tcp_port()
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    blocker.bind(("127.0.0.1", port))
    blocker.listen(1)

    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.PULL
    config.OTEL.METRICS_PULL_HOST = "127.0.0.1"
    config.OTEL.METRICS_PULL_PORT = port
    config.OTEL.SYSTEM_METRICS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://127.0.0.1:4318"
    config.OTEL.SERVICE_NAME = "archipy-pull-busy-bdd"

    scenario_context.store("metrics_pull_port", port)
    scenario_context.store("metrics_pull_blocker", blocker)
    scenario_context.store("otel_enabled_for_test", True)


def _release_pull_blocker(context) -> None:
    scenario_context = get_current_scenario_context(context)
    blocker = scenario_context.get("metrics_pull_blocker")
    if blocker is not None:
        try:
            blocker.close()
        except OSError:
            pass
        scenario_context.store("metrics_pull_blocker", None)


@then("the OpenTelemetry meter provider should be available")
def step_then_meter_available(context):
    _release_pull_blocker(context)
    assert OtelUtils.meter_provider() is not None


@then("the OpenTelemetry tracer provider should be available")
def step_then_tracer_available(context):
    assert OtelUtils.tracer_provider() is not None


@then("the metrics registry should be available")
def step_then_metrics_registry_available(context):
    assert OtelUtils.metrics_registry() is not None


_PUSHGATEWAY_JOB = "archipy-pushgateway-bdd"


def _pushgateway_container(context):
    return get_current_scenario_context(context).get("test_containers").get_container("pushgateway")


def _pushgateway_group(context, job: str) -> dict | None:
    """Return the group the real Pushgateway holds for ``job``, or None."""
    for group in _pushgateway_container(context).groups():
        if group.get("labels", {}).get("job") == job:
            return group
    return None


def _wait_for_pushgateway_group(context, job: str, predicate=lambda group: True, timeout: float = 5.0) -> dict | None:
    deadline = time.monotonic() + timeout
    while True:
        group = _pushgateway_group(context, job)
        if group is not None and predicate(group):
            return group
        if time.monotonic() >= deadline:
            return group
        time.sleep(0.1)


def _group_push_time(group: dict) -> float:
    return float(group["push_time_seconds"]["metrics"][0]["value"])


def _configure_pushgateway(context, *, url: str | None = None, delete_on_shutdown: bool = True) -> None:
    """Point the real Pushgateway exporter at the Pushgateway container (or at ``url``)."""
    from archipy.configs.config_template import OtelMetricsExporter

    scenario_context = get_current_scenario_context(context)
    _snapshot_otel_config(scenario_context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False
    pushgateway = _pushgateway_container(context)
    pushgateway.clear()

    port = _free_tcp_port()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = False
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.METRICS_EXPORTER = OtelMetricsExporter.PUSHGATEWAY
    config.OTEL.METRICS_PUSHGATEWAY_URL = url or pushgateway.url
    config.OTEL.METRICS_PUSHGATEWAY_JOB = _PUSHGATEWAY_JOB
    config.OTEL.METRICS_PUSHGATEWAY_INTERVAL_SECONDS = 1
    config.OTEL.METRICS_PUSHGATEWAY_TIMEOUT_SECONDS = 1.0
    config.OTEL.METRICS_PUSHGATEWAY_GROUPING_KEY = {"instance": "bdd"}
    config.OTEL.METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN = delete_on_shutdown
    config.OTEL.METRICS_PULL_HOST = "127.0.0.1"
    config.OTEL.METRICS_PULL_PORT = port
    config.OTEL.SYSTEM_METRICS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://127.0.0.1:4318"
    config.OTEL.SERVICE_NAME = "archipy-pushgateway-bdd"

    scenario_context.store("metrics_pull_port", port)
    scenario_context.store("otel_enabled_for_test", True)


class _PushFailureCollector(logging.Handler):
    """Collect the warning ArchiPy logs when a Pushgateway push fails."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.seen = threading.Event()

    def emit(self, record: logging.LogRecord) -> None:
        if "Failed to push metrics to Pushgateway" in record.getMessage():
            self.seen.set()


@given("OpenTelemetry is configured for pushgateway metrics with a real Pushgateway")
def step_given_pushgateway_real(context):
    _configure_pushgateway(context)


@given("OpenTelemetry is configured for pushgateway metrics with an unreachable Pushgateway")
def step_given_pushgateway_unreachable(context):
    scenario_context = get_current_scenario_context(context)
    # A port nothing listens on: the push fails with a real connection error.
    _configure_pushgateway(context, url=f"http://127.0.0.1:{_free_tcp_port()}")
    collector = _PushFailureCollector()
    otel_logger = logging.getLogger("archipy.helpers.utils.otel_utils")
    otel_logger.addHandler(collector)
    context.add_cleanup(otel_logger.removeHandler, collector)
    scenario_context.store("pushgateway_failure_collector", collector)


@given("OpenTelemetry is configured for pushgateway metrics with a real Pushgateway that keeps its group on shutdown")
def step_given_pushgateway_keeps_group(context):
    _configure_pushgateway(context, delete_on_shutdown=False)


@when("I wait for a Pushgateway push")
def step_when_wait_pushgateway_push(context):
    group = _wait_for_pushgateway_group(context, _PUSHGATEWAY_JOB)
    assert group is not None, "Timed out waiting for Pushgateway push"


@when("I wait for a Pushgateway push attempt")
def step_when_wait_pushgateway_attempt(context):
    collector = get_current_scenario_context(context).get("pushgateway_failure_collector")
    assert collector.seen.wait(timeout=5), "Timed out waiting for Pushgateway push attempt"


@when('I note the Pushgateway push time for job "{job}"')
def step_when_note_pushgateway_push_time(context, job):
    group = _pushgateway_group(context, job)
    assert group is not None, f"Pushgateway holds no group for job {job!r}"
    get_current_scenario_context(context).store("pushgateway_push_time_before", _group_push_time(group))


@then('the Pushgateway should have received a push for job "{job}"')
def step_then_pushgateway_push(context, job):
    group = _pushgateway_group(context, job)
    assert group is not None, f"Expected a Pushgateway group for job {job!r}"
    assert group.get("last_push_successful") is True, group
    assert OtelUtils.metrics_registry() is not None


@then('the Pushgateway group for job "{job}" should carry label "{label}" equal to "{value}"')
def step_then_pushgateway_label(context, job, label, value):
    group = _pushgateway_group(context, job)
    assert group is not None, f"Expected a Pushgateway group for job {job!r}"
    assert group["labels"].get(label) == value, f"Expected {label}={value!r}, got {group['labels']}"


@then('the Pushgateway group for job "{job}" should contain a metric named "{needle}"')
def step_then_pushgateway_metric(context, job, needle):
    def has_metric(group: dict) -> bool:
        return any(needle in name for name in group if isinstance(group[name], dict) and "metrics" in group[name])

    group = _wait_for_pushgateway_group(context, job, has_metric)
    assert group is not None and has_metric(group), (
        f"No metric containing {needle!r} in Pushgateway group {sorted(group) if group else None}"
    )


@then('the Pushgateway should no longer hold job "{job}"')
def step_then_pushgateway_deleted(context, job):
    assert _pushgateway_group(context, job) is None, f"Pushgateway still holds a group for job {job!r}"


@then('the Pushgateway should still hold job "{job}"')
def step_then_pushgateway_still_holds(context, job):
    assert _pushgateway_group(context, job) is not None, f"Pushgateway lost the group for job {job!r}"


@then('the Pushgateway push time for job "{job}" should have advanced')
def step_then_pushgateway_push_time_advanced(context, job):
    before = get_current_scenario_context(context).get("pushgateway_push_time_before")
    group = _pushgateway_group(context, job)
    assert group is not None, f"Pushgateway holds no group for job {job!r}"
    after = _group_push_time(group)
    assert after > before, f"Expected a push during shutdown, push time stayed at {before}"


# ---------------------------------------------------------------------------
# Auto-instrumentation of installed libraries (httpx / httpx2)
# ---------------------------------------------------------------------------


class _ErrorRecordCollector(logging.Handler):
    """Collect ERROR+ records emitted by the OTel instrumentor logger."""

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


class _RecordCollector(logging.Handler):
    """Collect every record of the logger it is attached to."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _run_auto_instrumentation(scenario_context) -> None:
    instrumentor_logger = logging.getLogger("opentelemetry.instrumentation.instrumentor")
    archipy_logger = logging.getLogger("archipy.helpers.utils.otel_utils")
    collector = _ErrorRecordCollector()
    archipy_collector = _RecordCollector()
    previous_level = archipy_logger.level
    instrumentor_logger.addHandler(collector)
    archipy_logger.addHandler(archipy_collector)
    archipy_logger.setLevel(logging.DEBUG)
    try:
        OtelUtils._instrument_installed_libraries(BaseConfig.global_config())
    finally:
        instrumentor_logger.removeHandler(collector)
        archipy_logger.removeHandler(archipy_collector)
        archipy_logger.setLevel(previous_level)
    scenario_context.store("instrumentor_error_records", collector.records)
    scenario_context.store("archipy_otel_records", archipy_collector.records)


@given("the httpx instrumentor targets a library version that is not installed")
def step_given_httpx_dependency_out_of_range(context):
    """Point the httpx instrumentor at an installed library (httpx2) with an unsatisfiable version range."""
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    scenario_context = get_current_scenario_context(context)
    _uninstrument_httpx()
    original = HTTPXClientInstrumentor._instrumentation_dependencies
    HTTPXClientInstrumentor._instrumentation_dependencies = ("httpx2 >= 9999.0",)
    scenario_context.store("httpx_original_dependencies", original)


@then('an OpenTelemetry warning should say that "{key}" emits no spans because of its version range')
def step_then_warning_version_range(context, key):
    scenario_context = get_current_scenario_context(context)
    warnings = [r for r in scenario_context.get("archipy_otel_records") or [] if r.levelno == logging.WARNING]
    matching = [r for r in warnings if r.args and r.args[0] == key]
    assert matching, f"No warning for {key!r}: {[r.getMessage() for r in warnings]}"
    message = matching[0].getMessage()
    assert "no spans will be emitted" in message and "httpx2 >= 9999.0" in message, message
    assert "httpx2" in message and "falls outside" in message, message


@given("the SQLAlchemy instrumentor is not bound yet")
def step_given_sqlalchemy_instrumentor_unbound(context):
    """Start from an unbound SQLAlchemy instrumentor so the version check runs against the installed SQLAlchemy."""
    from features.steps.adapter_spans_steps import _uninstrument_all

    _snapshot_otel_config(get_current_scenario_context(context))
    _uninstrument_all()
    OtelUtils._instrumented_libraries.discard("sqlalchemy")


@given("the OTEL instrumentation skip list is empty")
def step_given_skip_dep_check_empty(context):
    _snapshot_otel_config(get_current_scenario_context(context))
    BaseConfig.global_config().OTEL.INSTRUMENTATION_SKIP_DEP_CHECK = []


@then('an OpenTelemetry warning should say that the version check is bypassed for "{key}"')
def step_then_warning_version_check_bypassed(context, key):
    scenario_context = get_current_scenario_context(context)
    warnings = [r for r in scenario_context.get("archipy_otel_records") or [] if r.levelno == logging.WARNING]
    messages = [r.getMessage() for r in warnings if r.args and r.args[0] == key]
    assert any("INSTRUMENTATION_SKIP_DEP_CHECK" in message and "is enabled" in message for message in messages), (
        f"No bypass warning for {key!r}: {[r.getMessage() for r in warnings]}"
    )


@then('an OpenTelemetry warning should say that "{key}" emits no spans')
def step_then_warning_no_spans(context, key):
    scenario_context = get_current_scenario_context(context)
    warnings = [r for r in scenario_context.get("archipy_otel_records") or [] if r.levelno == logging.WARNING]
    messages = [r.getMessage() for r in warnings if r.args and r.args[0] == key]
    assert any("no spans will be emitted" in message for message in messages), (
        f"No 'no spans' warning for {key!r}: {[r.getMessage() for r in warnings]}"
    )


@when("I guard the Redis search attributes twice")
def step_when_guard_redis_search_twice(context):
    from opentelemetry.instrumentation.redis import util as redis_util

    # Leave the guard in place for later scenarios, whatever this one does.
    context.add_cleanup(OtelUtils._guard_redis_search_attributes)
    OtelUtils.restore_redis_search_attributes()
    upstream = redis_util._add_search_attributes
    OtelUtils._guard_redis_search_attributes()
    first = redis_util._add_search_attributes
    OtelUtils._guard_redis_search_attributes()
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("redis_search_upstream", upstream)
    scenario_context.store("redis_search_first_guard", first)


@then("the Redis search helper should be wrapped exactly once")
def step_then_redis_search_wrapped_once(context):
    from opentelemetry.instrumentation.redis import util as redis_util

    scenario_context = get_current_scenario_context(context)
    upstream = scenario_context.get("redis_search_upstream")
    first = scenario_context.get("redis_search_first_guard")
    assert first is not upstream, "The helper was not wrapped"
    assert redis_util._add_search_attributes is first, "A second guard call wrapped the helper again"
    assert first._archipy_original is upstream


@when("I restore the Redis search attributes")
def step_when_restore_redis_search(context):
    OtelUtils.restore_redis_search_attributes()


@then("the Redis search helper should be the upstream function")
def step_then_redis_search_upstream(context):
    from opentelemetry.instrumentation.redis import util as redis_util

    upstream = get_current_scenario_context(context).get("redis_search_upstream")
    assert redis_util._add_search_attributes is upstream


@then('no OpenTelemetry warning should be logged for "{key}"')
def step_then_no_warning_for_library(context, key):
    scenario_context = get_current_scenario_context(context)
    records = scenario_context.get("archipy_otel_records") or []
    warnings = [r for r in records if r.levelno >= logging.WARNING and r.args and r.args[0] == key]
    assert not warnings, f"Unexpected warnings for {key!r}: {[r.getMessage() for r in warnings]}"
    skipped = [r for r in records if r.levelno == logging.DEBUG and r.args and r.args[0] == key]
    assert skipped, f"Expected a debug skip record for {key!r}"


@given("the httpx instrumentor reports its target library as missing")
def step_given_httpx_dependency_missing(context):
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    scenario_context = get_current_scenario_context(context)
    _uninstrument_httpx()
    original = HTTPXClientInstrumentor._instrumentation_dependencies
    HTTPXClientInstrumentor._instrumentation_dependencies = ("archipy-missing-httpx-dist >= 0.18.0",)
    scenario_context.store("httpx_original_dependencies", original)


@when("I run auto-instrumentation of installed libraries")
def step_when_run_auto_instrumentation(context):
    scenario_context = get_current_scenario_context(context)
    _uninstrument_httpx()
    OtelUtils._instrumented_libraries.discard("httpx")
    OtelUtils._instrumented_libraries.discard("httpx2")
    try:
        _run_auto_instrumentation(scenario_context)
    finally:
        original = scenario_context.get("httpx_original_dependencies")
        if original is not None:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor._instrumentation_dependencies = original


@then('the library "{key}" should be auto-instrumented')
def step_then_library_instrumented(context, key):
    assert key in OtelUtils._instrumented_libraries, (
        f"Expected '{key}' in instrumented libraries, got {sorted(OtelUtils._instrumented_libraries)}"
    )


@then('the library "{key}" should not be auto-instrumented')
def step_then_library_not_instrumented(context, key):
    assert key not in OtelUtils._instrumented_libraries, (
        f"Did not expect '{key}' in instrumented libraries, got {sorted(OtelUtils._instrumented_libraries)}"
    )


@then("httpx2 transports should be wrapped by OpenTelemetry")
def step_then_httpx2_transports_wrapped(context):
    import httpx2

    assert hasattr(httpx2.HTTPTransport.handle_request, "__wrapped__"), "httpx2.HTTPTransport not instrumented"
    assert hasattr(httpx2.AsyncHTTPTransport.handle_async_request, "__wrapped__"), (
        "httpx2.AsyncHTTPTransport not instrumented"
    )


@then("no OpenTelemetry instrumentor error should be logged")
def step_then_no_instrumentor_error(context):
    scenario_context = get_current_scenario_context(context)
    records = scenario_context.get("instrumentor_error_records") or []
    assert not records, f"Unexpected instrumentor errors: {[r.getMessage() for r in records]}"


@given("FastAPI log records are {state} with a logger provider")
def step_given_fastapi_logs(context: Context, state: str) -> None:
    from opentelemetry.sdk._logs import LoggerProvider

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.FASTAPI_LOGS_ENABLED = state == "enabled"
    OtelUtils._logger_provider = LoggerProvider()
    # Ensures teardown_otel_testing resets the provider and config flag.
    scenario_context.store("otel_enabled_for_test", True)


@when("I build the FastAPI telemetry config")
def step_when_build_fastapi_telemetry(context):
    from archipy.helpers.utils.app_utils import FastAPIUtils

    scenario_context = get_current_scenario_context(context)
    scenario_context.store("fastapi_telemetry", FastAPIUtils.build_otel_telemetry_config(BaseConfig.global_config()))


@then("the FastAPI telemetry config should have logs {state}")
def step_then_fastapi_telemetry_logs(context, state):
    telemetry = get_current_scenario_context(context).get("fastapi_telemetry")
    assert telemetry["logs"] is (state == "on"), telemetry
    assert ("logger_provider" in telemetry) is (state == "on"), telemetry
    assert telemetry["auto_configure"] is False, telemetry


@given("FastAPI log records are enabled with the collector")
def step_given_fastapi_logs_collector(context: Context) -> None:
    _setup_collector_otel(context, logs=True)
    BaseConfig.global_config().OTEL.FASTAPI_LOGS_ENABLED = True


@when('I create an instrumented FastAPI app whose endpoint "{path}" raises')
def step_when_fastapi_raises(context, path):
    from fastapi.testclient import TestClient

    from archipy.helpers.utils.app_utils import AppUtils

    app = AppUtils.create_fastapi_app(BaseConfig.global_config(), configure_exception_handlers=False)

    @app.get(path)
    def otel_boom():
        raise RuntimeError("otel boom")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path)
    assert response.status_code == 500, response.text


@then("an OTel log record should be exported")
def step_then_log_record_exported(context):
    telemetry = _telemetry(context)
    telemetry.flush()
    records = telemetry.wait_for(
        lambda: [record for record in telemetry.logs() if "otel boom" in repr(record.body) + repr(record.attributes)],
    )
    assert records, (
        "FastAPI emitted no OTel log record for the unhandled exception; "
        f"exported: {[(record.body, record.attributes) for record in telemetry.logs()]}"
    )


def _histogram_metric(context: Context, instrument_name: str):
    telemetry = _telemetry(context)
    if telemetry is not None:
        telemetry.flush()
        metric = telemetry.wait_for(lambda: telemetry.metrics().get(instrument_name))
        assert metric, f"No metric named {instrument_name!r}"
        return metric
    reader: InMemoryMetricReader = get_current_scenario_context(context).get("metric_reader")
    metrics_data = reader.get_metrics_data()
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name == instrument_name:
                    return metric
    raise AssertionError(f"No metric named {instrument_name!r}")


@then('the "{first}" and "{second}" histograms should have the same unit and buckets')
def step_then_histograms_similar(context, first, second):
    a = _histogram_metric(context, first)
    b = _histogram_metric(context, second)
    assert a.unit == b.unit == "s", f"Units differ: {a.unit!r} vs {b.unit!r}"
    bounds_a = a.data.data_points[0].explicit_bounds
    bounds_b = b.data.data_points[0].explicit_bounds
    assert bounds_a == bounds_b, f"Buckets differ: {bounds_a} vs {bounds_b}"


@then('an up-down counter metric named "{instrument_name}" should net to 0 with datapoints')
def step_then_up_down_counter_zero(context, instrument_name):
    points = _metric_datapoints(context, instrument_name)
    assert points, f"No datapoints for up-down counter '{instrument_name}'"
    assert sum(point.value for point in points) == 0, [point.value for point in points]


@given("a class decorated with trace_class that holds a nested class")
def step_given_trace_class_nested(context):
    @trace_class()
    class Service:
        class Config:
            value = 1

        def public_method(self) -> str:
            return "public"

    get_current_scenario_context(context).store("traced_nested_owner", Service)


@then("the nested class should still be a class")
def step_then_nested_class_untouched(context):
    owner = get_current_scenario_context(context).get("traced_nested_owner")
    assert isinstance(owner.Config, type), f"Nested class was replaced by {owner.Config!r}"
    assert owner.Config.value == 1


@when("I call the traced sync function with wrong arguments")
def step_when_call_traced_sync_wrong_args(context):
    scenario_context = get_current_scenario_context(context)
    try:
        scenario_context.get("traced_sync")(1, 2, 3)
        scenario_context.store("call_error", None)
    except Exception as exc:
        scenario_context.store("call_error", exc)


@then("the function's own TypeError should be raised")
def step_then_functions_own_type_error(context):
    error = get_current_scenario_context(context).get("call_error")
    assert isinstance(error, TypeError), f"Got {error!r}"
    assert "traced_sync()" in str(error), f"Error did not come from the traced function: {error}"


@given("a sync function decorated with measure_duration whose histogram fails to record")
def step_given_measure_duration_failing_histogram(context):
    from unittest import mock

    from archipy.helpers.decorators import metrics as metrics_module

    class _BrokenHistogram:
        def record(self, *_args, **_kwargs):
            raise RuntimeError("exporter exploded")

    patcher = mock.patch.object(metrics_module, "_get_or_create_histogram", lambda *_a, **_k: _BrokenHistogram())
    patcher.start()
    context.add_cleanup(patcher.stop)

    @measure_duration(name="test.broken.duration")
    def measured_sync() -> str:
        return "timed"

    get_current_scenario_context(context).store("measured_sync", measured_sync)


@then("the measured function should still return its result")
def step_then_measured_result(context):
    assert get_current_scenario_context(context).get("result") == "timed"


# ---------------------------------------------------------------------------
# gRPC metrics interceptor edge cases
# ---------------------------------------------------------------------------


@when("a sync response stream is intercepted for an RPC that already terminated")
def step_when_stream_on_terminated_rpc(context):
    from archipy.helpers.interceptors.grpc.base.server_interceptor import MethodName
    from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
        GrpcServerOtelMetricsInterceptor,
        _RpcInstruments,
    )

    _RpcInstruments.clear()

    class _TerminatedRpcContext:
        def add_callback(self, _callback) -> bool:
            return False

        def code(self):
            return None

    def stream_handler(_request, _context):
        yield b"never consumed"

    method_name = MethodName(full_name="test.Svc/Stream", package="test", service="Svc", method="Stream")
    stream = GrpcServerOtelMetricsInterceptor().intercept(stream_handler, b"", _TerminatedRpcContext(), method_name)
    assert stream is not None  # the stream is returned but never iterated


@when("{count:d} threads request the RPC instruments at the same time")
def step_when_threads_request_instruments(context, count):
    from concurrent.futures import ThreadPoolExecutor

    from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import _RpcInstruments

    _RpcInstruments.clear()
    barrier = threading.Barrier(count)

    def fetch():
        barrier.wait(timeout=5)
        return _RpcInstruments.get()

    with ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda _: fetch(), range(count)))
    get_current_scenario_context(context).store("rpc_instruments_results", results)


@then("every thread should receive the same RPC instruments")
def step_then_same_instruments(context):
    results = get_current_scenario_context(context).get("rpc_instruments_results")
    assert all(result is not None for result in results), "Metrics were unavailable"
    assert all(result is results[0] for result in results), "Instruments were created twice"


# ---------------------------------------------------------------------------
# Initialization back-off, provider shutdown tracking
# ---------------------------------------------------------------------------


def _fail_provider_construction(context):
    """Make provider construction raise, counting attempts; restored when the scenario ends."""
    scenario_context = get_current_scenario_context(context)
    reset_otel_for_testing()
    OtelUtils._globals_set = False
    config = BaseConfig.global_config()
    _reset_otel_config_defaults()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://localhost:4318"

    attempts: list[int] = []
    def _boom(_config):
        attempts.append(1)
        raise RuntimeError("provider construction boom")

    patcher = patch.object(OtelUtils.runtime(), "_build_providers", _boom)
    patcher.start()
    context.add_cleanup(patcher.stop)
    context.add_cleanup(reset_otel_for_testing)
    scenario_context.store("provider_attempts", attempts)
    scenario_context.store("otel_enabled_for_test", True)
    return config


@when("OpenTelemetry provider construction fails and initialization is requested twice in a row")
def step_when_init_fails_twice(context):
    config = _fail_provider_construction(context)
    OtelUtils.init_otel_if_needed(config)
    OtelUtils.init_otel_if_needed(config)


@when("OpenTelemetry provider construction fails and initialization is requested again after the back-off")
def step_when_init_fails_then_retries(context):
    import time

    config = _fail_provider_construction(context)
    OtelUtils.init_otel_if_needed(config)
    OtelUtils._init_failed_at = time.monotonic() - 3600
    OtelUtils.init_otel_if_needed(config)


@then("provider construction should have been attempted {expected:d} time")
@then("provider construction should have been attempted {expected:d} times")
def step_then_provider_attempts(context, expected):
    attempts = get_current_scenario_context(context).get("provider_attempts")
    assert len(attempts) == expected, f"Expected {expected} attempt(s), got {len(attempts)}"


@when("a provider is marked as shut down and then dropped")
def step_when_provider_marked_shutdown(context):
    import gc

    class _Provider:
        """Plain provider stand-in: real SDK providers register an atexit hook that keeps them alive."""

    scenario_context = get_current_scenario_context(context)
    provider = _Provider()
    OtelUtils._mark_provider_shutdown(provider)
    scenario_context.store("unusable_while_alive", not OtelUtils._is_usable_provider(provider))
    before = len(OtelUtils._shutdown_providers)
    del provider
    gc.collect()
    scenario_context.store("registry_size_change", before - len(OtelUtils._shutdown_providers))


@then("the provider should have been reported as unusable while alive")
def step_then_provider_unusable_while_alive(context):
    assert get_current_scenario_context(context).get("unusable_while_alive") is True


@then("the shut down provider registry should no longer hold it")
def step_then_registry_released(context):
    assert get_current_scenario_context(context).get("registry_size_change") >= 1


@when("I create every observable instrument on the no-op meter")
def step_when_noop_observables(context):
    from archipy.helpers.utils._otel.noop import _NoOpGauge, _NoOpMeter

    meter = _NoOpMeter()
    gauge = meter.create_gauge("sync_gauge")
    gauge.set(1)
    assert isinstance(gauge, _NoOpGauge)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store(
        "noop_observables",
        [
            meter.create_observable_counter("c", callbacks=[]),
            meter.create_observable_gauge("g", callbacks=[]),
            meter.create_observable_up_down_counter("u", callbacks=[]),
        ],
    )


@then("each no-op observable instrument should be the no-op stub")
def step_then_noop_observables(context):
    from archipy.helpers.utils._otel.noop import _NoOpObservableInstrument

    instruments = get_current_scenario_context(context).get("noop_observables")
    assert len(instruments) == 3
    assert all(isinstance(i, _NoOpObservableInstrument) for i in instruments)
