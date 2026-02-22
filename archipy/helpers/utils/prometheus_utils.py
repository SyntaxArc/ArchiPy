"""Prometheus utilities for managing Prometheus HTTP server and metrics.

This module provides utilities for Prometheus metrics server management that
can be shared across FastAPI, gRPC, and Temporal adapters.
"""

import logging
import socket

from prometheus_client import start_http_server

logger = logging.getLogger(__name__)


def is_prometheus_server_running(port: int) -> bool:
    """Check if Prometheus server is already running on the specified port.

    Args:
        port (int): The port number to check.

    Returns:
        bool: True if server is running, False otherwise.

    Example:
        ```python
        from archipy.helpers.utils.prometheus_utils import is_prometheus_server_running

        if not is_prometheus_server_running(8200):
            from prometheus_client import start_http_server

            start_http_server(8200)
        ```
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("localhost", port))
    sock.close()
    return result == 0


def start_prometheus_server_if_needed(port: int) -> None:
    """Start Prometheus HTTP server if not already running on the specified port.

    Args:
        port (int): The port number for the Prometheus metrics endpoint.

    Example:
        ```python
        from archipy.helpers.utils.prometheus_utils import start_prometheus_server_if_needed

        # This will start the server only if it's not already running
        start_prometheus_server_if_needed(8200)
        ```
    """
    if not is_prometheus_server_running(port):
        try:
            start_http_server(port)
            logger.info(f"Started Prometheus HTTP server on port {port}")
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
        logger.debug(f"Prometheus HTTP server already running on port {port}")
