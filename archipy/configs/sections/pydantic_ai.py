"""Pydantic AI configuration."""

from typing import Literal

from pydantic import BaseModel, Field


class PydanticAIConfig(BaseModel):
    """Configuration settings for Pydantic AI integration.

    Controls how ArchiPy instruments Pydantic AI agents when OpenTelemetry is enabled and ``pydantic-ai-slim`` is
    installed (``archipy[otel-pydantic-ai]``). Spans and metrics go through the providers built from
    ``BaseConfig.OTEL``.
    """

    INSTRUMENTATION_ENABLED: bool = Field(
        default=True,
        description="Instrument Pydantic AI agents when OpenTelemetry is enabled",
    )
    INSTRUMENTATION_INCLUDE_CONTENT: bool = Field(
        default=True,
        description=(
            "Put prompts, model output and tool arguments and results in span attributes; "
            "turn off when they hold personal or secret data"
        ),
    )
    INSTRUMENTATION_INCLUDE_BINARY_CONTENT: bool = Field(
        default=False,
        description="Put binary content (images, audio, documents) in span attributes",
    )
    INSTRUMENTATION_INCLUDE_MODEL_REQUEST_PARAMETERS: bool = Field(
        default=True,
        description="Put the model request parameters (temperature, max tokens, ...) in model request span attributes",
    )
    INSTRUMENTATION_VERSION: Literal[5, 6] = Field(
        default=6,
        description=(
            "Version of the span and attribute format Pydantic AI emits (the OpenTelemetry GenAI conventions it "
            "follows change between versions; older versions are deprecated upstream)"
        ),
    )
    INSTRUMENTATION_USE_AGGREGATED_USAGE_ATTRIBUTE_NAMES: bool = Field(
        default=True,
        description="Name the usage attributes of the agent run span ``gen_ai.aggregated_usage.*``",
    )
