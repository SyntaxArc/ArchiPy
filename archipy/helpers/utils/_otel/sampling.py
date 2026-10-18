"""Trace sampler selection for the OpenTelemetry SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.trace.sampling import Sampler

    from archipy.configs.config_template import OpentelemetryConfig


def create_sampler(otel: OpentelemetryConfig) -> Sampler:
    """Return the SDK sampler named by ``otel.TRACES_SAMPLER``; the ratio ones use ``TRACES_SAMPLE_RATIO``."""
    from opentelemetry.sdk.trace.sampling import (
        ALWAYS_OFF,
        ALWAYS_ON,
        ParentBased,
        ParentBasedTraceIdRatio,
        TraceIdRatioBased,
    )

    from archipy.configs.config_template import OtelSampler

    match otel.TRACES_SAMPLER:
        case OtelSampler.ALWAYS_ON:
            return ALWAYS_ON
        case OtelSampler.ALWAYS_OFF:
            return ALWAYS_OFF
        case OtelSampler.TRACEIDRATIO:
            return TraceIdRatioBased(otel.TRACES_SAMPLE_RATIO)
        case OtelSampler.PARENTBASED_ALWAYS_ON:
            return ParentBased(ALWAYS_ON)
        case OtelSampler.PARENTBASED_ALWAYS_OFF:
            return ParentBased(ALWAYS_OFF)
        case _:
            return ParentBasedTraceIdRatio(otel.TRACES_SAMPLE_RATIO)
