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


class InvalidStateError(BaseError):
    """Exception raised when an operation is attempted in an invalid state."""

    code: ClassVar[str] = "INVALID_STATE"
    message_en: ClassVar[str] = "Invalid state for the requested operation"
    message_fa: ClassVar[str] = "وضعیت نامعتبر برای عملیات درخواستی"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )

    def __init__(
        self,
        current_state: str | None = None,
        expected_state: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if current_state:
            data["current_state"] = current_state
        if expected_state:
            data["expected_state"] = expected_state
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class FailedPreconditionError(BaseError):
    """Exception raised when a precondition for an operation is not met."""

    code: ClassVar[str] = "FAILED_PRECONDITION"
    message_en: ClassVar[str] = "Operation preconditions not met"
    message_fa: ClassVar[str] = "پیش‌نیازهای عملیات برآورده نشده است."
    http_status: ClassVar[int] = (
        HTTPStatus.PRECONDITION_FAILED.value if HTTP_AVAILABLE and HTTPStatus is not None else 412
    )
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )

    def __init__(
        self,
        precondition: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if precondition:
            data["precondition"] = precondition
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class BusinessRuleViolationError(BaseError):
    """Exception raised when a business rule is violated."""

    code: ClassVar[str] = "BUSINESS_RULE_VIOLATION"
    message_en: ClassVar[str] = "Business rule violation"
    message_fa: ClassVar[str] = "نقض قوانین کسب و کار"
    http_status: ClassVar[int] = HTTPStatus.CONFLICT.value if HTTP_AVAILABLE and HTTPStatus is not None else 409
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )

    def __init__(
        self,
        rule: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if rule:
            data["rule"] = rule
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidOperationError(BaseError):
    """Exception raised when an operation is not allowed in the current context."""

    code: ClassVar[str] = "INVALID_OPERATION"
    message_en: ClassVar[str] = "Operation is not allowed in the current context"
    message_fa: ClassVar[str] = "عملیات در وضعیت فعلی مجاز نیست"
    http_status: ClassVar[int] = HTTPStatus.FORBIDDEN.value if HTTP_AVAILABLE and HTTPStatus is not None else 403
    grpc_status: ClassVar[int] = (
        StatusCode.PERMISSION_DENIED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.PERMISSION_DENIED.value, tuple)
        else (StatusCode.PERMISSION_DENIED.value if GRPC_AVAILABLE and StatusCode is not None else 7)
    )

    def __init__(
        self,
        operation: str | None = None,
        context: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if operation:
            data["operation"] = operation
        if context:
            data["context"] = context
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InsufficientFundsError(BaseError):
    """Exception raised when there are insufficient funds for an operation."""

    code: ClassVar[str] = "INSUFFICIENT_FUNDS"
    message_en: ClassVar[str] = "Insufficient funds for the operation"
    message_fa: ClassVar[str] = "موجودی ناکافی برای عملیات"
    http_status: ClassVar[int] = HTTPStatus.PAYMENT_REQUIRED.value if HTTP_AVAILABLE and HTTPStatus is not None else 402
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )


class InsufficientBalanceError(BaseError):
    """Exception raised when an operation fails due to insufficient account balance."""

    code: ClassVar[str] = "INSUFFICIENT_BALANCE"
    message_en: ClassVar[str] = "Insufficient balance for operation"
    message_fa: ClassVar[str] = "عدم موجودی کافی برای عملیات."
    http_status: ClassVar[int] = HTTPStatus.PAYMENT_REQUIRED.value if HTTP_AVAILABLE and HTTPStatus is not None else 402
    grpc_status: ClassVar[int] = (
        StatusCode.FAILED_PRECONDITION.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.FAILED_PRECONDITION.value, tuple)
        else (StatusCode.FAILED_PRECONDITION.value if GRPC_AVAILABLE and StatusCode is not None else 9)
    )


class MaintenanceModeError(BaseError):
    """Exception raised when the system is in maintenance mode."""

    code: ClassVar[str] = "MAINTENANCE_MODE"
    message_en: ClassVar[str] = "System is currently in maintenance mode"
    message_fa: ClassVar[str] = "سیستم در حال حاضر در حالت تعمیر و نگهداری است"
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
        estimated_duration: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"estimated_duration": estimated_duration} if estimated_duration else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)
