"""Steps that check the OpenTelemetry spans and metrics emitted by Pydantic AI agents.

Agents run on Pydantic AI's offline ``TestModel`` and ``FunctionModel``, so no model provider is involved; the
spans and metrics are exported to the real collector container and read back from it.
"""

import asyncio
import time

from behave import given, then, when
from features.steps.otel_steps import _setup_collector_otel
from features.test_helpers import get_current_scenario_context
from features.test_helpers_otel import CollectorTelemetry, reset_otel_for_testing
from opentelemetry import trace
from opentelemetry.trace import StatusCode
from pydantic_ai import Agent, ModelResponse, RunContext, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.instrumented import InstrumentationSettings
from pydantic_ai.models.test import TestModel

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.otel_utils import OtelUtils

SPAN_TIMEOUT_SECONDS = 8.0
# The prompt the steps send and the text their tool returns.
_PROMPT_TEXT = "hello"
_TOOL_OUTPUT_TEXT = "pong"


def _telemetry(context) -> CollectorTelemetry:
    return get_current_scenario_context(context).get("pydantic_ai_telemetry")


def _reset_pydantic_ai() -> None:
    """Forget the instrumentation an earlier scenario left on every agent of this process."""
    Agent.instrument_all(False)


def _reset_pydantic_ai_config() -> None:
    pydantic_ai = BaseConfig.global_config().PYDANTIC_AI
    pydantic_ai.INSTRUMENTATION_ENABLED = True
    pydantic_ai.INSTRUMENTATION_INCLUDE_CONTENT = True
    pydantic_ai.INSTRUMENTATION_INCLUDE_BINARY_CONTENT = True


def _start_scenario_state(context) -> None:
    """Reset Pydantic AI state once per scenario, whichever step runs first."""
    scenario_context = get_current_scenario_context(context)
    if scenario_context.get("pydantic_ai_state_reset"):
        return
    scenario_context.store("pydantic_ai_state_reset", True)
    _reset_pydantic_ai()
    _reset_pydantic_ai_config()
    context.add_cleanup(_reset_pydantic_ai)
    context.add_cleanup(_reset_pydantic_ai_config)


def _wait_for_spans(context, predicate, description: str) -> list:
    telemetry = _telemetry(context)
    telemetry.flush()
    spans = telemetry.wait_for(
        lambda: [span for span in telemetry.spans() if predicate(span)],
        timeout=SPAN_TIMEOUT_SECONDS,
    )
    assert spans, (
        f"No span {description}. Exported spans: {[(span.name, span.status.status_code) for span in telemetry.spans()]}"
    )
    return spans


@given("Pydantic AI telemetry is exported to the collector")
@when("Pydantic AI telemetry is exported to the collector")
def step_pydantic_ai_telemetry(context):
    """Start OpenTelemetry against the collector; ArchiPy instruments Pydantic AI on initialization."""
    scenario_context = get_current_scenario_context(context)
    _start_scenario_state(context)
    telemetry = _setup_collector_otel(context, traces=True, metrics=True)
    scenario_context.get("test_containers").get_container("otel-collector").mark()
    scenario_context.store("pydantic_ai_telemetry", telemetry)


@given("the Pydantic AI config does not include Pydantic AI content")
def step_config_no_content(context):
    _start_scenario_state(context)
    config = BaseConfig.global_config()
    config.PYDANTIC_AI.INSTRUMENTATION_INCLUDE_CONTENT = False
    config.PYDANTIC_AI.INSTRUMENTATION_INCLUDE_BINARY_CONTENT = False


@given("the Pydantic AI config turns Pydantic AI instrumentation off")
def step_config_instrumentation_off(context):
    _start_scenario_state(context)
    BaseConfig.global_config().PYDANTIC_AI.INSTRUMENTATION_ENABLED = False


@given("OpenTelemetry has not been initialized")
def step_otel_not_initialized(context):
    _start_scenario_state(context)
    reset_otel_for_testing()


@given("the application instruments all Pydantic AI agents itself")
def step_application_instruments(context):
    _start_scenario_state(context)
    settings = InstrumentationSettings(include_content=True)
    Agent.instrument_all(settings)
    get_current_scenario_context(context).store("app_pydantic_ai_settings", settings)


