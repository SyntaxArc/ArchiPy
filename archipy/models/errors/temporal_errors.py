"""Temporal-specific error definitions.

This module defines custom exception classes for Temporal worker operations,
extending the base ArchiPy error handling patterns.
"""

from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from http import HTTPStatus

    from grpc import StatusCode
else:
    HTTPStatus = None
    StatusCode = None

try:
    from http import HTTPStatus

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False

try:
    from grpc import StatusCode

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False

from archipy.models.errors.base_error import BaseError


class TemporalError(BaseError):
    """Base exception for all Temporal-related errors.

    This is the root exception class for all Temporal workflow engine errors
    within the ArchiPy system.
    """

    code: ClassVar[str] = "TEMPORAL_ERROR"
    message_en: ClassVar[str] = "Temporal error occurred"
    message_fa: ClassVar[str] = "خطای Temporal رخ داده است"
    http_status: ClassVar[int] = (
        HTTPStatus.INTERNAL_SERVER_ERROR.value if HTTP_AVAILABLE and HTTPStatus is not None else 500
    )
    grpc_status: ClassVar[int] = (
        StatusCode.INTERNAL.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INTERNAL.value, tuple)
        else (StatusCode.INTERNAL.value if GRPC_AVAILABLE and StatusCode is not None else 13)
    )


class WorkerConnectionError(TemporalError):
    """Exception raised when a worker fails to connect to Temporal server."""

    code: ClassVar[str] = "WORKER_CONNECTION_ERROR"
    message_en: ClassVar[str] = "Failed to connect to Temporal server"
    message_fa: ClassVar[str] = "خطا در اتصال به سرور Temporal"
    http_status: ClassVar[int] = (
        HTTPStatus.SERVICE_UNAVAILABLE.value if HTTP_AVAILABLE and HTTPStatus is not None else 503
    )
    grpc_status: ClassVar[int] = (
        StatusCode.UNAVAILABLE.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAVAILABLE.value, tuple)
        else (StatusCode.UNAVAILABLE.value if GRPC_AVAILABLE and StatusCode is not None else 14)
    )

    def __init__(
        self,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the worker connection error."""
        super().__init__(additional_data=additional_data)


class WorkerShutdownError(TemporalError):
    """Exception raised when a worker fails to shutdown gracefully."""

    code: ClassVar[str] = "WORKER_SHUTDOWN_ERROR"
    message_en: ClassVar[str] = "Failed to shutdown Temporal worker gracefully"
    message_fa: ClassVar[str] = "خطا در خاموش‌سازی صحیح کارگر Temporal"
    http_status: ClassVar[int] = (
        HTTPStatus.INTERNAL_SERVER_ERROR.value if HTTP_AVAILABLE and HTTPStatus is not None else 500
    )
    grpc_status: ClassVar[int] = (
        StatusCode.INTERNAL.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INTERNAL.value, tuple)
        else (StatusCode.INTERNAL.value if GRPC_AVAILABLE and StatusCode is not None else 13)
    )

    def __init__(
        self,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the worker shutdown error."""
        super().__init__(additional_data=additional_data)
