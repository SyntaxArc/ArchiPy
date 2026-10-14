"""Readers for the OTLP JSON files the OpenTelemetry Collector test container writes.

The collector exports every signal as OTLP JSON lines. These helpers decode them into light objects that
expose the same attributes the OpenTelemetry SDK's finished spans and metric data points do, so scenarios
can assert on what really crossed the wire instead of on in-memory exporters.

Every scenario runs with its own ``service.name``; readers keep only the telemetry of that service so late
exports from an earlier scenario cannot leak into the current one.
"""

import asyncio
import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from opentelemetry.trace import StatusCode

from archipy.helpers.utils.otel_utils import OtelUtils

# The collector's file exporter flushes every 100 ms; a short settle after a client-side flush lets it write.
SETTLE_SECONDS = 0.25
POLL_TIMEOUT_SECONDS = 5.0
POLL_STEP_SECONDS = 0.1

_STATUS_CODES = {
    0: StatusCode.UNSET,
    1: StatusCode.OK,
    2: StatusCode.ERROR,
    "STATUS_CODE_UNSET": StatusCode.UNSET,
    "STATUS_CODE_OK": StatusCode.OK,
    "STATUS_CODE_ERROR": StatusCode.ERROR,
}


def decode_value(value: dict[str, Any]) -> Any:
    """Decode an OTLP JSON ``AnyValue`` into a Python value."""
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        return int(value["intValue"])
    if "boolValue" in value:
        return bool(value["boolValue"])
    if "doubleValue" in value:
        return float(value["doubleValue"])
    if "arrayValue" in value:
        return [decode_value(item) for item in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return decode_attributes(value["kvlistValue"].get("values", []))
    return None


def decode_attributes(items: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Decode an OTLP JSON ``KeyValue`` list into a dict."""
    return {item["key"]: decode_value(item.get("value", {})) for item in items or []}


def _hex_to_int(value: str | None) -> int:
    return int(value, 16) if value else 0


def _resource_attributes(block: dict[str, Any]) -> dict[str, Any]:
    return decode_attributes(block.get("resource", {}).get("attributes"))


def _decode_span(span: dict[str, Any], resource: dict[str, Any]) -> SimpleNamespace:
    parent_id = _hex_to_int(span.get("parentSpanId"))
    status = span.get("status", {})
    return SimpleNamespace(
        name=span.get("name", ""),
        kind=span.get("kind"),
        attributes=decode_attributes(span.get("attributes")),
        status=SimpleNamespace(
            status_code=_STATUS_CODES.get(status.get("code", 0), StatusCode.UNSET),
            description=status.get("message"),
        ),
        events=[
            SimpleNamespace(name=event.get("name", ""), attributes=decode_attributes(event.get("attributes")))
            for event in span.get("events", [])
        ],
        context=SimpleNamespace(
            trace_id=_hex_to_int(span.get("traceId")),
            span_id=_hex_to_int(span.get("spanId")),
        ),
        parent=SimpleNamespace(span_id=parent_id) if parent_id else None,
        links=[
            SimpleNamespace(
                context=SimpleNamespace(
                    trace_id=_hex_to_int(link.get("traceId")),
                    span_id=_hex_to_int(link.get("spanId")),
                ),
            )
            for link in span.get("links", [])
        ],
        resource=SimpleNamespace(attributes=resource),
    )


def _decode_log(record: dict[str, Any], resource: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        body=decode_value(record.get("body", {})),
        attributes=decode_attributes(record.get("attributes")),
        severity_text=record.get("severityText"),
        trace_id=_hex_to_int(record.get("traceId")),
        span_id=_hex_to_int(record.get("spanId")),
        resource=SimpleNamespace(attributes=resource),
    )


def _decode_point(point: dict[str, Any]) -> SimpleNamespace:
    if "asInt" in point:
        value: Any = int(point["asInt"])
    elif "asDouble" in point:
        value = float(point["asDouble"])
    else:
        value = None
    return SimpleNamespace(
        attributes=decode_attributes(point.get("attributes")),
        value=value,
        count=int(point["count"]) if "count" in point else None,
        sum=float(point["sum"]) if "sum" in point else None,
        bucket_counts=[int(count) for count in point.get("bucketCounts", [])],
        explicit_bounds=[float(bound) for bound in point.get("explicitBounds", [])],
        time_unix_nano=int(point.get("timeUnixNano", 0)),
    )


def _decode_metric(metric: dict[str, Any]) -> SimpleNamespace:
    for kind in ("histogram", "sum", "gauge", "exponentialHistogram"):
        if kind in metric:
            points = [_decode_point(point) for point in metric[kind].get("dataPoints", [])]
            return SimpleNamespace(
                name=metric["name"],
                unit=metric.get("unit", ""),
                kind=kind,
                is_monotonic=metric[kind].get("isMonotonic"),
                data=SimpleNamespace(data_points=points),
            )
    return SimpleNamespace(name=metric["name"], unit=metric.get("unit", ""), kind=None, is_monotonic=None, data=SimpleNamespace(data_points=[]))


def _attribute_key(attributes: dict[str, Any]) -> tuple:
    return tuple(sorted((key, repr(value)) for key, value in attributes.items()))


class CollectorTelemetry:
    """Reads the telemetry one service exported to the collector test container."""

    def __init__(self, collector: Any, service_name: str) -> None:
        """Create a reader.

        Args:
            collector: The running ``OtelCollectorTestContainer``.
            service_name: ``service.name`` resource attribute of the scenario under test.
        """
        self.collector = collector
        self.service_name = service_name

    def flush(self) -> None:
        """Flush the client-side providers, then give the collector a moment to write the files."""
        OtelUtils.force_flush(timeout_millis=2000)
        time.sleep(SETTLE_SECONDS)

    def _is_mine(self, resource: dict[str, Any]) -> bool:
        return resource.get("service.name") == self.service_name

    def spans(self) -> list[SimpleNamespace]:
        """Return every exported span of this service, oldest first."""
        spans: list[SimpleNamespace] = []
        for document in self.collector.read_signal("traces"):
            for resource_spans in document.get("resourceSpans", []):
                resource = _resource_attributes(resource_spans)
                if not self._is_mine(resource):
                    continue
                for scope_spans in resource_spans.get("scopeSpans", []):
                    spans.extend(_decode_span(span, resource) for span in scope_spans.get("spans", []))
        return spans

    def logs(self) -> list[SimpleNamespace]:
        """Return every exported log record of this service, oldest first."""
        records: list[SimpleNamespace] = []
        for document in self.collector.read_signal("logs"):
            for resource_logs in document.get("resourceLogs", []):
                resource = _resource_attributes(resource_logs)
                if not self._is_mine(resource):
                    continue
                for scope_logs in resource_logs.get("scopeLogs", []):
                    records.extend(_decode_log(record, resource) for record in scope_logs.get("logRecords", []))
        return records

    def metrics(self) -> dict[str, SimpleNamespace]:
        """Return the latest cumulative snapshot of every exported instrument of this service.

        Each instrument keeps, per attribute set, the data point with the newest timestamp.
        """
        latest: dict[str, dict[tuple, SimpleNamespace]] = {}
        templates: dict[str, SimpleNamespace] = {}
        for document in self.collector.read_signal("metrics"):
            for resource_metrics in document.get("resourceMetrics", []):
                if not self._is_mine(_resource_attributes(resource_metrics)):
                    continue
                for scope_metrics in resource_metrics.get("scopeMetrics", []):
                    for raw_metric in scope_metrics.get("metrics", []):
                        metric = _decode_metric(raw_metric)
                        templates[metric.name] = metric
                        by_attributes = latest.setdefault(metric.name, {})
                        for point in metric.data.data_points:
                            key = _attribute_key(point.attributes)
                            known = by_attributes.get(key)
                            if known is None or point.time_unix_nano >= known.time_unix_nano:
                                by_attributes[key] = point
        result: dict[str, SimpleNamespace] = {}
        for name, template in templates.items():
            template.data = SimpleNamespace(data_points=list(latest[name].values()))
            result[name] = template
        return result

    def wait_for(self, read: Callable[[], Any], timeout: float = POLL_TIMEOUT_SECONDS) -> Any:
        """Poll ``read`` until it returns something truthy or the timeout passes; return the last result."""
        deadline = time.monotonic() + timeout
        result = read()
        while not result and time.monotonic() < deadline:
            time.sleep(POLL_STEP_SECONDS)
            result = read()
        return result


async def wait_for_metric_async(reader: CollectorTelemetry, name: str, timeout: float = POLL_TIMEOUT_SECONDS) -> None:
    """Wait (bounded) until the collector has received the named instrument; flushes the providers on each try."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        OtelUtils.force_flush(timeout_millis=2000)
        await asyncio.sleep(SETTLE_SECONDS)
        if name in reader.metrics():
            return
