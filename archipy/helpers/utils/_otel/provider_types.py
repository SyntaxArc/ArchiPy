"""Type aliases for the providers ArchiPy owns or adopts.

With ``temporalio`` installed the runtime owns Temporal's replay-safe wrappers, which subclass the API providers and
wrap an SDK provider instead of subclassing it. The aliases cover both so no caller needs a cast. See
``temporal_providers`` for the one module that creates and detects the wrappers, and for why there is no logger alias.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.trace import TracerProvider
    from temporalio.contrib.opentelemetry import (
        ReplaySafeMeterProvider,
        ReplaySafeTracerProvider,
    )

type OwnedTracerProvider = TracerProvider | ReplaySafeTracerProvider
type OwnedMeterProvider = MeterProvider | ReplaySafeMeterProvider
