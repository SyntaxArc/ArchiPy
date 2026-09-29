from concurrent.futures import ThreadPoolExecutor

import grpc
from behave import given, then, when
from opentelemetry.instrumentation.grpc import aio_server_interceptor, server_interceptor
from opentelemetry.sdk.trace import TracerProvider

from archipy.helpers.interceptors.grpc.exception.server_interceptor import (
    AsyncGrpcServerExceptionInterceptor,
    GrpcServerExceptionInterceptor,
)
from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
    AsyncGrpcServerOtelMetricsInterceptor,
    GrpcServerOtelMetricsInterceptor,
)
from archipy.models.errors import InvalidArgumentError
from features.test_helpers import get_current_scenario_context

_SERVICE = "archipy.test.Streaming"


async def _count(request: bytes, _context):
    """Server-streaming handler yielding ``request`` messages."""
    for index in range(int(request)):
        yield str(index).encode()


async def _count_then_fail(request: bytes, _context):
    """Server-streaming handler that raises after yielding ``request`` messages."""
    for index in range(int(request)):
        yield str(index).encode()
    raise InvalidArgumentError(argument_name="stream")


async def _count_then_crash(request: bytes, _context):
    """Server-streaming handler that raises an unexpected error after ``request`` messages."""
    for index in range(int(request)):
        yield str(index).encode()
    raise ValueError("boom")


async def _write_count(request: bytes, context) -> None:
    """Coroutine-style streaming handler: pushes responses through ``context.write``."""
    for index in range(int(request)):
        await context.write(str(index).encode())


async def _write_then_fail(request: bytes, context) -> None:
    """Coroutine-style streaming handler that raises after ``request`` writes."""
    await _write_count(request, context)
    raise InvalidArgumentError(argument_name="stream")


async def _echo(request_iterator, _context):
    """Bidirectional handler echoing each request."""
    async for message in request_iterator:
        yield message


async def _sum(request_iterator, _context) -> bytes:
    """Client-streaming handler returning the sum of all request messages."""
    total = 0
    async for message in request_iterator:
        total += int(message)
    return str(total).encode()


async def _ping(_request: bytes, _context) -> bytes:
    """Unary handler."""
    return b"pong"


def _sync_count(request: bytes, _context):
    yield from (str(index).encode() for index in range(int(request)))


def _sync_count_then_fail(request: bytes, _context):
    yield from (str(index).encode() for index in range(int(request)))
    raise InvalidArgumentError(argument_name="stream")


def _sync_count_then_crash(request: bytes, _context):
    yield from (str(index).encode() for index in range(int(request)))
    raise ValueError("boom")


