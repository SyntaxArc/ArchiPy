---
title: Pydantic AI
description: Install the pydantic-ai extra, configure BaseConfig.PYDANTIC_AI, and export Pydantic AI agent, model and tool telemetry through ArchiPy's OpenTelemetry providers.
---

# Pydantic AI

ArchiPy does not wrap Pydantic AI agents. It ships one integration: when OpenTelemetry is enabled, ArchiPy
instruments every Pydantic AI `Agent` so agent runs, model requests and tool calls become spans and token usage
becomes a metric, exported through the providers built from `BaseConfig.OTEL`. `BaseConfig.PYDANTIC_AI`
(`PydanticAIConfig`) controls that instrumentation.

## Installation

| Extra                       | Purpose                                                                         |
|-----------------------------|---------------------------------------------------------------------------------|
| `archipy[pydantic-ai]`      | `pydantic-ai-slim>=2.62.0` only                                                 |
| `archipy[otel-pydantic-ai]` | `archipy[pydantic-ai]` plus `archipy[otel]`: the library and the OTel exporters |

```bash
uv add "archipy[otel-pydantic-ai]"
```

Install the `pydantic-ai-slim` provider extra for the model you call (for example `pydantic-ai-slim[openai]`).

## Configuration

Settings live in `BaseConfig.PYDANTIC_AI` and use the `PYDANTIC_AI__` environment prefix. The instrumentation
only runs when `OTEL__IS_ENABLED=true`, so enable OpenTelemetry as described in [Observability](observability.md).

### Environment Variables

```bash
# OpenTelemetry (see the Observability tutorial)
OTEL__IS_ENABLED=true
OTEL__SERVICE_NAME=my-agent-service
OTEL__OTLP_ENDPOINT=http://localhost:4317

# Pydantic AI instrumentation (defaults shown)
PYDANTIC_AI__INSTRUMENTATION_ENABLED=true
PYDANTIC_AI__INSTRUMENTATION_INCLUDE_CONTENT=true
PYDANTIC_AI__INSTRUMENTATION_INCLUDE_BINARY_CONTENT=false
PYDANTIC_AI__INSTRUMENTATION_INCLUDE_MODEL_REQUEST_PARAMETERS=true
PYDANTIC_AI__INSTRUMENTATION_VERSION=6
PYDANTIC_AI__INSTRUMENTATION_USE_AGGREGATED_USAGE_ATTRIBUTE_NAMES=true
```

| Field                                                  | Default | Description                                                             |
|--------------------------------------------------------|---------|-------------------------------------------------------------------------|
| `INSTRUMENTATION_ENABLED`                              | `true`  | Instrument agents when OpenTelemetry is enabled                         |
| `INSTRUMENTATION_INCLUDE_CONTENT`                      | `true`  | Prompts, model output and tool arguments and results in span attributes |
| `INSTRUMENTATION_INCLUDE_BINARY_CONTENT`               | `false` | Images, audio and documents in span attributes                          |
| `INSTRUMENTATION_INCLUDE_MODEL_REQUEST_PARAMETERS`     | `true`  | Temperature, max tokens and similar parameters in model request spans   |
| `INSTRUMENTATION_VERSION`                              | `6`     | Span and attribute format version, `5` or `6`                           |
| `INSTRUMENTATION_USE_AGGREGATED_USAGE_ATTRIBUTE_NAMES` | `true`  | Name the agent run usage attributes `gen_ai.aggregated_usage.*`         |

!!! warning "Personal or secret data"
    With `INSTRUMENTATION_INCLUDE_CONTENT=true` prompts and tool results are exported to your telemetry backend.
    Set it to `false` when they can hold personal or secret data.

### Direct Configuration

```python
import logging

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OpentelemetryConfig, PydanticAIConfig

logger = logging.getLogger(__name__)


class AppConfig(BaseConfig):
    """Application configuration with agent telemetry settings."""

    OTEL: OpentelemetryConfig = OpentelemetryConfig(
        IS_ENABLED=True,
        SERVICE_NAME="my-agent-service",
        OTLP_ENDPOINT="http://localhost:4317",
    )
    PYDANTIC_AI: PydanticAIConfig = PydanticAIConfig(
        INSTRUMENTATION_INCLUDE_CONTENT=False,  # keep prompts out of spans
    )


BaseConfig.set_global(AppConfig())
config = BaseConfig.global_config()
logger.info("Pydantic AI instrumentation enabled: %s", config.PYDANTIC_AI.INSTRUMENTATION_ENABLED)
```

## How Agents Get Instrumented

`OtelUtils.init_otel_if_needed` runs when the application bootstraps through `AppUtils.create_fastapi_app` or
`create_grpc_app`, or when a tracing or metrics decorator first runs. It then calls `Agent.instrument_all` with
`InstrumentationSettings` that carry ArchiPy's tracer and meter providers and the `PYDANTIC_AI` options. You do
not pass anything to your agents:

- Agent runs become `invoke_agent <name>` spans, model requests `chat <model>` spans and tool calls
  `execute_tool <name>` spans.
- Token usage becomes the `gen_ai.client.token.usage` metric.
- Delegated agents are traced under the calling tool, and agents run inside FastAPI or gRPC requests join the
  request trace.
- Settings your application installed itself with `Agent.instrument_all` are left alone. Settings ArchiPy
  installed earlier are replaced when the runtime is re-initialized.
- Nothing happens when `pydantic-ai-slim` is not installed, when `PYDANTIC_AI__INSTRUMENTATION_ENABLED=false`, or
  when no tracer and meter provider exist.

## Basic Usage

Name your agents: the name appears in the `invoke_agent <name>` span.

```python
import logging

from fastapi import FastAPI
from pydantic_ai import Agent

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils
from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)

agent = Agent("openai:gpt-5", name="support-agent", instructions="Answer briefly.")


async def ask(question: str) -> str:
    """Run the agent and return its answer."""
    try:
        result = await agent.run(question)
    except Exception as e:
        logger.exception("Agent run failed")
        raise InternalError() from e
    else:
        return result.output


def create_app() -> FastAPI:
    """Build the app; this initializes OpenTelemetry and the agent instrumentation."""
    app = AppUtils.create_fastapi_app(BaseConfig.global_config())

    @app.get("/ask")
    async def ask_endpoint(q: str) -> dict[str, str]:
        return {"answer": await ask(q)}

    return app
```

In a worker without `AppUtils`, a tracing or metrics decorator from `archipy.helpers.decorators` triggers the same
initialization.

## See Also

- [Observability](observability.md) - OpenTelemetry setup, extras and the `PYDANTIC_AI` field reference
- [Configuration Management](config_management.md) - `BaseConfig` and environment variables
- [Error Handling](error_handling.md) - Domain errors and exception chaining
- [Configs API Reference](../api_reference/configs.md) - `PydanticAIConfig`
- [Installation](../getting-started/installation.md) - All extras
- [Changelog 5.22.0](../community/changelog/5/5.22.0.md) - Release that added the integration
