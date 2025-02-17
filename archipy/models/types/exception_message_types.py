from enum import Enum

from archipy.models.dtos.exception_dto import ExceptionDetailDTO

try:
    from http import HTTPStatus

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    HTTPStatus = None

try:
    from grpc import StatusCode

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    StatusCode = None


def create_exception_detail(
    code: str,
    message_en: str,
    message_fa: str,
    http_status: int | HTTPStatus | None = None,
    grpc_status: int | StatusCode | None = None,
) -> ExceptionDetailDTO:
    """Helper function to create ExceptionDetailDTO with appropriate status codes"""
    status_kwargs = {}

    if HTTP_AVAILABLE and http_status is not None:
        status_kwargs['http_status'] = http_status.value if isinstance(http_status, HTTPStatus) else http_status

    if GRPC_AVAILABLE and grpc_status is not None:
        status_kwargs['grpc_status'] = grpc_status.value[0] if isinstance(grpc_status, StatusCode) else grpc_status

    return ExceptionDetailDTO(code=code, message_en=message_en, message_fa=message_fa, **status_kwargs)


class ExceptionMessageType(Enum):
    # Authentication Errors (400, 401, 403)
    UNAUTHENTICATED_TYPE = create_exception_detail(
        code='UNAUTHENTICATED_TYPE',
        message_en='You are not authorized to perform this action.',
        message_fa='You are not authorized to perform this action.',
        http_status=HTTPStatus.UNAUTHORIZED if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNAUTHENTICATED if GRPC_AVAILABLE else None,
    )
    INVALID_PHONE = create_exception_detail(
        code="INVALID_PHONE",
        message_en="Invalid Iranian phone number",
        message_fa="شماره تلفن همراه ایران نامعتبر است",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INVALID_ARGUMENT if GRPC_AVAILABLE else None,
    )

    INVALID_LANDLINE = create_exception_detail(
        code="INVALID_LANDLINE",
        message_en="Invalid Iranian landline number",
        message_fa="شماره تلفن ثابت ایران نامعتبر است",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INVALID_ARGUMENT if GRPC_AVAILABLE else None,
    )

    INVALID_NATIONAL_CODE = create_exception_detail(
        code="INVALID_NATIONAL_CODE",
        message_en="Invalid national code format",
        message_fa="کد ملی وارد شده اشتباه است",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INVALID_ARGUMENT if GRPC_AVAILABLE else None,
    )

    TOKEN_EXPIRED = create_exception_detail(
        code="TOKEN_EXPIRED",
        message_en="Authentication token has expired",
        message_fa="توکن احراز هویت منقضی شده است",
        http_status=HTTPStatus.UNAUTHORIZED if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNAUTHENTICATED if GRPC_AVAILABLE else None,
    )

    INVALID_TOKEN = create_exception_detail(
        code="INVALID_TOKEN",
        message_en="Invalid authentication token",
        message_fa="توکن احراز هویت نامعتبر است",
        http_status=HTTPStatus.UNAUTHORIZED if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNAUTHENTICATED if GRPC_AVAILABLE else None,
    )

    PERMISSION_DENIED = create_exception_detail(
        code="PERMISSION_DENIED",
        message_en="Permission denied for this operation",
        message_fa="دسترسی برای این عملیات مجاز نیست",
        http_status=HTTPStatus.FORBIDDEN if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.PERMISSION_DENIED if GRPC_AVAILABLE else None,
    )

    # Resource Errors (404, 409)
    NOT_FOUND = create_exception_detail(
        code="NOT_FOUND",
        message_en="Requested resource not found",
        message_fa="منبع درخواستی یافت نشد",
        http_status=HTTPStatus.NOT_FOUND if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.NOT_FOUND if GRPC_AVAILABLE else None,
    )

    ALREADY_EXISTS = create_exception_detail(
        code="ALREADY_EXISTS",
        message_en="Resource already exists",
        message_fa="منبع از قبل موجود است",
        http_status=HTTPStatus.CONFLICT if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.ALREADY_EXISTS if GRPC_AVAILABLE else None,
    )

    # Validation Errors (400)
    INVALID_ARGUMENT = create_exception_detail(
        code="INVALID_ARGUMENT",
        message_en="Invalid argument provided",
        message_fa="پارامتر ورودی نامعتبر است",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INVALID_ARGUMENT if GRPC_AVAILABLE else None,
    )

    OUT_OF_RANGE = create_exception_detail(
        code="OUT_OF_RANGE",
        message_en="Value is out of acceptable range",
        message_fa="مقدار خارج از محدوده مجاز است",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.OUT_OF_RANGE if GRPC_AVAILABLE else None,
    )

    # Operation Errors (408, 409, 412, 429)
    DEADLINE_EXCEEDED = create_exception_detail(
        code="DEADLINE_EXCEEDED",
        message_en="Operation deadline exceeded",
        message_fa="مهلت عملیات به پایان رسیده است",
        http_status=HTTPStatus.REQUEST_TIMEOUT if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.DEADLINE_EXCEEDED if GRPC_AVAILABLE else None,
    )

    FAILED_PRECONDITION = create_exception_detail(
        code="FAILED_PRECONDITION",
        message_en="Operation preconditions not met",
        message_fa="پیش‌نیازهای عملیات برآورده نشده است",
        http_status=HTTPStatus.PRECONDITION_FAILED if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.FAILED_PRECONDITION if GRPC_AVAILABLE else None,
    )

    RESOURCE_EXHAUSTED = create_exception_detail(
        code="RESOURCE_EXHAUSTED",
        message_en="Resource limit has been reached",
        message_fa="محدودیت منابع به پایان رسیده است",
        http_status=HTTPStatus.TOO_MANY_REQUESTS if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.RESOURCE_EXHAUSTED if GRPC_AVAILABLE else None,
    )

    ABORTED = create_exception_detail(
        code="ABORTED",
        message_en="Operation was aborted",
        message_fa="عملیات متوقف شد",
        http_status=HTTPStatus.CONFLICT if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.ABORTED if GRPC_AVAILABLE else None,
    )

    CANCELLED = create_exception_detail(
        code="CANCELLED",
        message_en="Operation was cancelled",
        message_fa="عملیات لغو شد",
        http_status=HTTPStatus.CONFLICT if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.CANCELLED if GRPC_AVAILABLE else None,
    )

    # System Errors (500, 501, 503)
    INVALID_ENTITY_TYPE = create_exception_detail(
        code="INVALID_ENTITY",
        message_en="Invalid entity type",
        message_fa="اینتیتی تایپ اشتباه است.",
        http_status=HTTPStatus.BAD_REQUEST if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INVALID_ARGUMENT if GRPC_AVAILABLE else None,
    )
    INTERNAL_ERROR = create_exception_detail(
        code="INTERNAL_ERROR",
        message_en="Internal system error occurred",
        message_fa="خطای داخلی سیستم رخ داده است",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INTERNAL if GRPC_AVAILABLE else None,
    )

    DATA_LOSS = create_exception_detail(
        code="DATA_LOSS",
        message_en="Critical data loss detected",
        message_fa="از دست دادن اطلاعات حیاتی تشخیص داده شد",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.DATA_LOSS if GRPC_AVAILABLE else None,
    )

    UNIMPLEMENTED = create_exception_detail(
        code="UNIMPLEMENTED",
        message_en="Requested operation is not implemented",
        message_fa="عملیات درخواستی پیاده‌سازی نشده است",
        http_status=HTTPStatus.NOT_IMPLEMENTED if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNIMPLEMENTED if GRPC_AVAILABLE else None,
    )

    UNAVAILABLE = create_exception_detail(
        code="UNAVAILABLE",
        message_en="Service is currently unavailable",
        message_fa="سرویس در حال حاضر در دسترس نیست",
        http_status=HTTPStatus.SERVICE_UNAVAILABLE if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNAVAILABLE if GRPC_AVAILABLE else None,
    )

    UNKNOWN_ERROR = create_exception_detail(
        code="UNKNOWN_ERROR",
        message_en="An unknown error occurred",
        message_fa="خطای ناشناخته‌ای رخ داده است",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.UNKNOWN if GRPC_AVAILABLE else None,
    )

    DEADLOCK_TYPE = create_exception_detail(
        code="DEADLOCK_TYPE",
        message_en="Deadlock type detected",
        message_fa="خطای دیتابیس رخ داده است.",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR if HTTP_AVAILABLE else None,
        grpc_status=StatusCode.INTERNAL if GRPC_AVAILABLE else None,
    )
