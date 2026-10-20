"""Capture exceptions: log them locally and record them on the active OpenTelemetry span."""

from __future__ import annotations

import logging

from archipy.configs.base_config import BaseConfig

# Logger name kept from the former ``error_utils`` module so existing logging configuration still applies.
logger = logging.getLogger("archipy.helpers.utils.error_utils")


def capture_exception(exception: BaseException) -> None:
    """Captures an exception and records it on the current OpenTelemetry span.

    Always logs locally. When OTel is enabled and a recording span is active,
    records the exception event and sets span status via ``OtelUtils.status_for_exception``.

    Args:
        exception (BaseException): The exception to capture and report.
    """
    logger.error(
        "An exception occurred: %s: %s",
        type(exception).__name__,
        exception,
        exc_info=(type(exception), exception, exception.__traceback__),
    )
    config = BaseConfig.global_config()

    if not config.OTEL.IS_ENABLED or not config.OTEL.TRACES_ENABLED:
        return

    try:
        from opentelemetry import trace

        from archipy.helpers.utils.otel_utils import OtelUtils

        span = trace.get_current_span()
        if span.is_recording():
            span.record_exception(exception)
            status = OtelUtils.status_for_exception(exception)
            if status is not None:
                span.set_status(status)
    except ImportError:
        logger.debug("opentelemetry is not installed, cannot record exception on span.")
