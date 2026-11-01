"""The only place the OpenTelemetry runtime knows about Temporal's replay-safe providers.

Temporal's tracing interceptor needs a ``ReplaySafeTracerProvider``, workflow code that records metrics needs a
``ReplaySafeMeterProvider``, and workflow code that emits OpenTelemetry log records needs a
``ReplaySafeLoggerProvider`` so the records are not duplicated on replay. They wrap an SDK provider instead of
subclassing it and forward ``shutdown``, ``force_flush`` and ``add_span_processor``, which is all ArchiPy uses; log
record processors are attached before the logger provider is wrapped. They are detected rather than registered so the
result does not depend on whether the OpenTelemetry runtime or the Temporal adapter initializes first. Without
``temporalio`` (or with a version that lacks the classes) every helper falls back to the plain SDK provider.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanLimits
    from opentelemetry.sdk.trace.sampling import Sampler

    from archipy.helpers.utils._otel.provider_types import OwnedLoggerProvider, OwnedMeterProvider, OwnedTracerProvider


def new_tracer_provider(
    resource: Resource,
    sampler: Sampler | None = None,
    span_limits: SpanLimits | None = None,
) -> OwnedTracerProvider:
    """Create an empty tracer provider, replay-safe when ``temporalio`` provides one.

    Args:
        resource: Resource describing the service.
        sampler: Optional sampler; the SDK default applies when omitted.
        span_limits: Optional span limits; the SDK defaults (and its own ``OTEL_*`` variables) apply when omitted.

    Returns:
        The tracer provider.
    """
    from opentelemetry.sdk.trace import TracerProvider

    try:
        from temporalio.contrib.opentelemetry import create_tracer_provider
    except ImportError:
        return TracerProvider(resource=resource, sampler=sampler, span_limits=span_limits)
    return create_tracer_provider(sampler=sampler, resource=resource, span_limits=span_limits)


def wrap_meter_provider(provider: OwnedMeterProvider) -> OwnedMeterProvider:
    """Wrap ``provider`` so metrics recorded from workflow code are dropped on replay, when ``temporalio`` allows.

    Args:
        provider: The SDK meter provider to wrap.

    Returns:
        The wrapped provider, or ``provider`` itself.
    """
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeMeterProvider
    except ImportError:
        return provider
    return ReplaySafeMeterProvider(provider)


def wrap_logger_provider(provider: OwnedLoggerProvider) -> OwnedLoggerProvider:
    """Wrap ``provider`` so log records emitted from workflow code are dropped on replay, when ``temporalio`` allows.

    Attach the log record processors first: the wrapper only forwards them to the SDK provider.

    Args:
        provider: The SDK logger provider to wrap.

    Returns:
        The wrapped provider, or ``provider`` itself.
    """
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeLoggerProvider
    except ImportError:
        return provider
    return ReplaySafeLoggerProvider(provider)


def as_replay_safe_tracer_provider(provider: object) -> OwnedTracerProvider | None:
    """Return ``provider`` when it is Temporal's replay-safe tracer provider, else ``None``."""
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeTracerProvider
    except ImportError:
        return None
    return provider if isinstance(provider, ReplaySafeTracerProvider) else None


def as_replay_safe_meter_provider(provider: object) -> OwnedMeterProvider | None:
    """Return ``provider`` when it is Temporal's replay-safe meter provider, else ``None``."""
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeMeterProvider
    except ImportError:
        return None
    return provider if isinstance(provider, ReplaySafeMeterProvider) else None


def as_replay_safe_logger_provider(provider: object) -> OwnedLoggerProvider | None:
    """Return ``provider`` when it is Temporal's replay-safe logger provider, else ``None``."""
    try:
        from temporalio.contrib.opentelemetry import ReplaySafeLoggerProvider
    except ImportError:
        return None
    return provider if isinstance(provider, ReplaySafeLoggerProvider) else None
