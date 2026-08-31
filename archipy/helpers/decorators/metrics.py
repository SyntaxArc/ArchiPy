"""OpenTelemetry metrics decorators for duration histograms and call counters."""

from __future__ import annotations

import functools
import inspect
import time
from typing import TYPE_CHECKING, Any, Protocol

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


class _Function(Protocol):
    """A callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class _AsyncFunction(Protocol):
    """An async callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]: ...


def _metrics_active(config: Any) -> bool:
    """Return True when OTel metrics should be recorded.

    Args:
        config: Application configuration.

    Returns:
        True if OTel is enabled and metrics export is enabled.
    """
    return OtelUtils.is_otel_enabled(config) and bool(config.OTEL.METRICS_ENABLED)


def _merge_status_attributes(
    attributes: dict[str, Any] | None,
    status: str,
) -> dict[str, Any]:
    """Build metric attributes including a status label.

    Args:
        attributes: Optional static attributes from the decorator.
        status: ``"ok"`` or ``"error"``.

    Returns:
        A new attributes dict including ``status``.
    """
    merged: dict[str, Any] = dict(attributes) if attributes else {}
    merged["status"] = status
    return merged


_HISTOGRAM_CACHE: dict[tuple[int, str, str, str], Any] = {}
_COUNTER_CACHE: dict[tuple[int, str, str, str], Any] = {}


def clear_instrument_caches() -> None:
    """Clear cached histogram and counter instruments.

    Call after provider reset/re-init so instruments are rebound to the new
    ``MeterProvider``. Used by ``OtelUtils.reset_for_testing()``.
    """
    _HISTOGRAM_CACHE.clear()
    _COUNTER_CACHE.clear()


def _instrument_cache_key(
    func: Callable[..., Any],
    instrument_name: str,
) -> tuple[int, str, str, str]:
    """Build a provider-aware cache key for a metric instrument.

    Args:
        func: The decorated function.
        instrument_name: Resolved instrument name.

    Returns:
        Tuple of ``(provider_id, module, qualname, instrument_name)``.
    """
    provider = OtelUtils.meter_provider()
    module = getattr(func, "__module__", None) or "unknown"
    qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", None) or "unknown"
    return (id(provider), module, qualname, instrument_name)


def _get_or_create_histogram(
    func: Callable[..., Any],
    name: str | None,
    unit: str,
) -> Any:
    """Return a cached duration histogram for ``func``, creating it if needed.

    Args:
        func: The decorated function.
        name: Explicit instrument name, or None for the default.
        unit: Histogram unit (default ``"s"``).

    Returns:
        An OpenTelemetry histogram instrument.
    """
    module = getattr(func, "__module__", None) or "unknown"
    qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", None) or "unknown"
    instrument_name = name or f"{module}.{qualname}.duration"
    cache_key = _instrument_cache_key(func, instrument_name)
    histogram = _HISTOGRAM_CACHE.get(cache_key)
    if histogram is not None:
        return histogram
    meter = OtelUtils.get_meter(module)
    histogram = meter.create_histogram(instrument_name, unit=unit)
    _HISTOGRAM_CACHE[cache_key] = histogram
    return histogram


def _get_or_create_counter(
    func: Callable[..., Any],
    name: str | None,
) -> Any:
    """Return a cached call counter for ``func``, creating it if needed.

    Args:
        func: The decorated function.
        name: Explicit instrument name, or None for the default.

    Returns:
        An OpenTelemetry counter instrument.
    """
    module = getattr(func, "__module__", None) or "unknown"
    qualname = getattr(func, "__qualname__", None) or getattr(func, "__name__", None) or "unknown"
    instrument_name = name or f"{module}.{qualname}.calls"
    cache_key = _instrument_cache_key(func, instrument_name)
    counter = _COUNTER_CACHE.get(cache_key)
    if counter is not None:
        return counter
    meter = OtelUtils.get_meter(module)
    counter = meter.create_counter(instrument_name)
    _COUNTER_CACHE[cache_key] = counter
    return counter


