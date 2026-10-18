"""Context propagator selection for the OpenTelemetry SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archipy.models.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.propagators.textmap import TextMapPropagator

_B3_INSTALL_HINT = 'b3 propagation needs opentelemetry-propagator-b3. Install with: uv add "archipy[otel]"'


def create_propagator(names: Sequence[str]) -> CompositePropagator:
    """Return one composite propagator for the named propagators, in order.

    Args:
        names: Propagator names (``tracecontext``, ``baggage``, ``b3``, ``b3multi``, ``none``). A repeat counts once.

    Returns:
        A ``CompositePropagator``; empty for ``none``.

    Raises:
        ConfigurationError: If ``b3`` or ``b3multi`` is requested and ``opentelemetry-propagator-b3`` is not installed.
    """
    from opentelemetry.baggage.propagation import W3CBaggagePropagator
    from opentelemetry.propagators.composite import CompositePropagator
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    propagators: list[TextMapPropagator] = []
    for name in dict.fromkeys(names):
        if name == "tracecontext":
            propagators.append(TraceContextTextMapPropagator())
        elif name == "baggage":
            propagators.append(W3CBaggagePropagator())
        elif name in {"b3", "b3multi"}:
            try:
                from opentelemetry.propagators.b3 import B3MultiFormat, B3SingleFormat
            except ImportError as e:
                raise ConfigurationError(
                    operation="otel",
                    reason="b3_propagator_missing",
                    additional_data={"hint": _B3_INSTALL_HINT},
                ) from e
            propagators.append(B3SingleFormat() if name == "b3" else B3MultiFormat())
    return CompositePropagator(propagators)
