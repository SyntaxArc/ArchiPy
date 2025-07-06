import json
from typing import ClassVar

from keycloak.exceptions import KeycloakError

from archipy.models.errors.base_error import BaseError
from archipy.models.errors.system_errors import InternalError
from archipy.models.types.keycloak_error_message_types import KeycloakErrorMessageType


class RealmAlreadyExistsError(BaseError):
    """Exception raised when trying to create a realm that already exists."""

    http_status_code: ClassVar[int] = 409
    grpc_status_code: ClassVar[int] = 6  # ALREADY_EXISTS


class UserAlreadyExistsError(BaseError):
    """Exception raised when trying to create a user that already exists."""

    http_status_code: ClassVar[int] = 409
    grpc_status_code: ClassVar[int] = 6  # ALREADY_EXISTS


class ClientAlreadyExistsError(BaseError):
    """Exception raised when trying to create a client that already exists."""

    http_status_code: ClassVar[int] = 409
    grpc_status_code: ClassVar[int] = 6  # ALREADY_EXISTS


class RoleAlreadyExistsError(BaseError):
    """Exception raised when trying to create a role that already exists."""

    http_status_code: ClassVar[int] = 409
    grpc_status_code: ClassVar[int] = 6  # ALREADY_EXISTS


class InvalidCredentialsError(BaseError):
    """Exception raised for invalid authentication credentials."""

    http_status_code: ClassVar[int] = 401
    grpc_status_code: ClassVar[int] = 16  # UNAUTHENTICATED


class ResourceNotFoundError(BaseError):
    """Exception raised when a resource is not found."""

    http_status_code: ClassVar[int] = 404
    grpc_status_code: ClassVar[int] = 5  # NOT_FOUND


class InsufficientPermissionsError(BaseError):
    """Exception raised when user lacks required permissions."""

    http_status_code: ClassVar[int] = 403
    grpc_status_code: ClassVar[int] = 7  # PERMISSION_DENIED


class ValidationError(BaseError):
    """Exception raised for validation errors."""

    http_status_code: ClassVar[int] = 400
    grpc_status_code: ClassVar[int] = 3  # INVALID_ARGUMENT


class PasswordPolicyError(BaseError):
    """Exception raised when password doesn't meet policy requirements."""

    http_status_code: ClassVar[int] = 400
    grpc_status_code: ClassVar[int] = 3  # INVALID_ARGUMENT


class KeycloakConnectionTimeoutError(BaseError):
    """Exception raised when Keycloak connection times out."""

    http_status_code: ClassVar[int] = 504
    grpc_status_code: ClassVar[int] = 4  # DEADLINE_EXCEEDED


class KeycloakServiceUnavailableError(BaseError):
    """Exception raised when Keycloak service is unavailable."""

    http_status_code: ClassVar[int] = 503
    grpc_status_code: ClassVar[int] = 14  # UNAVAILABLE


def get_error_message(keycloak_error: KeycloakError) -> str:
    """Extract the actual error message from Keycloak error."""
    error_message = str(keycloak_error)

    # Try to parse JSON response body
    if hasattr(keycloak_error, "response_body") and keycloak_error.response_body:
        try:
            body = keycloak_error.response_body
            if isinstance(body, bytes):
                body = body.decode("utf-8")

            if isinstance(body, str):
                parsed = json.loads(body)
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


def handle_keycloak_error(keycloak_error: KeycloakError, **additional_data) -> BaseError:
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
        return RealmAlreadyExistsError(
            error=KeycloakErrorMessageType.REALM_ALREADY_EXISTS.value,
            additional_data=context,
        )

    # User errors
    if "user exists with same" in error_lower:
        return UserAlreadyExistsError(error=KeycloakErrorMessageType.USER_ALREADY_EXISTS.value, additional_data=context)

    # Client errors
    if "client" in error_lower and "already exists" in error_lower:
        return ClientAlreadyExistsError(
            error=KeycloakErrorMessageType.CLIENT_ALREADY_EXISTS.value,
            additional_data=context,
        )

    # Authentication errors
    if any(
        phrase in error_lower for phrase in ["invalid user credentials", "invalid credentials", "authentication failed"]
    ):
        return InvalidCredentialsError(
            error=KeycloakErrorMessageType.INVALID_CREDENTIALS.value,
            additional_data=context,
        )

    # Not found errors
    if "not found" in error_lower:
        return ResourceNotFoundError(error=KeycloakErrorMessageType.RESOURCE_NOT_FOUND.value, additional_data=context)

    # Permission errors
    if any(phrase in error_lower for phrase in ["forbidden", "access denied", "insufficient permissions"]):
        return InsufficientPermissionsError(
            error=KeycloakErrorMessageType.INSUFFICIENT_PERMISSIONS.value,
            additional_data=context,
        )

    # Validation errors (400 status codes that don't match above)
    if response_code == 400:
        return ValidationError(error=KeycloakErrorMessageType.VALIDATION_ERROR.value, additional_data=context)

    # Default to InternalError for unrecognized errors
    return InternalError(additional_data=context)
