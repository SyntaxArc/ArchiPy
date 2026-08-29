"""OpenTelemetry utilities for provider lifecycle, instrumentation, and status mapping."""

from __future__ import annotations

import atexit
import logging
import threading
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)

HTTP_SERVER_ERROR_MIN = 500

_OTEL_INSTALL_HINT = 'OpenTelemetry requires the optional dependency. Install with: uv add "archipy[otel]"'
_OTEL_FASTAPI_HINT = 'FastAPI OTel instrumentation requires: uv add "archipy[otel-fastapi]"'
_OTEL_GRPC_HINT = 'gRPC OTel instrumentation requires: uv add "archipy[otel-grpc]"'


class OtelUtils:
    """Idempotent OpenTelemetry provider management and helpers.

    Owns ``TracerProvider`` / ``MeterProvider`` / ``LoggerProvider`` references and
    passes them explicitly to instrumentors. Globals are set once for third-party
    interop (e.g. Temporal ``TracingInterceptor``), but internal callers use
    ``get_tracer`` / ``get_meter`` against owned providers.

    Providers are built programmatically from ``BaseConfig.OTEL`` only —
    ``OTEL_*`` environment-variable autoconfiguration is not used.
    """

    _lock = threading.Lock()
    _initialized: bool = False
    _logging_handler_attached: bool = False
    _atexit_registered: bool = False
    _instrumented_libraries: ClassVar[set[str]] = set()

    _tracer_provider: Any | None = None
    _meter_provider: Any | None = None
    _logger_provider: Any | None = None
    _globals_set: bool = False

    @staticmethod
    def is_otel_enabled(config: BaseConfig) -> bool:
        """Return True when the OTel master switch is enabled.

        Args:
            config: Application configuration.

        Returns:
            True if ``config.OTEL.IS_ENABLED`` is True.
        """
        return bool(config.OTEL.IS_ENABLED)

    @classmethod
    def get_tracer(cls, name: str) -> Any:
        """Return a tracer from the owned tracer provider (or a no-op tracer).

        Args:
            name: Instrumentation scope name.

        Returns:
            An OpenTelemetry ``Tracer`` instance.
        """
        from opentelemetry import trace

        if cls._tracer_provider is not None:
            return cls._tracer_provider.get_tracer(name)
        return trace.get_tracer(name)

    @classmethod
    def get_meter(cls, name: str) -> Any:
        """Return a meter from the owned meter provider (or a no-op meter).

        Args:
            name: Instrumentation scope name.

        Returns:
            An OpenTelemetry ``Meter`` instance.
        """
        from opentelemetry import metrics

        if cls._meter_provider is not None:
            return cls._meter_provider.get_meter(name)
        return metrics.get_meter(name)

    @classmethod
    def tracer_provider(cls) -> Any | None:
        """Return the owned tracer provider, if initialized."""
        return cls._tracer_provider

    @classmethod
    def meter_provider(cls) -> Any | None:
        """Return the owned meter provider, if initialized."""
        return cls._meter_provider

    @staticmethod
    def status_for_exception(exception: BaseException) -> Any:
        """Map an exception to an OpenTelemetry ``Status``.

        ``BaseError`` with ``http_status`` below 500 leaves the span OK (client
        error — server handled the request correctly). All other exceptions
        become ``StatusCode.ERROR``.

        Args:
            exception: The exception raised during a span.

        Returns:
            An OpenTelemetry ``Status`` instance.
        """
        from opentelemetry.trace import Status, StatusCode

        from archipy.models.errors.base_error import BaseError

        if isinstance(exception, BaseError) and exception.http_status < HTTP_SERVER_ERROR_MIN:
            return Status(StatusCode.OK)
        return Status(StatusCode.ERROR, description=str(exception))

    @classmethod
    def init_otel_if_needed(cls, config: BaseConfig) -> None:
        """Initialize OTel providers once (idempotent, thread-safe).

        Args:
            config: Application configuration.
        """
        if not config.OTEL.IS_ENABLED or cls._initialized:
            return

        with cls._lock:
            if not config.OTEL.IS_ENABLED or cls._initialized:
                return
            try:
                cls._build_providers(config)
                cls._instrument_installed_libraries()
                cls._register_atexit()
                cls._initialized = True
            except ImportError:
                logger.debug("%s", _OTEL_INSTALL_HINT)
            except Exception:
                logger.exception("Failed to initialize OpenTelemetry")

    @classmethod
    def configure_for_testing(
        cls,
        span_exporter: Any | None = None,
        metric_reader: Any | None = None,
        *,
        service_name: str = "archipy-test",
    ) -> None:
        """Swap in in-memory providers for BDD / unit tests.

        Args:
            span_exporter: Optional span exporter (e.g. ``InMemorySpanExporter``).
            metric_reader: Optional metric reader (e.g. ``InMemoryMetricReader``).
            service_name: Resource service name for the test providers.
        """
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        with cls._lock:
            resource = Resource.create({"service.name": service_name})
            tracer_provider = TracerProvider(resource=resource)
            if span_exporter is not None:
                tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
            cls._tracer_provider = tracer_provider
            if not cls._globals_set:
                trace.set_tracer_provider(tracer_provider)

            if metric_reader is not None:
                from opentelemetry.sdk.metrics import MeterProvider

                meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
                cls._meter_provider = meter_provider
                if not cls._globals_set:
                    metrics.set_meter_provider(meter_provider)

            cls._globals_set = True
            cls._initialized = True

    @classmethod
    def reset_for_testing(cls) -> None:
        """Reset owned providers for the next BDD scenario.

        Does not replace OTel globals (first-call-wins); subsequent scenarios
        reuse ``configure_for_testing`` which overwrites class attributes and
        rebuilds processors/readers on the existing global providers when possible.
        """
        with cls._lock:
            if cls._tracer_provider is not None:
                try:
                    cls._tracer_provider.shutdown()
                except Exception:
                    logger.debug("Error shutting down test tracer provider", exc_info=True)
            if cls._meter_provider is not None:
                try:
                    cls._meter_provider.shutdown()
                except Exception:
                    logger.debug("Error shutting down test meter provider", exc_info=True)
            if cls._logger_provider is not None:
                try:
                    cls._logger_provider.shutdown()
                except Exception:
                    logger.debug("Error shutting down test logger provider", exc_info=True)
            cls._tracer_provider = None
            cls._meter_provider = None
            cls._logger_provider = None
            cls._initialized = False
            cls._instrumented_libraries.clear()

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
    def _build_providers(cls, config: BaseConfig) -> None:
        """Build and register tracer/meter/logger providers from config."""
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.resources import Resource

        otel = config.OTEL
        resource_attrs: dict[str, Any] = dict(otel.RESOURCE_ATTRIBUTES)
        if otel.SERVICE_NAME:
            resource_attrs["service.name"] = otel.SERVICE_NAME
        if otel.ENVIRONMENT is not None:
            resource_attrs["deployment.environment"] = str(otel.ENVIRONMENT)
        resource = Resource.create(resource_attrs)

        if otel.TRACES_ENABLED:
            cls._tracer_provider = cls._build_tracer_provider(otel, resource)
            if not cls._globals_set:
                trace.set_tracer_provider(cls._tracer_provider)

        if otel.METRICS_ENABLED:
            cls._meter_provider = cls._build_meter_provider(otel, resource)
            if not cls._globals_set:
                metrics.set_meter_provider(cls._meter_provider)

        if otel.LOGS_ENABLED:
            cls._logger_provider = cls._build_logger_provider(otel, resource)
            cls._attach_logging_handler(otel)

        cls._globals_set = True

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
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        exporter = cls._create_metric_exporter(otel)
        reader = PeriodicExportingMetricReader(
            exporter,
            export_interval_millis=otel.METRIC_EXPORT_INTERVAL_MS,
        )
        return MeterProvider(resource=resource, metric_readers=[reader])

    @classmethod
    def _build_logger_provider(cls, otel: Any, resource: Any) -> Any:
        from opentelemetry._logs import set_logger_provider
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor

        provider = LoggerProvider(resource=resource)
        exporter = cls._create_log_exporter(otel)
        provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
        set_logger_provider(provider)
        return provider

    @classmethod
    def _create_span_exporter(cls, otel: Any) -> Any:
        headers = dict(otel.OTLP_HEADERS) or None
        if otel.PROTOCOL == "http/protobuf":
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            return OTLPSpanExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)

    @classmethod
    def _create_metric_exporter(cls, otel: Any) -> Any:
        headers = dict(otel.OTLP_HEADERS) or None
        if otel.PROTOCOL == "http/protobuf":
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )

            return OTLPMetricExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
            OTLPMetricExporter,
        )

        return OTLPMetricExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)

    @classmethod
    def _create_log_exporter(cls, otel: Any) -> Any:
        headers = dict(otel.OTLP_HEADERS) or None
        if otel.PROTOCOL == "http/protobuf":
            from opentelemetry.exporter.otlp.proto.http._log_exporter import (
                OTLPLogExporter,
            )

            return OTLPLogExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)
        from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
            OTLPLogExporter,
        )

        return OTLPLogExporter(endpoint=otel.OTLP_ENDPOINT, headers=headers, timeout=otel.TIMEOUT)

    @classmethod
    def _attach_logging_handler(cls, otel: Any) -> None:
        if cls._logging_handler_attached or cls._logger_provider is None:
            return
        from opentelemetry.sdk._logs import LoggingHandler

        level = getattr(logging, otel.LOGS_LEVEL.upper(), logging.INFO)
        handler = LoggingHandler(level=level, logger_provider=cls._logger_provider)
        logging.getLogger().addHandler(handler)
        cls._logging_handler_attached = True

    @classmethod
    def _instrument_installed_libraries(cls) -> None:
        """Best-effort auto-instrumentation of installed contrib packages.

        Each entry is ``(cache_key, module, class_name)``. Missing packages are
        skipped via ``ImportError`` — install the matching ``archipy[otel-*]``
        extra (or the contrib package directly) to enable them.

        Driver-level DB instrumentors (psycopg/pymysql/sqlite3) are omitted:
        ArchiPy goes through SQLAlchemy — use ``archipy[otel-sqlalchemy]``.
        """
        instrumentors: Sequence[tuple[str, str, str]] = (
            # Context propagation (no spans of its own)
            ("threading", "opentelemetry.instrumentation.threading", "ThreadingInstrumentor"),
            # Host/process metrics (included in archipy[otel])
            ("system_metrics", "opentelemetry.instrumentation.system_metrics", "SystemMetricsInstrumentor"),
            # Adapters / HTTP
            ("sqlalchemy", "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
            ("redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor"),
            ("elasticsearch", "opentelemetry.instrumentation.elasticsearch", "ElasticsearchInstrumentor"),
            ("cassandra", "opentelemetry.instrumentation.cassandra", "CassandraInstrumentor"),
            ("confluent_kafka", "opentelemetry.instrumentation.confluent_kafka", "ConfluentKafkaInstrumentor"),
            ("botocore", "opentelemetry.instrumentation.botocore", "BotocoreInstrumentor"),
            ("httpx", "opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
            ("requests", "opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
        )
        for key, module_name, class_name in instrumentors:
            if key in cls._instrumented_libraries:
                continue
            try:
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_cls = getattr(module, class_name)
                kwargs: dict[str, Any] = {}
                if cls._tracer_provider is not None:
                    kwargs["tracer_provider"] = cls._tracer_provider
                if cls._meter_provider is not None:
                    kwargs["meter_provider"] = cls._meter_provider
                try:
                    instrumentor_cls().instrument(**kwargs)
                except TypeError:
                    # Older instrumentors may not accept meter_provider
                    kwargs.pop("meter_provider", None)
                    instrumentor_cls().instrument(**kwargs)
                cls._instrumented_libraries.add(key)
                logger.debug("Instrumented library: %s", key)
            except ImportError:
                logger.debug("Skipping OTel instrumentation for %s (package not installed)", key)
            except Exception:
                logger.debug("Failed to instrument %s", key, exc_info=True)

    @classmethod
    def _register_atexit(cls) -> None:
        if cls._atexit_registered:
            return

        def _shutdown() -> None:
            for provider in (cls._tracer_provider, cls._meter_provider, cls._logger_provider):
                if provider is not None:
                    try:
                        provider.shutdown()
                    except Exception:
                        logger.debug("Error during OTel provider shutdown", exc_info=True)

        atexit.register(_shutdown)
        cls._atexit_registered = True


# Re-export install hints for app_utils
OTEL_FASTAPI_INSTALL_HINT = _OTEL_FASTAPI_HINT
OTEL_GRPC_INSTALL_HINT = _OTEL_GRPC_HINT
OTEL_INSTALL_HINT = _OTEL_INSTALL_HINT