def measure_duration[F: _Function](
    name: str | None = None,
    *,
    unit: str = "s",
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync function to record execution duration as a histogram.

    Instrument name defaults to ``{module}.{qualname}.duration``. The histogram
    is cached in a module-level map keyed by provider id + instrument name. Each
    recording includes a ``status`` attribute of ``ok`` or ``error``.

    No-ops when OTel is disabled or ``config.OTEL.METRICS_ENABLED`` is False.

    Args:
        name: Histogram instrument name. Defaults to module-qualified duration name.
        unit: Unit of the recorded duration. Defaults to ``"s"``.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that records duration around the target function.

    Raises:
        InvalidArgumentError: If the decorated object is a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "measure_duration",
                    "func_name": func.__name__,
                    "hint": "Use async_measure_duration instead of measure_duration",
                },
            )

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not _metrics_active(config):
                return func(*args, **kwargs)

            OtelUtils.init_otel_if_needed(config)
            histogram = _get_or_create_histogram(func, name, unit)
            start = time.perf_counter()
            status = "ok"
            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                histogram.record(
                    time.perf_counter() - start,
                    _merge_status_attributes(attributes, status),
                )

        return wrapper

    return decorator


def async_measure_duration[F: _AsyncFunction](
    name: str | None = None,
    *,
    unit: str = "s",
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function to record execution duration as a histogram.

    Args:
        name: Histogram instrument name. Defaults to module-qualified duration name.
        unit: Unit of the recorded duration. Defaults to ``"s"``.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that records duration around the target coroutine function.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_measure_duration",
                    "func_name": func.__name__,
                },
            )

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not _metrics_active(config):
                return await func(*args, **kwargs)

            OtelUtils.init_otel_if_needed(config)
            histogram = _get_or_create_histogram(func, name, unit)
            start = time.perf_counter()
            status = "ok"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                histogram.record(
                    time.perf_counter() - start,
                    _merge_status_attributes(attributes, status),
                )

        return wrapper

    return decorator


def count_calls[F: _Function](
    name: str | None = None,
    *,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync function to increment a call counter.

    Instrument name defaults to ``{module}.{qualname}.calls``. The counter is
    cached in a module-level map keyed by provider id + instrument name. Each
    increment includes a ``status`` attribute of ``ok`` or ``error``.

    No-ops when OTel is disabled or ``config.OTEL.METRICS_ENABLED`` is False.

    Args:
        name: Counter instrument name. Defaults to module-qualified calls name.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that counts invocations of the target function.

    Raises:
        InvalidArgumentError: If the decorated object is a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Any]:
        if inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "count_calls",
                    "func_name": func.__name__,
                    "hint": "Use async_count_calls instead of count_calls",
                },
            )

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not _metrics_active(config):
                return func(*args, **kwargs)

            OtelUtils.init_otel_if_needed(config)
            counter = _get_or_create_counter(func, name)
            status = "ok"
            try:
                return func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                counter.add(1, _merge_status_attributes(attributes, status))

        return wrapper

    return decorator


def async_count_calls[F: _AsyncFunction](
    name: str | None = None,
    *,
    attributes: dict[str, Any] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function to increment a call counter.

    Args:
        name: Counter instrument name. Defaults to module-qualified calls name.
        attributes: Optional static attributes merged into each recording.

    Returns:
        A decorator that counts invocations of the target coroutine function.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_count_calls",
                    "func_name": func.__name__,
                },
            )

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not _metrics_active(config):
                return await func(*args, **kwargs)

            OtelUtils.init_otel_if_needed(config)
            counter = _get_or_create_counter(func, name)
            status = "ok"
            try:
                return await func(*args, **kwargs)
            except Exception:
                status = "error"
                raise
            finally:
                counter.add(1, _merge_status_attributes(attributes, status))

        return wrapper

    return decorator
