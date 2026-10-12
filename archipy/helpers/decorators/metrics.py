"""OpenTelemetry metrics decorators for duration histograms and call counters."""

from __future__ import annotations

import functools
import inspect
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, Protocol

from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators._deprecation_alias import warn_deprecated_name
from archipy.helpers.utils.otel_utils import DURATION_HISTOGRAM_BUCKETS_S, OtelUtils
from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


logger = logging.getLogger(__name__)


class _Function(Protocol):
    """A callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class _AsyncFunction(Protocol):
    """An async callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]: ...


def _active_metrics_config() -> BaseConfig | None:
    """Return the global config when OTel metrics should be recorded, else None.

    Reads the global config once, initializes OTel on first use and reports whether
    metrics are enabled and the OTel packages are importable.

    Returns:
        The application configuration if metrics are active, otherwise None.
    """
    config = BaseConfig.global_config()
    if not OtelUtils.is_metrics_enabled(config):
        return None
    OtelUtils.init_otel_if_needed(config)
    if OtelUtils.import_failed():
        return None
    return config


def _merge_status_attributes(
    attributes: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    """Build metric attributes including a status label.

    Args:
        attributes: Optional static attributes from the decorator.
        status: ``"ok"``, ``"error"``, or ``"cancelled"``.

    Returns:
        A new attributes dict including ``status``.
    """
    merged: dict[str, Any] = dict(attributes) if attributes else {}
    merged["status"] = status
    return merged


def _status_for_base_exception(exc: BaseException) -> str:
    """Map a raised exception to the ``status`` label.

    Args:
        exc: The exception raised by the decorated function.

    Returns:
        ``"cancelled"`` for cancellation and interpreter-level interrupts, otherwise the
        status computed by ``OtelUtils.metric_status_for_exception``.
    """
    if isinstance(exc, Exception):
        return OtelUtils.metric_status_for_exception(exc)
    return "cancelled"


def _safe_emit(emit: Callable[..., Any], *args: Any) -> None:
    """Record a metric without letting telemetry failures replace the function outcome.

    Args:
        emit: ``histogram.record`` or ``counter.add``.
        *args: Arguments forwarded to ``emit``.
    """
    try:
        emit(*args)
    except Exception:  # telemetry must never break the decorated function
        logger.warning("Failed to record metric", exc_info=True)


_CACHE_LOCK = threading.Lock()
_HISTOGRAM_CACHE: dict[tuple[int, str, str, str], Any] = {}
_COUNTER_CACHE: dict[tuple[int, str, str], Any] = {}


def clear_instrument_caches() -> None:
    """Clear cached histogram and counter instruments.

    Call after provider reset/re-init so instruments are rebound to the new
    ``MeterProvider``. Used by ``OtelUtils.reset_for_testing()``.
    """
    with _CACHE_LOCK:
        _HISTOGRAM_CACHE.clear()
        _COUNTER_CACHE.clear()


def _instrument_identity(module: str, instrument_name: str) -> tuple[int, str, str]:
    """Build a provider-aware identity tuple for a metric instrument.

    Args:
        module: Module of the decorated function.
        instrument_name: Resolved instrument name.

    Returns:
        Tuple of ``(provider_id, module, instrument_name)``.
    """
    return (id(OtelUtils.meter_provider()), module, instrument_name)


def _resolve_instrument_name(func: Callable[..., Any], name: str | None, suffix: str) -> tuple[str, str]:
    """Resolve ``(module, instrument_name)`` once, when the decorator is applied.

    Args:
        func: The decorated function.
        name: Explicit instrument name, or None for the default.
        suffix: Default name suffix (``"duration"`` or ``"calls"``).

    Returns:
        The function's module and the instrument name.
    """
    module = getattr(func, "__module__", None) or "unknown"
    qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", None) or "unknown"
    return module, name or f"{module}.{qualname}.{suffix}"


def _get_or_create_histogram(module: str, instrument_name: str, unit: str) -> Any:
    """Return a cached duration histogram, creating it if needed.

    Args:
        module: Module of the decorated function (meter name).
        instrument_name: Resolved instrument name.
        unit: Histogram unit (default ``"s"``).

    Returns:
        An OpenTelemetry histogram instrument.
    """
    cache_key = (*_instrument_identity(module, instrument_name), unit)
    with _CACHE_LOCK:
        histogram = _HISTOGRAM_CACHE.get(cache_key)
        if histogram is not None:
            return histogram
        meter = OtelUtils.get_meter(module)
        histogram = meter.create_histogram(
            instrument_name,
            unit=unit,
            description="Function execution duration",
            explicit_bucket_boundaries_advisory=DURATION_HISTOGRAM_BUCKETS_S,
        )
        _HISTOGRAM_CACHE[cache_key] = histogram
        return histogram


def _get_or_create_counter(module: str, instrument_name: str) -> Any:
    """Return a cached call counter, creating it if needed.

    Args:
        module: Module of the decorated function (meter name).
        instrument_name: Resolved instrument name.

    Returns:
        An OpenTelemetry counter instrument.
    """
    cache_key = _instrument_identity(module, instrument_name)
    with _CACHE_LOCK:
        counter = _COUNTER_CACHE.get(cache_key)
        if counter is not None:
            return counter
        meter = OtelUtils.get_meter(module)
        counter = meter.create_counter(
            instrument_name,
            description="Function call count",
        )
        _COUNTER_CACHE[cache_key] = counter
        return counter


def _instrumented(
    func: Callable[..., Any],
    *,
    get_instrument: Callable[[], Any],
    emit: Callable[[Any, float, str], None],
) -> Callable[..., Any]:
    """Wrap a sync or async function so every call is recorded on a metric instrument.

    Args:
        func: The function to wrap. Coroutine functions get an async wrapper.
        get_instrument: Returns the (cached) histogram or counter.
        emit: Records one measurement as ``(instrument, elapsed_seconds, status)``.

    Returns:
        The wrapped function.
    """

    def record(instrument: Any, start: float, status: str) -> None:
        _safe_emit(emit, instrument, time.perf_counter() - start, status)

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if _active_metrics_config() is None:
                return await func(*args, **kwargs)

            instrument = get_instrument()
            start = time.perf_counter()
            status = "ok"
            try:
                return await func(*args, **kwargs)
            except BaseException as exc:
                status = _status_for_base_exception(exc)
                raise
            finally:
                record(instrument, start, status)

        return async_wrapper

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if _active_metrics_config() is None:
            return func(*args, **kwargs)

        instrument = get_instrument()
        start = time.perf_counter()
        status = "ok"
        try:
            return func(*args, **kwargs)
        except BaseException as exc:
            status = _status_for_base_exception(exc)
            raise
        finally:
            record(instrument, start, status)

    return wrapper


def _duration_wrapper(
    func: Callable[..., Any],
    name: str | None,
    unit: str,
    attributes: dict[str, Any] | None,
) -> Callable[..., Any]:
    module, instrument_name = _resolve_instrument_name(func, name, "duration")
    return _instrumented(
        func,
        get_instrument=lambda: _get_or_create_histogram(module, instrument_name, unit),
        emit=lambda histogram, elapsed, status: histogram.record(elapsed, _merge_status_attributes(attributes, status)),
    )


def _counter_wrapper(
    func: Callable[..., Any],
    name: str | None,
    attributes: dict[str, Any] | None,
) -> Callable[..., Any]:
    module, instrument_name = _resolve_instrument_name(func, name, "calls")
    return _instrumented(
        func,
        get_instrument=lambda: _get_or_create_counter(module, instrument_name),
        emit=lambda counter, _elapsed, status: counter.add(1, _merge_status_attributes(attributes, status)),
    )


def _require_coroutine_function(func: Callable[..., Any], decorator_name: str) -> None:
    """Raise when an ``async_*`` decorator is applied to a non-coroutine function.

    Args:
        func: The candidate function.
        decorator_name: Name of the decorator for the error payload.

    Raises:
        InvalidArgumentError: If ``func`` is not a coroutine function.
    """
    if not inspect.iscoroutinefunction(func):
        raise InvalidArgumentError(
            argument_name="func",
            additional_data={
                "decorator": decorator_name,
                "func_name": getattr(func, "__name__", "unknown"),
            },
        )


def measure_duration[F: _Function](
    name: str | None = None,
    *,
    unit: str = "s",
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync or async function to record execution duration as a histogram.

    Instrument name defaults to ``{module}.{qualname}.duration``. The histogram
    is cached in a module-level map keyed by provider id + instrument name. Each
    recording includes a ``status`` attribute of ``ok``, ``error`` or ``cancelled``.

    Works for ``def`` and ``async def`` functions alike. No-ops when OTel is disabled
    or ``config.OTEL.METRICS_ENABLED`` is False.

    Args:
        name: Histogram instrument name. Defaults to module-qualified duration name.
        unit: Unit of the recorded duration. Defaults to ``"s"``.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that records duration around the target function.
    """

    def decorator(func: F) -> Callable[..., Any]:
        return _duration_wrapper(func, name, unit, attributes)

    return decorator


def async_measure_duration[F: _AsyncFunction](
    name: str | None = None,
    *,
    unit: str = "s",
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function to record execution duration as a histogram.

    Deprecated:
        Use :func:`measure_duration`, which supports async functions directly.

    Args:
        name: Histogram instrument name. Defaults to module-qualified duration name.
        unit: Unit of the recorded duration. Defaults to ``"s"``.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that records duration around the target coroutine function.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """
    warn_deprecated_name("async_measure_duration", "measure_duration")

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        _require_coroutine_function(func, "async_measure_duration")
        return _duration_wrapper(func, name, unit, attributes)

    return decorator


def count_calls[F: _Function](
    name: str | None = None,
    *,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync or async function to increment a call counter.

    Instrument name defaults to ``{module}.{qualname}.calls``. The counter is
    cached in a module-level map keyed by provider id + instrument name. Each
    increment includes a ``status`` attribute of ``ok``, ``error`` or ``cancelled``.

    Works for ``def`` and ``async def`` functions alike. No-ops when OTel is disabled
    or ``config.OTEL.METRICS_ENABLED`` is False.

    Args:
        name: Counter instrument name. Defaults to module-qualified calls name.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that counts invocations of the target function.
    """

    def decorator(func: F) -> Callable[..., Any]:
        return _counter_wrapper(func, name, attributes)

    return decorator


def async_count_calls[F: _AsyncFunction](
    name: str | None = None,
    *,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function to increment a call counter.

    Deprecated:
        Use :func:`count_calls`, which supports async functions directly.

    Args:
        name: Counter instrument name. Defaults to module-qualified calls name.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that counts invocations of the target coroutine function.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """
    warn_deprecated_name("async_count_calls", "count_calls")

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        _require_coroutine_function(func, "async_count_calls")
        return _counter_wrapper(func, name, attributes)

    return decorator
