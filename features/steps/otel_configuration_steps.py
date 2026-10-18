"""Behave steps for the OpenTelemetry configuration scenarios; they build providers and exporters without exporting."""

import json
import sys
from unittest.mock import patch

from behave import given, then, when

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OpentelemetryConfig
from archipy.helpers.utils._otel.env import apply_standard_env, sdk_disabled
from archipy.helpers.utils._otel.propagation import create_propagator
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import ConfigurationError
from features.test_helpers import get_current_scenario_context


def _ctx(context):
    return get_current_scenario_context(context)


@given("an OpenTelemetry config built from:")
def step_given_otel_config(context):
    _ctx(context).store("otel_cfg", OpentelemetryConfig(**json.loads(context.text)))


@then('building an OpenTelemetry config from the following fails with "{reason}":')
def step_then_otel_config_fails(context, reason):
    try:
        OpentelemetryConfig(**json.loads(context.text))
    except ConfigurationError as error:
        assert error.additional_data["reason"] == reason, error.additional_data
    else:
        raise AssertionError("the config was accepted")


@when("the tracer provider is built from the config")
def step_when_tracer_provider(context):
    sc = _ctx(context)
    otel = sc.get("otel_cfg")
    provider = OtelUtils._build_tracer_provider(otel, OtelUtils._create_resource(otel))
    context.add_cleanup(provider.shutdown)
    sc.store("tracer_provider_built", provider)


@then('the sampler description contains "{text}"')
def step_then_sampler(context, text):
    description = _ctx(context).get("tracer_provider_built").sampler.get_description()
    assert text in description, description


@then("the span batch processor holds queue {queue:d}, batch {batch:d}, delay {delay:d} and timeout {timeout:d}")
def step_then_batch_processor(context, queue, batch, delay, timeout):
    provider = _ctx(context).get("tracer_provider_built")
    processor = provider._active_span_processor._span_processors[0]._batch_processor
    assert (
        processor._max_queue_size,
        processor._max_export_batch_size,
        processor._schedule_delay_millis,
        processor._export_timeout_millis,
    ) == (queue, batch, delay, timeout)


@when("the OTLP exporters are created from the config")
def step_when_exporters(context):
    sc = _ctx(context)
    otel = sc.get("otel_cfg")
    exporters = [
        OtelUtils._create_span_exporter(otel),
        OtelUtils._create_metric_exporter(otel),
        OtelUtils._create_otlp_log_exporter(otel),
    ]
    context.add_cleanup(lambda: [exporter.shutdown() for exporter in exporters])
    sc.store("exporters", exporters)


def _compression_names(context):
    return [str(exporter._compression).lower() for exporter in _ctx(context).get("exporters")]


@then("every OTLP exporter compresses with gzip")
def step_then_gzip(context):
    names = _compression_names(context)
    assert all(name.endswith("gzip") or name == "2" for name in names), names


@then("no OTLP exporter compresses")
def step_then_no_compression(context):
    names = _compression_names(context)
    assert all("nocompression" in name or name == "0" for name in names), names


@when("the resource is created from the config")
def step_when_resource(context):
    sc = _ctx(context)
    sc.store("resource", OtelUtils._create_resource(sc.get("otel_cfg")))


@then('the resource attribute "{name}" is "{value}"')
def step_then_resource_attribute(context, name, value):
    attributes = _ctx(context).get("resource").attributes
    assert attributes.get(name) == value, attributes


@then('the resource has the attributes "{names}"')
def step_then_resource_has(context, names):
    attributes = _ctx(context).get("resource").attributes
    missing = [name for name in (n.strip() for n in names.split(",")) if name not in attributes]
    assert not missing, f"missing {missing} in {sorted(attributes)}"


@then('the resource has no attribute "{name}"')
def step_then_resource_lacks(context, name):
    assert name not in _ctx(context).get("resource").attributes


@when('the propagator is created for "{names}"')
def step_when_propagator(context, names):
    _ctx(context).store("propagator", create_propagator([n for n in names.split(",") if n]))


@then('the propagator carries the fields "{fields}"')
def step_then_propagator_fields(context, fields):
    expected = set() if fields == "(none)" else set(fields.split(","))
    assert set(_ctx(context).get("propagator").fields) == expected, _ctx(context).get("propagator").fields


@given("the b3 propagator package is not installed")
def step_given_no_b3(context):
    patcher = patch.dict(sys.modules, {"opentelemetry.propagators.b3": None})
    patcher.start()
    context.add_cleanup(patcher.stop)


@then('creating the propagator for "{names}" fails with "{reason}"')
def step_then_propagator_fails(context, names, reason):
    try:
        create_propagator(names.split(","))
    except ConfigurationError as error:
        assert error.additional_data["reason"] == reason, error.additional_data
        assert "archipy[otel]" in error.additional_data["hint"]
    else:
        raise AssertionError("the propagator was created")


@given("the standard OTEL environment:")
def step_given_standard_env(context):
    _ctx(context).store("standard_env", {row["name"]: row["value"] for row in context.table})


@when("the standard environment is applied")
def step_when_apply_env(context):
    sc = _ctx(context)
    sc.store("effective_otel", apply_standard_env(sc.get("otel_cfg"), sc.get("standard_env")))


@then('the effective setting "{name}" is {value}')
def step_then_effective_setting(context, name, value):
    actual = getattr(_ctx(context).get("effective_otel"), name)
    expected = json.loads(value)
    assert (str(actual) if isinstance(expected, str) else actual) == expected, f"{name}: {actual!r}"


@then("the OpenTelemetry SDK is {state}")
def step_then_sdk_state(context, state):
    sc = _ctx(context)
    assert sdk_disabled(sc.get("otel_cfg"), sc.get("standard_env")) == (state == "disabled")


