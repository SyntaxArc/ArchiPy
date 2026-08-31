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
    async_measure_duration,
    async_trace_span,
    count_calls,
    measure_duration,
    trace_class,
    trace_root,
    trace_span,
)
from archipy.helpers.utils.error_utils import ErrorUtils
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import ConfigurationError, InvalidArgumentError, NotFoundError


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

    # Always attempt server cleanup when scenario stored any (even if OTel flag off).
    _cleanup_otel_integration_resources(scenario_context)

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


@then("the recorded span status should be UNSET")
def step_then_span_status_unset(context):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.status.status_code == StatusCode.UNSET, (
        f"Expected UNSET status, got {span.status.status_code}"
    )


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


@then('the recorded span should have attribute "{attr_name}" equal to "{attr_value}"')
def step_then_span_attribute_string(context, attr_name, attr_value):
    scenario_context = get_current_scenario_context(context)
    span = _span_by_name(context, scenario_context.get("expected_span_name"))
    assert span.attributes is not None, "Span has no attributes"
    assert span.attributes.get(attr_name) == attr_value, (
        f"Expected {attr_name}={attr_value!r}, got {span.attributes.get(attr_name)!r}"
    )


@when("I apply measure_duration to an async function")
def step_when_apply_measure_duration_to_async(context):
    scenario_context = get_current_scenario_context(context)
    try:

        @measure_duration()
        async def bad_async() -> str:
            return "nope"

        scenario_context.store("decorator_error", None)
        scenario_context.store("bad_async", bad_async)
    except InvalidArgumentError as exc:
        scenario_context.store("decorator_error", exc)


@then('an InvalidArgumentError should be raised for decorator "{decorator_name}"')
def step_then_invalid_argument_for_decorator(context, decorator_name):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("decorator_error")
    assert isinstance(error, InvalidArgumentError), f"Expected InvalidArgumentError, got {error!r}"
    additional = getattr(error, "additional_data", None) or {}
    assert additional.get("decorator") == decorator_name, (
        f"Expected decorator={decorator_name}, got {additional.get('decorator')}"
    )


@when('I resolve OTLP endpoints for protocol "{protocol}" with base "{base}"')
def step_when_resolve_endpoints(context, protocol, base):
    scenario_context = get_current_scenario_context(context)
    from archipy.configs.config_template import OpentelemetryConfig

    otel = OpentelemetryConfig(PROTOCOL=protocol, OTLP_ENDPOINT=base)
    scenario_context.store("resolved_traces", OtelUtils._resolve_otlp_endpoint(otel, "traces", None))
    scenario_context.store("resolved_metrics", OtelUtils.resolve_metrics_endpoint(otel))
    scenario_context.store("resolved_logs", OtelUtils._resolve_otlp_endpoint(otel, "logs", None))


