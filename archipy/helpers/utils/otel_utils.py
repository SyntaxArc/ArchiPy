"""OpenTelemetry utilities for provider lifecycle, instrumentation, and status mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from archipy.helpers.utils._otel.constants import (
    _OTEL_FASTAPI_HINT,
    _OTEL_GRPC_HINT,
    _OTEL_INSTALL_HINT,
    DURATION_HISTOGRAM_BUCKETS_S,
)
from archipy.helpers.utils._otel.runtime import OtelRuntime

if TYPE_CHECKING:
    import grpc.aio
    from opentelemetry.instrumentation.grpc._client import OpenTelemetryClientInterceptor
    from opentelemetry.metrics import Meter
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import LogRecordExporter
    from opentelemetry.sdk.metrics.export import MetricReader
    from opentelemetry.sdk.trace.export import SpanExporter
    from opentelemetry.trace import Status, Tracer
    from prometheus_client import CollectorRegistry

    from archipy.configs.base_config import BaseConfig
    from archipy.configs.config_template import OpentelemetryConfig
    from archipy.helpers.utils._otel.noop import _NoOpMeter, _NoOpTracer
    from archipy.helpers.utils._otel.provider_types import OwnedMeterProvider, OwnedTracerProvider

__all__ = [
    "DURATION_HISTOGRAM_BUCKETS_S",
    "OTEL_FASTAPI_INSTALL_HINT",
    "OTEL_GRPC_INSTALL_HINT",
    "OTEL_INSTALL_HINT",
    "OtelRuntime",
    "OtelUtils",
]


class _OtelUtilsMeta(type):
    """Forward the names ``OtelUtils`` does not define to the default runtime.

    Tests and a few callers read or replace runtime internals through ``OtelUtils`` (``_initialized``,
    ``_instrumented_libraries``, ``_build_providers``, ...). Reads fall through to the runtime, and writes of a
    private name land on the runtime instead of shadowing it on the class.
    """

    def __getattr__(cls, name: str) -> object:
        if name.startswith("__"):
            raise AttributeError(name)
        return getattr(type.__getattribute__(cls, "_runtime"), name)

    def __setattr__(cls, name: str, value: object) -> None:
        if name.startswith("_") and not name.startswith("__") and name != "_runtime":
            setattr(type.__getattribute__(cls, "_runtime"), name, value)
        else:
            super().__setattr__(name, value)


class OtelUtils(metaclass=_OtelUtilsMeta):
    """Idempotent OpenTelemetry provider management and helpers.

    A facade over the default ``OtelRuntime``, which owns the ``TracerProvider`` / ``MeterProvider`` /
    ``LoggerProvider`` references and passes them explicitly to instrumentors. Globals are set once for third-party
    interop (e.g. Temporal ``TracingInterceptor``), but internal callers use ``get_tracer`` / ``get_meter`` against
    owned or adopted providers. Everything process-wide (the OpenTelemetry globals, the propagator, the instrumented
    libraries) is shared by every runtime; ``set_runtime`` swaps the object that owns the providers, for example to
    give a test its own.

    Providers are built programmatically from ``BaseConfig.OTEL``. The SDK's ``OTEL_*`` autoconfiguration is not used;
    with ``OTEL.USE_STANDARD_ENV`` the standard variables fill in the settings the config leaves unset. On init,
    ArchiPy installs the composite textmap propagator named by ``OTEL.PROPAGATORS`` (W3C TraceContext + Baggage by
    default, idempotent) so cross-service carriers stay locked to the intended ones.

    Initialization is transactional: providers are published only after all enabled signals succeed. Pre-existing
    concrete global providers are adopted (not replaced) so ArchiPy and third-party libraries share context. Only
    ArchiPy-owned providers are shut down.
    """

    _runtime: ClassVar[OtelRuntime] = OtelRuntime()

    @classmethod
    def runtime(cls) -> OtelRuntime:
        """Return the runtime the facade currently delegates to."""
        return cls._runtime

    @classmethod
    def set_runtime(cls, runtime: OtelRuntime) -> OtelRuntime:
        """Make ``runtime`` the one the facade delegates to.

        Args:
            runtime: The runtime to use from now on.

        Returns:
            The runtime that was in use before, so the caller can put it back.
        """
        previous = cls._runtime
        type.__setattr__(cls, "_runtime", runtime)
        return previous

    @staticmethod
    def duration_histogram_buckets() -> tuple[float, ...]:
        """Return the explicit bucket boundaries, in seconds, of the duration histograms ArchiPy records."""
        return OtelRuntime.duration_histogram_buckets()

    @staticmethod
    def error_type_for_exception(exception: BaseException) -> str:
        """Return the ``error.type`` attribute value of a failure (``BaseError.code`` or the exception class name)."""
        return OtelRuntime.error_type_for_exception(exception)

    @staticmethod
    def is_otel_enabled(config: BaseConfig) -> bool:
        """Return whether OpenTelemetry is enabled in ``config``."""
        return OtelRuntime.is_otel_enabled(config)

    @staticmethod
    def is_traces_enabled(config: BaseConfig) -> bool:
        """Return whether OpenTelemetry and its traces are enabled in ``config``."""
        return OtelRuntime.is_traces_enabled(config)

    @staticmethod
    def is_metrics_enabled(config: BaseConfig) -> bool:
        """Return whether OpenTelemetry and its metrics are enabled in ``config``."""
        return OtelRuntime.is_metrics_enabled(config)

    @staticmethod
    def is_logs_enabled(config: BaseConfig) -> bool:
        """Return whether OpenTelemetry and its logs are enabled in ``config``."""
        return OtelRuntime.is_logs_enabled(config)

    @classmethod
    def import_failed(cls) -> bool:
        """Return whether OpenTelemetry could not be imported when initialization was attempted."""
        return cls._runtime.import_failed()

    @classmethod
    def get_tracer(cls, name: str) -> Tracer | _NoOpTracer:
        """Return a tracer from the owned tracer provider (or a no-op tracer)."""
        return cls._runtime.get_tracer(name)

    @classmethod
    def get_meter(cls, name: str) -> Meter | _NoOpMeter:
        """Return a meter from the owned meter provider (or a no-op meter)."""
        return cls._runtime.get_meter(name)

    @classmethod
    def tracer_provider(cls) -> OwnedTracerProvider | None:
        """Return the owned or adopted tracer provider, if any."""
        return cls._runtime.tracer_provider()

    @classmethod
    def meter_provider(cls) -> OwnedMeterProvider | None:
        """Return the owned or adopted meter provider, if any."""
        return cls._runtime.meter_provider()

    @classmethod
    def logger_provider(cls) -> LoggerProvider | None:
        """Return the owned or adopted logger provider, if any."""
        return cls._runtime.logger_provider()

    @classmethod
    def metrics_registry(cls) -> CollectorRegistry | None:
        """Return the Prometheus registry of the pull or Pushgateway metrics exporter, if any."""
        return cls._runtime.metrics_registry()

    @staticmethod
    def status_for_exception(exception: BaseException) -> Status | None:
        """Map an exception to an OpenTelemetry ``Status``, or ``None`` for UNSET."""
        return OtelRuntime.status_for_exception(exception)

    @staticmethod
    def metric_status_for_exception(exception: BaseException) -> str:
        """Map an exception to a metric ``status`` attribute value (``"ok"`` or ``"error"``)."""
        return OtelRuntime.metric_status_for_exception(exception)

    @staticmethod
    def status_for_cancellation() -> Status:
        """Return an ERROR status for asyncio task cancellation."""
        return OtelRuntime.status_for_cancellation()

    @classmethod
    def init_otel_if_needed(cls, config: BaseConfig) -> None:
        """Build and publish the providers once per process, as ``config`` asks."""
        cls._runtime.init_otel_if_needed(config)

    @classmethod
    def force_flush(cls, timeout_millis: int = 30_000) -> bool:
        """Flush the owned providers; return whether every flush succeeded."""
        return cls._runtime.force_flush(timeout_millis)

    @classmethod
    def shutdown(cls) -> None:
        """Shut down the providers this runtime owns and stop its metrics workers."""
        cls._runtime.shutdown()

    @classmethod
    def configure_for_testing(
        cls,
        span_exporter: SpanExporter | None = None,
        metric_reader: MetricReader | None = None,
        log_exporter: LogRecordExporter | None = None,
        *,
        service_name: str = "archipy-test",
    ) -> None:
        """Install in-memory providers for a test."""
        cls._runtime.configure_for_testing(span_exporter, metric_reader, log_exporter, service_name=service_name)

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset the owned providers for the next test scenario."""
        cls._runtime.reset_for_testing()

    @classmethod
    def grpc_client_interceptors(cls) -> list[OpenTelemetryClientInterceptor]:
        """Return sync gRPC client interceptors for outbound trace propagation."""
        return cls._runtime.grpc_client_interceptors()

    @classmethod
    def async_grpc_client_interceptors(cls) -> list[grpc.aio.ClientInterceptor]:
        """Return async gRPC client interceptors for outbound trace propagation."""
        return cls._runtime.async_grpc_client_interceptors()

    @classmethod
    def resolve_metrics_endpoint(cls, otel: OpentelemetryConfig) -> str:
        """Return the resolved OTLP metrics endpoint for Temporal / callers."""
        return cls._runtime.resolve_metrics_endpoint(otel)

    @classmethod
    def restore_redis_search_attributes(cls) -> None:
        """Undo the guard around the Redis instrumentor's search helper (for tests)."""
        cls._runtime.restore_redis_search_attributes()


# Re-export install hints for app_utils
OTEL_FASTAPI_INSTALL_HINT = _OTEL_FASTAPI_HINT
OTEL_GRPC_INSTALL_HINT = _OTEL_GRPC_HINT
OTEL_INSTALL_HINT = _OTEL_INSTALL_HINT
