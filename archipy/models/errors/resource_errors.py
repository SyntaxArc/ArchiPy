"""Resource-related error types."""

from http import HTTPStatus
from typing import Any, ClassVar

from archipy.models.errors.base_error import BaseError
from archipy.models.types.language_type import LanguageType


class NotFoundError(BaseError):
    """Exception raised when a resource is not found."""

    code: ClassVar[str] = "NOT_FOUND"
    message_en: ClassVar[str] = "Requested resource not found: {resource_type}"
    message_fa: ClassVar[str] = "منبع درخواستی یافت نشد: {resource_type}"
    http_status: ClassVar[int] = HTTPStatus.NOT_FOUND.value
    grpc_status: ClassVar[int] = 5

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize NotFoundError."""
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)

    def get_message(self) -> str:
        """Gets the localized error message with resource type."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        resource_type = self.additional_data.get("resource_type", "resource_type")
        return template.format(resource_type=resource_type)


class AlreadyExistsError(BaseError):
    """Exception raised when a resource already exists."""

    code: ClassVar[str] = "ALREADY_EXISTS"
    message_en: ClassVar[str] = "Resource already exists: {resource_type}"
    message_fa: ClassVar[str] = "منبع از قبل موجود است: {resource_type}"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value
    grpc_status: ClassVar[int] = 6

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize AlreadyExistsError."""
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)

    def get_message(self) -> str:
        """Gets the localized error message with resource type."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        resource_type = self.additional_data.get("resource_type", "resource_type")
        return template.format(resource_type=resource_type)


class ConflictError(BaseError):
    """Exception raised when there is a resource conflict."""

    code: ClassVar[str] = "CONFLICT"
    message_en: ClassVar[str] = "Resource conflict detected"
    message_fa: ClassVar[str] = "تعارض در منابع تشخیص داده شد"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value
    grpc_status: ClassVar[int] = 10

    def __init__(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ConflictError."""
        data = {}
        if resource_type:
            data["resource_type"] = resource_type
        if resource_id:
            data["resource_id"] = resource_id
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class ResourceLockedError(BaseError):
    """Exception raised when a resource is locked."""

    code: ClassVar[str] = "RESOURCE_LOCKED"
    message_en: ClassVar[str] = "Resource is currently locked"
    message_fa: ClassVar[str] = "منبع در حال حاضر قفل شده است"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value
    grpc_status: ClassVar[int] = 10

    def __init__(
        self,
        resource_id: str | None = None,
        lock_owner: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ResourceLockedError."""
        data = {}
        if resource_id:
            data["resource_id"] = resource_id
        if lock_owner:
            data["lock_owner"] = lock_owner
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class ResourceBusyError(BaseError):
    """Exception raised when a resource is busy."""

    code: ClassVar[str] = "RESOURCE_BUSY"
    message_en: ClassVar[str] = "Resource is currently busy"
    message_fa: ClassVar[str] = "منبع در حال حاضر مشغول است"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value
    grpc_status: ClassVar[int] = 10

    def __init__(
        self,
        resource_id: str | None = None,
        busy_reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ResourceBusyError."""
        data = {}
        if resource_id:
            data["resource_id"] = resource_id
        if busy_reason:
            data["busy_reason"] = busy_reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class DataLossError(BaseError):
    """Exception raised when data is lost."""

    code: ClassVar[str] = "DATA_LOSS"
    message_en: ClassVar[str] = "Critical data loss detected"
    message_fa: ClassVar[str] = "از دست دادن اطلاعات حیاتی تشخیص داده شد."
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 15


class InvalidEntityTypeError(BaseError):
    """Exception raised for invalid entity types."""

    code: ClassVar[str] = "INVALID_ENTITY"
    message_en: ClassVar[str] = "Invalid entity type"
    message_fa: ClassVar[str] = "نوع موجودیت نامعتبر است."
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value
    grpc_status: ClassVar[int] = 3

    def __init__(
        self,
        message: str | None = None,
        expected_type: str | None = None,
        actual_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidEntityTypeError."""
        data = {}
        if message:
            data["message"] = message
        if expected_type:
            data["expected_type"] = expected_type
        if actual_type:
            data["actual_type"] = actual_type
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class FileTooLargeError(BaseError):
    """Exception raised when a file is too large."""

    code: ClassVar[str] = "FILE_TOO_LARGE"
    message_en: ClassVar[str] = "File size exceeds the maximum allowed limit"
    message_fa: ClassVar[str] = "حجم فایل از حد مجاز بیشتر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value
    grpc_status: ClassVar[int] = 3

    def __init__(
        self,
        file_name: str | None = None,
        file_size: int | None = None,
        max_size: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize FileTooLargeError."""
        data = {}
        if file_name:
            data["file_name"] = file_name
        if file_size:
            data["file_size"] = file_size
        if max_size:
            data["max_size"] = max_size
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class InvalidFileTypeError(BaseError):
    """Exception raised for invalid file types."""

    code: ClassVar[str] = "INVALID_FILE_TYPE"
    message_en: ClassVar[str] = "File type is not supported"
    message_fa: ClassVar[str] = "نوع فایل پشتیبانی نمی‌شود"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value
    grpc_status: ClassVar[int] = 3

    def __init__(
        self,
        file_name: str | None = None,
        file_type: str | None = None,
        allowed_types: list[str] | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize InvalidFileTypeError."""
        data = {}
        if file_name:
            data["file_name"] = file_name
        if file_type:
            data["file_type"] = file_type
        if allowed_types:
            data["allowed_types"] = allowed_types
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class QuotaExceededError(BaseError):
    """Exception raised when a quota is exceeded."""

    code: ClassVar[str] = "QUOTA_EXCEEDED"
    message_en: ClassVar[str] = "Storage quota has been exceeded"
    message_fa: ClassVar[str] = "سهمیه ذخیره‌سازی به پایان رسیده است"
    http_status: ClassVar[int] = HTTPStatus.FORBIDDEN.value
    grpc_status: ClassVar[int] = 8

    def __init__(
        self,
        quota_type: str | None = None,
        current_usage: int | None = None,
        quota_limit: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize QuotaExceededError."""
        data = {}
        if quota_type:
            data["quota_type"] = quota_type
        if current_usage:
            data["current_usage"] = current_usage
        if quota_limit:
            data["quota_limit"] = quota_limit
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class ResourceExhaustedError(BaseError):
    """Exception raised when a resource is exhausted."""

    code: ClassVar[str] = "RESOURCE_EXHAUSTED"
    message_en: ClassVar[str] = "Resource limit has been reached"
    message_fa: ClassVar[str] = "محدودیت منابع به پایان رسیده است."
    http_status: ClassVar[int] = HTTPStatus.TOO_MANY_REQUESTS.value
    grpc_status: ClassVar[int] = 8

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize ResourceExhaustedError."""
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)


class StorageError(BaseError):
    """Exception raised for storage-related errors."""

    code: ClassVar[str] = "STORAGE_ERROR"
    message_en: ClassVar[str] = "Storage access error occurred"
    message_fa: ClassVar[str] = "خطا در دسترسی به فضای ذخیره‌سازی"
    http_status: ClassVar[int] = HTTPStatus.INTERNAL_SERVER_ERROR.value
    grpc_status: ClassVar[int] = 13

    def __init__(
        self,
        storage_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize StorageError."""
        data = {"storage_type": storage_type} if storage_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data or None)
