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

from archipy.helpers.utils.string_utils import StringUtils
from archipy.models.errors.base_error import BaseError
from archipy.models.types.language_type import LanguageType


class InvalidArgumentError(BaseError):
    """Exception raised for invalid arguments."""

    code: ClassVar[str] = "INVALID_ARGUMENT"
    message_en: ClassVar[str] = "Invalid argument provided: {argument}"
    message_fa: ClassVar[str] = "پارامتر ورودی نامعتبر است: {argument}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        argument_name: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"argument": argument_name} if argument_name else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with argument name."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        argument = self.additional_data.get("argument", "argument")
        return template.format(argument=argument)


class InvalidFormatError(BaseError):
    """Exception raised for invalid data formats."""

    code: ClassVar[str] = "INVALID_FORMAT"
    message_en: ClassVar[str] = "Invalid data format"
    message_fa: ClassVar[str] = "فرمت داده نامعتبر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        format_type: str | None = None,
        expected_format: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if format_type:
            data["format_type"] = format_type
        if expected_format:
            data["expected_format"] = expected_format
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidEmailError(BaseError):
    """Exception raised for invalid email formats."""

    code: ClassVar[str] = "INVALID_EMAIL"
    message_en: ClassVar[str] = "Invalid email format: {email}"
    message_fa: ClassVar[str] = "فرمت ایمیل نامعتبر است: {email}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        email: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"email": email} if email else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with email."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        email = self.additional_data.get("email", "email")
        return template.format(email=email)


class InvalidPhoneNumberError(BaseError):
    """Exception raised for invalid phone numbers."""

    code: ClassVar[str] = "INVALID_PHONE"
    message_en: ClassVar[str] = "Invalid Iranian phone number: {phone_number}"
    message_fa: ClassVar[str] = "شماره تلفن همراه ایران نامعتبر است: {phone_number}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        phone_number: str,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"phone_number": phone_number}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data)

    def get_message(self) -> str:
        """Gets the localized error message with phone number and normalization."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        phone_number = self.additional_data.get("phone_number", "phone_number")
        message = template.format(phone_number=phone_number)

        # Convert numbers to Persian if language is FA
        if self.lang == LanguageType.FA:
            message = StringUtils.convert_english_number_to_persian(message)

        return message


class InvalidLandlineNumberError(BaseError):
    """Exception raised for invalid landline numbers."""

    code: ClassVar[str] = "INVALID_LANDLINE"
    message_en: ClassVar[str] = "Invalid Iranian landline number: {landline_number}"
    message_fa: ClassVar[str] = "شماره تلفن ثابت ایران نامعتبر است: {landline_number}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        landline_number: str,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"landline_number": landline_number}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data)

    def get_message(self) -> str:
        """Gets the localized error message with landline number and normalization."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        landline_number = self.additional_data.get("landline_number", "landline_number")
        message = template.format(landline_number=landline_number)

        # Convert numbers to Persian if language is FA
        if self.lang == LanguageType.FA:
            message = StringUtils.convert_english_number_to_persian(message)

        return message


