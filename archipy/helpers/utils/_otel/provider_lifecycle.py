"""Adoption, publication, flush and shutdown of OpenTelemetry providers."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeIs

from archipy.helpers.utils._otel.process_state import _ProcessState

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider

logger = logging.getLogger("archipy.helpers.utils.otel_utils")


def is_concrete_provider[T](provider: object, sdk_type: type[T]) -> TypeIs[T]:
    """Return True when ``provider`` is an instance of the SDK type (and not an API proxy or no-op)."""
    return isinstance(provider, sdk_type)


def is_usable_provider(provider: object) -> bool:
    """Return False for providers that were shut down or are otherwise unusable."""
    if provider is None or provider in _ProcessState.shutdown_providers:
        return False
    return not getattr(provider, "_shutdown", False)


def mark_provider_shutdown(provider: TracerProvider | MeterProvider | LoggerProvider | None) -> None:
    """Remember that a provider was shut down."""
    if provider is not None:
        # Hold the provider weakly: ``id()`` values are reused after garbage collection.
        _ProcessState.shutdown_providers.add(provider)


def existing_concrete_tracer_provider() -> TracerProvider | None:
    """Return the usable concrete global tracer provider, if any."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    current = trace.get_tracer_provider()
    if is_concrete_provider(current, TracerProvider) and is_usable_provider(current):
        return current
    return None


def existing_concrete_meter_provider() -> MeterProvider | None:
    """Return the usable concrete global meter provider, if any."""
    from opentelemetry import metrics
    from opentelemetry.sdk.metrics import MeterProvider

    current = metrics.get_meter_provider()
    if is_concrete_provider(current, MeterProvider) and is_usable_provider(current):
        return current
    return None


def existing_concrete_logger_provider() -> LoggerProvider | None:
    """Return the usable concrete global logger provider, if any."""
    from opentelemetry._logs import get_logger_provider
    from opentelemetry.sdk._logs import LoggerProvider

    current = get_logger_provider()
    if is_concrete_provider(current, LoggerProvider) and is_usable_provider(current):
        return current
    return None


def acquire_provider[P](
    *,
    signal_name: str,
    existing: P | None,
    builder: Callable[[], P],
) -> tuple[P, bool]:
    """Adopt an existing provider or build a new owned one.

    Args:
        signal_name: Signal label for warning messages (e.g. ``"trace"``).
        existing: Concrete global provider to adopt, or None.
        builder: Zero-arg callable that builds a new provider.

    Returns:
        Tuple of ``(provider, owns_provider)``.
    """
    if existing is not None:
        logger.warning(
            "Adopting existing %s provider; ArchiPy OTEL %s exporter configuration is ignored for this process",
            signal_name,
            signal_name,
        )
        return existing, False
    return builder(), True


def shutdown_owned(
    providers: Iterable[tuple[TracerProvider | MeterProvider | LoggerProvider | None, bool]],
    error_message: str = "Error shutting down OTel provider",
) -> None:
    """Shut down every provider ArchiPy owns and mark it as shut down.

    Args:
        providers: ``(provider, owns)`` pairs; adopted and missing providers are skipped.
        error_message: Debug message logged when a shutdown raises.
    """
    for provider, owns in providers:
        if not owns or provider is None:
            continue
        try:
            provider.shutdown()
        except Exception:
            logger.debug(error_message, exc_info=True)
        mark_provider_shutdown(provider)


def flush_providers(
    providers: Iterable[TracerProvider | MeterProvider | LoggerProvider | None],
    timeout_millis: int,
) -> bool:
    """Force-flush every provider that supports it.

    Args:
        providers: Providers to flush; ``None`` entries are skipped.
        timeout_millis: Maximum time to wait per provider.

    Returns:
        True when every provider flushed successfully (or none exist).
    """
    ok = True
    for provider in providers:
        if provider is None or not hasattr(provider, "force_flush"):
            continue
        try:
            result = provider.force_flush(timeout_millis)
            if result is False:
                ok = False
        except Exception:
            logger.debug("Error during OTel force_flush", exc_info=True)
            ok = False
    return ok


def publish_trace_global(provider: TracerProvider | None, owns: bool) -> tuple[TracerProvider | None, bool]:
    """Set an owned tracer provider as the global one, or adopt the one another library set first."""
    from opentelemetry import trace

    if not owns or provider is None or _ProcessState.globals_set:
        return provider, owns
    trace.set_tracer_provider(provider)
    after = existing_concrete_tracer_provider()
    if after is not None and after is not provider:
        shutdown_owned([(provider, True)], "Error shutting down partial OTel provider")
        logger.warning("Global TracerProvider was set by another library; adopting it")
        return after, False
    return provider, True


def publish_metric_global(provider: MeterProvider | None, owns: bool) -> tuple[MeterProvider | None, bool]:
    """Set an owned meter provider as the global one, or adopt the one another library set first."""
    from opentelemetry import metrics

    if not owns or provider is None or _ProcessState.globals_set:
        return provider, owns
    metrics.set_meter_provider(provider)
    after = existing_concrete_meter_provider()
    if after is not None and after is not provider:
        shutdown_owned([(provider, True)], "Error shutting down partial OTel provider")
        logger.warning("Global MeterProvider was set by another library; adopting it")
        return after, False
    return provider, True