class _FailingIterator:
    """A plain (non-generator) response iterator that raises after ``limit`` messages."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._index = 0

    def __iter__(self) -> "_FailingIterator":
        return self

    def __next__(self) -> bytes:
        if self._index >= self._limit:
            raise InvalidArgumentError(argument_name="stream")
        self._index += 1
        return str(self._index - 1).encode()


def _sync_iter_count(request: bytes, _context):
    return iter([str(index).encode() for index in range(int(request))])


def _sync_iter_count_then_fail(request: bytes, _context) -> _FailingIterator:
    return _FailingIterator(int(request))


def _sync_echo(request_iterator, _context):
    yield from request_iterator


def _sync_sum(request_iterator, _context) -> bytes:
    return str(sum(int(message) for message in request_iterator)).encode()


def _sync_ping(_request: bytes, _context) -> bytes:
    return b"pong"


def _build_sync_interceptors(stack: str) -> list:
    if stack == "exception":
        return [GrpcServerExceptionInterceptor()]
    if stack == "metrics":
        return [GrpcServerOtelMetricsInterceptor()]
    if stack == "full":
        return [
            server_interceptor(tracer_provider=TracerProvider()),
            GrpcServerOtelMetricsInterceptor(),
            GrpcServerExceptionInterceptor(),
        ]
    raise ValueError(f"Unsupported interceptor stack: {stack!r}")


def _build_interceptors(stack: str) -> list:
    if stack == "exception":
        return [AsyncGrpcServerExceptionInterceptor()]
    if stack == "metrics":
        return [AsyncGrpcServerOtelMetricsInterceptor()]
    if stack == "full":
        return [
            aio_server_interceptor(tracer_provider=TracerProvider()),
            AsyncGrpcServerOtelMetricsInterceptor(),
            AsyncGrpcServerExceptionInterceptor(),
        ]
    raise ValueError(f"Unsupported interceptor stack: {stack!r}")


async def _with_server(stack: str, call):
    """Start an aio server with the stack, run ``call(channel)``, then stop the server."""
    server = grpc.aio.server(interceptors=_build_interceptors(stack))
    handlers = {
        "Count": grpc.unary_stream_rpc_method_handler(_count),
        "CountThenFail": grpc.unary_stream_rpc_method_handler(_count_then_fail),
        "CountThenCrash": grpc.unary_stream_rpc_method_handler(_count_then_crash),
        "WriteCount": grpc.unary_stream_rpc_method_handler(_write_count),
        "WriteThenFail": grpc.unary_stream_rpc_method_handler(_write_then_fail),
        "Echo": grpc.stream_stream_rpc_method_handler(_echo),
        "Sum": grpc.stream_unary_rpc_method_handler(_sum),
        "Ping": grpc.unary_unary_rpc_method_handler(_ping),
    }
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler(_SERVICE, handlers),))
    port = server.add_insecure_port("127.0.0.1:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
            return await call(channel)
    finally:
        await server.stop(None)


def _with_sync_server(stack: str, call):
    """Start a sync server with the stack, run ``call(channel)``, then stop the server."""
    server = grpc.server(ThreadPoolExecutor(max_workers=4), interceptors=_build_sync_interceptors(stack))
    handlers = {
        "Count": grpc.unary_stream_rpc_method_handler(_sync_count),
        "CountThenFail": grpc.unary_stream_rpc_method_handler(_sync_count_then_fail),
        "CountThenCrash": grpc.unary_stream_rpc_method_handler(_sync_count_then_crash),
        "IterCount": grpc.unary_stream_rpc_method_handler(_sync_iter_count),
        "IterCountThenFail": grpc.unary_stream_rpc_method_handler(_sync_iter_count_then_fail),
        "Echo": grpc.stream_stream_rpc_method_handler(_sync_echo),
        "Sum": grpc.stream_unary_rpc_method_handler(_sync_sum),
        "Ping": grpc.unary_unary_rpc_method_handler(_sync_ping),
    }
    server.add_generic_rpc_handlers((grpc.method_handlers_generic_handler(_SERVICE, handlers),))
    port = server.add_insecure_port("127.0.0.1:0")
    server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            return call(channel)
    finally:
        server.stop(None).wait()


def _read_sync_stream(call) -> tuple[list[str], str]:
    """Drain a sync streaming call, returning messages and final status name."""
    messages: list[str] = []
    try:
        messages.extend(message.decode() for message in call)
    except grpc.RpcError as error:
        return messages, error.code().name
    return messages, call.code().name


async def _run(context, method: str, make_input):
    """Run one RPC against a server of the scenario's mode/stack; return the raw result."""
    scenario_context = get_current_scenario_context(context)
    stack = scenario_context.get("grpc_stream_stack")
    is_sync = scenario_context.get("grpc_stream_mode") == "sync"
    is_unary = method in {"Ping", "Sum"}  # single response message
    kind = {"Ping": "unary_unary", "Sum": "stream_unary", "Echo": "stream_stream"}.get(method, "unary_stream")

    if is_sync:

        def sync_call(channel):
            rpc = getattr(channel, kind)(f"/{_SERVICE}/{method}")
            return rpc(make_input()) if is_unary else _read_sync_stream(rpc(make_input()))

        return _with_sync_server(stack, sync_call)

    async def async_call(channel):
        rpc = getattr(channel, kind)(f"/{_SERVICE}/{method}")
        return await rpc(make_input()) if is_unary else await _read_stream(rpc(make_input()))

    return await _with_server(stack, async_call)


async def _read_stream(call) -> tuple[list[str], str]:
    """Drain a streaming call, returning messages and final status name."""
    messages: list[str] = []
    try:
        async for message in call:
            messages.append(message.decode())
    except grpc.aio.AioRpcError as error:
        return messages, error.code().name
    return messages, (await call.code()).name