class InvalidNationalCodeError(BaseError):
    """Exception raised for invalid national codes."""

    code: ClassVar[str] = "INVALID_NATIONAL_CODE"
    message_en: ClassVar[str] = "Invalid national code format: {national_code}"
    message_fa: ClassVar[str] = "فرمت کد ملی وارد شده اشتباه است: {national_code}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        national_code: str,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"national_code": national_code}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data)

    def get_message(self) -> str:
        """Gets the localized error message with national code and normalization."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        national_code = self.additional_data.get("national_code", "national_code")
        message = template.format(national_code=national_code)

        # Convert numbers to Persian if language is FA
        if self.lang == LanguageType.FA:
            message = StringUtils.convert_english_number_to_persian(message)

        return message


class InvalidPasswordError(BaseError):
    """Exception raised when a password does not meet the security requirements."""

    code: ClassVar[str] = "INVALID_PASSWORD"
    message_en: ClassVar[str] = "Password does not meet the security requirements"
    message_fa: ClassVar[str] = "رمز عبور الزامات امنیتی را برآورده نمی‌کند."
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        requirements: list[str] | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"requirements": requirements} if requirements else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidDateError(BaseError):
    """Exception raised for invalid date formats."""

    code: ClassVar[str] = "INVALID_DATE"
    message_en: ClassVar[str] = "Invalid date format"
    message_fa: ClassVar[str] = "فرمت تاریخ نامعتبر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        date: str | None = None,
        expected_format: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if date:
            data["date"] = date
        if expected_format:
            data["expected_format"] = expected_format
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidUrlError(BaseError):
    """Exception raised for invalid URL formats."""

    code: ClassVar[str] = "INVALID_URL"
    message_en: ClassVar[str] = "Invalid URL format: {url}"
    message_fa: ClassVar[str] = "فرمت URL نامعتبر است: {url}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        url: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"url": url} if url else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with URL."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        url = self.additional_data.get("url", "url")
        return template.format(url=url)


class InvalidIpError(BaseError):
    """Exception raised for invalid IP address formats."""

    code: ClassVar[str] = "INVALID_IP"
    message_en: ClassVar[str] = "Invalid IP address format: {ip}"
    message_fa: ClassVar[str] = "فرمت آدرس IP نامعتبر است: {ip}"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        ip: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"ip": ip} if ip else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)

    def get_message(self) -> str:
        """Gets the localized error message with IP address."""
        template = self.message_fa if self.lang == LanguageType.FA else self.message_en
        ip = self.additional_data.get("ip", "ip")
        return template.format(ip=ip)


class InvalidJsonError(BaseError):
    """Exception raised for invalid JSON formats."""

    code: ClassVar[str] = "INVALID_JSON"
    message_en: ClassVar[str] = "Invalid JSON format"
    message_fa: ClassVar[str] = "فرمت JSON نامعتبر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        json_data: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if json_data:
            data["json_data"] = json_data
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class InvalidTimestampError(BaseError):
    """Exception raised when a timestamp format is invalid."""

    code: ClassVar[str] = "INVALID_TIMESTAMP"
    message_en: ClassVar[str] = "Invalid timestamp format"
    message_fa: ClassVar[str] = "فرمت زمان نامعتبر است"
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.INVALID_ARGUMENT.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.INVALID_ARGUMENT.value, tuple)
        else (StatusCode.INVALID_ARGUMENT.value if GRPC_AVAILABLE and StatusCode is not None else 3)
    )

    def __init__(
        self,
        timestamp: str | None = None,
        expected_format: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {}
        if timestamp:
            data["timestamp"] = timestamp
        if expected_format:
            data["expected_format"] = expected_format
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)


class OutOfRangeError(BaseError):
    """Exception raised when a value is out of range."""

    code: ClassVar[str] = "OUT_OF_RANGE"
    message_en: ClassVar[str] = "Value is out of acceptable range"
    message_fa: ClassVar[str] = "مقدار خارج از محدوده مجاز است."
    http_status: ClassVar[int] = HTTPStatus.BAD_REQUEST.value if HTTP_AVAILABLE and HTTPStatus is not None else 400
    grpc_status: ClassVar[int] = (
        StatusCode.OUT_OF_RANGE.value[0]
        if GRPC_AVAILABLE and StatusCode is not None and isinstance(StatusCode.OUT_OF_RANGE.value, tuple)
        else (StatusCode.OUT_OF_RANGE.value if GRPC_AVAILABLE and StatusCode is not None else 11)
    )

    def __init__(
        self,
        field_name: str | None = None,
        lang: LanguageType | None = None,
        additional_data: dict | None = None,
    ) -> None:
        data = {"field": field_name} if field_name else {}
        if additional_data:
            data.update(additional_data)
        super().__init__(lang=lang, additional_data=data if data else None)
