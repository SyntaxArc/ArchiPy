from typing import TYPE_CHECKING, ClassVar

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
from archipy.models.types.language_type import LanguageType


class NotFoundError(BaseError):
    """Exception raised when a resource is not found."""

    code: ClassVar[str] = "NOT_FOUND"
    message_en: ClassVar[str] = "Requested resource not found: {resource_type}"
    message_fa: ClassVar[str] = "منبع درخواستی یافت نشد: {resource_type}"
    http_status: ClassVar[int] = HTTPStatus.NOT_FOUND.value if HTTP_AVAILABLE and HTTPStatus is not None else 404
    grpc_status: ClassVar[int] = (
        StatusCode.NOT_FOUND.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.NOT_FOUND.value, tuple)
        else (StatusCode.NOT_FOUND.value if GRPC_AVAILABLE and StatusCode is not None else 5)
    )

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

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
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ALREADY_EXISTS.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ALREADY_EXISTS.value, tuple)
        else (StatusCode.ALREADY_EXISTS.value if GRPC_AVAILABLE and StatusCode is not None else 6)
    )

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

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
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ABORTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ABORTED.value, tuple)
        else (StatusCode.ABORTED.value if GRPC_AVAILABLE and StatusCode is not None else 10)
    )

    def __init__(
        self,
        resource_type: str | None = None,
        resource_id: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if resource_type:
            data["resource_type"] = resource_type
        if resource_id:
            data["resource_id"] = resource_id
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class ResourceLockedError(BaseError):
    """Exception raised when a resource is locked."""

    code: ClassVar[str] = "RESOURCE_LOCKED"
    message_en: ClassVar[str] = "Resource is currently locked"
    message_fa: ClassVar[str] = "منبع در حال حاضر قفل شده است"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ABORTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ABORTED.value, tuple)
        else (StatusCode.ABORTED.value if GRPC_AVAILABLE and StatusCode is not None else 10)
    )

    def __init__(
        self,
        resource_id: str | None = None,
        lock_owner: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if resource_id:
            data["resource_id"] = resource_id
        if lock_owner:
            data["lock_owner"] = lock_owner
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class ResourceBusyError(BaseError):
    """Exception raised when a resource is busy."""

    code: ClassVar[str] = "RESOURCE_BUSY"
    message_en: ClassVar[str] = "Resource is currently busy"
    message_fa: ClassVar[str] = "منبع در حال حاضر مشغول است"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ABORTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ABORTED.value, tuple)
        else (StatusCode.ABORTED.value if GRPC_AVAILABLE and StatusCode is not None else 10)
    )

    def __init__(
        self,
        resource_id: str | None = None,
        busy_reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if resource_id:
            data["resource_id"] = resource_id
        if busy_reason:
            data["busy_reason"] = busy_reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class DataLossError(BaseError):
    """Exception raised when data is lost."""

    code: ClassVar[str] = "DATA_LOSS"
    message_en: ClassVar[str] = "Critical data loss detected"
    message_fa: ClassVar[str] = "از دست دادن اطلاعات حیاتی تشخیص داده شد."
    http_status: ClassVar[int] = (
        HTTPStatus.INTERNAL_SERVER_ERROR.value if HTTP_AVAILABLE and HTTPStatus is not None else 500
    )
    grpc_status: ClassVar[int] = (
        StatusCode.DATA_LOSS.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.DATA_LOSS.value, tuple)
        else (StatusCode.DATA_LOSS.value if GRPC_AVAILABLE and StatusCode is not None else 15)
    )


class InvalidEntityTypeError(BaseError):
    """Exception raised for invalid entity types."""

    code: ClassVar[str] = "INVALID_ENTITY"
    message_en: ClassVar[str] = "Invalid entity type"
    message_fa: ClassVar[str] = "نوع موجودیت نامعتبر است."
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        message: str | None = None,
        expected_type: str | None = None,
        actual_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if message:
            data["message"] = message
        if expected_type:
            data["expected_type"] = expected_type
        if actual_type:
            data["actual_type"] = actual_type
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class FileTooLargeError(BaseError):
    """Exception raised when a file is too large."""

    code: ClassVar[str] = "FILE_TOO_LARGE"
    message_en: ClassVar[str] = "File size exceeds the maximum allowed limit"
    message_fa: ClassVar[str] = "حجم فایل از حد مجاز بیشتر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        file_name: str | None = None,
        file_size: int | None = None,
        max_size: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if file_name:
            data["file_name"] = file_name
        if file_size:
            data["file_size"] = file_size
        if max_size:
            data["max_size"] = max_size
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidFileTypeError(BaseError):
    """Exception raised for invalid file types."""

    code: ClassVar[str] = "INVALID_FILE_TYPE"
    message_en: ClassVar[str] = "File type is not supported"
    message_fa: ClassVar[str] = "نوع فایل پشتیبانی نمی‌شود"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        file_name: str | None = None,
        file_type: str | None = None,
        allowed_types: list[str] | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if file_name:
            data["file_name"] = file_name
        if file_type:
            data["file_type"] = file_type
        if allowed_types:
            data["allowed_types"] = allowed_types
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class QuotaExceededError(BaseError):
    """Exception raised when a quota is exceeded."""

    code: ClassVar[str] = "QUOTA_EXCEEDED"
    message_en: ClassVar[str] = "Storage quota has been exceeded"
    message_fa: ClassVar[str] = "سهمیه ذخیره‌سازی به پایان رسیده است"
    http_status: ClassVar[int] = HTTPStatus.FORBIDDEN.value if HTTP_AVAILABLE and HTTPStatus is not None else 403
    grpc_status: ClassVar[int] = (
        StatusCode.RESOURCE_EXHAUSTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.RESOURCE_EXHAUSTED.value, tuple)
        else (StatusCode.RESOURCE_EXHAUSTED.value if GRPC_AVAILABLE and StatusCode is not None else 8)
    )

    def __init__(
        self,
        quota_type: str | None = None,
        current_usage: int | None = None,
        quota_limit: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if quota_type:
            data["quota_type"] = quota_type
        if current_usage:
            data["current_usage"] = current_usage
        if quota_limit:
            data["quota_limit"] = quota_limit
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class ResourceExhaustedError(BaseError):
    """Exception raised when a resource is exhausted."""

    code: ClassVar[str] = "RESOURCE_EXHAUSTED"
    message_en: ClassVar[str] = "Resource limit has been reached"
    message_fa: ClassVar[str] = "محدودیت منابع به پایان رسیده است."
    http_status: ClassVar[int] = (
        HTTPStatus.TOO_MANY_REQUESTS.value if HTTP_AVAILABLE and HTTPStatus is not None else 429
    )
    grpc_status: ClassVar[int] = (
        StatusCode.RESOURCE_EXHAUSTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.RESOURCE_EXHAUSTED.value, tuple)
        else (StatusCode.RESOURCE_EXHAUSTED.value if GRPC_AVAILABLE and StatusCode is not None else 8)
    )

    def __init__(
        self,
        resource_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"resource_type": resource_type} if resource_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class StorageError(BaseError):
    """Exception raised for storage-related errors."""

    code: ClassVar[str] = "STORAGE_ERROR"
    message_en: ClassVar[str] = "Storage access error occurred"
    message_fa: ClassVar[str] = "خطا در دسترسی به فضای ذخیره‌سازی"
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
        storage_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"storage_type": storage_type} if storage_type else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)
