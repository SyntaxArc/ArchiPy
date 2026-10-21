"""The only place the OpenTelemetry runtime knows about Temporal's replay-safe providers.

Temporal's tracing interceptor needs a ``ReplaySafeTracerProvider``, and workflow code that records metrics needs a
``ReplaySafeMeterProvider``. Both wrap an SDK provider instead of subclassing it and forward ``shutdown``,
``force_flush`` and ``add_span_processor``, which is all ArchiPy uses. They are detected rather than registered so the
result does not depend on whether the OpenTelemetry runtime or the Temporal adapter initializes first. Without
``temporalio`` (or with a version that lacks the classes) every helper falls back to the plain SDK provider.

There is no logger counterpart: ``temporalio`` 1.34.0's ``ReplaySafeLoggerProvider`` cannot be instantiated with
``opentelemetry-api`` 1.45 (``Logger.enabled`` became abstract), so logs stay unwrapped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.sampling import Sampler

    from archipy.helpers.utils._otel.provider_types import OwnedMeterProvider, OwnedTracerProvider


def new_tracer_provider(resource: Resource, sampler: Sampler | None = None) -> OwnedTracerProvider:
    """Create an empty tracer provider, replay-safe when ``temporalio`` provides one.

    Args:
        resource: Resource describing the service.
        sampler: Optional sampler; the SDK default applies when omitted.

    Returns:
        The tracer provider.
    """
    from opentelemetry.sdk.trace import TracerProvider

    try:
        from temporalio.contrib.opentelemetry import create_tracer_provider
    except ImportError:
        return TracerProvider(resource=resource, sampler=sampler)
    return create_tracer_provider(sampler=sampler, resource=resource)


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
