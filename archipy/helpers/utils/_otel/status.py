"""Mapping of exceptions to OpenTelemetry span and metric status."""

from __future__ import annotations

from typing import Any

HTTP_SERVER_ERROR_MIN = 500
_STATUS_DESC_MAX_LEN = 256


def truncate_status_description(exception: BaseException) -> str:
    """Return a bounded status description for span status."""
    text = str(exception)
    if len(text) > _STATUS_DESC_MAX_LEN:
        return text[:_STATUS_DESC_MAX_LEN]
    return text


def status_for_exception(exception: BaseException) -> Any | None:
    """Map an exception to an OpenTelemetry ``Status``, or ``None`` for UNSET.

    ``BaseError`` with ``http_status`` below 500 leaves status UNSET (handled
    client error — OTel spec recommends not forcing OK). All other exceptions
    become ``StatusCode.ERROR``.

    Args:
        exception: The exception raised during a span.

    Returns:
        An OpenTelemetry ``Status`` instance, or ``None`` to leave status UNSET.
    """
    from opentelemetry.trace import Status, StatusCode

    from archipy.models.errors.base_error import BaseError

    if isinstance(exception, BaseError) and exception.http_status < HTTP_SERVER_ERROR_MIN:
        return None
    return Status(StatusCode.ERROR, description=truncate_status_description(exception))


def metric_status_for_exception(exception: BaseException) -> str:
    """Map an exception to a metric ``status`` attribute value.

    Aligns with ``status_for_exception``: handled client ``BaseError`` values
    (HTTP status below 500) record as ``ok``; other exceptions as ``error``.
    Callers that catch ``asyncio.CancelledError`` should record ``cancelled``
    before invoking this helper.

    Args:
        exception: The exception raised during the instrumented call.

    Returns:
        ``"ok"`` or ``"error"``.
    """
    if status_for_exception(exception) is None:
        return "ok"
    return "error"


def status_for_cancellation() -> Any:
    """Return an ERROR status for asyncio task cancellation.

    Returns:
        An OpenTelemetry ``Status`` with ``StatusCode.ERROR``.
    """
    from opentelemetry.trace import Status, StatusCode

    return Status(StatusCode.ERROR, description="cancelled")