def _tool_calling_model(tool_name: str) -> FunctionModel:
    """Return a model that calls ``tool_name`` once and then answers."""

    def respond(messages, info: AgentInfo) -> ModelResponse:
        from pydantic_ai import ModelRequest, ToolReturnPart

        returned = any(
            isinstance(part, ToolReturnPart) for message in messages if isinstance(message, ModelRequest) for part in message.parts
        )
        if returned:
            return ModelResponse(parts=[_text_part("done")])
        return ModelResponse(parts=[ToolCallPart(tool_name, {})])

    return FunctionModel(respond)


def _text_part(text: str):
    from pydantic_ai import TextPart

    return TextPart(text)


@when('I run a Pydantic AI agent named "{name}" that calls a tool named "{tool}"')
def step_run_agent(context, name, tool):
    agent = Agent(TestModel(), name=name)

    @agent.tool_plain(name=tool)
    def _tool() -> str:
        return "pong"

    agent.run_sync("hello")


@when('I run a Pydantic AI agent named "{name}" whose tool "{tool}" raises an error')
def step_run_failing_agent(context, name, tool):
    agent = Agent(_tool_calling_model(tool), name=name)

    @agent.tool_plain(name=tool, retries=0)
    def _tool() -> str:
        raise RuntimeError("tool failed")

    try:
        agent.run_sync("hello")
    except RuntimeError:
        pass


@then('the collector should have the Pydantic AI span "{name}"')
def step_span_exists(context, name):
    _wait_for_spans(context, lambda span: span.name == name, f"named {name!r}")


@then('the collector should have the Pydantic AI span "{name}" with error status')
def step_span_error(context, name):
    _wait_for_spans(
        context,
        lambda span: span.name == name and span.status.status_code == StatusCode.ERROR,
        f"named {name!r} with error status",
    )


@then("the Pydantic AI model request span should be a child of the agent run span")
def step_span_parent(context):
    spans = _telemetry(context).spans()
    run = next(span for span in spans if span.name.startswith("invoke_agent"))
    chats = [span for span in spans if span.name.startswith("chat")]
    assert chats, "no model request span exported"
    for chat in chats:
        assert chat.context.trace_id == run.context.trace_id, "model request is in another trace"
        assert chat.parent is not None and chat.parent.span_id == run.context.span_id, (
            "model request is not a child of the agent run"
        )


@then('the collector should have the Pydantic AI metric "{name}"')
def step_metric_exists(context, name):
    telemetry = _telemetry(context)
    telemetry.flush()
    metrics = telemetry.wait_for(telemetry.metrics, timeout=SPAN_TIMEOUT_SECONDS)
    assert name in metrics, f"metric {name!r} not exported; got {sorted(metrics)}"
    assert metrics[name].data.data_points, f"metric {name!r} has no data points"


@then("the application's Pydantic AI instrumentation should still be installed")
def step_application_settings_kept(context):
    expected = get_current_scenario_context(context).get("app_pydantic_ai_settings")
    assert Agent._instrument_default is expected, "ArchiPy replaced the application's instrumentation settings"
    assert "pydantic_ai" in OtelUtils._instrumented_libraries


def _content_leaks(context) -> list[tuple[str, str]]:
    _wait_for_spans(context, lambda span: span.name.startswith("chat"), "for the model request")
    return [
        (span.name, key)
        for span in _telemetry(context).spans()
        for key, value in span.attributes.items()
        if any(text in str(value) for text in (_PROMPT_TEXT, _TOOL_OUTPUT_TEXT))
    ]


@then("no exported Pydantic AI span should carry the prompt or tool content")
def step_no_content(context):
    leaked = _content_leaks(context)
    assert not leaked, f"content exported in span attributes: {leaked}"


@then("an exported Pydantic AI span should carry the prompt and tool content")
def step_has_content(context):
    assert _content_leaks(context), "no span attribute carries the prompt or tool output"


def _flushed_spans(context) -> list:
    """Return the exported spans once the providers are flushed and the agent runs have arrived."""
    telemetry = _telemetry(context)
    telemetry.flush()
    telemetry.wait_for(lambda: any(span.name.startswith("invoke_agent") for span in telemetry.spans()))
    telemetry.flush()
    return telemetry.spans()


def _run_span(spans, agent_name):
    runs = [span for span in spans if span.name == f"invoke_agent {agent_name}"]
    assert len(runs) == 1, f"expected one run span of {agent_name!r}, got {len(runs)}"
    return runs[0]


