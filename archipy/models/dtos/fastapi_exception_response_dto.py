from http import HTTPStatus

from archipy.models.errors.base_error import BaseError


class FastAPIErrorResponseDTO:
    """Standardized error response model for OpenAPI documentation."""

    def __init__(self, exception: type[BaseError], additional_properties: dict | None = None) -> None:
        """Initialize the error response model.

        Args:
            exception: The exception class (not instance) with error details as class attributes
            additional_properties: Additional properties to include in the response
        """
        self.status_code = exception.http_status

        # Base properties that all errors have
        detail_properties = {
            "code": {"type": "string", "example": exception.code, "description": "Error code identifier"},
            "message_en": {
                "type": "string",
                "example": exception.message_en,
                "description": "Error message in English",
            },
            "message_fa": {
                "type": "string",
                "example": exception.message_fa,
                "description": "Error message in Persian",
            },
            "http_status": {"type": "integer", "example": exception.http_status, "description": "HTTP status code"},
        }

        # Add additional properties if provided
        if additional_properties:
            detail_properties.update(additional_properties)

        self.model = {
            "description": exception.message_en,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "example": exception.code,
                                "description": "Error code identifier",
                            },
                            "detail": {
                                "type": "object",
                                "properties": detail_properties,
                                "required": ["code", "message_en", "message_fa", "http_status"],
                                "additionalProperties": False,
                                "description": "Detailed error information",
                            },
                        },
                    },
                },
            },
        }


class ValidationErrorResponseDTO(FastAPIErrorResponseDTO):
    """Specific response model for validation errors."""

    def __init__(self) -> None:
        """Initialize the validation error response model."""
        self.status_code = HTTPStatus.UNPROCESSABLE_ENTITY
        self.model = {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "string",
                                "example": "VALIDATION_ERROR",
                                "description": "Error code identifier",
                            },
                            "detail": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {
                                            "type": "string",
                                            "example": "email",
                                            "description": "Field name that failed validation",
                                        },
                                        "message": {
                                            "type": "string",
                                            "example": "Invalid email format",
                                            "description": "Validation error message",
                                        },
                                        "value": {
                                            "type": "string",
                                            "example": "invalid@email",
                                            "description": "Invalid value that caused the error",
                                        },
                                    },
                                },
                                "example": [
                                    {"field": "email", "message": "Invalid email format", "value": "invalid@email"},
                                    {
                                        "field": "password",
                                        "message": "Password must be at least 8 characters",
                                        "value": "123",
                                    },
                                ],
                            },
                        },
                    },
                },
            },
        }
