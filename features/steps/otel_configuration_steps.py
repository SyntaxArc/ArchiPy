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
    # With temporalio installed the builder returns a replay-safe wrapper around the SDK provider; these steps assert
    # on the SDK provider's sampler and span processor.
    sc.store("tracer_provider_built", getattr(provider, "_tracer_provider", provider))


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


# A FastAPI request that fans out to gRPC servers and HTTP services keeps one trace


@when('the FastAPI app that calls gRPC servers and an HTTP service is requested at "{path}" with the header {header} "{value}"')
async def step_when_fan_out_request(context, path, header, value):
    """Serve the fan-out app and its backends on this step's event loop, request it once, and tear everything down."""
    import asyncio
    from concurrent import futures

    import grpc
    import grpc.aio
    import httpx
    import httpx2
    from fastapi import FastAPI
    from opentelemetry.instrumentation.grpc import aio_server_interceptor, intercept_channel, server_interceptor
    from opentelemetry.instrumentation.httpx import HTTPX2ClientInstrumentor, HTTPXClientInstrumentor

    sc = _ctx(context)
    provider = sc.get("memory_provider")

    def handle(_request, _rpc_context):
        return b"ok"

    async def handle_async(_request, _rpc_context):
        return b"ok"

    def method(function):
        return grpc.unary_unary_rpc_method_handler(
            function,
            request_deserializer=lambda payload: payload,
            response_serializer=lambda payload: payload,
        )

    sync_server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=2),
        interceptors=[server_interceptor(tracer_provider=provider)],
    )
    sync_server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler("otel.Probe", {"Call": method(handle)}),))
    sync_port = sync_server.add_insecure_port("127.0.0.1:0")
    sync_server.start()

    aio_server = grpc.aio.server(interceptors=[aio_server_interceptor(tracer_provider=provider)])
    aio_server.add_generic_rpc_handlers(
        (grpc.method_handlers_generic_handler("otel.Probe", {"Call": method(handle_async)}),),
    )
    aio_port = aio_server.add_insecure_port("127.0.0.1:0")
    await aio_server.start()

    received_http: dict[str, str] = {}

    async def echo(reader, writer):
        head = await reader.readuntil(b"\r\n\r\n")
        for line in head.decode().split("\r\n")[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                received_http[key.strip().lower()] = value.strip()
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok")
        await writer.drain()
        writer.close()

    http_server = await asyncio.start_server(echo, "127.0.0.1", 0)
    http_port = http_server.sockets[0].getsockname()[1]

    original = OtelUtils._tracer_provider
    OtelUtils._tracer_provider = provider
    sync_channel = intercept_channel(
        grpc.insecure_channel(f"127.0.0.1:{sync_port}"),
        *OtelUtils.grpc_client_interceptors(),
    )

    async def call_aio() -> str:
        async with grpc.aio.insecure_channel(
            f"127.0.0.1:{aio_port}",
            interceptors=OtelUtils.async_grpc_client_interceptors(),
        ) as channel:
            return (await channel.unary_unary("/otel.Probe/Call")(b"x")).decode()

    app = FastAPI(
        telemetry={
            "tracing": True,
            "metrics": False,
            "logs": False,
            "tracer_provider": provider,
            "auto_configure": False,
        },
    )

    @app.get("/def-sync-client")
    def def_sync_client():
        return {"r": sync_channel.unary_unary("/otel.Probe/Call")(b"x").decode()}

    @app.get("/async-aio-client")
    async def async_aio_client():
        return {"r": await call_aio()}

    @app.get("/async-sync-client")
    async def async_sync_client():
        return {"r": sync_channel.unary_unary("/otel.Probe/Call")(b"x").decode()}

    @app.get("/def-aio-client")
    def def_aio_client():
        return {"r": asyncio.run(call_aio())}

    @app.get("/httpx")
    async def call_httpx():
        async with httpx.AsyncClient() as client:
            HTTPXClientInstrumentor.instrument_client(client, tracer_provider=provider)
            await client.get(f"http://127.0.0.1:{http_port}/probe")
        return {"r": "ok"}

    @app.get("/httpx2")
    async def call_httpx2():
        async with httpx2.AsyncClient() as client:
            HTTPX2ClientInstrumentor.instrument_client(client, tracer_provider=provider)
            await client.get(f"http://127.0.0.1:{http_port}/probe")
        return {"r": "ok"}

    try:
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://app") as client:
            response = await client.get(path, headers={header: value})
        assert response.status_code == 200, response.text
        sc.store("received_http", received_http)
    finally:
        OtelUtils._tracer_provider = original
        sync_channel.close()
        sync_server.stop(0)
        http_server.close()
        await aio_server.stop(0)


@then('every recorded span belongs to trace "{trace_id}"')
def step_then_one_trace(context, trace_id):
    spans = _ctx(context).get("memory_exporter").get_finished_spans()
    assert spans
    assert {format(span.context.trace_id, "032x") for span in spans} == {trace_id}, [span.name for span in spans]


@then("a gRPC server span was recorded")
def step_then_grpc_server_span(context):
    from opentelemetry.trace import SpanKind

    spans = _ctx(context).get("memory_exporter").get_finished_spans()
    assert [span for span in spans if span.kind == SpanKind.SERVER and "otel.Probe/Call" in span.name]


@then('the outbound HTTP request carried the header "{name}" and not "{absent}"')
def step_then_http_headers(context, name, absent):
    received = _ctx(context).get("received_http")
    assert name in received and absent not in received, sorted(received)


# Side effects of the defaults: validation, the bytes on the wire, and the size of a full batch


@then('the config setting "{name}" is {value:d}')
def step_then_config_setting(context, name, value):
    assert getattr(_ctx(context).get("otel_cfg"), name) == value


def _finished_spans(count: int, attributes: int, stack_trace_chars: int = 0):
    """Return finished spans whose attribute values are random, so compression ratios are realistic, not best case."""
    import random
    import string

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    generator = random.Random(1)  # noqa: S311 - reproducible test data, not security
    alphabet = string.ascii_lowercase + string.digits

    def text(length: int) -> str:
        return "".join(generator.choices(alphabet, k=length))

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("batch-probe")
    for index in range(count):
        with tracer.start_as_current_span(f"operation-{index % 7}") as span:
            for number in range(attributes):
                span.set_attribute(f"app.attribute.{number}", text(40))
            if stack_trace_chars:
                frames = ["  File \"/app/" + text(12) + ".py\", line " + str(generator.randint(1, 900)) for _ in range(stack_trace_chars // 40)]
                span.add_event("exception", {"exception.type": "ValueError", "exception.stacktrace": "\n".join(frames)})
    provider.shutdown()
    return exporter.get_finished_spans()


@when("the HTTP span exporter of the config sends one span to a local collector")
def step_when_http_export(context):
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    captured: dict[str, object] = {}

    class Collector(BaseHTTPRequestHandler):
        def do_POST(self):
            captured["headers"] = {key.lower(): value for key, value in self.headers.items()}
            captured["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    context.add_cleanup(server.server_close)
    context.add_cleanup(server.shutdown)

    sc = _ctx(context)
    otel = sc.get("otel_cfg").model_copy(update={"TRACES_ENDPOINT": f"http://127.0.0.1:{server.server_port}/v1/traces"})
    exporter = OtelUtils._create_span_exporter(otel)
    context.add_cleanup(exporter.shutdown)
    result = exporter.export(_finished_spans(1, 3))
    assert result.name == "SUCCESS", result
    sc.store("collector_capture", captured)


@then("the collector received a valid trace request {state}")
def step_then_collector_request(context, state):
    import gzip

    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    capture = _ctx(context).get("collector_capture")
    encoding = capture["headers"].get("content-encoding")
    body = capture["body"]
    if state == "gzip-encoded":
        assert encoding == "gzip", capture["headers"]
        body = gzip.decompress(body)
    else:
        assert encoding is None, capture["headers"]
    assert ExportTraceServiceRequest.FromString(body).resource_spans


@then(
    "a full default batch of spans with {attributes:d} attributes and a {stack_chars:d} character stack trace each "
    "encodes to under {mebibytes:d} MiB",
)
def step_then_batch_size(context, attributes, stack_chars, mebibytes):
    from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans

    otel = _ctx(context).get("otel_cfg")
    count = otel.SPAN_BATCH_MAX_EXPORT_BATCH_SIZE
    payload = encode_spans(_finished_spans(count, attributes, stack_chars)).SerializeToString()
    _ctx(context).store("full_batch_payload", payload)
    assert len(payload) < mebibytes * 1024 * 1024, f"{len(payload)} bytes for {count} spans"


@then("gzip makes that batch at least {ratio:f} times smaller")
def step_then_gzip_ratio(context, ratio):
    import gzip

    payload = _ctx(context).get("full_batch_payload")
    assert len(payload) / len(gzip.compress(payload)) >= ratio, (len(payload), len(gzip.compress(payload)))


# gRPC compression: the handler cannot see it, so count the bytes that cross a proxy in front of a real server


class _CountingProxy:
    """TCP proxy that forwards to a target port and counts the bytes the client sends."""

    def __init__(self, target_port: int) -> None:
        import socket
        import threading

        self._target_port = target_port
        self._lock = threading.Lock()
        self._sent = 0
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen()
        self.port = self._listener.getsockname()[1]
        self._sockets = [self._listener]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        import socket
        import threading

        while True:
            try:
                client, _ = self._listener.accept()
            except OSError:
                return
            upstream = socket.create_connection(("127.0.0.1", self._target_port))
            self._sockets.extend([client, upstream])
            threading.Thread(target=self._pump, args=(client, upstream, True), daemon=True).start()
            threading.Thread(target=self._pump, args=(upstream, client, False), daemon=True).start()

    def _pump(self, source, destination, counted: bool) -> None:
        try:
            while data := source.recv(65536):
                if counted:
                    with self._lock:
                        self._sent += len(data)
                destination.sendall(data)
        except OSError:
            return

    def reset(self) -> None:
        with self._lock:
            self._sent = 0

    @property
    def bytes_sent(self) -> int:
        with self._lock:
            return self._sent

    def close(self) -> None:
        for sock in self._sockets:
            try:
                sock.close()
            except OSError:
                continue


@given("a gRPC trace collector behind a byte-counting proxy")
def step_given_grpc_collector_proxy(context):
    from concurrent import futures

    import grpc

    def export(_request, _rpc_context):
        return b""

    handler = grpc.unary_unary_rpc_method_handler(
        export,
        request_deserializer=lambda payload: payload,
        response_serializer=lambda payload: payload,
    )
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    server.add_generic_rpc_handlers(
        (grpc.method_handlers_generic_handler("opentelemetry.proto.collector.trace.v1.TraceService", {"Export": handler}),),
    )
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    proxy = _CountingProxy(port)
    context.add_cleanup(server.stop, 0)
    context.add_cleanup(proxy.close)
    _ctx(context).store("collector_proxy", proxy)


@when('the gRPC span exporter of the config sends {count:d} spans through the proxy with compression "{compression}"')
def step_when_grpc_export(context, count, compression):
    sc = _ctx(context)
    proxy = sc.get("collector_proxy")
    otel = sc.get("otel_cfg").model_copy(
        update={
            "PROTOCOL": "grpc",
            "OTLP_COMPRESSION": compression,
            "TRACES_ENDPOINT": f"http://127.0.0.1:{proxy.port}",
        },
    )
    exporter = OtelUtils._create_span_exporter(otel)
    context.add_cleanup(exporter.shutdown)
    proxy.reset()
    result = exporter.export(_finished_spans(count, 25, 4000))
    assert result.name == "SUCCESS", result
    sent = sc.get("grpc_bytes_sent") or {}
    sent[compression] = proxy.bytes_sent
    sc.store("grpc_bytes_sent", sent)


@then("the gzip export sent less than {fraction:f} of the bytes of the uncompressed export")
def step_then_grpc_bytes(context, fraction):
    sent = _ctx(context).get("grpc_bytes_sent")
    assert sent["gzip"] < fraction * sent["none"], sent


# Runtimes: the object that owns the providers can be swapped, the process-wide state cannot


@given("a second OpenTelemetry runtime is in use with in-memory exporters")
def step_given_second_runtime(context):
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    from archipy.helpers.utils.otel_utils import OtelRuntime

    sc = _ctx(context)
    first = OtelUtils.runtime()
    sc.store("first_runtime", first)
    sc.store("first_tracer_provider", first._tracer_provider)
    second = OtelRuntime()
    previous = OtelUtils.set_runtime(second)
    context.add_cleanup(OtelUtils.set_runtime, previous)
    second.configure_for_testing(span_exporter=InMemorySpanExporter(), service_name="second-runtime")
    context.add_cleanup(second.reset_for_testing)
    sc.store("second_runtime", second)


@then("the facade delegates to the second runtime and its tracer provider is its own")
def step_then_second_runtime_owns(context):
    sc = _ctx(context)
    assert OtelUtils.runtime() is sc.get("second_runtime")
    provider = OtelUtils.tracer_provider()
    assert provider is not None
    assert provider is not sc.get("first_tracer_provider")
    assert provider is sc.get("second_runtime")._tracer_provider


@when("the first runtime is put back")
def step_when_first_runtime_back(context):
    OtelUtils.set_runtime(_ctx(context).get("first_runtime"))


@then("the facade delegates to the first runtime and its providers are untouched")
def step_then_first_runtime_back(context):
    sc = _ctx(context)
    assert OtelUtils.runtime() is sc.get("first_runtime")
    assert OtelUtils.tracer_provider() is sc.get("first_tracer_provider")


@then("both runtimes see the same process-wide OpenTelemetry state")
def step_then_shared_process_state(context):
    sc = _ctx(context)
    first, second = sc.get("first_runtime"), sc.get("second_runtime")
    original = first._globals_set
    context.add_cleanup(setattr, first, "_globals_set", original)
    first._globals_set = not original
    assert second._globals_set is (not original)
    assert first._instrumented_libraries is second._instrumented_libraries
    assert first._lock is second._lock
    assert first._shutdown_providers is second._shutdown_providers


@when('a private name "{name}" is set through the OtelUtils facade')
def step_when_facade_set_private(context, name):
    runtime = OtelUtils.runtime()
    original = getattr(runtime, name)
    context.add_cleanup(setattr, runtime, name, original)
    setattr(OtelUtils, name, not original)
    _ctx(context).store("facade_name", name)
    _ctx(context).store("facade_original", original)


@then("the default runtime holds the new value and no copy sits on the facade class")
def step_then_facade_forwarded(context):
    sc = _ctx(context)
    name = sc.get("facade_name")
    assert getattr(OtelUtils.runtime(), name) is (not sc.get("facade_original"))
    assert name not in vars(OtelUtils)
    assert getattr(OtelUtils, name) is (not sc.get("facade_original"))
