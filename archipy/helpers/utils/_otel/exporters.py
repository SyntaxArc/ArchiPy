"""Builders for the OTLP and console exporters of the OpenTelemetry signals."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


def create_console_log_exporter() -> Any:
    """Return a console exporter that splits INFO/DEBUG to stdout and WARNING+ to stderr."""
    import sys

    from opentelemetry._logs.severity import SeverityNumber
    from opentelemetry.sdk._logs.export import ConsoleLogRecordExporter, LogRecordExportResult

    stdout_exporter = ConsoleLogRecordExporter(out=sys.stdout)
    stderr_exporter = ConsoleLogRecordExporter(out=sys.stderr)
    warn_min = SeverityNumber.WARN

    class _StdoutStderrLogExporter:
        """Route log records to stdout or stderr by severity."""

        def export(self, batch: Sequence[Any]) -> Any:
            low: list[Any] = []
            high: list[Any] = []
            for record in batch:
                severity = getattr(record.log_record, "severity_number", None) or SeverityNumber.UNSPECIFIED
                severity_value = severity.value if isinstance(severity, SeverityNumber) else int(severity)
                if severity_value >= warn_min.value:
                    high.append(record)
                else:
                    low.append(record)
            results: list[Any] = []
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

        def force_flush(self, timeout_millis: int = 30_000) -> bool:
            _ = timeout_millis
            return True

    return _StdoutStderrLogExporter()


def resolve_otlp_endpoint(
    otel: Any,
    signal: str,
    override: Any | None,
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


def resolve_metrics_endpoint(otel: Any) -> str:
    """Return the resolved OTLP metrics endpoint for Temporal / callers.

    Args:
        otel: OpenTelemetry config section.

    Returns:
        The resolved metrics endpoint URL.
    """
    return resolve_otlp_endpoint(otel, "metrics", getattr(otel, "METRICS_ENDPOINT", None))


def create_span_exporter(otel: Any) -> Any:
    headers = dict(otel.OTLP_HEADERS) or None
    endpoint = resolve_otlp_endpoint(otel, "traces", getattr(otel, "TRACES_ENDPOINT", None))
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )

    return OTLPSpanExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)


def create_metric_exporter(otel: Any) -> Any:
    headers = dict(otel.OTLP_HEADERS) or None
    endpoint = resolve_metrics_endpoint(otel)
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )

        return OTLPMetricExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )

    return OTLPMetricExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)


def create_otlp_log_exporter(otel: Any) -> Any:
    headers = dict(otel.OTLP_HEADERS) or None
    endpoint = resolve_otlp_endpoint(otel, "logs", getattr(otel, "LOGS_ENDPOINT", None))
    if otel.PROTOCOL == "http/protobuf":
        from opentelemetry.exporter.otlp.proto.http._log_exporter import (
            OTLPLogExporter,
        )

        return OTLPLogExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
        OTLPLogExporter,
    )

    return OTLPLogExporter(endpoint=endpoint, headers=headers, timeout=otel.TIMEOUT)