def _store_stream_result(context, result: tuple[list[str], str]) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("grpc_stream_messages", result[0])
    scenario_context.store("grpc_stream_status", result[1])


@given("a {mode} gRPC server using the {stack} interceptor stack")
def step_given_grpc_server_stack(context, mode, stack):
    assert mode in {"sync", "async"}, f"Unsupported mode {mode!r}"
    (_build_sync_interceptors if mode == "sync" else _build_interceptors)(stack)  # validate early
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("grpc_stream_mode", mode)
    scenario_context.store("grpc_stream_stack", stack)


@when("a server-streaming RPC is invoked requesting {count:d} messages")
async def step_when_server_streaming(context, count):
    _store_stream_result(context, await _run(context, "Count", lambda: str(count).encode()))


@when("a server-streaming RPC returning a plain iterator is invoked requesting {count:d} messages")
async def step_when_plain_iterator_streaming(context, count):
    _store_stream_result(context, await _run(context, "IterCount", lambda: str(count).encode()))


@when("a server-streaming RPC returning a plain iterator is invoked that fails after {count:d} message")
async def step_when_plain_iterator_streaming_fails(context, count):
    _store_stream_result(context, await _run(context, "IterCountThenFail", lambda: str(count).encode()))


@when("a coroutine-style streaming RPC is invoked requesting {count:d} messages")
async def step_when_coroutine_streaming(context, count):
    _store_stream_result(context, await _run(context, "WriteCount", lambda: str(count).encode()))


@when("a coroutine-style streaming RPC is invoked that fails after {count:d} message")
async def step_when_coroutine_streaming_fails(context, count):
    _store_stream_result(context, await _run(context, "WriteThenFail", lambda: str(count).encode()))


@when("a server-streaming RPC is invoked that crashes after {count:d} message")
async def step_when_server_streaming_crashes(context, count):
    _store_stream_result(context, await _run(context, "CountThenCrash", lambda: str(count).encode()))


@when("a server-streaming RPC is invoked that fails after {count:d} message")
async def step_when_server_streaming_fails(context, count):
    _store_stream_result(context, await _run(context, "CountThenFail", lambda: str(count).encode()))


@when('a bidirectional RPC is invoked sending "{payload}"')
async def step_when_bidirectional(context, payload):
    items = [item.encode() for item in payload.split(",")]
    is_sync = get_current_scenario_context(context).get("grpc_stream_mode") == "sync"

    async def async_requests():
        for item in items:
            yield item

    _store_stream_result(context, await _run(context, "Echo", (lambda: iter(items)) if is_sync else async_requests))


@when('a client-streaming RPC is invoked sending "{payload}"')
async def step_when_client_streaming(context, payload):
    items = [item.encode() for item in payload.split(",")]
    is_sync = get_current_scenario_context(context).get("grpc_stream_mode") == "sync"

    async def async_requests():
        for item in items:
            yield item

    response = await _run(context, "Sum", (lambda: iter(items)) if is_sync else async_requests)
    get_current_scenario_context(context).store("grpc_unary_response", response.decode())


@when("a unary RPC is invoked")
async def step_when_unary(context):
    response = await _run(context, "Ping", lambda: b"")
    get_current_scenario_context(context).store("grpc_unary_response", response.decode())


@then('the gRPC stream should deliver messages "{expected}"')
def step_then_stream_messages(context, expected):
    actual = get_current_scenario_context(context).get("grpc_stream_messages")
    assert actual == expected.split(","), f"Expected messages {expected.split(',')!r}, got {actual!r}"


@then("the gRPC stream should finish with status {status}")
def step_then_stream_status(context, status):
    actual = get_current_scenario_context(context).get("grpc_stream_status")
    assert actual == status, f"Expected status {status}, got {actual}"


@then('the gRPC unary response should be "{expected}"')
def step_then_unary_response(context, expected):
    actual = get_current_scenario_context(context).get("grpc_unary_response")
    assert actual == expected, f"Expected unary response {expected!r}, got {actual!r}"
