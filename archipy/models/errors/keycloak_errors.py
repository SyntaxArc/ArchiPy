import json
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from http import HTTPStatus

    from grpc import StatusCode
else:
    HTTPStatus = None
    StatusCode = None

try:
    from keycloak.exceptions import KeycloakError
except ImportError:
    KeycloakError: type[Exception] = Exception

from archipy.models.errors.base_error import BaseError
from archipy.models.errors.system_errors import InternalError


class RealmAlreadyExistsError(BaseError):
    """Exception raised when trying to create a realm that already exists."""

    code: ClassVar[str] = "REALM_ALREADY_EXISTS"
    message_en: ClassVar[str] = "Realm already exists"
    message_fa: ClassVar[str] = "قلمرو از قبل وجود دارد"
    http_status: ClassVar[int] = 409
    grpc_status: ClassVar[int] = 6


class UserAlreadyExistsError(BaseError):
    """Exception raised when trying to create a user that already exists."""

    code: ClassVar[str] = "USER_ALREADY_EXISTS"
    message_en: ClassVar[str] = "User already exists"
    message_fa: ClassVar[str] = "کاربر از قبل وجود دارد"
    http_status: ClassVar[int] = 409
    grpc_status: ClassVar[int] = 6


class ClientAlreadyExistsError(BaseError):
    """Exception raised when trying to create a client that already exists."""

    code: ClassVar[str] = "CLIENT_ALREADY_EXISTS"
    message_en: ClassVar[str] = "Client already exists"
    message_fa: ClassVar[str] = "کلاینت از قبل وجود دارد"
    http_status: ClassVar[int] = 409
    grpc_status: ClassVar[int] = 6


class RoleAlreadyExistsError(BaseError):
    """Exception raised when trying to create a role that already exists."""

    code: ClassVar[str] = "ROLE_ALREADY_EXISTS"
    message_en: ClassVar[str] = "Role already exists"
    message_fa: ClassVar[str] = "نقش از قبل وجود دارد"
    http_status: ClassVar[int] = 409
    grpc_status: ClassVar[int] = 6


class InvalidCredentialsError(BaseError):
    """Exception raised for invalid authentication credentials."""

    code: ClassVar[str] = "INVALID_CREDENTIALS"
    message_en: ClassVar[str] = "Invalid credentials"
    message_fa: ClassVar[str] = "اطلاعات ورود نامعتبر"
    http_status: ClassVar[int] = 401
    grpc_status: ClassVar[int] = 16


class ResourceNotFoundError(BaseError):
    """Exception raised when a resource is not found."""

    code: ClassVar[str] = "RESOURCE_NOT_FOUND"
    message_en: ClassVar[str] = "Resource not found"
    message_fa: ClassVar[str] = "منبع یافت نشد"
    http_status: ClassVar[int] = 404
    grpc_status: ClassVar[int] = 5


class InsufficientPermissionsError(BaseError):
    """Exception raised when user lacks required permissions."""

    code: ClassVar[str] = "INSUFFICIENT_PERMISSIONS"
    message_en: ClassVar[str] = "Insufficient permissions"
    message_fa: ClassVar[str] = "دسترسی کافی نیست"
    http_status: ClassVar[int] = 403
    grpc_status: ClassVar[int] = 7


class ValidationError(BaseError):
    """Exception raised for validation errors."""

    code: ClassVar[str] = "VALIDATION_ERROR"
    message_en: ClassVar[str] = "Validation error"
    message_fa: ClassVar[str] = "خطای اعتبارسنجی"
    http_status: ClassVar[int] = 400
    grpc_status: ClassVar[int] = 3


class PasswordPolicyError(BaseError):
    """Exception raised when password doesn't meet policy requirements."""

    code: ClassVar[str] = "PASSWORD_POLICY_VIOLATION"
    message_en: ClassVar[str] = "Password does not meet policy requirements"
    message_fa: ClassVar[str] = "رمز عبور الزامات سیاست را برآورده نمی‌کند"
    http_status: ClassVar[int] = 400
    grpc_status: ClassVar[int] = 3


class KeycloakConnectionTimeoutError(BaseError):
    """Exception raised when Keycloak connection times out."""

    code: ClassVar[str] = "CONNECTION_TIMEOUT"
    message_en: ClassVar[str] = "Connection timeout"
    message_fa: ClassVar[str] = "زمان اتصال به پایان رسید"
    http_status: ClassVar[int] = 504
    grpc_status: ClassVar[int] = 4


class KeycloakServiceUnavailableError(BaseError):
    """Exception raised when Keycloak service is unavailable."""

    code: ClassVar[str] = "SERVICE_UNAVAILABLE"
    message_en: ClassVar[str] = "Service unavailable"
    message_fa: ClassVar[str] = "سرویس در دسترس نیست"
    http_status: ClassVar[int] = 503
    grpc_status: ClassVar[int] = 14


def get_error_message(keycloak_error: KeycloakError) -> str:
    """Extract the actual error message from Keycloak error."""
    error_message = str(keycloak_error)

    # Try to parse JSON response body
    if hasattr(keycloak_error, "response_body") and keycloak_error.response_body:
        try:
            body = keycloak_error.response_body
            body_str = body.decode("utf-8") if isinstance(body, bytes) else str(body)

            # body_str is now guaranteed to be str after decode
            parsed = json.loads(body_str)
            if isinstance(parsed, dict):
                error_message = (
                    parsed.get("errorMessage")
                    or parsed.get("error_description")
                    or parsed.get("error")
                    or error_message
                )
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    return error_message


def handle_keycloak_error(keycloak_error: KeycloakError, **additional_data: Any) -> BaseError:
    """Convert Keycloak error to appropriate custom error."""
    error_message = get_error_message(keycloak_error)
    response_code = getattr(keycloak_error, "response_code", None)

    # Add context data
    context = {
        "original_error": error_message,
        "response_code": response_code,
        "keycloak_error_type": type(keycloak_error).__name__,
        **additional_data,
    }

    # Simple string matching to identify error types
    error_lower = error_message.lower()

    # Realm errors
    if "realm" in error_lower and "already exists" in error_lower:
        return RealmAlreadyExistsError(additional_data=context)

    # User errors
    if "user exists with same" in error_lower:
        return UserAlreadyExistsError(additional_data=context)

    # Client errors
    if "client" in error_lower and "already exists" in error_lower:
        return ClientAlreadyExistsError(additional_data=context)

    # Authentication errors
    if any(
        phrase in error_lower for phrase in ["invalid user credentials", "invalid credentials", "authentication failed"]
    ):
        return InvalidCredentialsError(additional_data=context)

    # Not found errors
    if "not found" in error_lower:
        return ResourceNotFoundError(additional_data=context)

    # Permission errors
    if any(phrase in error_lower for phrase in ["forbidden", "access denied", "insufficient permissions"]):
        return InsufficientPermissionsError(additional_data=context)

    # Validation errors (400 status codes that don't match above)
    if response_code == 400:
        return ValidationError(additional_data=context)

    # Default to InternalError for unrecognized errors
    return InternalError(additional_data=context)
