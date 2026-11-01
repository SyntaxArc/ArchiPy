"""Builders for the OTLP and console exporters of the OpenTelemetry signals."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import grpc
    from opentelemetry.exporter.otlp.proto.http import Compression
    from opentelemetry.sdk._logs import ReadableLogRecord
    from opentelemetry.sdk._logs.export import LogRecordExporter
    from opentelemetry.sdk.metrics.export import MetricExporter
    from opentelemetry.sdk.trace.export import SpanExporter

    from archipy.configs.config_template import OpentelemetryConfig


def create_console_log_exporter() -> LogRecordExporter:
    """Return a console exporter that splits INFO/DEBUG to stdout and WARNING+ to stderr."""
    import sys

    from opentelemetry._logs.severity import SeverityNumber
    from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, LogRecordExporter, LogRecordExportResult

    stdout_exporter = ConsoleLogRecordExporter(out=sys.stdout)
    stderr_exporter = ConsoleLogRecordExporter(out=sys.stderr)
    warn_min = SeverityNumber.WARN

    class _StdoutStderrLogExporter(LogRecordExporter):
        """Route log records to stdout or stderr by severity."""

        def export(self, batch: Sequence[ReadableLogRecord]) -> LogRecordExportResult:
            low: list[ReadableLogRecord] = []
            high: list[ReadableLogRecord] = []
            for record in batch:
                severity = getattr(record.log_record, "severity_number", None) or SeverityNumber.UNSPECIFIED
                severity_value = severity.value if isinstance(severity, SeverityNumber) else int(severity)
                if severity_value >= warn_min.value:
                    high.append(record)
                else:
                    low.append(record)
            results: list[LogRecordExportResult] = []
            if low:
                results.append(stdout_exporter.export(low))
            if high:
                results.append(stderr_exporter.export(high))
            if any(result == LogRecordExportResult.FAILURE for result in results):
                return LogRecordExportResult.FAILURE
            return LogRecordExportResult.SUCCESS

        def shutdown(self) -> None:
            stdout_exporter.shutdown()
            stderr_exporter.shutdown()

        def force_flush(self, timeout_millis: float = 30_000) -> bool:
            _ = timeout_millis
            return True

    return _StdoutStderrLogExporter()


def resolve_otlp_endpoint(
    otel: OpentelemetryConfig,
    signal: str,
    override: object | None,
) -> str:
    """Resolve the OTLP endpoint for a signal.

    Prefer a per-signal override. For ``http/protobuf``, append
    ``/v1/{signal}`` when the base URL has no path (or only ``/``).
    gRPC uses the base endpoint as-is.

    Args:
        otel: OpenTelemetry config section.
        signal: One of ``traces``, ``metrics``, or ``logs``.
        override: Optional per-signal endpoint override.

    Returns:
        The resolved endpoint URL.
    """
    from urllib.parse import urlparse, urlunparse

    if override:
        return str(override).rstrip("/")
    base = str(otel.OTLP_ENDPOINT).rstrip("/")
    if otel.PROTOCOL != "http/protobuf":
        return base
    parsed = urlparse(base)
    path = (parsed.path or "").rstrip("/")
    if path:
        return base
    return urlunparse(parsed._replace(path=f"/v1/{signal}"))


def resolve_metrics_endpoint(otel: OpentelemetryConfig) -> str:
    """Return the resolved OTLP metrics endpoint for Temporal / callers.

    Args:
        otel: OpenTelemetry config section.

    Returns:
        The resolved metrics endpoint URL.
    """
    return resolve_otlp_endpoint(otel, "metrics", getattr(otel, "METRICS_ENDPOINT", None))


def _http_compression(otel: OpentelemetryConfig) -> Compression | None:
    """Return gzip for the HTTP exporters when ``OTLP_COMPRESSION`` asks for it."""
    from opentelemetry.exporter.otlp.proto.http import Compression

    return Compression.Gzip if otel.OTLP_COMPRESSION == "gzip" else None


def _grpc_compression(otel: OpentelemetryConfig) -> grpc.Compression | None:
    """Return gzip for the gRPC exporters when ``OTLP_COMPRESSION`` asks for it."""
    import grpc

    return grpc.Compression.Gzip if otel.OTLP_COMPRESSION == "gzip" else None


def _signal_headers(otel: OpentelemetryConfig, signal: str) -> dict[str, str] | None:
    """Return the OTLP headers of one signal: ``<SIGNAL>_HEADERS`` when set, else ``OTLP_HEADERS``.

    A per-signal value replaces the shared one instead of merging with it, as the OpenTelemetry specification
    defines, so two signals can carry different ``Authorization`` headers.
    """
    specific: dict[str, str] | None = getattr(otel, f"{signal}_HEADERS", None)
    return dict(specific if specific is not None else otel.OTLP_HEADERS) or None


def create_span_exporter(otel: OpentelemetryConfig) -> SpanExporter:
    headers = _signal_headers(otel, "TRACES")
    endpoint = resolve_otlp_endpoint(otel, "traces", getattr(otel, "TRACES_ENDPOINT", None))
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(
            endpoint=endpoint,
            headers=headers,
            timeout=otel.TIMEOUT,
            compression=_http_compression(otel),
        )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )

    return OTLPSpanExporter(
        endpoint=endpoint,
        headers=headers,
        timeout=otel.TIMEOUT,
        compression=_grpc_compression(otel),
    )


def create_metric_exporter(otel: OpentelemetryConfig) -> MetricExporter:
    headers = _signal_headers(otel, "METRICS")
    endpoint = resolve_metrics_endpoint(otel)
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )

        return OTLPMetricExporter(
            endpoint=endpoint,
            headers=headers,
            timeout=otel.TIMEOUT,
            compression=_http_compression(otel),
        )
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )

    return OTLPMetricExporter(
        endpoint=endpoint,
        headers=headers,
        timeout=otel.TIMEOUT,
        compression=_grpc_compression(otel),
    )


def create_otlp_log_exporter(otel: OpentelemetryConfig) -> LogRecordExporter:
    headers = _signal_headers(otel, "LOGS")
    endpoint = resolve_otlp_endpoint(otel, "logs", getattr(otel, "LOGS_ENDPOINT", None))
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )

        return OTLPLogExporter(
            endpoint=endpoint,
            headers=headers,
            timeout=otel.TIMEOUT,
            compression=_http_compression(otel),
        )
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
        OTLPLogExporter,
    )

    return OTLPLogExporter(
        endpoint=endpoint,
        headers=headers,
        timeout=otel.TIMEOUT,
        compression=_grpc_compression(otel),
    )
