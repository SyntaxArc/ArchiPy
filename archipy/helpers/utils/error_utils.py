import logging
from typing import Any, Protocol

from pydantic_core._pydantic_core import ValidationError

from archipy.configs.base_config import BaseConfig
from archipy.models.dtos.fastapi_exception_response_dto import (
    FastAPIErrorResponseDTO,
    ValidationErrorResponseDTO,
)
from archipy.models.errors import BaseError

logger = logging.getLogger(__name__)


# Define type protocols for better type checking
class RequestProtocol(Protocol):
    """Protocol for FastAPI Request objects."""


class JSONResponseProtocol(Protocol):
    """Protocol for FastAPI JSONResponse objects."""


# Define forward references for conditional imports
class _HTTPStatusPlaceholder:
    INTERNAL_SERVER_ERROR = 500


class _StatusCodePlaceholder:
    class UNKNOWN:
        value = (2, "UNKNOWN")


# Use real classes if available, otherwise use placeholders
try:
    from http import HTTPStatus

    from fastapi import Request  # noqa: F401
    from fastapi.responses import JSONResponse

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    # Using globals() to avoid "cannot assign to a type" error
    globals()["HTTPStatus"] = _HTTPStatusPlaceholder
    globals()["Request"] = object
    globals()["JSONResponse"] = object

try:
    from grpc import StatusCode

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    globals()["StatusCode"] = _StatusCodePlaceholder


class ErrorUtils:
    """A utility class for handling errors, including capturing, reporting, and generating responses."""

    @staticmethod
    def format_validation_errors(
        validation_error: ValidationError,
        *,
        include_type: bool = False,
    ) -> list[dict[str, str]]:
        """Formats Pydantic validation errors into a structured format.

        Args:
            validation_error (ValidationError): The validation error to format.
            include_type (bool): Whether to include the error type in the output. Defaults to False.

        Returns:
            list[dict[str, str]]: A list of formatted validation error details.
        """
        formatted_errors = []
        for error in validation_error.errors():
            error_dict = {
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "value": str(error.get("input", "")),
            }
            if include_type:
                error_dict["type"] = error["type"]
            formatted_errors.append(error_dict)

        return formatted_errors

    @staticmethod
    def capture_exception(exception: BaseException) -> None:
        """Captures an exception and reports it to configured external services.

        This method logs the exception locally and optionally reports it to Sentry and Elastic APM,
        depending on the configuration.

        Args:
            exception (BaseException): The exception to capture and report.
        """
        # Always log the exception locally
        logger.exception("An exception occurred")
        config: Any = BaseConfig.global_config()

        # Report exception to Sentry if enabled
        if config.SENTRY.IS_ENABLED:
            try:
                import sentry_sdk

                sentry_sdk.capture_exception(exception)
            except ImportError:
                logger.exception("sentry_sdk is not installed, cannot capture exception in Sentry.")

        # Report exception to Elastic APM if enabled
        if config.ELASTIC_APM.IS_ENABLED:
            try:
                import elasticapm

                # Type ignoring elasticapm.get_client() as it's a third-party function
                client = elasticapm.get_client()
                client.capture_exception()
            except ImportError:
                logger.exception("elasticapm is not installed, cannot capture exception in Elastic APM.")

    @staticmethod
    async def async_handle_fastapi_exception(_request: RequestProtocol, exception: BaseError) -> JSONResponseProtocol:
        """Handles a FastAPI exception and returns a JSON response.

        Args:
            _request (Request): The incoming FastAPI request.
            exception (BaseError): The exception to handle.

        Returns:
            JSONResponse: A JSON response containing the exception details.

        Raises:
            NotImplementedError: If FastAPI is not available.
        """
        if not HTTP_AVAILABLE:
            raise NotImplementedError
        return JSONResponse(
            status_code=exception.http_status or HTTPStatus.INTERNAL_SERVER_ERROR,
            content=exception.to_dict(),
        )

    @staticmethod
    def handle_grpc_exception(exception: BaseError) -> tuple[int, str]:
        """Handles a gRPC exception and returns a tuple of status code and message.

        Args:
            exception (BaseError): The exception to handle.

        Returns:
            tuple[int, str]: A tuple containing the gRPC status code and error message.

        Raises:
            NotImplementedError: If gRPC is not available.
        """
        if not GRPC_AVAILABLE:
            raise NotImplementedError
        return exception.grpc_status or StatusCode.UNKNOWN.value[0], exception.get_message()

    @staticmethod
    def get_fastapi_exception_responses(exceptions: list[type[BaseError]]) -> dict[int, dict[str, Any]]:
        """Generates OpenAPI response documentation for the given errors.

        This method creates OpenAPI-compatible response schemas for FastAPI errors,
        including validation errors and custom errors.

        Args:
            exceptions (list[type[BaseError]]): A list of exception types to generate responses for.

        Returns:
            dict[int, dict[str, Any]]: A dictionary mapping HTTP status codes to their corresponding response schemas.
        """
        responses: dict[int, dict[str, Any]] = {}

        # Add validation error response by default
        validation_error_response = ValidationErrorResponseDTO()
        if validation_error_response.status_code is not None:
            responses[validation_error_response.status_code] = validation_error_response.model

        exception_schemas = {
            "InvalidPhoneNumberError": {
                "phone_number": {"type": "string", "example": "1234567890", "description": "The invalid phone number"},
            },
            "InvalidLandlineNumberError": {
                "landline_number": {
                    "type": "string",
                    "example": "02112345678",
                    "description": "The invalid landline number",
                },
            },
            "NotFoundError": {
                "resource_type": {
                    "type": "string",
                    "example": "user",
                    "description": "Type of resource that was not found",
                },
            },
            "AlreadyExistsError": {
                "resource_type": {
                    "type": "string",
                    "example": "user",
                    "description": "Type of resource that was not found",
                },
            },
            "InvalidNationalCodeError": {
                "national_code": {
                    "type": "string",
                    "example": "1234567890",
                    "description": "The invalid national code",
                },
            },
            "InvalidArgumentError": {
                "argument": {
                    "type": "string",
                    "example": "mobile_number",
                    "description": "Argument that was invalid",
                },
            },
        }

        for exc in exceptions:
            # Use exception class directly (error details are now class attributes)
            if exc.http_status:
                additional_properties = exception_schemas.get(exc.__name__)
                response = FastAPIErrorResponseDTO(exc, additional_properties)
                if response.status_code is not None:
                    responses[response.status_code] = response.model

        return responses
