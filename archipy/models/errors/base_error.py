"""Base error types for ArchiPy."""

from typing import Any, ClassVar

from archipy.models.types.language_type import LanguageType


class BaseError(Exception):
    """Base exception class for all custom errors.

    This class provides a standardized way to handle errors with support for:
    - Localization of error messages
    - Additional context data
    - Integration with HTTP and gRPC status codes
    - Template string formatting for dynamic message formatting (using {variable} placeholders)
    - Text normalization and Persian number conversion

    Subclasses should define the following class attributes:
        code (ClassVar[str]): Error code identifier
        message_en (ClassVar[str]): English error message (can use {variable} placeholders)
        message_fa (ClassVar[str]): Persian error message (can use {variable} placeholders)
        http_status (ClassVar[int]): HTTP status code
        grpc_status (ClassVar[int]): gRPC status code

    """

    # Default error details - subclasses should override these
    code: ClassVar[str] = "UNKNOWN_ERROR"
    message_en: ClassVar[str] = "An unknown error occurred"
    message_fa: ClassVar[str] = "خطای ناشناخته‌ای رخ داده است."
    http_status: ClassVar[int] = 500
    grpc_status: ClassVar[int] = 13  # grpc.StatusCode.INTERNAL

    def __init__(
        self,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
        *args: object,
    ) -> None:
        """Initialize the error with message and optional context.

        Args:
            lang: Language code for the error message (defaults to Persian).
            additional_data: Additional context data for the error.
            *args: Additional arguments for the base Exception class.
        """
        if lang is None:
            try:
                from archipy.configs.base_config import BaseConfig

                self.lang = BaseConfig.global_config().LANGUAGE
            except ImportError, AssertionError:
                self.lang = LanguageType.FA
        else:
            self.lang = lang

        self.additional_data = additional_data or {}

        # Initialize base Exception with the message
        super().__init__(self.get_message(), *args)

    def get_message(self) -> str:
        """Gets the localized error message based on the language setting.

        Returns:
            str: The error message in the current language.
        """
        return self.message_fa if self.lang == LanguageType.FA else self.message_en

    def to_dict(self) -> dict:
        """Converts the exception to a dictionary format for API responses.

        Returns:
            dict: A dictionary containing error details and additional data.
        """
        # Get the processed message (not the template)
        processed_message = self.get_message()

        response = {
            "error": self.code,
            "detail": {
                "code": self.code,
                "message": processed_message,
                "http_status": self.http_status,
                "grpc_status": self.grpc_status,
            },
        }

        # Add additional data if present
        if self.additional_data:
            detail = response["detail"]
            if isinstance(detail, dict):
                detail.update(self.additional_data)

        return response

    def __str__(self) -> str:
        """String representation of the exception.

        Returns:
            str: A formatted string containing the error code and message.
        """
        return (
            f"{self.__class__.__name__}("
            f"code='{self.code}', "
            f"message='{self.get_message()}', "
            f"http_status={self.http_status}, "
            f"grpc_status={self.grpc_status}, "
            f"additional_data={self.additional_data}"
            f")"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the exception.

        Returns:
            str: A detailed string representation including all error details.
        """
        return (
            f"{self.__class__.__name__}("
            f"code='{self.code}', "
            f"message='{self.get_message()}', "
            f"http_status={self.http_status}, "
            f"grpc_status={self.grpc_status}, "
            f"additional_data={self.additional_data}"
            f")"
        )

    @property
    def message(self) -> str:
        """Gets the current language message.

        Returns:
            str: The error message in the current language.
        """
        return self.get_message()
