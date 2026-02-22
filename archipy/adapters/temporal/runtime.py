"""Temporal Runtime singleton for managing Runtime instances with telemetry.

This module provides a singleton class for creating and managing Temporal Runtime
instances with Prometheus metrics integration.
"""

import logging

from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig

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

        # Get Runtime with Prometheus enabled
        runtime = manager.get_runtime(prometheus_enabled=True, prometheus_port=18201)
        ```
    """

    def __init__(self) -> None:
        """Initialize the TemporalRuntimeManager singleton."""
        self._runtime: Runtime | None = None

    def get_runtime(self, prometheus_enabled: bool = False, prometheus_port: int = 18201) -> Runtime | None:
        """Get or create a Runtime with Prometheus telemetry.

        Args:
            prometheus_enabled (bool): Whether to enable Prometheus metrics collection.
            prometheus_port (int): Port for the Prometheus metrics endpoint.

        Returns:
            Runtime | None: The configured Runtime instance if metrics are enabled,
                None otherwise (uses default Runtime).

        Note:
            Once a Runtime is created with metrics enabled, it cannot be disabled
            or recreated on a different port due to Temporal SDK limitations.
            Subsequent calls will return the existing Runtime regardless of parameters.
        """
        if not prometheus_enabled:
            logger.debug("Prometheus metrics disabled for Temporal, using default runtime")
            return None

        # If Runtime already created, return it (can't change once bound to port)
        if self._runtime is not None:
            logger.debug("Returning existing Temporal Runtime instance")
            return self._runtime

        logger.info("Creating Temporal Runtime with Prometheus metrics on port %d", prometheus_port)

        try:
            self._runtime = Runtime(
                telemetry=TelemetryConfig(
                    metrics=PrometheusConfig(bind_address=f"0.0.0.0:{prometheus_port}"),
                ),
            )
            logger.info("Temporal Runtime created successfully with Prometheus telemetry")
        except Exception:
            logger.exception("Failed to create Temporal Runtime with Prometheus config")
            # Return None so Temporal uses default Runtime
            return None

        return self._runtime

    def reset_runtime(self) -> None:
        """Reset the Runtime instance.

        Warning:
            This does NOT actually close the Runtime or release the port binding.
            The Temporal SDK does not support Runtime cleanup. This method only
            resets internal references for testing purposes. The port will remain
            bound until the process exits.
        """
        logger.warning("Resetting Temporal Runtime reference (port remains bound until process exit)")
        self._runtime = None
