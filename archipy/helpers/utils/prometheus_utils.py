"""Prometheus utilities for managing Prometheus HTTP server and metrics.

This module provides utilities for Prometheus metrics server management that
can be shared across FastAPI, gRPC, and Temporal adapters.
"""

import logging
import socket

logger = logging.getLogger(__name__)


class PrometheusUtils:
    """Utilities for Prometheus server lifecycle operations."""

    _PROMETHEUS_INSTALL_HINT = (
        'Prometheus metrics require the optional dependency. Install with: uv add "archipy[prometheus]"'
    )

    @staticmethod
    def is_prometheus_server_running(port: int) -> bool:
        """Check if Prometheus server is already running on the specified port.

        Args:
            port (int): The port number to check.

        Returns:
            bool: True if server is running, False otherwise.

        Example:
            ```python
            from archipy.helpers.utils.prometheus_utils import PrometheusUtils

            if not PrometheusUtils.is_prometheus_server_running(8200):
                PrometheusUtils.start_prometheus_server_if_needed(8200)
            ```
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", port))
        sock.close()
        return result == 0

    @classmethod
    def start_prometheus_server_if_needed(cls, port: int) -> None:
        """Start Prometheus HTTP server if not already running on the specified port.

        Requires the ``prometheus`` extra (``prometheus-client``). Port checks via
        ``is_prometheus_server_running`` do not.

        Args:
            port (int): The port number for the Prometheus metrics endpoint.

        Raises:
            ImportError: If ``prometheus-client`` is not installed.

        Example:
            ```python
            from archipy.helpers.utils.prometheus_utils import PrometheusUtils

            # This will start the server only if it's not already running
            PrometheusUtils.start_prometheus_server_if_needed(8200)
            ```
        """
        if not cls.is_prometheus_server_running(port):
            try:
                from prometheus_client import start_http_server  # noqa: PLC0415
            except ModuleNotFoundError as exc:
                raise ImportError(cls._PROMETHEUS_INSTALL_HINT) from exc
            try:
                start_http_server(port)
                logger.info("Started Prometheus HTTP server on port %d", port)
            except Exception as error:
                logger.exception(
                    "Failed to start Prometheus HTTP server",
                    extra={
                        "port": port,
                        "error": str(error),
                    },
                )
                raise
        else:
            logger.debug("Prometheus HTTP server already running on port %d", port)
