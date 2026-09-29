import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import httpx
import uvicorn
from behave import given, then, when
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils
from archipy.models.errors import InvalidArgumentError
from features.test_helpers import get_current_scenario_context

_ACK_TIMEOUT_SECONDS = 5.0


class _SseState:
    """Shared state between the SSE endpoints (server thread) and the reading client."""

    def __init__(self) -> None:
        self.first_event_acknowledged = threading.Event()
        self.first_event_arrived_early = False
        self.stream_closed = threading.Event()


def _sse_frame(index: int) -> str:
    return f"id: {index}\ndata: event-{index}\n\n"


def _build_sse_app(config: BaseConfig, state: _SseState) -> FastAPI:
    """Create an ArchiPy FastAPI app exposing SSE endpoints."""
    app = AppUtils.create_fastapi_app(config, configure_exception_handlers=True)

    async def events(count: int, *, gated: bool):
        try:
            for index in range(count):
                yield _sse_frame(index)
                if not gated:
                    await asyncio.sleep(0.02)
                elif index == 0:
                    # Blocks until the client confirms it already received event 0. A buffering
                    # middleware would hold event 0 back, so the wait would time out.
                    deadline = time.monotonic() + _ACK_TIMEOUT_SECONDS
                    while not state.first_event_acknowledged.is_set() and time.monotonic() < deadline:
                        await asyncio.sleep(0.02)
                    state.first_event_arrived_early = state.first_event_acknowledged.is_set()
        finally:
            state.stream_closed.set()

    async def failing_events():
        yield _sse_frame(0)
        await asyncio.sleep(0.05)
        raise RuntimeError("stream failed")

    @app.get("/events")
    async def stream_events(count: int = 3, gated: bool = True) -> StreamingResponse:
        return StreamingResponse(
            events(count, gated=gated),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    @app.get("/events-fail")
    async def stream_failing_events() -> StreamingResponse:
        return StreamingResponse(failing_events(), media_type="text/event-stream")

    @app.get("/events-invalid")
    async def stream_invalid_events() -> StreamingResponse:
        raise InvalidArgumentError(argument_name="topic")

    return app


def _reset_optional_middleware(config: BaseConfig) -> None:
    fastapi_config = config.FASTAPI
    fastapi_config.GZIP_MIDDLEWARE_IS_ENABLED = False
    fastapi_config.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = False
    fastapi_config.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS = []
    fastapi_config.HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED = False


def _store_app(context, *, gzip: bool = False, reset: bool = True, trusted_hosts: list[str] | None = None) -> None:
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    if reset:
        _reset_optional_middleware(config)
    config.FASTAPI.GZIP_MIDDLEWARE_IS_ENABLED = gzip
    if trusted_hosts:
        config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = True
        config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS = trusted_hosts
    state = _SseState()
    scenario_context.store("sse_state", state)
    scenario_context.store("sse_app", _build_sse_app(config, state))


@given("a FastAPI app with a server-sent events endpoint")
def step_given_sse_app(context):
    _store_app(context)


@given("a FastAPI app with GZip middleware enabled and a server-sent events endpoint")
def step_given_sse_app_gzip(context):
    _store_app(context, gzip=True)


@given("an instrumented FastAPI app with a server-sent events endpoint")
def step_given_sse_app_instrumented(context):
    _store_app(context, reset=False)


@given('a FastAPI app with TrustedHost middleware enabled for "{host}" and a server-sent events endpoint')
def step_given_sse_app_trusted_host(context, host):
    _store_app(context, trusted_hosts=[host])


@contextmanager
def _running_server(app: FastAPI):
    """Serve ``app`` with uvicorn on a free local port; yield the port."""
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started, "uvicorn server did not start"
    try:
        yield server.servers[0].sockets[0].getsockname()[1]
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _read_stream(
    port: int,
    path: str,
    state: _SseState,
    *,
    headers: dict[str, str] | None = None,
    disconnect_after: int | None = None,
) -> dict:
    """Stream ``path``, acking the first event; optionally disconnect after N events."""
    result: dict = {"events": [], "error": None, "disconnected": False}
    request_headers = {"Accept": "text/event-stream", **(headers or {})}
    try:
        with (
            httpx.Client(timeout=10) as client,
            client.stream("GET", f"http://127.0.0.1:{port}{path}", headers=request_headers) as response,
        ):
            result["status"] = response.status_code
            result["headers"] = dict(response.headers)
            result["content_type"] = response.headers.get("content-type", "")
            result["content_encoding"] = response.headers.get("content-encoding", "")
            try:
                for line in response.iter_lines():
                    if line.startswith("data: "):
                        result["events"].append(line.removeprefix("data: "))
                        state.first_event_acknowledged.set()
                        if disconnect_after is not None and len(result["events"]) >= disconnect_after:
                            result["disconnected"] = True
                            break
            except httpx.HTTPError as error:
                result["error"] = error
    finally:
        state.first_event_acknowledged.set()  # never leave the server waiting
    return result


def _read(context, path: str, **kwargs) -> None:
    scenario_context = get_current_scenario_context(context)
    state = scenario_context.get("sse_state")
    with _running_server(scenario_context.get("sse_app")) as port:
        result = _read_stream(port, path, state, **kwargs)
        if result["disconnected"]:
            # Must be observed while the server is still up, otherwise shutdown would close the stream itself.
            result["server_closed_stream"] = state.stream_closed.wait(_ACK_TIMEOUT_SECONDS)
    scenario_context.store("sse_result", result)


@when("the client reads {count:d} server-sent events")
def step_when_read_events(context, count):
    _read(context, f"/events?count={count}")


@when("the client reads {count:d} server-sent events from origin \"{origin}\"")
def step_when_read_events_with_origin(context, count, origin):
    _read(context, f"/events?count={count}", headers={"Origin": origin})


@when('the client reads {count:d} server-sent events with host "{host}"')
def step_when_read_events_with_host(context, count, host):
    _read(context, f"/events?count={count}", headers={"Host": host})


@when("the client reads a server-sent events stream that fails after the first event")
def step_when_read_failing_events(context):
    _read(context, "/events-fail")


@when("the client reads a server-sent events stream that is rejected before it starts")
def step_when_read_invalid_events(context):
    _read(context, "/events-invalid")


@when("the client reads {read:d} of an endless server-sent events stream and disconnects")
def step_when_read_and_disconnect(context, read):
    _read(context, "/events?count=100000&gated=false", disconnect_after=read)


@when("{clients:d} clients read {count:d} server-sent events concurrently")
def step_when_concurrent_clients(context, clients, count):
    scenario_context = get_current_scenario_context(context)
    state = scenario_context.get("sse_state")
    with (
        _running_server(scenario_context.get("sse_app")) as port,
        ThreadPoolExecutor(max_workers=clients) as pool,
    ):
        results = list(pool.map(lambda _: _read_stream(port, f"/events?count={count}&gated=false", state), range(clients)))
    scenario_context.store("sse_results", results)


@then('the client should have received the events "{expected}"')
def step_then_events_received(context, expected):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["events"] == expected.split(","), f"Expected {expected.split(',')!r}, got {result['events']!r}"


@then("the client should have received no events")
def step_then_no_events(context):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["events"] == [], f"Expected no events, got {result['events']!r}"


@then('every client should have received the events "{expected}"')
def step_then_every_client_events(context, expected):
    results = get_current_scenario_context(context).get("sse_results")
    for index, result in enumerate(results):
        assert result["events"] == expected.split(","), f"Client {index} got {result['events']!r}"


@then("the response should be an event stream")
def step_then_event_stream_headers(context):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["status"] == 200, f"Expected HTTP 200, got {result['status']}"
    assert result["content_type"].startswith("text/event-stream"), f"Unexpected content type {result['content_type']!r}"


@then("the event stream request should return status code {status:d}")
def step_then_sse_status(context, status):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["status"] == status, f"Expected HTTP {status}, got {result['status']}"


@then('the response should allow origin "{origin}"')
def step_then_allow_origin(context, origin):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["headers"].get("access-control-allow-origin") == origin, result["headers"]


@then("the response should not allow any origin")
def step_then_no_allow_origin(context):
    result = get_current_scenario_context(context).get("sse_result")
    assert "access-control-allow-origin" not in result["headers"], result["headers"]


@then("the first event should have arrived before the stream finished")
def step_then_first_event_early(context):
    state = get_current_scenario_context(context).get("sse_state")
    assert state.first_event_arrived_early, "Event 0 was buffered until the stream ended instead of being flushed"


@then("the server should stop producing events")
def step_then_server_stops(context):
    result = get_current_scenario_context(context).get("sse_result")
    assert result["server_closed_stream"], "Server kept streaming after the client disconnected"


@then("the response should not be compressed")
def step_then_not_compressed(context):
    result = get_current_scenario_context(context).get("sse_result")
    assert not result["content_encoding"], f"Unexpected content-encoding {result['content_encoding']!r}"