@when('I run a Pydantic AI agent named "{parent}" whose tool "{tool}" runs the agent "{child}"')
def step_run_delegating_agent(context, parent, tool, child):
    child_agent = Agent(TestModel(), name=child)
    parent_agent = Agent(_tool_calling_model(tool), name=parent)

    @parent_agent.tool(name=tool)
    async def _delegate(ctx: RunContext[None]) -> str:
        result = await child_agent.run("delegated", usage=ctx.usage)
        return result.output

    parent_agent.run_sync("hello")


@when('I stream the response of a Pydantic AI agent named "{name}"')
def step_stream_agent(context, name):
    async def stream() -> None:
        async with Agent(TestModel(), name=name).run_stream("hello") as response:
            async for _ in response.stream_text():
                pass

    asyncio.run(stream())


@when("I run {count:d} Pydantic AI agents at the same time")
def step_run_concurrent_agents(context, count):
    async def run_all() -> None:
        agents = [Agent(TestModel(), name=f"parallel-bot-{index}") for index in range(count)]
        await asyncio.gather(*(agent.run("hello") for agent in agents))

    asyncio.run(run_all())


@when('I run two Pydantic AI agents one after another inside a span named "{name}"')
def step_run_agents_in_request(context, name):
    with trace.get_tracer("archipy.bdd").start_as_current_span(name):
        Agent(TestModel(), name="first-bot").run_sync("hello")
        Agent(TestModel(), name="second-bot").run_sync("hello")


@then('the Pydantic AI agent run "{child}" should be a child of the tool call "{tool}"')
def step_child_run_under_tool(context, child, tool):
    spans = _flushed_spans(context)
    tool_span = next(span for span in spans if span.name == f"execute_tool {tool}")
    child_run = _run_span(spans, child)
    assert child_run.parent is not None and child_run.parent.span_id == tool_span.context.span_id, (
        f"agent run {child!r} is not a child of the tool call {tool!r}"
    )


@then('the Pydantic AI agent runs "{first}" and "{second}" should share one trace')
def step_runs_share_trace(context, first, second):
    spans = _flushed_spans(context)
    assert _run_span(spans, first).context.trace_id == _run_span(spans, second).context.trace_id


_AGGREGATED_INPUT_TOKENS = "gen_ai.aggregated_usage.input_tokens"


@then('the Pydantic AI agent run "{name}" should count only the input tokens of its own model requests')
def step_run_counts_own_requests(context, name):
    spans = _flushed_spans(context)
    run = _run_span(spans, name)
    own = [
        span.attributes["gen_ai.usage.input_tokens"]
        for span in spans
        if span.name.startswith("chat") and span.parent is not None and span.parent.span_id == run.context.span_id
    ]
    assert own, f"no model request span under the agent run {name!r}"
    assert run.attributes[_AGGREGATED_INPUT_TOKENS] == sum(own), (
        f"run counted {run.attributes[_AGGREGATED_INPUT_TOKENS]}, its own model requests used {sum(own)}"
    )


@then('the Pydantic AI agent run "{name}" should count its own input tokens')
def step_run_counts_tokens(context, name):
    run = _run_span(_flushed_spans(context), name)
    assert run.attributes.get(_AGGREGATED_INPUT_TOKENS, 0) > 0


@then("the collector should have {count:d} Pydantic AI agent run spans in {traces:d} different traces")
def step_concurrent_runs(context, count, traces):
    runs = _wait_for_spans(context, lambda span: span.name.startswith("invoke_agent parallel-bot-"), "of the agent runs")
    assert len(runs) == count, f"expected {count} agent run spans, got {len(runs)}"
    assert len({span.context.trace_id for span in runs}) == traces


@then("each Pydantic AI model request span should be a child of its own agent run")
def step_requests_under_own_run(context):
    spans = _flushed_spans(context)
    runs = {span.context.span_id: span for span in spans if span.name.startswith("invoke_agent parallel-bot-")}
    requests = [span for span in spans if span.name.startswith("chat")]
    assert requests, "no model request span exported"
    for request in requests:
        run = runs.get(request.parent.span_id if request.parent else None)
        assert run is not None, "model request is not under an agent run"
        assert run.context.trace_id == request.context.trace_id
        assert run.attributes["gen_ai.agent.name"] == request.attributes["gen_ai.agent.name"]


@then('every Pydantic AI agent run span should be a child of the span "{name}"')
def step_runs_under_request(context, name):
    spans = _wait_for_spans(context, lambda span: span.name == name, f"named {name!r}")
    request = spans[0]
    runs = [span for span in _flushed_spans(context) if span.name.startswith("invoke_agent")]
    assert len(runs) == 2, f"expected 2 agent run spans, got {len(runs)}"
    for run in runs:
        assert run.parent is not None and run.parent.span_id == request.context.span_id
        assert run.context.trace_id == request.context.trace_id