@then("the duration histogram buckets of the global config are {buckets}")
def step_then_duration_buckets(context, buckets):
    expected = tuple(float(bucket) for bucket in buckets.split(","))
    otel = BaseConfig.global_config().OTEL
    original = otel.METRICS_DURATION_BUCKETS_S
    context.add_cleanup(setattr, otel, "METRICS_DURATION_BUCKETS_S", original)
    otel.METRICS_DURATION_BUCKETS_S = list(_ctx(context).get("otel_cfg").METRICS_DURATION_BUCKETS_S)
    assert OtelUtils.duration_histogram_buckets() == expected


# Propagation through the real server integrations


@given('the global propagator is set to "{names}"')
def step_given_global_propagator(context, names):
    from opentelemetry.propagate import get_global_textmap, set_global_textmap

    previous = get_global_textmap()
    context.add_cleanup(set_global_textmap, previous)
    set_global_textmap(create_propagator(names.split(",")))


@given("a tracer provider that keeps its spans in memory")
def step_given_memory_tracer_provider(context):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    context.add_cleanup(provider.shutdown)
    sc = _ctx(context)
    sc.store("memory_exporter", exporter)
    sc.store("memory_provider", provider)


@when('a FastAPI route with native telemetry receives the header {header} "{value}"')
def step_when_fastapi_receives_header(context, header, value):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    sc = _ctx(context)
    app = FastAPI(
        telemetry={
            "tracing": True,
            "metrics": False,
            "logs": False,
            "tracer_provider": sc.get("memory_provider"),
            "auto_configure": False,
        },
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    with TestClient(app) as client:
        client.get("/ping", headers={header: value})


@then('the server span continues trace "{trace_id}" from parent span "{span_id}"')
def step_then_server_span_continues(context, trace_id, span_id):
    from opentelemetry.trace import SpanKind

    spans = _ctx(context).get("memory_exporter").get_finished_spans()
    servers = [span for span in spans if span.kind == SpanKind.SERVER]
    assert servers, [span.name for span in spans]
    assert format(servers[0].context.trace_id, "032x") == trace_id
    assert servers[0].parent is not None and format(servers[0].parent.span_id, "016x") == span_id


@when("a gRPC client with the OpenTelemetry interceptor calls a server with the OpenTelemetry interceptor")
def step_when_grpc_roundtrip(context):
    from concurrent import futures

    import grpc
    from opentelemetry.instrumentation.grpc import intercept_channel, server_interceptor

    sc = _ctx(context)
    provider = sc.get("memory_provider")
    seen: dict[str, str] = {}

    def handle(_request, rpc_context):
        seen.update({key: value for key, value in rpc_context.invocation_metadata()})
        return b"ok"

    handler = grpc.unary_unary_rpc_method_handler(
        handle,
        request_deserializer=lambda payload: payload,
        response_serializer=lambda payload: payload,
    )
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=2),
        interceptors=[server_interceptor(tracer_provider=provider)],
    )
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler("otel.Probe", {"Call": handler}),))
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    context.add_cleanup(server.stop, 0)

    original = OtelUtils._tracer_provider
    OtelUtils._tracer_provider = provider
    context.add_cleanup(setattr, OtelUtils, "_tracer_provider", original)
    channel = intercept_channel(grpc.insecure_channel(f"127.0.0.1:{port}"), *OtelUtils.grpc_client_interceptors())
    context.add_cleanup(channel.close)
    with provider.get_tracer("probe").start_as_current_span("client-root") as root:
        channel.unary_unary("/otel.Probe/Call")(b"x")
        sc.store("client_trace_id", format(root.get_span_context().trace_id, "032x"))
    sc.store("received_metadata", seen)


@then('the gRPC server received the header "{present}" and not "{absent}"')
def step_then_grpc_headers(context, present, absent):
    metadata = _ctx(context).get("received_metadata")
    assert present in metadata and absent not in metadata, sorted(metadata)


@then("the gRPC server span belongs to the trace of the client span")
def step_then_grpc_trace(context):
    from opentelemetry.trace import SpanKind

    servers = [
        span for span in _ctx(context).get("memory_exporter").get_finished_spans() if span.kind == SpanKind.SERVER
    ]
    assert servers
    assert format(servers[0].context.trace_id, "032x") == _ctx(context).get("client_trace_id")


@when("an async gRPC client with the OpenTelemetry interceptor calls an async server with the OpenTelemetry interceptor")
async def step_when_grpc_aio_roundtrip(context):
    import grpc
    import grpc.aio
    from opentelemetry.instrumentation.grpc import aio_server_interceptor

    sc = _ctx(context)
    provider = sc.get("memory_provider")
    seen: dict[str, str] = {}

    async def handle(_request, rpc_context):
        seen.update({key: value for key, value in rpc_context.invocation_metadata()})
        return b"ok"

    handler = grpc.unary_unary_rpc_method_handler(
        handle,
        request_deserializer=lambda payload: payload,
        response_serializer=lambda payload: payload,
    )
    server = grpc.aio.server(interceptors=[aio_server_interceptor(tracer_provider=provider)])
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler("otel.Probe", {"Call": handler}),))
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()

    original = OtelUtils._tracer_provider
    OtelUtils._tracer_provider = provider
    try:
        async with grpc.aio.insecure_channel(
            f"127.0.0.1:{port}",
            interceptors=OtelUtils.async_grpc_client_interceptors(),
        ) as channel:
            with provider.get_tracer("probe").start_as_current_span("client-root") as root:
                await channel.unary_unary("/otel.Probe/Call")(b"x")
                sc.store("client_trace_id", format(root.get_span_context().trace_id, "032x"))
    finally:
        OtelUtils._tracer_provider = original
        await server.stop(0)
    sc.store("received_metadata", seen)