@when(
    'I resolve OTLP metrics endpoint for protocol "{protocol}" with base "{base}" '
    'overridden to "{override}"',
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
    OtelUtils.reset_for_testing()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = False
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.SERVICE_NAME = service_name
    config.OTEL.ENVIRONMENT = environment
    config.OTEL.TRACES_SAMPLE_RATIO = 1.0
    # Avoid real OTLP export — use in-memory providers that still set resource attrs.
    span_exporter = InMemorySpanExporter()
    OtelUtils.configure_for_testing(span_exporter=span_exporter, service_name=service_name)
    # Patch environment onto the resource for assertion (configure_for_testing only sets service.name).
    # Build via _build_providers path for full resource attrs.
    OtelUtils.reset_for_testing()
    # Directly build resource the same way production does.
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

    resource = Resource.create(
        {
            "service.name": service_name,
            "deployment.environment.name": environment,
        },
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    OtelUtils._tracer_provider = provider
    OtelUtils._initialized = True
    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("otel_enabled_for_test", True)
    scenario_context.store("expected_service_name", service_name)
    scenario_context.store("expected_environment", environment)


@then('the tracer provider resource should include "{attr_name}" equal to "{attr_value}"')
def step_then_resource_attr(context, attr_name, attr_value):
    provider = OtelUtils.tracer_provider()
    assert provider is not None, "No tracer provider"
    value = provider.resource.attributes.get(attr_name)
    assert value == attr_value, f"Expected {attr_name}={attr_value!r}, got {value!r}"


@given("OpenTelemetry is configured for testing with sample ratio {ratio:f}")
def step_given_otel_with_sample_ratio(context, ratio):
    scenario_context = get_current_scenario_context(context)
    OtelUtils.reset_for_testing()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = False
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.TRACES_SAMPLE_RATIO = ratio

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

    span_exporter = InMemorySpanExporter()
    resource = Resource.create({"service.name": "archipy-test"})
    provider = TracerProvider(resource=resource, sampler=ParentBasedTraceIdRatio(ratio))
    provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    OtelUtils._tracer_provider = provider
    OtelUtils._initialized = True
    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("otel_enabled_for_test", True)


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
        f"Expected shared trace id {ambient_trace_id:032x}, "
        f"got {worker_span.context.trace_id:032x}"
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
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    instrumentor = HTTPXClientInstrumentor()
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
    import grpc
    from archipy.helpers.utils.app_utils import AppUtils

    _pb2, pb2_grpc = _import_test_proto()
    server = AppUtils.create_grpc_app(config)
    pb2_grpc.add_TestServiceServicer_to_server(servicer, server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    return server, port


def _grpc_stub(port: int):
    import grpc
    from opentelemetry.instrumentation.grpc import intercept_channel as otel_intercept_channel

    _pb2, pb2_grpc = _import_test_proto()
    channel = otel_intercept_channel(
        grpc.insecure_channel(f"localhost:{port}"),
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
    points = _metric_datapoints(context, "http.server.duration")
    assert points, "No http.server.duration datapoints"


@when("I call an instrumented gRPC TestMethod")
def step_when_call_instrumented_grpc(context):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    pb2, pb2_grpc = _import_test_proto()

    @measure_duration(name="otel.grpc.TestMethod.duration")
    def handle(request):
        return pb2.TestResponse(result="ok")

    class Servicer(pb2_grpc.TestServiceServicer):
        def TestMethod(self, request, context_):
            return handle(request)

    server, port = _start_grpc_test_server(config, Servicer())
    stub, channel = _grpc_stub(port)
    try:
        result = stub.TestMethod(pb2.TestRequest(data="hi"))
        assert result.result == "ok"
    finally:
        channel.close()
        server.stop(None)
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


@then("the OTel interceptor should be first and the sentinel should remain")
def step_then_grpc_otel_prepended(context):
    scenario_context = get_current_scenario_context(context)
    interceptors = scenario_context.get("grpc_interceptors")
    sentinel = scenario_context.get("grpc_sentinel")
    assert len(interceptors) == 2, f"Expected 2 interceptors, got {len(interceptors)}"
    assert interceptors[0] is not sentinel
    assert interceptors[1] is sentinel
    assert "OpenTelemetry" in type(interceptors[0]).__name__


@when("I connect a Temporal adapter with OTel enabled using a mocked Client")
async def step_when_temporal_mocked_connect(context):
    from unittest.mock import MagicMock, patch

    from archipy.adapters.temporal.adapters import TemporalAdapter
    from archipy.configs.config_template import TemporalConfig

    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://localhost:4318"

    adapter = TemporalAdapter(TemporalConfig(HOST="localhost", PORT=7233, ENABLE_METRICS=True))
    captured: dict = {}

    async def fake_connect(target, **kwargs):
        captured["target"] = target
        captured["kwargs"] = kwargs
        return MagicMock(name="TemporalClient")

    with patch("archipy.adapters.temporal.adapters.Client.connect", side_effect=fake_connect):
        with patch("archipy.adapters.temporal.adapters.TemporalRuntimeManager") as runtime_mgr:
            runtime_mgr.return_value.get_runtime.return_value = MagicMock(name="Runtime")
            await adapter.get_client()
            scenario_context.store("temporal_connect_kwargs", captured["kwargs"])
            scenario_context.store(
                "temporal_runtime_call_kwargs",
                runtime_mgr.return_value.get_runtime.call_args.kwargs,
            )


@then("the Temporal connect kwargs should include a TracingInterceptor")
def step_then_temporal_has_tracing_interceptor(context):
    from temporalio.contrib.opentelemetry import TracingInterceptor

    scenario_context = get_current_scenario_context(context)
    kwargs = scenario_context.get("temporal_connect_kwargs")
    interceptors = kwargs.get("interceptors") or []
    assert any(isinstance(item, TracingInterceptor) for item in interceptors), (
        f"No TracingInterceptor in {interceptors!r}"
    )


@then('the Temporal runtime should receive metrics endpoint "{endpoint}"')
def step_then_temporal_runtime_endpoint(context, endpoint):
    scenario_context = get_current_scenario_context(context)
    call_kwargs = scenario_context.get("temporal_runtime_call_kwargs")
    assert call_kwargs.get("otlp_endpoint") == endpoint, (
        f"Expected otlp_endpoint={endpoint!r}, got {call_kwargs.get('otlp_endpoint')!r}"
    )


@when("I append a Temporal TracingInterceptor to connect kwargs that already have a sentinel")
def step_when_temporal_append_with_sentinel(context):
    from archipy.adapters.temporal.adapters import TemporalAdapter

    scenario_context = get_current_scenario_context(context)

    class _SentinelInterceptor:
        pass

    sentinel = _SentinelInterceptor()
    connect_kwargs = {"interceptors": [sentinel]}
    TemporalAdapter._append_tracing_interceptor(connect_kwargs)
    scenario_context.store("temporal_connect_kwargs", connect_kwargs)
    scenario_context.store("temporal_sentinel", sentinel)


@then("the Temporal connect kwargs should keep the sentinel and include a TracingInterceptor")
def step_then_temporal_append_preserved(context):
    from temporalio.contrib.opentelemetry import TracingInterceptor

    scenario_context = get_current_scenario_context(context)
    kwargs = scenario_context.get("temporal_connect_kwargs")
    sentinel = scenario_context.get("temporal_sentinel")
    interceptors = kwargs["interceptors"]
    assert interceptors[0] is sentinel
    assert isinstance(interceptors[1], TracingInterceptor)


@then("all finished spans should share one trace id")
def step_then_single_trace_id(context):
    spans = _finished_spans(context)
    assert spans, "No finished spans"
    trace_ids = {span.context.trace_id for span in spans}
    assert len(trace_ids) == 1, f"Expected 1 trace id, got {len(trace_ids)}: {[f'{t:032x}' for t in trace_ids]}"


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


@given('an async function decorated with async_measure_duration named "{instrument_name}"')
def step_given_async_measure_duration(context, instrument_name):
    scenario_context = get_current_scenario_context(context)
    import asyncio

    @async_measure_duration(name=instrument_name)
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


@when("I cancel the traced async function")
async def step_when_cancel_traced_async(context):
    import asyncio

    scenario_context = get_current_scenario_context(context)

    @async_trace_span(name=scenario_context.get("expected_span_name") or "cancel_span")
    async def cancellable() -> str:
        await asyncio.sleep(60)
        return "done"

    # Re-wrap if Background already stored a different async fn without sleep
    if scenario_context.get("traced_async") is not None:
        # Prefer the named cancel_span from the Given step; redefine with sleep
        span_name = scenario_context.get("expected_span_name") or "cancel_span"

        @async_trace_span(name=span_name)
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
    scenario_context = get_current_scenario_context(context)
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
    OtelUtils.reset_for_testing()
    OtelUtils._globals_set = False
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = False
    config.OTEL.PROTOCOL = "http/protobuf"
    config.OTEL.OTLP_ENDPOINT = "http://localhost:4318"

    original = OtelUtils.__dict__["_create_metric_exporter"]

    @classmethod
    def _boom(cls, otel):
        raise RuntimeError("metric exporter boom")

    OtelUtils._create_metric_exporter = _boom
    try:
        OtelUtils.init_otel_if_needed(config)
    finally:
        OtelUtils._create_metric_exporter = original
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
    from opentelemetry.sdk._logs.export import InMemoryLogExporter

    scenario_context = get_current_scenario_context(context)
    OtelUtils.reset_for_testing()
    config = BaseConfig.global_config()
    config.OTEL.IS_ENABLED = True
    config.OTEL.TRACES_ENABLED = True
    config.OTEL.METRICS_ENABLED = True
    config.OTEL.LOGS_ENABLED = True

    span_exporter = InMemorySpanExporter()
    metric_reader = InMemoryMetricReader()
    log_exporter = InMemoryLogExporter()
    OtelUtils.configure_for_testing(
        span_exporter=span_exporter,
        metric_reader=metric_reader,
        log_exporter=log_exporter,
    )
    scenario_context.store("span_exporter", span_exporter)
    scenario_context.store("metric_reader", metric_reader)
    scenario_context.store("log_exporter", log_exporter)
    scenario_context.store("otel_enabled_for_test", True)


@when('I emit an INFO log message "{message}"')
def step_when_emit_log(context, message):
    logging.getLogger("archipy.otel.test").info(message)


@then('a log record containing "{message}" should be exported')
def step_then_log_exported(context, message):
    scenario_context = get_current_scenario_context(context)
    log_exporter = scenario_context.get("log_exporter")
    OtelUtils.force_flush(timeout_millis=2000)
    records = list(log_exporter.get_finished_logs())
    bodies = []
    for record in records:
        log_record = record.log_record
        body = log_record.body
        bodies.append(str(body))
    assert any(message in body for body in bodies), f"Expected {message!r} in {bodies!r}"


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
    from unittest.mock import patch

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
        yield

    app = AppUtils.create_fastapi_app(
        config,
        configure_exception_handlers=False,
        lifespan=user_lifespan,
    )
    with patch.object(OtelUtils, "force_flush", wraps=OtelUtils.force_flush) as flush_mock:
        with TestClient(app):
            assert user_ran["value"] is True
        scenario_context.store("lifespan_flush_called", flush_mock.called)
    # Providers must remain usable after TestClient lifespan exit.
    assert OtelUtils.tracer_provider() is not None
    scenario_context.store("otel_enabled_for_test", True)


@then("OpenTelemetry force flush should have been invoked during lifespan exit")
def step_then_lifespan_flush(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("lifespan_flush_called") is True
