"""System-level error types."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Any, ClassVar

from archipy.models.errors.base_error import BaseError

if TYPE_CHECKING:
    from archipy.models.types.language_type import LanguageType


class InternalError(BaseError):
    """Represents an internal server error.

    This error is typically used when an unexpected condition is encountered
    that prevents the server from fulfilling the request.
    """

    code: ClassVar[str] = "INTERNAL_ERROR"
    message_en: ClassVar[str] = "Internal system error occurred"
    message_fa: ClassVar[str] = "خطای داخلی سیستم رخ داده است."
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 13

    def __init__(
        self,
        error_code: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InternalError."""
        data = {}
        if error_code:
            data["error_code"] = error_code
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class ConfigurationError(BaseError):
    """Represents a configuration error.

    This error is used when there is a problem with the application's
    configuration that prevents it from operating correctly.
    """

    code: ClassVar[str] = "CONFIGURATION_ERROR"
    message_en: ClassVar[str] = "Error in system configuration"
    message_fa: ClassVar[str] = "خطا در پیکربندی سیستم"
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 13

    def __init__(
        self,
        operation: str | None = None,
        reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ConfigurationError."""
        data = {}
        if operation:
            data["operation"] = operation
        if reason:
            data["reason"] = reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class UnavailableError(BaseError):
    """Represents a resource unavailability error.

    This error is used when a required resource is temporarily unavailable
    but may become available again in the future.
    """

    code: ClassVar[str] = "UNAVAILABLE"
    message_en: ClassVar[str] = "Service is currently unavailable"
    message_fa: ClassVar[str] = "سرویس در حال حاضر در دسترس نیست."
    http_status: ClassVar[int] = HTTPStatus.SERVICE_UNAVAILABLE.value
    grpc_status: ClassVar[int] = 14

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize UnavailableError."""
        data = {}
        if resource_type:
            data["resource_type"] = resource_type
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class UnknownError(BaseError):
    """Represents an unknown error.

    This is a catch-all error type for unexpected conditions that
    don't fit into other error categories.
    """

    code: ClassVar[str] = "UNKNOWN_ERROR"
    message_en: ClassVar[str] = "An unknown error occurred"
    message_fa: ClassVar[str] = "خطای ناشناخته‌ای رخ داده است."
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 2

    def __init__(
        self,
        config_key: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize UnknownError."""
        data = {}
        if config_key:
            data["config_key"] = config_key
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class AbortedError(BaseError):
    """Represents an aborted operation error.

    This error is used when an operation is aborted, typically due to
    a concurrency issue or user cancellation.
    """

    code: ClassVar[str] = "ABORTED"
    message_en: ClassVar[str] = "Operation was aborted"
    message_fa: ClassVar[str] = "عملیات متوقف شد."
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value
    grpc_status: ClassVar[int] = 10

    def __init__(
        self,
        service: str | None = None,
        reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AbortedError."""
        data = {}
        if service:
            data["service"] = service
        if reason:
            data["reason"] = reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class DeadlockDetectedError(BaseError):
    """Represents a deadlock detection error.

    This error is used when a deadlock is detected in a system operation,
    typically in database transactions or resource locking scenarios.
    """

    code: ClassVar[str] = "DEADLOCK"
    message_en: ClassVar[str] = "Deadlock detected"
    message_fa: ClassVar[str] = "خطای قفل‌شدگی (Deadlock) تشخیص داده شد."
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 13

    def __init__(
        self,
        service: str | None = None,
        reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize DeadlockDetectedError."""
        data = {}
        if service:
            data["service"] = service
        if reason:
            data["reason"] = reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class DeadlineExceededError(BaseError):
    """Raised when an operation exceeds its deadline/timeout.

    This error is typically used in decorators or functions that have
    time limits or deadlines for completion.
    """

    code: ClassVar[str] = "DEADLINE_EXCEEDED"
    message_en: ClassVar[str] = "Operation exceeded its deadline"
    message_fa: ClassVar[str] = "عملیات از مهلت زمانی مجاز تجاوز کرد"
    http_status: ClassVar[int] = HTTPStatus.REQUEST_TIMEOUT.value
    grpc_status: ClassVar[int] = 4

    def __init__(
        self,
        timeout: float | None = None,
        operation: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize DeadlineExceededError.

        Args:
            timeout: The timeout value that was exceeded (in seconds).
            operation: The operation that exceeded the deadline.
            lang: The language for error messages.
            additional_data: Additional context data.
        """
        data = {}
        if timeout is not None:
            data["timeout"] = timeout
        if operation:
            data["operation"] = operation
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class DeprecationError(BaseError):
    """Raised when deprecated functionality is used.

    This error is used to signal that a feature, method, or API
    is deprecated and should no longer be used.
    """

    code: ClassVar[str] = "DEPRECATED_FEATURE"
    message_en: ClassVar[str] = "This feature is deprecated and should no longer be used"
    message_fa: ClassVar[str] = "این ویژگی منسوخ شده و دیگر نباید استفاده شود"
    http_status: ClassVar[int] = HTTPStatus.GONE.value
    grpc_status: ClassVar[int] = 14

    def __init__(
        self,
        deprecated_feature: str | None = None,
        replacement: str | None = None,
        removal_version: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize DeprecationError.

        Args:
            deprecated_feature: The name of the deprecated feature.
            replacement: The recommended replacement feature.
            removal_version: The version when the feature will be removed.
            lang: The language for error messages.
            additional_data: Additional context data.
        """
        data = {}
        if deprecated_feature:
            data["deprecated_feature"] = deprecated_feature
        if replacement:
            data["replacement"] = replacement
        if removal_version:
            data["removal_version"] = removal_version
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)
