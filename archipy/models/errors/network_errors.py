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


class NetworkError(BaseError):
    """Exception raised for network-related errors."""

    code: ClassVar[str] = "NETWORK_ERROR"
    message_en: ClassVar[str] = "Network error occurred"
    message_fa: ClassVar[str] = "خطای شبکه رخ داده است"
    http_status: ClassVar[int] = HTTPStatus.BAD_GATEWAY.value if HTTP_AVAILABLE and HTTPStatus is not None else 502
    grpc_status: ClassVar[int] = (
        StatusCode.UNAVAILABLE.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAVAILABLE.value, tuple)
        else (StatusCode.UNAVAILABLE.value if GRPC_AVAILABLE and StatusCode is not None else 14)
    )

    def __init__(
        self,
        service: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if service:
            data["service"] = service
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class ConnectionTimeoutError(BaseError):
    """Exception raised when a connection times out."""

    code: ClassVar[str] = "CONNECTION_TIMEOUT"
    message_en: ClassVar[str] = "Connection timed out"
    message_fa: ClassVar[str] = "اتصال با تایم‌اوت مواجه شد"
    http_status: ClassVar[int] = HTTPStatus.REQUEST_TIMEOUT.value if HTTP_AVAILABLE and HTTPStatus is not None else 408
    grpc_status: ClassVar[int] = (
        StatusCode.DEADLINE_EXCEEDED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.DEADLINE_EXCEEDED.value, tuple)
        else (StatusCode.DEADLINE_EXCEEDED.value if GRPC_AVAILABLE and StatusCode is not None else 4)
    )

    def __init__(
        self,
        service: str | None = None,
        timeout: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if service:
            data["service"] = service
        if timeout:
            data["timeout"] = timeout
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class ServiceUnavailableError(BaseError):
    """Exception raised when a service is unavailable."""

    code: ClassVar[str] = "SERVICE_UNAVAILABLE"
    message_en: ClassVar[str] = "Service is currently unavailable"
    message_fa: ClassVar[str] = "سرویس در حال حاضر در دسترس نیست"
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
        service: str | None = None,
        retry_after: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if service:
            data["service"] = service
        if retry_after:
            data["retry_after"] = retry_after
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class GatewayTimeoutError(BaseError):
    """Exception raised when a gateway times out."""

    code: ClassVar[str] = "GATEWAY_TIMEOUT"
    message_en: ClassVar[str] = "Gateway timeout"
    message_fa: ClassVar[str] = "تایم‌اوت دروازه"
    http_status: ClassVar[int] = HTTPStatus.GATEWAY_TIMEOUT.value if HTTP_AVAILABLE and HTTPStatus is not None else 504
    grpc_status: ClassVar[int] = (
        StatusCode.DEADLINE_EXCEEDED.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.DEADLINE_EXCEEDED.value, tuple)
        else (StatusCode.DEADLINE_EXCEEDED.value if GRPC_AVAILABLE and StatusCode is not None else 4)
    )

    def __init__(
        self,
        gateway: str | None = None,
        timeout: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if gateway:
            data["gateway"] = gateway
        if timeout:
            data["timeout"] = timeout
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class BadGatewayError(BaseError):
    """Exception raised when a gateway returns an invalid response."""

    code: ClassVar[str] = "BAD_GATEWAY"
    message_en: ClassVar[str] = "Bad gateway"
    message_fa: ClassVar[str] = "دروازه نامعتبر"
    http_status: ClassVar[int] = HTTPStatus.BAD_GATEWAY.value if HTTP_AVAILABLE and HTTPStatus is not None else 502
    grpc_status: ClassVar[int] = (
        StatusCode.UNAVAILABLE.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.UNAVAILABLE.value, tuple)
        else (StatusCode.UNAVAILABLE.value if GRPC_AVAILABLE and StatusCode is not None else 14)
    )

    def __init__(
        self,
        gateway: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if gateway:
            data["gateway"] = gateway
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class RateLimitExceededError(BaseError):
    """Exception raised when a rate limit is exceeded."""

    code: ClassVar[str] = "RATE_LIMIT_EXCEEDED"
    message_en: ClassVar[str] = "Rate limit has been exceeded"
    message_fa: ClassVar[str] = "محدودیت نرخ درخواست به پایان رسیده است"
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
        rate_limit_type: str | None = None,
        retry_after: int | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if rate_limit_type:
            data["rate_limit_type"] = rate_limit_type
        if retry_after:
            data["retry_after"] = retry_after
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)
