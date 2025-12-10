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


class UnauthenticatedError(BaseError):
    """Exception raised when a user is unauthenticated."""

    code: ClassVar[str] = "UNAUTHENTICATED"
    message_en: ClassVar[str] = "You are not authorized to perform this action."
    message_fa: ClassVar[str] = "شما مجوز انجام این عمل را ندارید."
    http_status: ClassVar[int] = HTTPStatus.UNAUTHORIZED.value if HTTP_AVAILABLE and HTTPStatus is not None else 401
    grpc_status: ClassVar[int] = (
        StatusCode.UNAUTHENTICATED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAUTHENTICATED.value, tuple)
        else (
            StatusCode.UNAUTHENTICATED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 16
        )
    )


class InvalidCredentialsError(BaseError):
    """Exception raised for invalid credentials."""

    code: ClassVar[str] = "INVALID_CREDENTIALS"
    message_en: ClassVar[str] = "Invalid username or password: {username}"
    message_fa: ClassVar[str] = "نام کاربری یا رمز عبور نامعتبر است: {username}"
    http_status: ClassVar[int] = HTTPStatus.UNAUTHORIZED.value if HTTP_AVAILABLE and HTTPStatus is not None else 401
    grpc_status: ClassVar[int] = (
        StatusCode.UNAUTHENTICATED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAUTHENTICATED.value, tuple)
        else (
            StatusCode.UNAUTHENTICATED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 16
        )
    )

    def __init__(
        self,
        username: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"username": username} if username else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with username."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        username = self.additional_data.get("username", "username")
        return template.format(username=username)


class TokenExpiredError(BaseError):
    """Exception raised when a token has expired."""

    code: ClassVar[str] = "TOKEN_EXPIRED"
    message_en: ClassVar[str] = "Authentication token has expired"
    message_fa: ClassVar[str] = "توکن احراز هویت منقضی شده است."
    http_status: ClassVar[int] = HTTPStatus.UNAUTHORIZED.value if HTTP_AVAILABLE and HTTPStatus is not None else 401
    grpc_status: ClassVar[int] = (
        StatusCode.UNAUTHENTICATED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAUTHENTICATED.value, tuple)
        else (
            StatusCode.UNAUTHENTICATED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 16
        )
    )


class InvalidTokenError(BaseError):
    """Exception raised when a token is invalid."""

    code: ClassVar[str] = "INVALID_TOKEN"
    message_en: ClassVar[str] = "Invalid authentication token"
    message_fa: ClassVar[str] = "توکن احراز هویت نامعتبر است."
    http_status: ClassVar[int] = HTTPStatus.UNAUTHORIZED.value if HTTP_AVAILABLE and HTTPStatus is not None else 401
    grpc_status: ClassVar[int] = (
        StatusCode.UNAUTHENTICATED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAUTHENTICATED.value, tuple)
        else (
            StatusCode.UNAUTHENTICATED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 16
        )
    )


class SessionExpiredError(BaseError):
    """Exception raised when a session has expired."""

    code: ClassVar[str] = "SESSION_EXPIRED"
    message_en: ClassVar[str] = "Session has expired: {session_id}"
    message_fa: ClassVar[str] = "نشست کاربری منقضی شده است: {session_id}"
    http_status: ClassVar[int] = HTTPStatus.UNAUTHORIZED.value if HTTP_AVAILABLE and HTTPStatus is not None else 401
    grpc_status: ClassVar[int] = (
        StatusCode.UNAUTHENTICATED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAUTHENTICATED.value, tuple)
        else (
            StatusCode.UNAUTHENTICATED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 16
        )
    )

    def __init__(
        self,
        session_id: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"session_id": session_id} if session_id else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with session ID."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        session_id = self.additional_data.get("session_id", "session_id")
        return template.format(session_id=session_id)


class PermissionDeniedError(BaseError):
    """Exception raised when permission is denied."""

    code: ClassVar[str] = "PERMISSION_DENIED"
    message_en: ClassVar[str] = "Permission denied for this operation"
    message_fa: ClassVar[str] = "دسترسی برای انجام این عملیات وجود ندارد."
    http_status: ClassVar[int] = (
        HTTPStatus.FORBIDDEN.value if HTTP_AVAILABLE and HTTPStatus is not None and HTTPStatus is not None else 403
    )
    grpc_status: ClassVar[int] = (
        StatusCode.PERMISSION_DENIED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.PERMISSION_DENIED.value, tuple)
        else (
            StatusCode.PERMISSION_DENIED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 7
        )
    )


class AccountLockedError(BaseError):
    """Exception raised when an account is locked."""

    code: ClassVar[str] = "ACCOUNT_LOCKED"
    message_en: ClassVar[str] = "Account has been locked due to too many failed attempts"
    message_fa: ClassVar[str] = "حساب کاربری به دلیل تلاش‌های ناموفق متعدد قفل شده است"
    http_status: ClassVar[int] = (
        HTTPStatus.FORBIDDEN.value if HTTP_AVAILABLE and HTTPStatus is not None and HTTPStatus is not None else 403
    )
    grpc_status: ClassVar[int] = (
        StatusCode.PERMISSION_DENIED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.PERMISSION_DENIED.value, tuple)
        else (
            StatusCode.PERMISSION_DENIED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 7
        )
    )

    def __init__(
        self,
        username: str | None = None,
        lockout_duration: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if username:
            data["username"] = username
        if lockout_duration:
            data["lockout_duration"] = lockout_duration
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class AccountDisabledError(BaseError):
    """Exception raised when an account is disabled."""

    code: ClassVar[str] = "ACCOUNT_DISABLED"
    message_en: ClassVar[str] = "Account has been disabled"
    message_fa: ClassVar[str] = "حساب کاربری غیرفعال شده است"
    http_status: ClassVar[int] = (
        HTTPStatus.FORBIDDEN.value if HTTP_AVAILABLE and HTTPStatus is not None and HTTPStatus is not None else 403
    )
    grpc_status: ClassVar[int] = (
        StatusCode.PERMISSION_DENIED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.PERMISSION_DENIED.value, tuple)
        else (
            StatusCode.PERMISSION_DENIED.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 7
        )
    )

    def __init__(
        self,
        username: str | None = None,
        reason: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if username:
            data["username"] = username
        if reason:
            data["reason"] = reason
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidVerificationCodeError(BaseError):
    """Exception raised when a verification code is invalid."""

    code: ClassVar[str] = "INVALID_VERIFICATION_CODE"
    message_en: ClassVar[str] = "Invalid verification code"
    message_fa: ClassVar[str] = "کد تایید نامعتبر است"
    http_status: ClassVar[int] = (
        HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None and HTTPStatus is not None else 400
    )
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (
            StatusCode.INVALID_ARGUMENT.value
            if GRPC_AVAILABLE and StatusCode is not None and StatusCode is not None
            else 3
        )
    )

    def __init__(
        self,
        code: str | None = None,
        remaining_attempts: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if code:
            data["code"] = code
        if remaining_attempts is not None:
            data["remaining_attempts"] = remaining_attempts
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)
