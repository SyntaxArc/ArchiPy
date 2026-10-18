"""No-op tracer and meter stubs used when the opentelemetry package is not installed."""

from __future__ import annotations

from typing import Any, Self


class _NoOpSpan:
    """Minimal span stub used when the opentelemetry package is not installed."""

    def set_attribute(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""

    def record_exception(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""

    def set_status(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""

    def end(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""

    def is_recording(self) -> bool:
        """Return False — no real span is active."""
        return False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        """No-op."""


class _NoOpTracer:
    """Minimal tracer stub used when the opentelemetry package is not installed."""

    def start_as_current_span(self, *_args: Any, **_kwargs: Any) -> _NoOpSpan:
        """Return a no-op span context manager."""
        return _NoOpSpan()

    def start_span(self, *_args: Any, **_kwargs: Any) -> _NoOpSpan:
        """Return a no-op span."""
        return _NoOpSpan()


class _NoOpHistogram:
    """Minimal histogram stub used when the opentelemetry package is not installed."""

    def record(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""


class _NoOpCounter:
    """Minimal counter stub used when the opentelemetry package is not installed."""

    def add(self, *_args: Any, **_kwargs: Any) -> None:
        """No-op."""


class _NoOpMeter:
    """Minimal meter stub used when the opentelemetry package is not installed."""

    def create_histogram(self, *_args: Any, **_kwargs: Any) -> _NoOpHistogram:
        """Return a no-op histogram."""
        return _NoOpHistogram()

    def create_counter(self, *_args: Any, **_kwargs: Any) -> _NoOpCounter:
        """Return a no-op counter."""
        return _NoOpCounter()
