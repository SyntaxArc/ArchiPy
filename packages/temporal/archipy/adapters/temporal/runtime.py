"""Temporal Runtime singleton for managing Runtime instances with telemetry.

This module provides a singleton class for creating and managing Temporal Runtime
instances with OpenTelemetry metrics integration.
"""

import logging

from temporalio.runtime import OpenTelemetryConfig, Runtime, TelemetryConfig

from archipy.helpers.metaclasses.singleton import Singleton

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
    ) -> Runtime | None:
        """Get or create a Runtime with OpenTelemetry telemetry.

        Args:
            otel_metrics_enabled: Whether to enable OTLP metrics export.
            otlp_endpoint: OTLP collector endpoint URL.
            headers: Optional headers for OTLP export (auth tokens, routing).
            use_http: If True, use HTTP/protobuf transport instead of gRPC.

        Returns:
            Runtime | None: The configured Runtime instance if metrics are enabled,
                None otherwise (uses default Runtime).

        Note:
            Once a Runtime is created with metrics enabled, it cannot be disabled
            or recreated with different settings due to Temporal SDK limitations.
            Subsequent calls will return the existing Runtime regardless of parameters.
        """
        if not otel_metrics_enabled:
            logger.debug("OTLP metrics disabled for Temporal, using default runtime")
            return None

        # If Runtime already created, return it (can't change once bound)
        if self._runtime is not None:
            logger.debug("Returning existing Temporal Runtime instance")
            return self._runtime

        logger.info("Creating Temporal Runtime with OTLP metrics at %s", otlp_endpoint)

        try:
            self._runtime = Runtime(
                telemetry=TelemetryConfig(
                    metrics=OpenTelemetryConfig(
                        url=otlp_endpoint,
                        headers=headers or None,
                        http=use_http,
                    ),
                ),
            )
            logger.info("Temporal Runtime created successfully with OpenTelemetry telemetry")
        except Exception:
            logger.exception("Failed to create Temporal Runtime with OpenTelemetry config")
            # Return None so Temporal uses default Runtime
            return None

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
