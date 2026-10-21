"""Steps that check what Elastic APM Server stored in Elasticsearch for the telemetry a scenario exported.

Telemetry reaches APM Server either directly from the application or through a collector that forwards it, so
every adapter scenario can run against both routes.
"""

import logging
import time
from collections.abc import Callable

from behave import given, then, when
from opentelemetry import trace

from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import trace_span
from archipy.helpers.utils.otel_utils import OtelUtils
from features.test_helpers import get_current_scenario_context

APM_ROUTE_DIRECT = "directly"
APM_ROUTE_COLLECTOR = "through the collector"
APM_POLL_TIMEOUT_SECONDS = 30


def apm_endpoint(scenario_context, route: str) -> str:
    """Return the OTLP endpoint the application must export to for the given route.

    Args:
        scenario_context: Context of the running scenario.
        route: ``directly`` for APM Server itself, ``through the collector`` for the forwarding collector.

    Returns:
        str: The OTLP/gRPC endpoint URL.
    """
    containers = scenario_context.get("test_containers")
    if route == APM_ROUTE_DIRECT:
        return containers.get_container("apm-server").grpc_endpoint
    if route == APM_ROUTE_COLLECTOR:
        return containers.get_container("otel-collector-apm").grpc_endpoint
    raise AssertionError(f"Unknown APM route: {route!r}")


def _poll(read: Callable[[], object]) -> object:
    """Flush the providers and call ``read`` until it returns something truthy or the timeout passes."""
    deadline = time.monotonic() + APM_POLL_TIMEOUT_SECONDS
    result = read()
    while not result and time.monotonic() < deadline:
        OtelUtils.force_flush(timeout_millis=2000)
        time.sleep(0.5)
        result = read()
    return result


def wait_for_apm_metric(read: Callable[[], bool]) -> bool:
    """Flush the providers and poll until ``read`` is true or the timeout passes."""
    return bool(_poll(read))


def wait_for_apm_events(context, predicate: Callable[[dict], bool]) -> tuple[list[dict], list[dict]]:
    """Flush the providers and poll Elasticsearch until a stored event matches, or the timeout passes.

    Returns:
        tuple[list[dict], list[dict]]: The matching events and every event stored for the scenario's service.
    """
    apm_server = get_current_scenario_context(context).get("test_containers").get_container("apm-server")
    service_name = BaseConfig.global_config().OTEL.SERVICE_NAME
    deadline = time.monotonic() + APM_POLL_TIMEOUT_SECONDS
    stored: list[dict] = []
    matching: list[dict] = []
    while time.monotonic() < deadline:
        OtelUtils.force_flush(timeout_millis=2000)
        stored = apm_server.events(service_name)
        matching = [event for event in stored if predicate(event)]
        if matching:
            break
        time.sleep(0.5)
    return matching, stored


@then('Elastic APM Server should store a span of type "{span_type}" with subtype "{subtype}"')
def step_apm_server_span(context, span_type, subtype) -> None:
    """Check Elasticsearch holds a span with the type and subtype Elastic APM derived."""
    matching, stored = wait_for_apm_events(
        context,
        lambda event: event["processor"]["event"] == "span"
        and event["span"].get("type") == span_type
        and event["span"].get("subtype") == subtype,
    )
    assert matching, f"No {span_type}/{subtype} span stored: {stored}"


@then('Elastic APM Server should store a "{span_type}" span named "{name}"')
def step_apm_server_named_span(context, span_type, name) -> None:
    """Check Elasticsearch holds the named span with the type Elastic APM derived."""
    matching, stored = wait_for_apm_events(
        context,
        lambda event: event["processor"]["event"] == "span" and event["span"].get("name") == name,
    )
    types = {event["span"]["type"] for event in matching}
    assert types == {span_type}, f"{name}: span types {types}, stored {stored}"


