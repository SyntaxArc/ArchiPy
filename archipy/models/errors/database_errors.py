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


class DatabaseError(BaseError):
    """Base class for all database-related errors."""

    code: ClassVar[str] = "DATABASE_ERROR"
    message_en: ClassVar[str] = "Database error occurred"
    message_fa: ClassVar[str] = "خطای پایگاه داده رخ داده است"
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
        database: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if database:
            data["database"] = database
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class DatabaseConnectionError(DatabaseError):
    """Exception raised for database connection errors."""

    code: ClassVar[str] = "DATABASE_CONNECTION_ERROR"
    message_en: ClassVar[str] = "Failed to connect to the database"
    message_fa: ClassVar[str] = "خطا در اتصال به پایگاه داده"
    http_status: ClassVar[int] = (
        HTTPStatus.SERVICE_UNAVAILABLE.value if HTTP_AVAILABLE and HTTPStatus is not None else 503
    )
    grpc_status: ClassVar[int] = (
        StatusCode.UNAVAILABLE.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAVAILABLE.value, tuple)
        else (StatusCode.UNAVAILABLE.value if GRPC_AVAILABLE and StatusCode is not None else 14)
    )


class DatabaseQueryError(DatabaseError):
    """Exception raised for database query errors."""

    code: ClassVar[str] = "DATABASE_QUERY_ERROR"
    message_en: ClassVar[str] = "Error executing database query"
    message_fa: ClassVar[str] = "خطا در اجرای پرس و جوی پایگاه داده"
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
        database: str | None = None,
        query: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if query:
            data["query"] = query
        if additional_data:
            data.update(additional_data)
        super().__init__(database=database, lang=lang, additional_data=data if data else None)


class DatabaseTransactionError(DatabaseError):
    """Exception raised for database transaction errors."""

    code: ClassVar[str] = "DATABASE_TRANSACTION_ERROR"
    message_en: ClassVar[str] = "Error in database transaction"
    message_fa: ClassVar[str] = "خطا در تراکنش پایگاه داده"
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
        database: str | None = None,
        transaction_id: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if transaction_id:
            data["transaction_id"] = transaction_id
        if additional_data:
            data.update(additional_data)
        super().__init__(database=database, lang=lang, additional_data=data if data else None)


class DatabaseTimeoutError(DatabaseError):
    """Exception raised for database timeout errors."""

    code: ClassVar[str] = "DATABASE_TIMEOUT_ERROR"
    message_en: ClassVar[str] = "Database operation timed out"
    message_fa: ClassVar[str] = "عملیات پایگاه داده با تایم‌اوت مواجه شد"
    http_status: ClassVar[int] = HTTPStatus.REQUEST_TIMEOUT.value if HTTP_AVAILABLE and HTTPStatus is not None else 408
    grpc_status: ClassVar[int] = (
        StatusCode.DEADLINE_EXCEEDED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.DEADLINE_EXCEEDED.value, tuple)
        else (StatusCode.DEADLINE_EXCEEDED.value if GRPC_AVAILABLE and StatusCode is not None else 4)
    )

    def __init__(
        self,
        database: str | None = None,
        timeout: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if timeout:
            data["timeout"] = timeout
        if additional_data:
            data.update(additional_data)
        super().__init__(database=database, lang=lang, additional_data=data if data else None)


class DatabaseConstraintError(DatabaseError):
    """Exception raised for database constraint violations."""

    code: ClassVar[str] = "DATABASE_CONSTRAINT_ERROR"
    message_en: ClassVar[str] = "Database constraint violation"
    message_fa: ClassVar[str] = "نقض محدودیت پایگاه داده"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )

    def __init__(
        self,
        database: str | None = None,
        constraint: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if constraint:
            data["constraint"] = constraint
        if additional_data:
            data.update(additional_data)
        super().__init__(database=database, lang=lang, additional_data=data if data else None)


class DatabaseIntegrityError(DatabaseError):
    """Exception raised for database integrity violations."""

    code: ClassVar[str] = "DATABASE_INTEGRITY_ERROR"
    message_en: ClassVar[str] = "Database integrity violation"
    message_fa: ClassVar[str] = "نقض یکپارچگی پایگاه داده"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )


class DatabaseDeadlockError(DatabaseError):
    """Exception raised for database deadlock errors."""

    code: ClassVar[str] = "DATABASE_DEADLOCK_ERROR"
    message_en: ClassVar[str] = "Database deadlock detected"
    message_fa: ClassVar[str] = "قفل‌شدگی پایگاه داده تشخیص داده شد"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ABORTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ABORTED.value, tuple)
        else (StatusCode.ABORTED.value if GRPC_AVAILABLE and StatusCode is not None else 10)
    )


class DatabaseSerializationError(DatabaseError):
    """Exception raised for database serialization errors."""

    code: ClassVar[str] = "DATABASE_SERIALIZATION_ERROR"
    message_en: ClassVar[str] = "Database serialization failure"
    message_fa: ClassVar[str] = "خطای سریال‌سازی پایگاه داده"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.ABORTED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.ABORTED.value, tuple)
        else (StatusCode.ABORTED.value if GRPC_AVAILABLE and StatusCode is not None else 10)
    )


class DatabaseConfigurationError(DatabaseError):
    """Exception raised for database configuration errors."""

    code: ClassVar[str] = "DATABASE_CONFIGURATION_ERROR"
    message_en: ClassVar[str] = "Database configuration error"
    message_fa: ClassVar[str] = "خطای پیکربندی پایگاه داده"
    http_status: ClassVar[int] = (
        HTTPStatus.INTERNAL_SERVER_ERROR.value if HTTP_AVAILABLE and HTTPStatus is not None else 500
    )
    grpc_status: ClassVar[int] = (
        StatusCode.INTERNAL.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INTERNAL.value, tuple)
        else (StatusCode.INTERNAL.value if GRPC_AVAILABLE and StatusCode is not None else 13)
    )


class CacheError(BaseError):
    """Exception raised for cache access errors."""

    code: ClassVar[str] = "CACHE_ERROR"
    message_en: ClassVar[str] = "Error accessing cache"
    message_fa: ClassVar[str] = "خطا در دسترسی به حافظه نهان"
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
        cache_type: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if cache_type:
            data["cache_type"] = cache_type
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class CacheMissError(BaseError):
    """Exception raised when requested data is not found in cache."""

    code: ClassVar[str] = "CACHE_MISS"
    message_en: ClassVar[str] = "Requested data not found in cache: {cache_key}"
    message_fa: ClassVar[str] = "داده درخواستی در حافظه نهان یافت نشد: {cache_key}"
    http_status: ClassVar[int] = HTTPStatus.NOT_FOUND.value if HTTP_AVAILABLE and HTTPStatus is not None else 404
    grpc_status: ClassVar[int] = (
        StatusCode.NOT_FOUND.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.NOT_FOUND.value, tuple)
        else (StatusCode.NOT_FOUND.value if GRPC_AVAILABLE and StatusCode is not None else 5)
    )

    def __init__(
        self,
        cache_key: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"cache_key": cache_key} if cache_key else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with cache key."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        cache_key = self.additional_data.get("cache_key", "cache_key")
        return template.format(cache_key=cache_key)
