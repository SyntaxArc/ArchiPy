"""OpenAPI documentation for the error responses of FastAPI routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from archipy.helpers.errors.fastapi.response_dtos import FastAPIErrorResponseDTO, ValidationErrorResponseDTO

if TYPE_CHECKING:
    from archipy.models.errors import BaseError


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
