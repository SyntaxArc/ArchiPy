"""Mapping of exceptions to OpenTelemetry span and metric status."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from opentelemetry.trace import Status

HTTP_SERVER_ERROR_MIN = 500
_STATUS_DESC_MAX_LEN = 256


def truncate_status_description(exception: BaseException) -> str:
    """Return a bounded status description for span status."""
    text = str(exception)
    if len(text) > _STATUS_DESC_MAX_LEN:
        return text[:_STATUS_DESC_MAX_LEN]
    return text


def status_for_exception(exception: BaseException) -> Status | None:
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


def error_type_for_exception(exception: BaseException) -> str:
    """Return the low-cardinality ``error.type`` of a failure.

    An ArchiPy ``BaseError`` is identified by its stable ``code``; any other exception by its fully qualified class
    name, as the OpenTelemetry error-recording convention suggests.

    Args:
        exception: The exception that ended the operation.

    Returns:
        The ``error.type`` attribute value.
    """
    from archipy.models.errors.base_error import BaseError

    if isinstance(exception, BaseError):
        return exception.code
    exception_type = type(exception)
    return f"{exception_type.__module__}.{exception_type.__qualname__}"


def status_for_cancellation() -> Status:
    """Return an ERROR status for asyncio task cancellation.

    Returns:
        An OpenTelemetry ``Status`` with ``StatusCode.ERROR``.
    """
    from opentelemetry.trace import Status, StatusCode

    return Status(StatusCode.ERROR, description="cancelled")
