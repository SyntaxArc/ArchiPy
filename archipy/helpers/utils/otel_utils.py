"""OpenTelemetry utilities for provider lifecycle, instrumentation, and status mapping."""

from __future__ import annotations

import atexit
import logging
import os
import threading
import time
import weakref
from typing import TYPE_CHECKING, Any, ClassVar

from archipy.helpers.utils._otel.exporters import (
    create_console_log_exporter,
    create_metric_exporter,
    create_otlp_log_exporter,
    create_span_exporter,
    resolve_metrics_endpoint,
    resolve_otlp_endpoint,
)
from archipy.helpers.utils._otel.metrics_export import MetricsExport
from archipy.helpers.utils._otel.noop import _NoOpMeter, _NoOpTracer
from archipy.helpers.utils._otel.status import (
    metric_status_for_exception,
    status_for_cancellation,
    status_for_exception,
    truncate_status_description,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)

_DEFAULT_FLUSH_TIMEOUT_MS = 30_000
_INIT_RETRY_BACKOFF_SECONDS = 30.0
DURATION_HISTOGRAM_BUCKETS_S: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
)

_REDIS_SEARCH_GUARD_MARKER = "_archipy_original"
_REDIS_SEARCH_ATTRIBUTES_NAME = "_add_search_attributes"
_OTEL_INSTALL_HINT = 'OpenTelemetry requires the optional dependency. Install with: uv add "archipy[otel]"'
_OTEL_FASTAPI_HINT = 'FastAPI OTel instrumentation requires: uv add "archipy[otel,fastapi]"'
_OTEL_GRPC_HINT = 'gRPC OTel instrumentation requires: uv add "archipy[otel-grpc]"'


