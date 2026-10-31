"""The OpenTelemetry runtime: the providers one process owns, and how they are built, flushed and shut down."""

from __future__ import annotations

import atexit
import logging
import os
import time
from typing import TYPE_CHECKING, TypeIs

from archipy.helpers.utils._otel import provider_lifecycle, providers, temporal_providers
from archipy.helpers.utils._otel.env import apply_standard_env, sdk_disabled
from archipy.helpers.utils._otel.exporters import (
    create_console_log_exporter,
    create_metric_exporter,
    create_otlp_log_exporter,
    create_span_exporter,
    resolve_metrics_endpoint,
    resolve_otlp_endpoint,
)
from archipy.helpers.utils._otel.instrumentation import Instrumentation
from archipy.helpers.utils._otel.logging_handler import attach_logging_handler, detach_logging_handler
from archipy.helpers.utils._otel.metrics_export import MetricsExport
from archipy.helpers.utils._otel.noop import _NoOpMeter, _NoOpTracer
from archipy.helpers.utils._otel.process_state import _ProcessState
from archipy.helpers.utils._otel.propagation import create_propagator
from archipy.helpers.utils._otel.resource import create_resource
from archipy.helpers.utils._otel.status import (
    error_type_for_exception,
    metric_status_for_exception,
    status_for_cancellation,
    status_for_exception,
    truncate_status_description,
)

if TYPE_CHECKING:
    import threading
    import weakref
    from collections.abc import Callable, Sequence

    import grpc.aio
    from opentelemetry.instrumentation.grpc._client import OpenTelemetryClientInterceptor
    from opentelemetry.metrics import Meter
    from opentelemetry.sdk._logs.export import LogRecordExporter
    from opentelemetry.sdk.metrics.export import MetricExporter, MetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace.export import SpanExporter
    from opentelemetry.trace import Status, Tracer
    from prometheus_client import CollectorRegistry

    from archipy.configs.base_config import BaseConfig
    from archipy.configs.config_template import OpentelemetryConfig
    from archipy.helpers.utils._otel.provider_types import OwnedLoggerProvider, OwnedMeterProvider, OwnedTracerProvider

from archipy.helpers.utils._otel.constants import (
    _DEFAULT_FLUSH_TIMEOUT_MS,
    _DEFAULT_PROPAGATORS,
    _INIT_RETRY_BACKOFF_SECONDS,
    _OTEL_GRPC_HINT,
    _OTEL_INSTALL_HINT,
    DURATION_HISTOGRAM_BUCKETS_S,
)

logger = logging.getLogger("archipy.helpers.utils.otel_utils")

__all__ = ["OtelRuntime", "_ProcessState"]