@given("Pydantic AI telemetry is exported to Elastic APM Server {route}")
def step_pydantic_ai_apm(context, route):
    """Start OpenTelemetry against Elastic APM Server and wait until it stores a span.

    Spans exported straight after APM Server's first start can be lost, so the scenario starts only once a warm-up
    span has been stored.
    """
    from features.steps.elastic_apm_steps import APM_POLL_TIMEOUT_SECONDS, apm_endpoint

    _start_scenario_state(context)
    scenario_context = get_current_scenario_context(context)
    _setup_collector_otel(
        context,
        traces=True,
        metrics=True,
        otlp_endpoint=apm_endpoint(scenario_context, route),
    )
    apm_server = scenario_context.get("test_containers").get_container("apm-server")
    service_name = BaseConfig.global_config().OTEL.SERVICE_NAME
    tracer = trace.get_tracer("archipy.bdd")
    deadline = time.monotonic() + APM_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        with tracer.start_as_current_span("pydantic-ai-apm-warmup"):
            pass
        OtelUtils.force_flush(timeout_millis=2000)
        stored = apm_server.events(service_name)
        if any(
            "pydantic-ai-apm-warmup" in (event.get("transaction", {}).get("name"), event.get("span", {}).get("name"))
            for event in stored
        ):
            return
        time.sleep(0.5)
    raise AssertionError(f"Elastic APM Server stored no warm-up span for {service_name}")



@when('I run a Pydantic AI agent named "{name}" inside a {transport} request')
async def step_run_agent_in_request(context, name, transport):
    import grpc
    from fastapi.testclient import TestClient
    from features.steps.otel_steps import _grpc_stub, _import_test_proto, _start_grpc_test_server

    from archipy.helpers.utils.app_utils import AppUtils

    config = BaseConfig.global_config()
    agent = Agent(TestModel(), name=name)
    if transport == "FastAPI":
        app = AppUtils.create_fastapi_app(config, configure_exception_handlers=False)

        @app.get("/agent")
        async def run_agent():
            result = await agent.run("hello")
            return {"output": result.output}

        with TestClient(app) as client:
            response = client.get("/agent")
        assert response.status_code == 200, response.text
        return

    pb2, pb2_grpc = _import_test_proto()
    if transport == "gRPC":

        class Servicer(pb2_grpc.TestServiceServicer):
            def TestMethod(self, request, context_):
                agent.run_sync("hello")
                return pb2.TestResponse(result="ok")

        server, port = _start_grpc_test_server(config, Servicer())
        stub, channel = _grpc_stub(port)
        try:
            assert stub.TestMethod(pb2.TestRequest(data="hi")).result == "ok"
        finally:
            channel.close()
            server.stop(None)
        return

    assert transport == "async gRPC", f"unknown transport {transport!r}"

    class AsyncServicer(pb2_grpc.TestServiceServicer):
        async def TestMethod(self, request, context_):
            await agent.run("hello")
            return pb2.TestResponse(result="ok")

    server = AppUtils.create_async_grpc_app(config)
    pb2_grpc.add_TestServiceServicer_to_server(AsyncServicer(), server)
    port = server.add_insecure_port("localhost:0")
    await server.start()
    channel = grpc.aio.insecure_channel(
        f"localhost:{port}",
        interceptors=OtelUtils.async_grpc_client_interceptors(),
    )
    try:
        result = await pb2_grpc.TestServiceStub(channel).TestMethod(pb2.TestRequest(data="hi"))
        assert result.result == "ok"
    finally:
        await channel.close()
        await server.stop(None)


@then('the Pydantic AI agent run "{name}" should descend from the span "{ancestor}"')
def step_run_descends_from_span(context, name, ancestor):
    spans = _flushed_spans(context)
    by_id = {span.context.span_id: span for span in spans}
    run = _run_span(spans, name)
    lineage = []
    current = by_id.get(run.parent.span_id) if run.parent is not None else None
    while current is not None:
        lineage.append(current)
        current = by_id.get(current.parent.span_id) if current.parent is not None else None
    assert any(span.name == ancestor for span in lineage), (
        f"agent run {name!r} does not descend from {ancestor!r}; its ancestors are {[span.name for span in lineage]}"
    )
    assert all(span.context.trace_id == run.context.trace_id for span in lineage)
