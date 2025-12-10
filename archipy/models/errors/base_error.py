import json
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from http import HTTPStatus

    import grpc
    from grpc import ServicerContext
    from grpc.aio import ServicerContext as AsyncServicerContext
else:
    HTTPStatus = None
    grpc = None
    ServicerContext = object
    AsyncServicerContext = object

try:
    import grpc
    from grpc import aio as grpc_aio

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc_aio: Any | None = None

try:
    from http import HTTPStatus

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False


if GRPC_AVAILABLE:
    from grpc import ServicerContext
    from grpc.aio import ServicerContext as AsyncServicerContext
elif not TYPE_CHECKING:
    # Fallback types for when grpc is not available (only at runtime, not in TYPE_CHECKING)
    ServicerContext = object
    AsyncServicerContext = object

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
    http_status: ClassVar[int] = (
        HTTPStatus.INTERNAL_SERVER_ERROR.value
        if HTTP_AVAILABLE and HTTPStatus is not None and HTTPStatus is not None
        else 500
    )
    grpc_status: ClassVar[int] = (
        grpc.StatusCode.INTERNAL.value[0]
        if GRPC_AVAILABLE and grpc is not None and isinstance(grpc.StatusCode.INTERNAL.value, tuple)
        else (grpc.StatusCode.INTERNAL.value if GRPC_AVAILABLE and grpc is not None else 13)
    )

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
            except (ImportError, AssertionError):
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
        return f"[{self.code}] {self.get_message()}"

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

    @staticmethod
    def _convert_int_to_grpc_status(status_int: int) -> grpc.StatusCode:
        """Convert integer status code to gRPC StatusCode enum.

        Args:
            status_int: Integer status code

        Returns:
            grpc.StatusCode: Corresponding StatusCode enum member

        Raises:
            ValueError: If gRPC is not available.
        """
        if not GRPC_AVAILABLE or grpc is None:
            raise ValueError("gRPC is not available")

        status_map = {
            0: grpc.StatusCode.OK,
            1: grpc.StatusCode.CANCELLED,
            2: grpc.StatusCode.UNKNOWN,
            3: grpc.StatusCode.INVALID_ARGUMENT,
            4: grpc.StatusCode.DEADLINE_EXCEEDED,
            5: grpc.StatusCode.NOT_FOUND,
            6: grpc.StatusCode.ALREADY_EXISTS,
            7: grpc.StatusCode.PERMISSION_DENIED,
            8: grpc.StatusCode.RESOURCE_EXHAUSTED,
            9: grpc.StatusCode.FAILED_PRECONDITION,
            10: grpc.StatusCode.ABORTED,
            11: grpc.StatusCode.OUT_OF_RANGE,
            12: grpc.StatusCode.UNIMPLEMENTED,
            13: grpc.StatusCode.INTERNAL,
            14: grpc.StatusCode.UNAVAILABLE,
            15: grpc.StatusCode.DATA_LOSS,
            16: grpc.StatusCode.UNAUTHENTICATED,
        }

        return status_map.get(status_int, grpc.StatusCode.INTERNAL)

    async def abort_grpc_async(self, context: AsyncServicerContext) -> None:
        """Aborts an async gRPC call with the appropriate status code and message.

        Args:
            context: The gRPC ServicerContext to abort.

        Raises:
            ValueError: If context is None or doesn't have abort method.
        """
        if context is None:
            raise ValueError("gRPC context cannot be None")

        if not GRPC_AVAILABLE or not hasattr(context, "abort"):
            raise ValueError("Invalid gRPC context: missing abort method")

        status_code: grpc.StatusCode = self._convert_int_to_grpc_status(self.grpc_status)
        message = self.get_message()

        if self.additional_data and hasattr(context, "set_trailing_metadata"):
            context.set_trailing_metadata((("additional_data", json.dumps(self.additional_data)),))

        if hasattr(context, "abort") and callable(context.abort):
            await context.abort(status_code, message)
        else:
            raise ValueError("gRPC context abort method not available or not callable")

    def abort_grpc_sync(self, context: ServicerContext) -> None:
        """Aborts a sync gRPC call with the appropriate status code and message.

        Args:
            context: The gRPC ServicerContext to abort.

        Raises:
            ValueError: If context is None or doesn't have abort method.
        """
        if context is None:
            raise ValueError("gRPC context cannot be None")

        if not GRPC_AVAILABLE or not hasattr(context, "abort"):
            raise ValueError("Invalid gRPC context: missing abort method")

        status_code: grpc.StatusCode = self._convert_int_to_grpc_status(self.grpc_status)
        message = self.get_message()

        if self.additional_data and hasattr(context, "set_trailing_metadata"):
            context.set_trailing_metadata((("additional_data", json.dumps(self.additional_data)),))

        if hasattr(context, "abort") and callable(context.abort):
            context.abort(status_code, message)
        else:
            raise ValueError("gRPC context abort method not available or not callable")

    @classmethod
    async def abort_with_error_async(
        cls,
        context: AsyncServicerContext,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Creates an error instance and immediately aborts the async gRPC context.

        Args:
            context: The async gRPC ServicerContext to abort.
            lang: Language code for the error message.
            additional_data: Additional context data for the error.

        Raises:
            ValueError: If context is None or invalid.
        """
        instance = cls(lang=lang, additional_data=additional_data)
        await instance.abort_grpc_async(context)

    @classmethod
    def abort_with_error_sync(
        cls,
        context: ServicerContext,
        lang: LanguageType | None = None,
        additional_data: dict[str, Any] | None = None,
    ) -> None:
        """Creates an error instance and immediately aborts the sync gRPC context.

        Args:
            context: The sync gRPC ServicerContext to abort.
            lang: Language code for the error message.
            additional_data: Additional context data for the error.

        Raises:
            ValueError: If context is None or invalid.
        """
        instance = cls(lang=lang, additional_data=additional_data)
        instance.abort_grpc_sync(context)
