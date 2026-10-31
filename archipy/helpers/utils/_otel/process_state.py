"""Process-wide OpenTelemetry state shared by every runtime."""

from __future__ import annotations

import threading
import weakref
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from archipy.helpers.utils._otel.provider_types import OwnedLoggerProvider, OwnedMeterProvider, OwnedTracerProvider


class _ProcessState:
    """What is true for the whole process, whichever runtime asks.

    OpenTelemetry's own globals (the tracer, meter and logger providers, the textmap propagator) and the
    monkey-patching of instrumented libraries are process-wide and first-call-wins, so a second runtime has to see
    what the first one published.
    """

    lock: ClassVar[threading.Lock] = threading.Lock()
    globals_set: ClassVar[bool] = False
    propagator_installed: ClassVar[bool] = False
    shutdown_providers: ClassVar[weakref.WeakSet[OwnedTracerProvider | OwnedMeterProvider | OwnedLoggerProvider]] = (
        weakref.WeakSet()
    )
