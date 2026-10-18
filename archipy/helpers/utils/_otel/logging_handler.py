"""The logging handler that ships Python log records through the OpenTelemetry logger provider."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

logger = logging.getLogger("archipy.helpers.utils.otel_utils")


class _DropOtelInternalLogs(logging.Filter):
    """Drop records from ``opentelemetry.*`` to avoid export feedback loops."""

    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.startswith("opentelemetry")


def attach_logging_handler(level: int, logger_provider: LoggerProvider) -> LoggingHandler:
    """Attach an OpenTelemetry ``LoggingHandler`` to the root logger.

    Args:
        level: Minimum level the handler forwards.
        logger_provider: Provider the handler exports through.

    Returns:
        The attached handler.
    """
    from opentelemetry.sdk._logs import LoggingHandler

    handler = LoggingHandler(level=level, logger_provider=logger_provider)
    handler.addFilter(_DropOtelInternalLogs())
    logging.getLogger().addHandler(handler)
    return handler


def detach_logging_handler(handler: LoggingHandler) -> None:
    """Remove the handler from the root logger and close it; failures are logged at debug level.

    Args:
        handler: The handler returned by :func:`attach_logging_handler`.
    """
    try:
        logging.getLogger().removeHandler(handler)
    except Exception:
        logger.debug("Error removing OTel logging handler", exc_info=True)
    try:
        handler.close()
    except Exception:
        logger.debug("Error closing OTel logging handler", exc_info=True)
