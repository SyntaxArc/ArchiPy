"""Temporal Runtime singleton for managing Runtime instances with telemetry.

This module provides a singleton class for creating and managing Temporal Runtime
instances with OpenTelemetry metrics integration.
"""

import logging
from typing import Any

from temporalio.runtime import (
    LoggingConfig,
    OpenTelemetryConfig,
    PrometheusConfig,
    Runtime,
    TelemetryConfig,
    TelemetryFilter,
)

from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import ConfigurationError

logger = logging.getLogger(__name__)


class TemporalRuntimeManager(metaclass=Singleton, thread_safe=True):
    """Singleton manager for Temporal Runtime instances with telemetry configuration.

    This class ensures only one Runtime instance is created and reused across all
    Temporal clients and workers. Once created with metrics enabled, the Runtime
    cannot be changed (Temporal SDK limitation).

    Example:
        ```python
        from archipy.adapters.temporal.runtime import TemporalRuntimeManager

        # Get the singleton manager
        manager = TemporalRuntimeManager()

        # Get Runtime with OTLP metrics enabled
        runtime = manager.get_runtime(
            otel_metrics_enabled=True,
            otlp_endpoint="http://localhost:4317",
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize the TemporalRuntimeManager singleton."""
        self._runtime: Runtime | None = None

    def get_runtime(
        self,
        otel_metrics_enabled: bool = False,
        otlp_endpoint: str = "http://localhost:4317",
        headers: dict[str, str] | None = None,
        use_http: bool = False,
        prometheus_bind_address: str | None = None,
        global_tags: dict[str, str] | None = None,
        core_log_level: str | None = None,
        disable_environment_info: bool = False,
    ) -> Runtime | None:
        """Get or create a Runtime with OpenTelemetry telemetry.

        Args:
            otel_metrics_enabled: Whether to enable OTLP metrics export.
            otlp_endpoint: OTLP collector endpoint URL.
            headers: Optional headers for OTLP export (auth tokens, routing).
            use_http: If True, use HTTP/protobuf transport instead of gRPC.
            prometheus_bind_address: If set (``host:port``), the Runtime serves a Prometheus ``/metrics``
                scrape endpoint on that address instead of exporting over OTLP.
            global_tags: Tags added to every Temporal SDK metric (e.g. service, environment).
            core_log_level: Level of the SDK core's own logs (``ERROR``, ``WARN``, ``INFO``, ``DEBUG``, ``TRACE``);
                None keeps the SDK default.
            disable_environment_info: Keep runtime, hosting and platform information out of worker heartbeats.
                A Runtime is built for it even when metrics are disabled.

        Returns:
            Runtime | None: The configured Runtime instance if metrics are enabled or environment info is disabled,
                None otherwise (uses default Runtime).

        Raises:
            ConfigurationError: If the Runtime cannot be built from the telemetry settings (e.g. an invalid URL).

        Note:
            Once a Runtime is created with metrics enabled, it cannot be disabled
            or recreated with different settings due to Temporal SDK limitations.
            Subsequent calls will return the existing Runtime regardless of parameters.
        """
        if not otel_metrics_enabled and not disable_environment_info:
            logger.debug("OTLP metrics disabled for Temporal, using default runtime")
            return None

        # If Runtime already created, return it (can't change once bound)
        if self._runtime is not None:
            logger.debug("Returning existing Temporal Runtime instance")
            return self._runtime

        metrics: OpenTelemetryConfig | PrometheusConfig | None
        if not otel_metrics_enabled:
            logger.info("Creating Temporal Runtime without metrics to disable environment info")
            metrics = None
        elif prometheus_bind_address:
            logger.info("Creating Temporal Runtime with a Prometheus scrape endpoint on %s", prometheus_bind_address)
            metrics = PrometheusConfig(bind_address=prometheus_bind_address)
        else:
            logger.info("Creating Temporal Runtime with OTLP metrics at %s", otlp_endpoint)
            metrics = OpenTelemetryConfig(url=otlp_endpoint, headers=headers or None, http=use_http)

        telemetry_kwargs: dict[str, Any] = {"metrics": metrics, "global_tags": global_tags or {}}
        if core_log_level is not None:
            telemetry_kwargs["logging"] = LoggingConfig(
                filter=TelemetryFilter(core_level=core_log_level, other_level=core_log_level),
            )
        try:
            self._runtime = Runtime(
                telemetry=TelemetryConfig(**telemetry_kwargs),
                disable_environment_info=disable_environment_info,
            )
            logger.info("Temporal Runtime created successfully")
        except Exception as error:
            # Falling back to the default Runtime would drop every SDK metric without a trace, so fail loudly.
            raise ConfigurationError(
                operation="temporal_runtime",
                reason=f"cannot build the Temporal Runtime telemetry: {error}",
            ) from error

        return self._runtime

    def reset_runtime(self) -> None:
        """Reset the Runtime instance.

        Warning:
            This does NOT actually close the Runtime or release telemetry resources.
            The Temporal SDK does not support Runtime cleanup. This method only
            resets internal references for testing purposes.
        """
        logger.warning("Resetting Temporal Runtime reference (resources remain until process exit)")
        self._runtime = None