class OtelUtils:
    """Idempotent OpenTelemetry provider management and helpers.

    Owns ``TracerProvider`` / ``MeterProvider`` / ``LoggerProvider`` references and
    passes them explicitly to instrumentors. Globals are set once for third-party
    interop (e.g. Temporal ``TracingInterceptor``), but internal callers use
    ``get_tracer`` / ``get_meter`` against owned or adopted providers.

    Providers are built programmatically from ``BaseConfig.OTEL`` only —
    ``OTEL_*`` environment-variable autoconfiguration is not used. On init,
    ArchiPy installs a W3C TraceContext + Baggage composite textmap propagator
    (idempotent) so cross-service ``traceparent`` / ``baggage`` carriers stay
    locked to the intended default.

    Initialization is transactional: providers are published only after all enabled
    signals succeed. Pre-existing concrete global providers are adopted (not replaced)
    so ArchiPy and third-party libraries share context. Only ArchiPy-owned providers
    are shut down.
    """

    _lock = threading.Lock()
    _initialized: bool = False
    _logging_handler_attached: bool = False
    _atexit_registered: bool = False
    _import_failed: bool = False
    _instrumented_libraries: ClassVar[set[str]] = set()

    _tracer_provider: Any | None = None
    _meter_provider: Any | None = None
    _logger_provider: Any | None = None
    _globals_set: bool = False

    _owns_tracer: bool = False
    _owns_meter: bool = False
    _owns_logger: bool = False
    _logging_handler: Any | None = None
    _init_pid: int | None = None
    _shutdown_providers: ClassVar[weakref.WeakSet[Any]] = weakref.WeakSet()
    _init_failed_at: float | None = None
    _textmap_propagator_installed: bool = False

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

    @classmethod
    def import_failed(cls) -> bool:
        """Return True when OTel initialization failed due to missing packages."""
        return cls._import_failed

    @classmethod
    def get_tracer(cls, name: str) -> Any:
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

        if cls._tracer_provider is not None:
            return cls._tracer_provider.get_tracer(name)
        return trace.get_tracer(name)

    @classmethod
    def get_meter(cls, name: str) -> Any:
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

        if cls._meter_provider is not None:
            return cls._meter_provider.get_meter(name)
        return metrics.get_meter(name)

    @classmethod
    def tracer_provider(cls) -> Any | None:
        """Return the owned or adopted tracer provider, if initialized."""
        return cls._tracer_provider

    @classmethod
    def meter_provider(cls) -> Any | None:
        """Return the owned or adopted meter provider, if initialized."""
        return cls._meter_provider

    @classmethod
    def logger_provider(cls) -> Any | None:
        """Return the owned or adopted logger provider, if initialized."""
        return cls._logger_provider

    @classmethod
    def metrics_registry(cls) -> Any | None:
        """Return the Prometheus ``CollectorRegistry`` for pull/pushgateway metrics.

        Returns:
            The registry when ``METRICS_EXPORTER`` is ``pull`` or ``pushgateway``
            and providers were built, otherwise ``None``.
        """
        return MetricsExport.registry

    @staticmethod
    def _truncate_status_description(exception: BaseException) -> str:
        """Return a bounded status description for span status."""
        return truncate_status_description(exception)

    @staticmethod
    def status_for_exception(exception: BaseException) -> Any | None:
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

    @classmethod
    def status_for_cancellation(cls) -> Any:
        """Return an ERROR status for asyncio task cancellation.

        Returns:
            An OpenTelemetry ``Status`` with ``StatusCode.ERROR``.
        """
        return status_for_cancellation()

    @classmethod
    def init_otel_if_needed(cls, config: BaseConfig) -> None:
        """Initialize OTel providers once (idempotent, thread-safe, fork-aware).

        Args:
            config: Application configuration.
        """
        if not config.OTEL.IS_ENABLED or cls._import_failed:
            return

        current_pid = os.getpid()
        if cls._initialized and cls._init_pid == current_pid:
            return
        if cls._init_failed_recently():
            return

        with cls._lock:
            if not config.OTEL.IS_ENABLED or cls._import_failed:
                return
            if cls._initialized and cls._init_pid == current_pid:
                return
            if cls._init_failed_recently():
                return
            if cls._initialized and cls._init_pid is not None and cls._init_pid != current_pid:
                cls._reset_after_fork()
            try:
                cls._install_textmap_propagator_unlocked()
                cls._build_providers(config)
                cls._instrument_installed_libraries(config)
                cls._register_atexit()
                cls._initialized = True
                cls._init_pid = current_pid
                cls._init_failed_at = None
            except ImportError:
                cls._import_failed = True
                logger.warning(
                    "OTEL.IS_ENABLED is True but OpenTelemetry is not installed; telemetry disabled. %s",
                    _OTEL_INSTALL_HINT,
                )
            except Exception:
                MetricsExport.stop_pushgateway_unlocked()
                MetricsExport.stop_pull_scrape_unlocked()
                cls._init_failed_at = time.monotonic()
                logger.exception("Failed to initialize OpenTelemetry")

    @classmethod
    def _init_failed_recently(cls) -> bool:
        """Return True while a failed initialization is still inside its retry back-off window."""
        failed_at = cls._init_failed_at
        return failed_at is not None and time.monotonic() - failed_at < _INIT_RETRY_BACKOFF_SECONDS

    @classmethod
    def force_flush(cls, timeout_millis: int = _DEFAULT_FLUSH_TIMEOUT_MS) -> bool:
        """Force-flush all known providers.

        Args:
            timeout_millis: Maximum time to wait per provider.

        Returns:
            True when every provider flushed successfully (or none exist).
        """
        ok = True
        # Flush outside the lock: a slow exporter must not block initialization or shutdown on other threads.
        with cls._lock:
            providers = (cls._tracer_provider, cls._meter_provider, cls._logger_provider)
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

    @classmethod
    def shutdown(cls) -> None:
        """Flush and shut down ArchiPy-owned providers; detach logging handler.

        Adopted (borrowed) providers are left running. Idempotent.
        """
        with cls._lock:
            cls._force_flush_unlocked(_DEFAULT_FLUSH_TIMEOUT_MS)
            cls._detach_logging_handler_unlocked()
            MetricsExport.stop_pushgateway_unlocked()
            MetricsExport.stop_pull_scrape_unlocked()
            cls._shutdown_owned_providers_unlocked()
            cls._tracer_provider = None
            cls._meter_provider = None
            cls._logger_provider = None
            cls._owns_tracer = False
            cls._owns_meter = False
            cls._owns_logger = False
            cls._initialized = False
            cls._init_pid = None
            cls._init_failed_at = None
            cls._instrumented_libraries.clear()
            cls._clear_metric_instrument_caches()

    @classmethod
    def configure_for_testing(
        cls,
        span_exporter: Any | None = None,
        metric_reader: Any | None = None,
        log_exporter: Any | None = None,
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
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        with cls._lock:
            cls._install_textmap_propagator_unlocked()
            resource = Resource.create({"service.name": service_name})
            tracer_provider = TracerProvider(resource=resource)
            if span_exporter is not None:
                tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            cls._tracer_provider = tracer_provider
            cls._owns_tracer = True
            if not cls._globals_set:
                trace.set_tracer_provider(tracer_provider)

            if metric_reader is not None:
                from opentelemetry.sdk.metrics import MeterProvider

                meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
                cls._meter_provider = meter_provider
                cls._owns_meter = True
                if not cls._globals_set:
                    metrics.set_meter_provider(meter_provider)

            if log_exporter is not None:
                from opentelemetry._logs import set_logger_provider
                from opentelemetry.sdk._logs import LoggerProvider
                from opentelemetry.sdk._logs.export import SimpleLogRecordProcessor

                logger_provider = LoggerProvider(resource=resource)
                logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
                set_logger_provider(logger_provider)
                cls._logger_provider = logger_provider
                cls._owns_logger = True
                cls._attach_logging_handler_unlocked(logging.INFO)

            cls._globals_set = True
            cls._initialized = True
            cls._init_pid = os.getpid()
            cls._import_failed = False
            cls._init_failed_at = None

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset owned providers for the next BDD scenario.

        Does not replace OTel globals (first-call-wins); subsequent scenarios
        reuse ``configure_for_testing`` which overwrites class attributes and
        rebuilds processors/readers on the existing global providers when possible.
        """
        with cls._lock:
            cls._detach_logging_handler_unlocked()
            MetricsExport.stop_pushgateway_unlocked()
            MetricsExport.stop_pull_scrape_unlocked()
            cls._shutdown_owned_providers_unlocked()
            cls._tracer_provider = None
            cls._meter_provider = None
            cls._logger_provider = None
            cls._owns_tracer = False
            cls._owns_meter = False
            cls._owns_logger = False
            cls._initialized = False
            cls._import_failed = False
            cls._init_failed_at = None
            cls._init_pid = None
            cls._instrumented_libraries.clear()
            cls._clear_metric_instrument_caches()
            # Keep global textmap propagator; first-call-wins across scenarios.

    @classmethod
    def _install_textmap_propagator_unlocked(cls) -> None:
        """Install W3C TraceContext + Baggage as the global textmap propagator.

        Idempotent. Locks ArchiPy's intended carriers (``traceparent``,
        ``tracestate``, ``baggage``) so another library cannot silently replace
        the default composite before ``init_otel_if_needed``.
        """
        if cls._textmap_propagator_installed:
            return
        from opentelemetry.baggage.propagation import W3CBaggagePropagator
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.propagators.composite import CompositePropagator
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        set_global_textmap(
            CompositePropagator(
                [
                    TraceContextTextMapPropagator(),
                    W3CBaggagePropagator(),
                ],
            ),
        )
        cls._textmap_propagator_installed = True

    @classmethod
    def grpc_client_interceptors(cls) -> list[Any]:
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
        return [client_interceptor(tracer_provider=cls._tracer_provider)]

    @classmethod
    def async_grpc_client_interceptors(cls) -> list[Any]:
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
        return list(aio_client_interceptors(tracer_provider=cls._tracer_provider))

    @classmethod
    def _reset_after_fork(cls) -> None:
        """Drop provider references after fork without shutting down parent threads."""
        logger.warning(
            "Process forked after OpenTelemetry init (parent_pid=%s, child_pid=%s); "
            "rebuilding ArchiPy-owned providers. Third-party code using OTel globals may "
            "need re-initialization in the child.",
            cls._init_pid,
            os.getpid(),
        )
        cls._detach_logging_handler_unlocked()
        # Do not call shutdown() — exporter threads belong to the parent process.
        # Drop scrape/push handles without stopping the parent's workers.
        MetricsExport.drop_handles()
        cls._tracer_provider = None
        cls._meter_provider = None
        cls._logger_provider = None
        cls._owns_tracer = False
        cls._owns_meter = False
        cls._owns_logger = False
        cls._initialized = False
        cls._globals_set = False
        cls._init_pid = None
        cls._instrumented_libraries.clear()
        cls._clear_metric_instrument_caches()

    @classmethod
    def _clear_metric_instrument_caches(cls) -> None:
        """Clear decorator and gRPC metric instrument caches after provider reset."""
        from archipy.helpers.decorators.metrics import clear_instrument_caches
        from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
            _RpcInstruments,
        )

        clear_instrument_caches()
        _RpcInstruments.clear()

    @classmethod
    def _force_flush_unlocked(cls, timeout_millis: int) -> bool:
        ok = True
        for provider in (cls._tracer_provider, cls._meter_provider, cls._logger_provider):
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

    @classmethod
    def _shutdown_owned_providers_unlocked(cls) -> None:
        owned: list[tuple[Any | None, bool]] = [
            (cls._tracer_provider, cls._owns_tracer),
            (cls._meter_provider, cls._owns_meter),
            (cls._logger_provider, cls._owns_logger),
        ]
        for provider, owns in owned:
            if not owns or provider is None:
                continue
            try:
                provider.shutdown()
            except Exception:
                logger.debug("Error shutting down OTel provider", exc_info=True)
            cls._mark_provider_shutdown(provider)

    @classmethod
    def _shutdown_partial(
        cls,
        tracer: Any | None,
        owns_tracer: bool,
        meter: Any | None,
        owns_meter: bool,
        log_provider: Any | None,
        owns_logger: bool,
    ) -> None:
        """Shut down providers built during a failed initialization attempt."""
        for provider, owns in (
            (tracer, owns_tracer),
            (meter, owns_meter),
            (log_provider, owns_logger),
        ):
            if not owns or provider is None:
                continue
            try:
                provider.shutdown()
            except Exception:
                logger.debug("Error shutting down partial OTel provider", exc_info=True)
            cls._mark_provider_shutdown(provider)

    @staticmethod
    def _is_concrete_provider(provider: Any, sdk_type: type) -> bool:
        return isinstance(provider, sdk_type)

    @classmethod
    def _is_usable_provider(cls, provider: Any) -> bool:
        """Return False for providers that were shut down or are otherwise unusable."""
        if provider is None or provider in cls._shutdown_providers:
            return False
        return not getattr(provider, "_shutdown", False)

    @classmethod
    def _mark_provider_shutdown(cls, provider: Any | None) -> None:
        if provider is not None:
            # Hold the provider weakly: ``id()`` values are reused after garbage collection.
            cls._shutdown_providers.add(provider)

    @classmethod
    def _existing_concrete_tracer_provider(cls) -> Any | None:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider

        current = trace.get_tracer_provider()
        if cls._is_concrete_provider(current, TracerProvider) and cls._is_usable_provider(current):
            return current
        return None

    @classmethod
    def _existing_concrete_meter_provider(cls) -> Any | None:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider

        current = metrics.get_meter_provider()
        if cls._is_concrete_provider(current, MeterProvider) and cls._is_usable_provider(current):
            return current
        return None

    @classmethod
    def _existing_concrete_logger_provider(cls) -> Any | None:
        from opentelemetry._logs import get_logger_provider
        from opentelemetry.sdk._logs import LoggerProvider

        current = get_logger_provider()
        if cls._is_concrete_provider(current, LoggerProvider) and cls._is_usable_provider(current):
            return current
        return None

    @classmethod
    def _create_resource(cls, otel: Any) -> Any:
        from opentelemetry.sdk.resources import Resource

        resource_attrs: dict[str, Any] = dict(otel.RESOURCE_ATTRIBUTES)
        if otel.SERVICE_NAME:
            resource_attrs["service.name"] = otel.SERVICE_NAME
        if otel.ENVIRONMENT is not None:
            resource_attrs["deployment.environment.name"] = str(otel.ENVIRONMENT)
        return Resource.create(resource_attrs)

    @classmethod
    def _acquire_provider(
        cls,
        *,
        signal_name: str,
        existing: Any | None,
        builder: Any,
    ) -> tuple[Any, bool]:
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

    @classmethod
    def _publish_trace_global(cls, provider: Any, owns: bool) -> tuple[Any, bool]:
        from opentelemetry import trace

        if not owns or provider is None or cls._globals_set:
            return provider, owns
        trace.set_tracer_provider(provider)
        after = cls._existing_concrete_tracer_provider()
        if after is not None and after is not provider:
            cls._shutdown_partial(provider, True, None, False, None, False)
            logger.warning("Global TracerProvider was set by another library; adopting it")
            return after, False
        return provider, True

    @classmethod
    def _publish_metric_global(cls, provider: Any, owns: bool) -> tuple[Any, bool]:
        from opentelemetry import metrics

        if not owns or provider is None or cls._globals_set:
            return provider, owns
        metrics.set_meter_provider(provider)
        after = cls._existing_concrete_meter_provider()
        if after is not None and after is not provider:
            cls._shutdown_partial(None, False, provider, True, None, False)
            logger.warning("Global MeterProvider was set by another library; adopting it")
            return after, False
        return provider, True

    @classmethod
    def _build_providers(cls, config: BaseConfig) -> None:
        """Build providers transactionally and publish only on full success."""
        from opentelemetry._logs import set_logger_provider

        otel = config.OTEL
        resource = cls._create_resource(otel)

        new_tracer: Any | None = None
        new_meter: Any | None = None
        new_logger: Any | None = None
        owns_tracer = False
        owns_meter = False
        owns_logger = False

        try:
            if otel.TRACES_ENABLED:
                new_tracer, owns_tracer = cls._acquire_provider(
                    signal_name="trace",
                    existing=cls._existing_concrete_tracer_provider(),
                    builder=lambda: cls._build_tracer_provider(otel, resource),
                )
            if otel.METRICS_ENABLED:
                new_meter, owns_meter = cls._acquire_provider(
                    signal_name="metric",
                    existing=cls._existing_concrete_meter_provider(),
                    builder=lambda: cls._build_meter_provider(otel, resource),
                )
            if otel.LOGS_ENABLED:
                new_logger, owns_logger = cls._acquire_provider(
                    signal_name="log",
                    existing=cls._existing_concrete_logger_provider(),
                    builder=lambda: cls._build_logger_provider(otel, resource),
                )
        except Exception:
            cls._shutdown_partial(new_tracer, owns_tracer, new_meter, owns_meter, new_logger, owns_logger)
            raise

        new_tracer, owns_tracer = cls._publish_trace_global(new_tracer, owns_tracer)
        new_meter, owns_meter = cls._publish_metric_global(new_meter, owns_meter)
        if owns_logger and new_logger is not None:
            set_logger_provider(new_logger)

        cls._tracer_provider = new_tracer
        cls._meter_provider = new_meter
        cls._logger_provider = new_logger
        cls._owns_tracer = owns_tracer
        cls._owns_meter = owns_meter
        cls._owns_logger = owns_logger
        if new_tracer is not None or new_meter is not None or new_logger is not None:
            cls._globals_set = True

        MetricsExport.maybe_start_pull_scrape_unlocked(
            otel,
            owns_meter=owns_meter,
            new_meter=new_meter,
        )
        MetricsExport.maybe_start_pushgateway_unlocked(
            otel,
            owns_meter=owns_meter,
            new_meter=new_meter,
        )

        if otel.LOGS_ENABLED and new_logger is not None:
            cls._attach_logging_handler_unlocked(getattr(logging, otel.LOGS_LEVEL.upper(), logging.INFO))

    @classmethod
    def _build_tracer_provider(cls, otel: Any, resource: Any) -> Any:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

        sampler = ParentBasedTraceIdRatio(otel.TRACES_SAMPLE_RATIO)
        provider = TracerProvider(resource=resource, sampler=sampler)
        exporter = cls._create_span_exporter(otel)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        return provider

    @classmethod
    def _build_meter_provider(cls, otel: Any, resource: Any) -> Any:
        from opentelemetry.sdk.metrics import MeterProvider

        from archipy.configs.config_template import OtelMetricsExporter

        readers: list[Any] = []
        if otel.METRICS_EXPORTER == OtelMetricsExporter.OTLP:
            from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

            exporter = cls._create_metric_exporter(otel)
            readers.append(
                PeriodicExportingMetricReader(
                    exporter,
                    export_interval_millis=otel.METRIC_EXPORT_INTERVAL_MS,
                ),
            )
        elif otel.METRICS_EXPORTER in {OtelMetricsExporter.PULL, OtelMetricsExporter.PUSHGATEWAY}:
            from opentelemetry.exporter.prometheus import PrometheusMetricReader
            from prometheus_client import CollectorRegistry

            registry = CollectorRegistry(auto_describe=True)
            MetricsExport.registry = registry
            readers.append(PrometheusMetricReader(registry=registry))

        return MeterProvider(resource=resource, metric_readers=readers)

    @classmethod
    def _build_logger_provider(cls, otel: Any, resource: Any) -> Any:
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor

        from archipy.configs.config_template import OtelLogsExporter

        provider = LoggerProvider(resource=resource)
        if otel.LOGS_EXPORTER == OtelLogsExporter.CONSOLE:
            provider.add_log_record_processor(SimpleLogRecordProcessor(cls._create_console_log_exporter()))
        else:
            exporter = cls._create_otlp_log_exporter(otel)
            provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        return provider

    @staticmethod
    def _create_console_log_exporter() -> Any:
        """Return a console exporter that splits INFO/DEBUG to stdout and WARNING+ to stderr."""
        return create_console_log_exporter()

    @staticmethod
    def _resolve_otlp_endpoint(
        otel: Any,
        signal: str,
        override: Any | None,
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

    @classmethod
    def resolve_metrics_endpoint(cls, otel: Any) -> str:
        """Return the resolved OTLP metrics endpoint for Temporal / callers.

        Args:
            otel: OpenTelemetry config section.

        Returns:
            The resolved metrics endpoint URL.
        """
        return resolve_metrics_endpoint(otel)

    @classmethod
    def _create_span_exporter(cls, otel: Any) -> Any:
        return create_span_exporter(otel)

    @classmethod
    def _create_metric_exporter(cls, otel: Any) -> Any:
        return create_metric_exporter(otel)

    @classmethod
    def _create_otlp_log_exporter(cls, otel: Any) -> Any:
        return create_otlp_log_exporter(otel)

    @classmethod
    def _attach_logging_handler_unlocked(cls, level: int) -> None:
        if cls._logging_handler_attached or cls._logger_provider is None:
            return
        from opentelemetry.sdk._logs import LoggingHandler

        class _DropOtelInternalLogs(logging.Filter):
            """Drop records from ``opentelemetry.*`` to avoid export feedback loops."""

            def filter(self, record: logging.LogRecord) -> bool:
                return not record.name.startswith("opentelemetry")

        handler = LoggingHandler(level=level, logger_provider=cls._logger_provider)
        handler.addFilter(_DropOtelInternalLogs())
        logging.getLogger().addHandler(handler)
        cls._logging_handler = handler
        cls._logging_handler_attached = True

    @classmethod
    def _detach_logging_handler_unlocked(cls) -> None:
        if not cls._logging_handler_attached or cls._logging_handler is None:
            cls._logging_handler_attached = False
            cls._logging_handler = None
            return
        root = logging.getLogger()
        try:
            root.removeHandler(cls._logging_handler)
        except Exception:
            logger.debug("Error removing OTel logging handler", exc_info=True)
        try:
            cls._logging_handler.close()
        except Exception:
            logger.debug("Error closing OTel logging handler", exc_info=True)
        cls._logging_handler = None
        cls._logging_handler_attached = False

    @classmethod
    def _instrument_installed_libraries(cls, config: BaseConfig) -> None:
        """Best-effort auto-instrumentation of installed contrib packages.

        Each entry is ``(cache_key, module, class_name)``. Missing packages are
        skipped via ``ImportError`` — install the matching ``archipy[otel-*]``
        extra (or the contrib package directly) to enable them. Instrumentors
        whose target library is absent (e.g. ``httpx`` when only ``httpx2`` is
        installed) raise ``DependencyConflictError`` and are skipped at debug
        level. A target library that is installed outside the instrumentor's
        supported version range is logged at warning level, because no spans
        are emitted for it.

        Driver-level DB instrumentors (psycopg/pymysql/sqlite3) are omitted:
        ArchiPy goes through SQLAlchemy — use ``archipy[otel-sqlalchemy]``.
        """
        instrumentors: Sequence[tuple[str, str, str]] = (
            ("threading", "opentelemetry.instrumentation.threading", "ThreadingInstrumentor"),
            ("system_metrics", "opentelemetry.instrumentation.system_metrics", "SystemMetricsInstrumentor"),
            ("sqlalchemy", "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
            ("redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor"),
            ("cassandra", "opentelemetry.instrumentation.cassandra", "CassandraInstrumentor"),
            ("confluent_kafka", "opentelemetry.instrumentation.confluent_kafka", "ConfluentKafkaInstrumentor"),
            ("botocore", "opentelemetry.instrumentation.botocore", "BotocoreInstrumentor"),
            ("httpx", "opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
            ("httpx2", "opentelemetry.instrumentation.httpx", "HTTPX2ClientInstrumentor"),
            ("requests", "opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
        )
        try:
            from opentelemetry.instrumentation.dependencies import DependencyConflictError
        except ImportError:
            logger.debug("Skipping OTel auto-instrumentation (opentelemetry-instrumentation not installed)")
            return
        otel = config.OTEL
        for key, module_name, class_name in instrumentors:
            if key in cls._instrumented_libraries:
                continue
            if key == "system_metrics" and not (
                otel.METRICS_ENABLED and otel.SYSTEM_METRICS_ENABLED and cls._meter_provider is not None
            ):
                logger.debug("Skipping system metrics instrumentation (disabled by config)")
                continue
            try:
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_cls = getattr(module, class_name)
                instrumentor = instrumentor_cls()
                if getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
                    cls._instrumented_libraries.add(key)
                    cls._after_library_instrumented(key)
                    logger.debug("Skipping already-instrumented library: %s", key)
                    continue
                cls._instrument_with_providers(instrumentor)
                cls._instrumented_libraries.add(key)
                cls._after_library_instrumented(key)
                logger.debug("Instrumented library: %s", key)
            except ImportError:
                logger.debug("Skipping OTel instrumentation for %s (package not installed)", key)
            except DependencyConflictError as e:
                cls._handle_instrumentation_conflict(key, e.conflict, module_name, class_name, otel)
            except Exception:
                logger.debug("Failed to instrument %s", key, exc_info=True)

    @classmethod
    def _after_library_instrumented(cls, key: str) -> None:
        """Apply the workaround that belongs to an instrumentor once it is bound."""
        if key == "redis":
            cls._guard_redis_search_attributes()

    @classmethod
    def _guard_redis_search_attributes(cls) -> None:
        """Keep ``opentelemetry-instrumentation-redis`` from raising into the application on a RESP3 search reply.

        The instrumentor parses an ``FT.SEARCH`` reply as a list, but RESP3 (ArchiPy's default) returns a mapping,
        so reading ``response[0]`` raises ``KeyError`` inside the caller's search. The guard calls the original and,
        when it cannot read the reply, records what it can from a mapping reply instead of raising. Idempotent.
        """
        try:
            import opentelemetry.instrumentation.redis as redis_instrumentation
            from opentelemetry.instrumentation.redis import util as redis_util
        except ImportError:
            return
        original = redis_util._add_search_attributes
        if getattr(original, _REDIS_SEARCH_GUARD_MARKER, None) is not None:
            return

        def guarded(span: Any, response: Any, args: Any) -> None:
            try:
                original(span, response, args)
            except KeyError, TypeError, IndexError:
                logger.debug("Redis search reply not understood by the OTel instrumentor", exc_info=True)
                total = response.get("total_results") if isinstance(response, dict) else None
                if total is not None:
                    span.set_attribute("redis.search.total", total)

        setattr(guarded, _REDIS_SEARCH_GUARD_MARKER, original)
        # The helper is imported by name into the instrumentor module, so both bindings are replaced.
        for module in (redis_util, redis_instrumentation):
            setattr(module, _REDIS_SEARCH_ATTRIBUTES_NAME, guarded)

    @classmethod
    def restore_redis_search_attributes(cls) -> None:
        """Undo :meth:`_guard_redis_search_attributes` (used by tests that need the upstream behaviour)."""
        try:
            import opentelemetry.instrumentation.redis as redis_instrumentation
            from opentelemetry.instrumentation.redis import util as redis_util
        except ImportError:
            return
        original = getattr(redis_util._add_search_attributes, _REDIS_SEARCH_GUARD_MARKER, None)
        if original is not None:
            for module in (redis_util, redis_instrumentation):
                setattr(module, _REDIS_SEARCH_ATTRIBUTES_NAME, original)

    @classmethod
    def _handle_instrumentation_conflict(
        cls,
        key: str,
        conflict: Any,
        module_name: str,
        class_name: str,
        otel: Any,
    ) -> None:
        """React to a ``DependencyConflictError`` raised by an instrumentor.

        A target library that is absent is skipped at debug level. One that is installed but outside the
        instrumentor's supported range would otherwise fail silently, so it is either instrumented anyway (when
        listed in ``OTEL.INSTRUMENTATION_SKIP_DEP_CHECK``) or reported at warning level.
        """
        if not (conflict.found or conflict.found_any):
            logger.debug("Skipping OTel instrumentation for %s (%s)", key, conflict)
        elif key in otel.INSTRUMENTATION_SKIP_DEP_CHECK:
            instrumentor_cls = getattr(__import__(module_name, fromlist=[class_name]), class_name)
            cls._instrument_ignoring_version_range(key, instrumentor_cls)
        else:
            # Without this the service would run silently without these spans.
            logger.warning(
                "OTel instrumentation for %s is disabled, no spans will be emitted: the installed version "
                "is outside the range the instrumentor supports (%s)",
                key,
                conflict,
            )

    @classmethod
    def _instrument_ignoring_version_range(cls, key: str, instrumentor_cls: Any) -> None:
        """Instrument a library whose installed version is newer than the instrumentor's declared range.

        Some instrumentors cap the library version in their metadata long before the runtime hooks they use
        break (for example ``opentelemetry-instrumentation-sqlalchemy`` caps SQLAlchemy below 2.1). Keys listed in
        ``OTEL.INSTRUMENTATION_SKIP_DEP_CHECK`` are instrumented anyway, with a warning.
        """
        try:
            cls._instrument_with_providers(instrumentor_cls(), skip_dep_check=True)
        except Exception:
            logger.warning(
                "OTel instrumentation for %s is disabled, no spans will be emitted: the installed version is "
                "outside the range the instrumentor supports and instrumenting it anyway failed",
                key,
                exc_info=True,
            )
            return
        cls._instrumented_libraries.add(key)
        logger.warning(
            "OTel instrumentation for %s is enabled although the installed version is outside the range the "
            "instrumentor declares (OTEL.INSTRUMENTATION_SKIP_DEP_CHECK); remove %r from that setting once the "
            "instrumentor supports this version",
            key,
            key,
        )

    @classmethod
    def _instrument_with_providers(cls, instrumentor: Any, *, skip_dep_check: bool = False) -> None:
        """Instrument with ArchiPy's providers; raise ``DependencyConflictError`` on a missing target library."""
        kwargs: dict[str, Any] = {"skip_dep_check": True} if skip_dep_check else {"raise_exception_on_conflict": True}
        if cls._tracer_provider is not None:
            kwargs["tracer_provider"] = cls._tracer_provider
        if cls._meter_provider is not None:
            kwargs["meter_provider"] = cls._meter_provider
        try:
            instrumentor.instrument(**kwargs)
        except TypeError:
            kwargs.pop("meter_provider", None)
            instrumentor.instrument(**kwargs)

    @classmethod
    def _register_atexit(cls) -> None:
        if cls._atexit_registered:
            return

        def _shutdown() -> None:
            try:
                cls.shutdown()
            except Exception:
                logger.debug("Error during OTel atexit shutdown", exc_info=True)

        atexit.register(_shutdown)
        cls._atexit_registered = True


# Re-export install hints for app_utils
OTEL_FASTAPI_INSTALL_HINT = _OTEL_FASTAPI_HINT
OTEL_GRPC_INSTALL_HINT = _OTEL_GRPC_HINT
OTEL_INSTALL_HINT = _OTEL_INSTALL_HINT