class OtelRuntime:
    """Idempotent OpenTelemetry provider management and helpers for one runtime.

    Owns ``TracerProvider`` / ``MeterProvider`` / ``LoggerProvider`` references and
    passes them explicitly to instrumentors. Globals are set once for third-party
    interop (e.g. Temporal ``TracingInterceptor``), but internal callers use
    ``get_tracer`` / ``get_meter`` against owned or adopted providers.

    Providers are built programmatically from ``BaseConfig.OTEL``. The SDK's ``OTEL_*``
    autoconfiguration is not used; with ``OTEL.USE_STANDARD_ENV`` the standard variables fill in
    the settings the config leaves unset. On init, ArchiPy installs the composite textmap
    propagator named by ``OTEL.PROPAGATORS`` (W3C TraceContext + Baggage by default,
    idempotent) so cross-service carriers stay locked to the intended ones.

    Initialization is transactional: providers are published only after all enabled
    signals succeed. Pre-existing concrete global providers are adopted (not replaced)
    so ArchiPy and third-party libraries share context. Only ArchiPy-owned providers
    are shut down.
    """

    def __init__(self) -> None:
        self._initialized = False
        self._logging_handler_attached = False
        self._atexit_registered = False
        self._import_failed = False
        self._tracer_provider: OwnedTracerProvider | None = None
        self._meter_provider: OwnedMeterProvider | None = None
        self._logger_provider: OwnedLoggerProvider | None = None
        self._owns_tracer = False
        self._owns_meter = False
        self._owns_logger = False
        self._logging_handler: logging.Handler | None = None
        self._init_pid: int | None = None
        self._init_failed_at: float | None = None
        self._metrics = MetricsExport()

    @property
    def _lock(self) -> threading.Lock:
        return _ProcessState.lock

    @property
    def _globals_set(self) -> bool:
        return _ProcessState.globals_set

    @_globals_set.setter
    def _globals_set(self, value: bool) -> None:
        _ProcessState.globals_set = value

    @property
    def _textmap_propagator_installed(self) -> bool:
        return _ProcessState.propagator_installed

    @_textmap_propagator_installed.setter
    def _textmap_propagator_installed(self, value: bool) -> None:
        _ProcessState.propagator_installed = value

    @property
    def _shutdown_providers(self) -> weakref.WeakSet[OwnedTracerProvider | OwnedMeterProvider | OwnedLoggerProvider]:
        return _ProcessState.shutdown_providers

    @property
    def _instrumented_libraries(self) -> set[str]:
        return Instrumentation.libraries

    @staticmethod
    def duration_histogram_buckets() -> tuple[float, ...]:
        """Return the explicit bucket boundaries, in seconds, of the duration histograms ArchiPy records.

        Reads ``OTEL.METRICS_DURATION_BUCKETS_S`` from the global config, and falls back to
        ``DURATION_HISTOGRAM_BUCKETS_S`` while no global config is set.

        Returns:
            The bucket boundaries.
        """
        from archipy.configs.base_config import BaseConfig

        try:
            return tuple(BaseConfig.global_config().OTEL.METRICS_DURATION_BUCKETS_S)
        except AssertionError:
            return DURATION_HISTOGRAM_BUCKETS_S

    @staticmethod
    def error_type_for_exception(exception: BaseException) -> str:
        """Return the ``error.type`` attribute value of a failure (``BaseError.code`` or the exception class name)."""
        return error_type_for_exception(exception)

    @staticmethod
    def is_otel_enabled(config: BaseConfig) -> bool:
        """Return True when the OTel master switch is enabled.

        Args:
            config: Application configuration.

        Returns:
            True if ``config.OTEL.IS_ENABLED`` is True.
        """
        return bool(config.OTEL.IS_ENABLED)

    @staticmethod
    def is_traces_enabled(config: BaseConfig) -> bool:
        """Return True when tracing should be active.

        Args:
            config: Application configuration.

        Returns:
            True if the master switch and ``TRACES_ENABLED`` are both True.
        """
        return bool(config.OTEL.IS_ENABLED and config.OTEL.TRACES_ENABLED)

    @staticmethod
    def is_metrics_enabled(config: BaseConfig) -> bool:
        """Return True when metrics should be active.

        Args:
            config: Application configuration.

        Returns:
            True if the master switch and ``METRICS_ENABLED`` are both True.
        """
        return bool(config.OTEL.IS_ENABLED and config.OTEL.METRICS_ENABLED)

    @staticmethod
    def is_logs_enabled(config: BaseConfig) -> bool:
        """Return True when log export should be active.

        Args:
            config: Application configuration.

        Returns:
            True if the master switch and ``LOGS_ENABLED`` are both True.
        """
        return bool(config.OTEL.IS_ENABLED and config.OTEL.LOGS_ENABLED)

    def import_failed(self) -> bool:
        """Return True when OTel initialization failed due to missing packages."""
        return self._import_failed

    def get_tracer(self, name: str) -> Tracer | _NoOpTracer:
        """Return a tracer from the owned tracer provider (or a no-op tracer).

        Args:
            name: Instrumentation scope name.

        Returns:
            An OpenTelemetry ``Tracer`` instance, or a no-op stub when the
            ``opentelemetry`` package is not installed.
        """
        try:
            from opentelemetry import trace
        except ImportError:
            return _NoOpTracer()

        if self._tracer_provider is not None:
            return self._tracer_provider.get_tracer(name)
        return trace.get_tracer(name)

    def get_meter(self, name: str) -> Meter | _NoOpMeter:
        """Return a meter from the owned meter provider (or a no-op meter).

        Args:
            name: Instrumentation scope name.

        Returns:
            An OpenTelemetry ``Meter`` instance, or a no-op stub when the
            ``opentelemetry`` package is not installed.
        """
        try:
            from opentelemetry import metrics
        except ImportError:
            return _NoOpMeter()

        if self._meter_provider is not None:
            return self._meter_provider.get_meter(name)
        return metrics.get_meter(name)

    def tracer_provider(self) -> OwnedTracerProvider | None:
        """Return the owned or adopted tracer provider, if initialized."""
        return self._tracer_provider

    def meter_provider(self) -> OwnedMeterProvider | None:
        """Return the owned or adopted meter provider, if initialized."""
        return self._meter_provider

    def logger_provider(self) -> OwnedLoggerProvider | None:
        """Return the owned or adopted logger provider, if initialized."""
        return self._logger_provider

    def metrics_registry(self) -> CollectorRegistry | None:
        """Return the Prometheus ``CollectorRegistry`` for pull/pushgateway metrics.

        Returns:
            The registry when ``METRICS_EXPORTER`` is ``pull`` or ``pushgateway``
            and providers were built, otherwise ``None``.
        """
        return self._metrics.registry

    @staticmethod
    def _truncate_status_description(exception: BaseException) -> str:
        """Return a bounded status description for span status."""
        return truncate_status_description(exception)

    @staticmethod
    def status_for_exception(exception: BaseException) -> Status | None:
        """Map an exception to an OpenTelemetry ``Status``, or ``None`` for UNSET.

        ``BaseError`` with ``http_status`` below 500 leaves status UNSET (handled client error). All other exceptions
        become ``StatusCode.ERROR``.

        Args:
            exception: The exception raised during a span.

        Returns:
            An OpenTelemetry ``Status`` instance, or ``None`` to leave status UNSET.
        """
        return status_for_exception(exception)

    @staticmethod
    def metric_status_for_exception(exception: BaseException) -> str:
        """Map an exception to a metric ``status`` attribute value (``"ok"`` or ``"error"``).

        Aligns with ``status_for_exception``: handled client ``BaseError`` values record as ``ok``. Callers that catch
        ``asyncio.CancelledError`` should record ``cancelled`` before invoking this helper.

        Args:
            exception: The exception raised during the instrumented call.

        Returns:
            ``"ok"`` or ``"error"``.
        """
        return metric_status_for_exception(exception)

    @staticmethod
    def status_for_cancellation() -> Status:
        """Return an ERROR status for asyncio task cancellation.

        Returns:
            An OpenTelemetry ``Status`` with ``StatusCode.ERROR``.
        """
        return status_for_cancellation()

    def init_otel_if_needed(self, config: BaseConfig) -> None:
        """Initialize OTel providers once (idempotent, thread-safe, fork-aware).

        Args:
            config: Application configuration.
        """
        if not config.OTEL.IS_ENABLED or self._import_failed or sdk_disabled(config.OTEL):
            return

        current_pid = os.getpid()
        if self._initialized and self._init_pid == current_pid:
            return
        if self._init_failed_recently():
            return

        with _ProcessState.lock:
            if not config.OTEL.IS_ENABLED or self._import_failed:
                return
            if self._initialized and self._init_pid == current_pid:
                return
            if self._init_failed_recently():
                return
            if self._initialized and self._init_pid is not None and self._init_pid != current_pid:
                self._reset_after_fork()
            try:
                self._install_textmap_propagator_unlocked(apply_standard_env(config.OTEL).PROPAGATORS)
                self._build_providers(config)
                self._instrument_installed_libraries(config)
                self._register_atexit()
                self._initialized = True
                self._init_pid = current_pid
                self._init_failed_at = None
            except ImportError:
                self._import_failed = True
                logger.warning(
                    "OTEL.IS_ENABLED is True but OpenTelemetry is not installed; telemetry disabled. %s",
                    _OTEL_INSTALL_HINT,
                )
            except Exception:
                self._metrics.stop_pushgateway_unlocked()
                self._metrics.stop_pull_scrape_unlocked()
                self._init_failed_at = time.monotonic()
                logger.exception("Failed to initialize OpenTelemetry")

    def _init_failed_recently(self) -> bool:
        """Return True while a failed initialization is still inside its retry back-off window."""
        failed_at = self._init_failed_at
        return failed_at is not None and time.monotonic() - failed_at < _INIT_RETRY_BACKOFF_SECONDS

    def force_flush(self, timeout_millis: int = _DEFAULT_FLUSH_TIMEOUT_MS) -> bool:
        """Force-flush all known providers.

        Args:
            timeout_millis: Maximum time to wait per provider.

        Returns:
            True when every provider flushed successfully (or none exist).
        """
        # Flush outside the lock: a slow exporter must not block initialization or shutdown on other threads.
        with _ProcessState.lock:
            known = (self._tracer_provider, self._meter_provider, self._logger_provider)
        return provider_lifecycle.flush_providers(known, timeout_millis)

    def shutdown(self) -> None:
        """Flush and shut down ArchiPy-owned providers; detach logging handler.

        Adopted (borrowed) providers are left running. Idempotent.
        """
        with _ProcessState.lock:
            self._force_flush_unlocked(_DEFAULT_FLUSH_TIMEOUT_MS)
            self._detach_logging_handler_unlocked()
            self._metrics.stop_pushgateway_unlocked()
            self._metrics.stop_pull_scrape_unlocked()
            self._shutdown_owned_providers_unlocked()
            self._tracer_provider = None
            self._meter_provider = None
            self._logger_provider = None
            self._owns_tracer = False
            self._owns_meter = False
            self._owns_logger = False
            self._initialized = False
            self._init_pid = None
            self._init_failed_at = None
            Instrumentation.libraries.clear()
            self._clear_metric_instrument_caches()

    def configure_for_testing(
        self,
        span_exporter: SpanExporter | None = None,
        metric_reader: MetricReader | None = None,
        log_exporter: LogRecordExporter | None = None,
        *,
        service_name: str = "archipy-test",
    ) -> None:
        """Swap in in-memory providers for BDD / unit tests.

        Args:
            span_exporter: Optional span exporter (e.g. ``InMemorySpanExporter``).
            metric_reader: Optional metric reader (e.g. ``InMemoryMetricReader``).
            log_exporter: Optional log exporter (e.g. ``InMemoryLogExporter``).
            service_name: Resource service name for the test providers.
        """
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        with _ProcessState.lock:
            self._install_textmap_propagator_unlocked(_DEFAULT_PROPAGATORS)
            resource = Resource.create({"service.name": service_name})
            tracer_provider = temporal_providers.new_tracer_provider(resource)
            if span_exporter is not None:
                tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            self._tracer_provider = tracer_provider
            self._owns_tracer = True
            if not _ProcessState.globals_set:
                trace.set_tracer_provider(tracer_provider)

            if metric_reader is not None:
                from opentelemetry.sdk.metrics import MeterProvider

                meter_provider = temporal_providers.wrap_meter_provider(
                    MeterProvider(resource=resource, metric_readers=[metric_reader]),
                )
                self._meter_provider = meter_provider
                self._owns_meter = True
                if not _ProcessState.globals_set:
                    metrics.set_meter_provider(meter_provider)

            if log_exporter is not None:
                from opentelemetry._logs import set_logger_provider
                from opentelemetry.sdk._logs import LoggerProvider
                from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

                sdk_logger_provider = LoggerProvider(resource=resource)
                sdk_logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
                logger_provider = temporal_providers.wrap_logger_provider(sdk_logger_provider)
                set_logger_provider(logger_provider)
                self._logger_provider = logger_provider
                self._owns_logger = True
                self._attach_logging_handler_unlocked(logging.INFO)

            _ProcessState.globals_set = True
            self._initialized = True
            self._init_pid = os.getpid()
            self._import_failed = False
            self._init_failed_at = None

    def reset_for_testing(self) -> None:
        """Reset owned providers for the next BDD scenario.

        Does not replace OTel globals (first-call-wins); subsequent scenarios
        reuse ``configure_for_testing`` which overwrites class attributes and
        rebuilds processors/readers on the existing global providers when possible.
        """
        with _ProcessState.lock:
            self._detach_logging_handler_unlocked()
            self._metrics.stop_pushgateway_unlocked()
            self._metrics.stop_pull_scrape_unlocked()
            self._shutdown_owned_providers_unlocked()
            self._tracer_provider = None
            self._meter_provider = None
            self._logger_provider = None
            self._owns_tracer = False
            self._owns_meter = False
            self._owns_logger = False
            self._initialized = False
            self._import_failed = False
            self._init_failed_at = None
            self._init_pid = None
            Instrumentation.libraries.clear()
            self._clear_metric_instrument_caches()
            # Keep global textmap propagator; first-call-wins across scenarios.

    def _install_textmap_propagator_unlocked(self, names: Sequence[str]) -> None:
        """Install the named propagators as the global textmap propagator.

        Idempotent. Locks ArchiPy's intended carriers (W3C ``traceparent``, ``tracestate`` and ``baggage`` by default)
        so another library cannot silently replace the default composite before ``init_otel_if_needed``.

        Args:
            names: Propagator names from ``OTEL.PROPAGATORS``.
        """
        if _ProcessState.propagator_installed:
            return
        from opentelemetry.propagate import set_global_textmap

        set_global_textmap(create_propagator(names))
        _ProcessState.propagator_installed = True

    def grpc_client_interceptors(self) -> list[OpenTelemetryClientInterceptor]:
        """Return sync gRPC client interceptors for outbound trace propagation.

        Returns:
            A list containing the contrib client interceptor.

        Raises:
            ImportError: If ``archipy[otel-grpc]`` is not installed.
        """
        try:
            from opentelemetry.instrumentation.grpc import client_interceptor
        except ImportError as exc:
            raise ImportError(_OTEL_GRPC_HINT) from exc
        return [client_interceptor(tracer_provider=self._tracer_provider)]

    def async_grpc_client_interceptors(self) -> list[grpc.aio.ClientInterceptor]:
        """Return async gRPC client interceptors for outbound trace propagation.

        Returns:
            A list of contrib aio client interceptors.

        Raises:
            ImportError: If ``archipy[otel-grpc]`` is not installed.
        """
        try:
            from opentelemetry.instrumentation.grpc import aio_client_interceptors
        except ImportError as exc:
            raise ImportError(_OTEL_GRPC_HINT) from exc
        return list(aio_client_interceptors(tracer_provider=self._tracer_provider))

    def _reset_after_fork(self) -> None:
        """Drop provider references after fork without shutting down parent threads."""
        logger.warning(
            "Process forked after OpenTelemetry init (parent_pid=%s, child_pid=%s); "
            "rebuilding ArchiPy-owned providers. Third-party code using OTel globals may "
            "need re-initialization in the child.",
            self._init_pid,
            os.getpid(),
        )
        self._detach_logging_handler_unlocked()
        # Do not call shutdown() — exporter threads belong to the parent process.
        # Drop scrape/push handles without stopping the parent's workers.
        self._metrics.drop_handles()
        self._tracer_provider = None
        self._meter_provider = None
        self._logger_provider = None
        self._owns_tracer = False
        self._owns_meter = False
        self._owns_logger = False
        self._initialized = False
        _ProcessState.globals_set = False
        self._init_pid = None
        Instrumentation.libraries.clear()
        self._clear_metric_instrument_caches()

    def _clear_metric_instrument_caches(self) -> None:
        """Clear decorator and gRPC metric instrument caches after provider reset."""
        from archipy.helpers.decorators.metrics import clear_instrument_caches
        from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
            _RpcInstruments,
        )

        clear_instrument_caches()
        _RpcInstruments.clear()

    def _force_flush_unlocked(self, timeout_millis: int) -> bool:
        return provider_lifecycle.flush_providers(
            (self._tracer_provider, self._meter_provider, self._logger_provider),
            timeout_millis,
        )

    def _shutdown_owned_providers_unlocked(self) -> None:
        provider_lifecycle.shutdown_owned(
            (
                (self._tracer_provider, self._owns_tracer),
                (self._meter_provider, self._owns_meter),
                (self._logger_provider, self._owns_logger),
            ),
        )

    def _shutdown_partial(
        self,
        tracer: OwnedTracerProvider | None,
        owns_tracer: bool,
        meter: OwnedMeterProvider | None,
        owns_meter: bool,
        log_provider: OwnedLoggerProvider | None,
        owns_logger: bool,
    ) -> None:
        """Shut down providers built during a failed initialization attempt."""
        provider_lifecycle.shutdown_owned(
            ((tracer, owns_tracer), (meter, owns_meter), (log_provider, owns_logger)),
            "Error shutting down partial OTel provider",
        )

    @staticmethod
    def _is_concrete_provider[T](provider: object, sdk_type: type[T]) -> TypeIs[T]:
        return provider_lifecycle.is_concrete_provider(provider, sdk_type)

    def _is_usable_provider(self, provider: object) -> bool:
        """Return False for providers that were shut down or are otherwise unusable."""
        return provider_lifecycle.is_usable_provider(provider)

    def _mark_provider_shutdown(
        self,
        provider: OwnedTracerProvider | OwnedMeterProvider | OwnedLoggerProvider | None,
    ) -> None:
        provider_lifecycle.mark_provider_shutdown(provider)

    def _existing_concrete_tracer_provider(self) -> OwnedTracerProvider | None:
        return provider_lifecycle.existing_concrete_tracer_provider()

    def _existing_concrete_meter_provider(self) -> OwnedMeterProvider | None:
        return provider_lifecycle.existing_concrete_meter_provider()

    def _existing_concrete_logger_provider(self) -> OwnedLoggerProvider | None:
        return provider_lifecycle.existing_concrete_logger_provider()

    def _create_resource(self, otel: OpentelemetryConfig) -> Resource:
        return create_resource(otel)

    def _acquire_provider[P](
        self,
        *,
        signal_name: str,
        existing: P | None,
        builder: Callable[[], P],
    ) -> tuple[P, bool]:
        """Adopt an existing provider or build a new owned one (see ``provider_lifecycle.acquire_provider``)."""
        return provider_lifecycle.acquire_provider(signal_name=signal_name, existing=existing, builder=builder)

    def _publish_trace_global(
        self,
        provider: OwnedTracerProvider | None,
        owns: bool,
    ) -> tuple[OwnedTracerProvider | None, bool]:
        return provider_lifecycle.publish_trace_global(provider, owns)

    def _publish_metric_global(
        self,
        provider: OwnedMeterProvider | None,
        owns: bool,
    ) -> tuple[OwnedMeterProvider | None, bool]:
        return provider_lifecycle.publish_metric_global(provider, owns)

    def _build_providers(self, config: BaseConfig) -> None:
        """Build providers transactionally and publish only on full success."""
        from opentelemetry._logs import set_logger_provider

        otel = apply_standard_env(config.OTEL)
        resource = self._create_resource(otel)

        new_tracer: OwnedTracerProvider | None = None
        new_meter: OwnedMeterProvider | None = None
        new_logger: OwnedLoggerProvider | None = None
        owns_tracer = False
        owns_meter = False
        owns_logger = False

        try:
            if otel.TRACES_ENABLED:
                new_tracer, owns_tracer = self._acquire_provider(
                    signal_name="trace",
                    existing=self._existing_concrete_tracer_provider(),
                    builder=lambda: self._build_tracer_provider(otel, resource),
                )
            if otel.METRICS_ENABLED:
                new_meter, owns_meter = self._acquire_provider(
                    signal_name="metric",
                    existing=self._existing_concrete_meter_provider(),
                    builder=lambda: self._build_meter_provider(otel, resource),
                )
            if otel.LOGS_ENABLED:
                new_logger, owns_logger = self._acquire_provider(
                    signal_name="log",
                    existing=self._existing_concrete_logger_provider(),
                    builder=lambda: self._build_logger_provider(otel, resource),
                )
        except Exception:
            self._shutdown_partial(new_tracer, owns_tracer, new_meter, owns_meter, new_logger, owns_logger)
            raise

        new_tracer, owns_tracer = self._publish_trace_global(new_tracer, owns_tracer)
        new_meter, owns_meter = self._publish_metric_global(new_meter, owns_meter)
        if owns_logger and new_logger is not None:
            set_logger_provider(new_logger)

        self._tracer_provider = new_tracer
        self._meter_provider = new_meter
        self._logger_provider = new_logger
        self._owns_tracer = owns_tracer
        self._owns_meter = owns_meter
        self._owns_logger = owns_logger
        if new_tracer is not None or new_meter is not None or new_logger is not None:
            _ProcessState.globals_set = True

        self._metrics.maybe_start_pull_scrape_unlocked(
            otel,
            owns_meter=owns_meter,
            new_meter=new_meter,
        )
        self._metrics.maybe_start_pushgateway_unlocked(
            otel,
            owns_meter=owns_meter,
            new_meter=new_meter,
        )

        if otel.LOGS_ENABLED and new_logger is not None:
            self._attach_logging_handler_unlocked(getattr(logging, otel.LOGS_LEVEL.upper(), logging.INFO))

    def _build_tracer_provider(self, otel: OpentelemetryConfig, resource: Resource) -> OwnedTracerProvider:
        return providers.build_tracer_provider(otel, resource, self._create_span_exporter)

    def _build_meter_provider(self, otel: OpentelemetryConfig, resource: Resource) -> OwnedMeterProvider:
        provider, registry = providers.build_meter_provider(otel, resource, self._create_metric_exporter)
        if registry is not None:
            self._metrics.registry = registry
        return provider

    def _build_logger_provider(self, otel: OpentelemetryConfig, resource: Resource) -> OwnedLoggerProvider:
        return providers.build_logger_provider(
            otel,
            resource,
            self._create_console_log_exporter,
            self._create_otlp_log_exporter,
        )

    @staticmethod
    def _create_console_log_exporter() -> LogRecordExporter:
        """Return a console exporter that splits INFO/DEBUG to stdout and WARNING+ to stderr."""
        return create_console_log_exporter()

    @staticmethod
    def _resolve_otlp_endpoint(
        otel: OpentelemetryConfig,
        signal: str,
        override: object | None,
    ) -> str:
        """Resolve the OTLP endpoint for a signal.

        Prefer a per-signal override. For ``http/protobuf``, append ``/v1/{signal}`` when the base URL has no path
        (or only ``/``). gRPC uses the base endpoint as-is.

        Args:
            otel: OpenTelemetry config section.
            signal: One of ``traces``, ``metrics``, or ``logs``.
            override: Optional per-signal endpoint override.

        Returns:
            The resolved endpoint URL.
        """
        return resolve_otlp_endpoint(otel, signal, override)

    def resolve_metrics_endpoint(self, otel: OpentelemetryConfig) -> str:
        """Return the resolved OTLP metrics endpoint for Temporal / callers.

        Args:
            otel: OpenTelemetry config section.

        Returns:
            The resolved metrics endpoint URL.
        """
        return resolve_metrics_endpoint(otel)

    def _create_span_exporter(self, otel: OpentelemetryConfig) -> SpanExporter:
        return create_span_exporter(otel)

    def _create_metric_exporter(self, otel: OpentelemetryConfig) -> MetricExporter:
        return create_metric_exporter(otel)

    def _create_otlp_log_exporter(self, otel: OpentelemetryConfig) -> LogRecordExporter:
        return create_otlp_log_exporter(otel)

    def _attach_logging_handler_unlocked(self, level: int) -> None:
        if self._logging_handler_attached or self._logger_provider is None:
            return
        self._logging_handler = attach_logging_handler(level, self._logger_provider)
        self._logging_handler_attached = True

    def _detach_logging_handler_unlocked(self) -> None:
        handler = self._logging_handler
        if self._logging_handler_attached and handler is not None:
            detach_logging_handler(handler)
        self._logging_handler = None
        self._logging_handler_attached = False

    def _instrument_installed_libraries(self, config: BaseConfig) -> None:
        """Best-effort auto-instrumentation of installed contrib packages with ArchiPy's providers."""
        Instrumentation.instrument_installed_libraries(
            config,
            tracer_provider=self._tracer_provider,
            meter_provider=self._meter_provider,
        )

    def _guard_redis_search_attributes(self) -> None:
        """Keep ``opentelemetry-instrumentation-redis`` from raising into the application on a RESP3 search reply."""
        Instrumentation.guard_redis_search_attributes()

    def restore_redis_search_attributes(self) -> None:
        """Undo :meth:`_guard_redis_search_attributes` (used by tests that need the upstream behaviour)."""
        Instrumentation.restore_redis_search_attributes()

    def _register_atexit(self) -> None:
        if self._atexit_registered:
            return

        def _shutdown() -> None:
            try:
                self.shutdown()
            except Exception:
                logger.debug("Error during OTel atexit shutdown", exc_info=True)

        atexit.register(_shutdown)
        self._atexit_registered = True
