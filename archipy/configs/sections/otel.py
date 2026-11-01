"""OpenTelemetry configuration."""

import logging
from enum import StrEnum
from itertools import pairwise
from typing import Literal, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator

from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)


class OtelMetricsExporter(StrEnum):
    """Unique metrics export mode for OpenTelemetry.

    Exactly one exporter is active when ``METRICS_ENABLED`` is true.
    """

    OTLP = "otlp"
    PULL = "pull"
    PUSHGATEWAY = "pushgateway"


class OtelLogsExporter(StrEnum):
    """Unique logs export mode for OpenTelemetry.

    Exactly one exporter is active when ``LOGS_ENABLED`` is true.
    """

    CONSOLE = "console"
    OTLP = "otlp"


class OtelSampler(StrEnum):
    """Trace sampler of the OpenTelemetry SDK, named as in the ``OTEL_TRACES_SAMPLER`` specification."""

    ALWAYS_ON = "always_on"
    ALWAYS_OFF = "always_off"
    TRACEIDRATIO = "traceidratio"
    PARENTBASED_ALWAYS_ON = "parentbased_always_on"
    PARENTBASED_ALWAYS_OFF = "parentbased_always_off"
    PARENTBASED_TRACEIDRATIO = "parentbased_traceidratio"


class OpentelemetryConfig(BaseModel):
    """Configuration settings for OpenTelemetry observability.

    Controls OTLP export of traces, metrics, and logs. Providers are built programmatically from this config.
    The SDK's own ``OTEL_*`` autoconfiguration is not used. With ``USE_STANDARD_ENV`` the standard variables fill in the
    settings that this config leaves unset, and an explicitly set field always wins. The resource also reads
    ``OTEL_SERVICE_NAME`` and ``OTEL_RESOURCE_ATTRIBUTES``, because the SDK's ``Resource.create`` does.
    """

    IS_ENABLED: bool = Field(default=False, description="Master switch for OpenTelemetry")
    TRACES_ENABLED: bool = Field(default=True, description="Export traces when OTel is enabled")
    METRICS_ENABLED: bool = Field(default=True, description="Export metrics when OTel is enabled")
    LOGS_ENABLED: bool = Field(default=True, description="Export logs when OTel is enabled")
    LOGS_EXPORTER: OtelLogsExporter = Field(
        default=OtelLogsExporter.CONSOLE,
        description=(
            "Unique logs exporter when LOGS_ENABLED is true: "
            "console (stdout for INFO/DEBUG, stderr for WARNING+) or otlp"
        ),
    )
    SERVICE_NAME: str | None = Field(default=None, description="OTel resource service.name")
    OTLP_ENDPOINT: HttpUrl = Field(
        default=HttpUrl("http://localhost:4317"),
        description=(
            "Default OTLP collector endpoint (gRPC port 4317; HTTP/protobuf typically 4318). "
            "For http/protobuf, signal paths (/v1/traces, /v1/metrics, /v1/logs) are appended "
            "when the URL has no path. Override per signal with TRACES/METRICS/LOGS_ENDPOINT."
        ),
    )
    TRACES_ENDPOINT: HttpUrl | None = Field(
        default=None,
        description="Optional per-signal OTLP traces endpoint (overrides OTLP_ENDPOINT)",
    )
    METRICS_ENDPOINT: HttpUrl | None = Field(
        default=None,
        description="Optional per-signal OTLP metrics endpoint (overrides OTLP_ENDPOINT)",
    )
    LOGS_ENDPOINT: HttpUrl | None = Field(
        default=None,
        description="Optional per-signal OTLP logs endpoint (overrides OTLP_ENDPOINT)",
    )
    PROTOCOL: Literal["grpc", "http/protobuf"] = Field(
        default="grpc",
        description="OTLP transport protocol",
    )
    OTLP_HEADERS: dict[str, str] = Field(
        default_factory=dict,
        description="Headers sent with each OTLP export (auth tokens, routing metadata)",
    )
    TRACES_HEADERS: dict[str, str] | None = Field(
        default=None,
        description="Optional per-signal OTLP traces headers; when set they replace OTLP_HEADERS for traces",
    )
    METRICS_HEADERS: dict[str, str] | None = Field(
        default=None,
        description="Optional per-signal OTLP metrics headers; when set they replace OTLP_HEADERS for metrics",
    )
    LOGS_HEADERS: dict[str, str] | None = Field(
        default=None,
        description="Optional per-signal OTLP logs headers; when set they replace OTLP_HEADERS for logs",
    )
    TIMEOUT: float = Field(default=10.0, ge=0.1, description="OTLP export timeout in seconds")
    TRACES_SAMPLER: OtelSampler = Field(
        default=OtelSampler.PARENTBASED_TRACEIDRATIO,
        description=(
            "Trace sampler. The default keeps the parent's decision and samples new traces at TRACES_SAMPLE_RATIO; "
            "the *_always_on / *_always_off samplers ignore the ratio"
        ),
    )
    TRACES_SAMPLE_RATIO: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description=(
            "Sampling ratio of the traceidratio and parentbased_traceidratio samplers "
            "(with the parent-based sampler, inbound sampled traces always continue)"
        ),
    )
    PROPAGATORS: list[Literal["tracecontext", "baggage", "b3", "b3multi", "none"]] = Field(
        default=["tracecontext", "baggage"],
        description=(
            "Context propagators, in order: tracecontext, baggage, b3 (single header), b3multi or none (no propagation)"
        ),
    )
    OTLP_COMPRESSION: Literal["none", "gzip"] = Field(
        default="none",
        description=(
            "Compression of OTLP exports for traces, metrics and logs. gzip is the only algorithm the OTLP "
            "specification defines, so every collector accepts it, and it cuts realistic payloads to about "
            "half or less; it costs CPU on the export thread, so it is worth it when the collector is across a network"
        ),
    )
    SPAN_BATCH_SCHEDULE_DELAY_MS: int = Field(
        default=5000,
        ge=1,
        description="Delay between two span exports of the batch processor in milliseconds",
    )
    SPAN_BATCH_EXPORT_TIMEOUT_MS: int = Field(
        default=30000,
        ge=1,
        description="Time the batch span processor allows one export in milliseconds",
    )
    SPAN_BATCH_MAX_QUEUE_SIZE: int = Field(
        default=4096,
        ge=1,
        description="Spans the batch processor queues before it drops new ones (a few MB of memory at most)",
    )
    SPAN_BATCH_MAX_EXPORT_BATCH_SIZE: int = Field(
        default=512,
        ge=1,
        description=(
            "Largest span batch of one export; at most SPAN_BATCH_MAX_QUEUE_SIZE. gRPC receivers reject messages over "
            "4 MiB by default, and spans with long SQL or stack traces reach several KB each, so keep batches small"
        ),
    )
    ATTRIBUTE_COUNT_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Most attributes a span, event or link keeps (None: SDK default, 128); the rest are dropped",
    )
    ATTRIBUTE_VALUE_LENGTH_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Longest attribute value kept in characters; longer values are truncated (None: no limit)",
    )
    SPAN_ATTRIBUTE_COUNT_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Most attributes a span keeps; overrides ATTRIBUTE_COUNT_LIMIT for spans",
    )
    SPAN_ATTRIBUTE_VALUE_LENGTH_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Longest span attribute value in characters; overrides ATTRIBUTE_VALUE_LENGTH_LIMIT for spans",
    )
    SPAN_EVENT_COUNT_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Most events a span keeps (None: SDK default, 128)",
    )
    SPAN_LINK_COUNT_LIMIT: int | None = Field(
        default=None,
        ge=0,
        description="Most links a span keeps (None: SDK default, 128)",
    )
    LOG_BATCH_SCHEDULE_DELAY_MS: int = Field(
        default=1000,
        ge=1,
        description="Delay between two log exports of the batch processor in milliseconds (LOGS_EXPORTER=otlp)",
    )
    LOG_BATCH_EXPORT_TIMEOUT_MS: int = Field(
        default=30000,
        ge=1,
        description="Time the batch log processor allows one export in milliseconds (LOGS_EXPORTER=otlp)",
    )
    LOG_BATCH_MAX_QUEUE_SIZE: int = Field(
        default=4096,
        ge=1,
        description="Log records the batch processor queues before it drops new ones (LOGS_EXPORTER=otlp)",
    )
    LOG_BATCH_MAX_EXPORT_BATCH_SIZE: int = Field(
        default=512,
        ge=1,
        description="Largest log batch of one export; at most LOG_BATCH_MAX_QUEUE_SIZE (LOGS_EXPORTER=otlp)",
    )
    USE_STANDARD_ENV: bool = Field(
        default=False,
        description=(
            "Read the standard OTEL_* environment variables (OTEL_EXPORTER_OTLP_*, OTEL_TRACES_SAMPLER*, "
            "OTEL_PROPAGATORS, OTEL_BSP_*, OTEL_BLRP_*, OTEL_METRIC_EXPORT_INTERVAL, OTEL_SERVICE_NAME) for every "
            "setting of this config that is not set explicitly. Invalid values are logged and ignored"
        ),
    )
    SERVICE_VERSION: str | None = Field(default=None, description="OTel resource service.version")
    SERVICE_INSTANCE_ID: str | None = Field(
        default=None,
        description="OTel resource service.instance.id (a UUID from the service_instance detector when unset)",
    )
    RESOURCE_DETECTORS: list[Literal["service_instance", "host", "os", "process"]] = Field(
        default=["service_instance", "host", "os"],
        description=(
            "Resource detectors that add service.instance.id, host.*, os.* or process.* attributes. process records "
            "the full command line, which may hold secrets, so it is opt-in. Explicit settings and "
            "RESOURCE_ATTRIBUTES override detected values"
        ),
    )
    METRICS_DURATION_BUCKETS_S: list[float] = Field(
        default=[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
        min_length=1,
        description="Explicit bucket boundaries in seconds of the duration histograms ArchiPy records",
    )
    RESOURCE_ATTRIBUTES: dict[str, str] = Field(
        default_factory=dict,
        description="Extra OTel resource attributes merged into the Resource",
    )
    METRIC_EXPORT_INTERVAL_MS: int = Field(
        default=60000,
        ge=1000,
        description="Periodic OTLP metric export interval in milliseconds (used when METRICS_EXPORTER=otlp)",
    )
    METRICS_CARDINALITY_LIMIT: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Maximum distinct attribute sets kept per metric instrument; the rest aggregate into the "
            "`otel.metric.overflow` series (None: SDK default, 2000)"
        ),
    )
    METRICS_EXPORTER: OtelMetricsExporter = Field(
        default=OtelMetricsExporter.OTLP,
        description="Unique metrics exporter when METRICS_ENABLED is true (otlp, pull, or pushgateway)",
    )
    METRICS_PULL_HOST: str = Field(
        default="0.0.0.0",  # noqa: S104 # nosec B104  # intentional scrape bind-all default; override via env
        description="Bind host for the metrics pull scrape server when METRICS_EXPORTER=pull",
    )
    METRICS_PULL_PORT: int = Field(
        default=8200,
        ge=1,
        le=65535,
        description="Bind port for the metrics pull scrape server (/metrics)",
    )
    METRICS_PUSHGATEWAY_URL: str | None = Field(
        default=None,
        description="Prometheus Pushgateway base URL when METRICS_EXPORTER=pushgateway (e.g. http://host:9091)",
    )
    METRICS_PUSHGATEWAY_JOB: str | None = Field(
        default=None,
        description="Pushgateway job label (defaults to SERVICE_NAME when unset)",
    )
    METRICS_PUSHGATEWAY_INTERVAL_SECONDS: int = Field(
        default=60,
        ge=1,
        description="Interval between Pushgateway pushes when METRICS_EXPORTER=pushgateway",
    )
    METRICS_PUSHGATEWAY_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        gt=0,
        description="HTTP timeout in seconds for Pushgateway push/delete calls",
    )
    METRICS_PUSHGATEWAY_GROUPING_KEY: dict[str, str] = Field(
        default_factory=dict,
        max_length=16,
        description="Extra Pushgateway grouping labels (instance, component, ...)",
    )
    METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN: bool = Field(
        default=True,
        description="Delete the Pushgateway grouping key on graceful OTel shutdown",
    )
    SYSTEM_METRICS_ENABLED: bool = Field(
        default=True,
        description="Instrument process/system metrics when METRICS_ENABLED is true",
    )
    ENVIRONMENT: str | None = Field(
        default=None,
        description="Deployment environment resource attribute (defaults from BaseConfig.ENVIRONMENT)",
    )
    FASTAPI_EXCLUDED_URLS: str | None = Field(
        default=None,
        description="Comma-separated URL patterns skipped by FastAPI instrumentation (e.g. health,docs)",
    )
    FASTAPI_OPERATION_SPANS_ENABLED: bool = Field(
        default=True,
        description=(
            "Record FastAPI child spans (dependencies, endpoint, serialization, background tasks) "
            "under the request span when TRACES_ENABLED is true"
        ),
    )
    INSTRUMENTATION_SKIP_DEP_CHECK: list[str] = Field(
        default=["sqlalchemy"],
        description=(
            "Auto-instrumentation keys (e.g. sqlalchemy) that are instrumented even when the installed library is "
            "newer than the instrumentor's declared version range. ArchiPy requires SQLAlchemy 2.1 while "
            "opentelemetry-instrumentation-sqlalchemy still declares <2.1.0; remove the key once upstream supports it"
        ),
    )
    FASTAPI_LOGS_ENABLED: bool = Field(
        default=False,
        description=(
            "Let FastAPI emit OTel log records for validation failures and unhandled exceptions "
            "(includes exception messages and stack traces; requires LOGS_ENABLED)"
        ),
    )
    LOGS_LEVEL: str = Field(
        default="INFO",
        description=(
            "Minimum level for the LoggingHandler on the root logger. "
            "Records from opentelemetry.* loggers are filtered to avoid feedback loops. "
            "Prefer WARNING+ in production when LOGS_EXPORTER=otlp to limit export volume."
        ),
    )

    def _fit_batch_sizes_to_queues(self) -> None:
        """Keep each batch no larger than its queue.

        A batch size left unset follows a queue that was lowered, so setting only ``*_MAX_QUEUE_SIZE`` below the default
        batch size just works. A batch size set explicitly above its queue is a mistake and is rejected.

        Raises:
            ConfigurationError: If an explicit batch size exceeds its queue size.
        """
        for batch_field, queue_field in (
            ("SPAN_BATCH_MAX_EXPORT_BATCH_SIZE", "SPAN_BATCH_MAX_QUEUE_SIZE"),
            ("LOG_BATCH_MAX_EXPORT_BATCH_SIZE", "LOG_BATCH_MAX_QUEUE_SIZE"),
        ):
            batch_size, queue_size = getattr(self, batch_field), getattr(self, queue_field)
            if batch_size <= queue_size:
                continue
            if batch_field in self.model_fields_set:
                raise ConfigurationError(
                    operation="otel",
                    reason="batch_size_exceeds_queue_size",
                    additional_data={"max_export_batch_size": batch_size, "max_queue_size": queue_size},
                )
            setattr(self, batch_field, queue_size)

    @model_validator(mode="after")
    def validate_otel_config(self) -> Self:
        """Validate signal switches, metrics exporters, and log level."""
        if self.IS_ENABLED and not (self.TRACES_ENABLED or self.METRICS_ENABLED or self.LOGS_ENABLED):
            raise ConfigurationError(
                operation="otel",
                reason="no_signals_enabled",
                additional_data={
                    "hint": "Enable at least one of TRACES_ENABLED, METRICS_ENABLED, or LOGS_ENABLED",
                },
            )

        if (
            self.METRICS_ENABLED
            and self.METRICS_EXPORTER == OtelMetricsExporter.PUSHGATEWAY
            and not (self.METRICS_PUSHGATEWAY_URL and self.METRICS_PUSHGATEWAY_URL.strip())
        ):
            raise ConfigurationError(
                operation="otel",
                reason="pushgateway_url_required",
                additional_data={
                    "hint": "Set METRICS_PUSHGATEWAY_URL when METRICS_EXPORTER=pushgateway",
                },
            )

        self._fit_batch_sizes_to_queues()

        buckets = self.METRICS_DURATION_BUCKETS_S
        if buckets[0] <= 0 or any(low >= high for low, high in pairwise(buckets)):
            raise ConfigurationError(
                operation="otel",
                reason="invalid_duration_buckets",
                additional_data={"hint": "METRICS_DURATION_BUCKETS_S must be positive and strictly increasing"},
            )

        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if self.LOGS_LEVEL.upper() not in valid_levels:
            raise ConfigurationError(
                operation="otel",
                reason="invalid_logs_level",
                additional_data={"logs_level": self.LOGS_LEVEL, "allowed": sorted(valid_levels)},
            )
        return self