@then('Elastic APM Server should store a transaction of type "{transaction_type}"')
def step_apm_server_transaction_type(context, transaction_type) -> None:
    """Check Elasticsearch holds a transaction of the type Elastic APM derived."""
    matching, stored = wait_for_apm_events(
        context,
        lambda event: event["processor"]["event"] == "transaction"
        and event["transaction"].get("type") == transaction_type,
    )
    assert matching, f"No {transaction_type} transaction stored: {stored}"


@then('Elastic APM Server should store a "{transaction_type}" transaction named "{name}"')
def step_apm_server_transaction(context, transaction_type, name) -> None:
    """Check Elasticsearch holds the named transaction with the type Elastic APM derived."""
    matching, stored = wait_for_apm_events(
        context,
        lambda event: event["processor"]["event"] == "transaction" and event["transaction"].get("name") == name,
    )
    types = [event["transaction"]["type"] for event in matching]
    assert types == [transaction_type], f"{name}: transaction types {types}, stored {stored}"


@then('Elastic APM Server should store {count:d} "{transaction_type}" transactions named "{name}"')
def step_apm_server_transactions(context, count, transaction_type, name) -> None:
    """Check Elasticsearch holds the expected number of the named transaction, for example one per retry attempt."""
    deadline = time.monotonic() + APM_POLL_TIMEOUT_SECONDS
    types: list[str] = []
    stored: list[dict] = []
    while time.monotonic() < deadline:
        matching, stored = wait_for_apm_events(
            context,
            lambda event: event["processor"]["event"] == "transaction" and event["transaction"].get("name") == name,
        )
        types = [event["transaction"]["type"] for event in matching]
        if len(types) >= count:
            break
        time.sleep(0.5)
    assert types == [transaction_type] * count, f"{name}: transaction types {types}, stored {stored}"


@given("OpenTelemetry traces, metrics and logs are exported to Elastic APM Server {route}")
def step_otel_apm_server(context, route) -> None:
    """Enable all three signals against Elastic APM Server, directly or through the forwarding collector."""
    from features.steps.otel_steps import _setup_collector_otel

    scenario_context = get_current_scenario_context(context)
    _setup_collector_otel(
        context,
        traces=True,
        metrics=True,
        logs=True,
        otlp_endpoint=apm_endpoint(scenario_context, route),
    )


@then('Elastic APM Server should store the metric "{name}"')
def step_apm_server_metric(context, name) -> None:
    """Check Elasticsearch holds the application metric under the scenario's service."""
    apm_server = get_current_scenario_context(context).get("test_containers").get_container("apm-server")
    service_name = BaseConfig.global_config().OTEL.SERVICE_NAME
    names = _poll(lambda: {item for item in apm_server.metric_names(service_name) if item == name})
    assert names, f"Metric {name!r} not stored; stored metrics: {apm_server.metric_names(service_name)}"


@when('I log "{message}" inside a traced function')
def step_log_inside_traced_function(context, message) -> None:
    """Emit a warning log from inside a span and remember the trace id."""
    scenario_context = get_current_scenario_context(context)

    @trace_span()
    def work() -> str:
        logging.getLogger("archipy.bdd.apm").warning(message)
        return format(trace.get_current_span().get_span_context().trace_id, "032x")

    scenario_context.store("logged_trace_id", work())


@then('Elastic APM Server should store the log "{message}" correlated with that trace')
def step_apm_server_log(context, message) -> None:
    """Check Elasticsearch holds the log record and that it carries the trace id of the span it was logged in."""
    scenario_context = get_current_scenario_context(context)
    apm_server = scenario_context.get("test_containers").get_container("apm-server")
    service_name = BaseConfig.global_config().OTEL.SERVICE_NAME
    expected_trace_id = scenario_context.get("logged_trace_id")
    matching = _poll(
        lambda: [item for item in apm_server.logs(service_name) if item.get("message") == message],
    )
    assert matching, f"Log {message!r} not stored: {apm_server.logs(service_name)}"
    assert matching[0]["trace"]["id"] == expected_trace_id, f"{matching[0]} != trace {expected_trace_id}"
