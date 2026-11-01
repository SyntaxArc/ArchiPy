"""Builders of the tracer, meter and logger providers from the OpenTelemetry config."""

from __future__ import annotations

from typing import TYPE_CHECKING

from archipy.helpers.utils._otel import temporal_providers
from archipy.helpers.utils._otel.exporters import (
    create_console_log_exporter,
    create_metric_exporter,
    create_otlp_log_exporter,
    create_span_exporter,
)
from archipy.helpers.utils._otel.sampling import create_sampler

if TYPE_CHECKING:
    from collections.abc import Callable

    from opentelemetry.sdk._logs.export import LogRecordExporter
    from opentelemetry.sdk.metrics._internal.export import CardinalityLimits
    from opentelemetry.sdk.metrics.export import MetricExporter, MetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanLimits
    from opentelemetry.sdk.trace.export import SpanExporter
    from prometheus_client import CollectorRegistry

    from archipy.configs.config_template import OpentelemetryConfig
    from archipy.helpers.utils._otel.provider_types import OwnedLoggerProvider, OwnedMeterProvider, OwnedTracerProvider


def create_span_limits(otel: OpentelemetryConfig) -> SpanLimits | None:
    """Return the span limits the config sets, or ``None`` when it sets none so the SDK defaults apply."""
    from opentelemetry.sdk.trace import SpanLimits

    values = {
        "max_attributes": otel.ATTRIBUTE_COUNT_LIMIT,
        "max_attribute_length": otel.ATTRIBUTE_VALUE_LENGTH_LIMIT,
        "max_span_attributes": otel.SPAN_ATTRIBUTE_COUNT_LIMIT,
        "max_span_attribute_length": otel.SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT,
        "max_events": otel.SPAN_EVENT_COUNT_LIMIT,
        "max_links": otel.SPAN_LINK_COUNT_LIMIT,
    }
    if all(value is None for value in values.values()):
        return None
    return SpanLimits(**values)


def build_tracer_provider(
    otel: OpentelemetryConfig,
    resource: Resource,
    span_exporter_factory: Callable[[OpentelemetryConfig], SpanExporter] = create_span_exporter,
) -> OwnedTracerProvider:
    """Build a tracer provider with the configured sampler and a batch span processor.

    Args:
        otel: OpenTelemetry config section.
        resource: Resource describing the service.
        span_exporter_factory: Builds the span exporter; the runtime passes its own seam so callers can swap it.

    Returns:
        The tracer provider.
    """
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = temporal_providers.new_tracer_provider(resource, create_sampler(otel), create_span_limits(otel))
    exporter = span_exporter_factory(otel)
    provider.add_span_processor(
        BatchSpanProcessor(
            exporter,
            max_queue_size=otel.SPAN_BATCH_MAX_QUEUE_SIZE,
            schedule_delay_millis=otel.SPAN_BATCH_SCHEDULE_DELAY_MS,
            max_export_batch_size=otel.SPAN_BATCH_MAX_EXPORT_BATCH_SIZE,
            export_timeout_millis=otel.SPAN_BATCH_EXPORT_TIMEOUT_MS,
        ),
    )
    return provider


def build_meter_provider(
    otel: OpentelemetryConfig,
    resource: Resource,
    metric_exporter_factory: Callable[[OpentelemetryConfig], MetricExporter] = create_metric_exporter,
) -> tuple[OwnedMeterProvider, CollectorRegistry | None]:
    """Build a meter provider for the configured metrics exporter.

    Args:
        otel: OpenTelemetry config section.
        resource: Resource describing the service.
        metric_exporter_factory: Builds the OTLP metric exporter.

    Returns:
        The provider, and the Prometheus registry when the exporter is ``pull`` or ``pushgateway`` (else ``None``).
    """
    from opentelemetry.sdk.metrics import MeterProvider

    from archipy.configs.config_template import OtelMetricsExporter

    readers: list[MetricReader] = []
    registry: CollectorRegistry | None = None
    cardinality_limits = metrics_cardinality_limits(otel.METRICS_CARDINALITY_LIMIT)
    if otel.METRICS_EXPORTER == OtelMetricsExporter.OTLP:
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        exporter = metric_exporter_factory(otel)
        readers.append(
            PeriodicExportingMetricReader(
                exporter,
                export_interval_millis=otel.METRIC_EXPORT_INTERVAL_MS,
                cardinality_limits=cardinality_limits,
            ),
        )
    elif otel.METRICS_EXPORTER in {OtelMetricsExporter.PULL, OtelMetricsExporter.PUSHGATEWAY}:
        from opentelemetry.exporter.prometheus import PrometheusMetricReader
        from prometheus_client import CollectorRegistry

        registry = CollectorRegistry(auto_describe=True)
        readers.append(PrometheusMetricReader(registry=registry, cardinality_limits=cardinality_limits))

    return temporal_providers.wrap_meter_provider(MeterProvider(resource=resource, metric_readers=readers)), registry


def metrics_cardinality_limits(limit: int | None) -> CardinalityLimits | None:
    """Build per-instrument cardinality limits for a metric reader.

    Args:
        limit: Maximum distinct attribute sets per instrument, or None for the SDK default.

    Returns:
        A mapping of every instrument class to ``limit``, or None when no limit is configured.
    """
    if limit is None:
        return None
    from opentelemetry.sdk.metrics import (
        Counter,
        Histogram,
        ObservableCounter,
        ObservableGauge,
        ObservableUpDownCounter,
        UpDownCounter,
    )
    from opentelemetry.sdk.metrics._internal.instrument import Gauge  # not exported publicly

    instruments = (
        Counter,
        UpDownCounter,
        Histogram,
        Gauge,
        ObservableCounter,
        ObservableUpDownCounter,
        ObservableGauge,
    )
    return dict.fromkeys(instruments, limit)


def build_logger_provider(
    otel: OpentelemetryConfig,
    resource: Resource,
    console_exporter_factory: Callable[[], LogRecordExporter] = create_console_log_exporter,
    otlp_exporter_factory: Callable[[OpentelemetryConfig], LogRecordExporter] = create_otlp_log_exporter,
) -> OwnedLoggerProvider:
    """Build a logger provider with a console (simple) or OTLP (batch) log record processor.

    With ``temporalio`` installed the provider is replay-safe, so records emitted from workflow code are not
    duplicated on replay.

    Args:
        otel: OpenTelemetry config section.
        resource: Resource describing the service.
        console_exporter_factory: Builds the console log exporter.
        otlp_exporter_factory: Builds the OTLP log exporter.

    Returns:
        The logger provider.
    """
    from opentelemetry.sdk._logs import LoggerProvider
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor

    from archipy.configs.config_template import OtelLogsExporter

    provider = LoggerProvider(resource=resource)
    if otel.LOGS_EXPORTER == OtelLogsExporter.CONSOLE:
        provider.add_log_record_processor(SimpleLogRecordProcessor(console_exporter_factory()))
    else:
        exporter = otlp_exporter_factory(otel)
        provider.add_log_record_processor(
            BatchLogRecordProcessor(
                exporter,
                max_queue_size=otel.LOG_BATCH_MAX_QUEUE_SIZE,
                schedule_delay_millis=otel.LOG_BATCH_SCHEDULE_DELAY_MS,
                max_export_batch_size=otel.LOG_BATCH_MAX_EXPORT_BATCH_SIZE,
                export_timeout_millis=otel.LOG_BATCH_EXPORT_TIMEOUT_MS,
            ),
        )
    # Wrapped last: the replay-safe wrapper only forwards to the processors already attached.
    return temporal_providers.wrap_logger_provider(provider)
