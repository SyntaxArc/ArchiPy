"""Deprecated error handling helpers; use ``archipy.helpers.errors`` instead."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from archipy.helpers._deprecation import warn_deprecated_name
from archipy.helpers.errors.capture import capture_exception

if TYPE_CHECKING:
    from archipy.models.errors import BaseError


class ErrorUtils:
    """Deprecated wrappers kept for ``BaseUtils`` callers; each method names its replacement in the warning."""

    @staticmethod
    def capture_exception(exception: BaseException) -> None:
        """Deprecated: use ``archipy.helpers.errors.capture_exception``.

        Args:
            exception (BaseException): The exception to capture and report.
        """
        warn_deprecated_name("BaseUtils.capture_exception", "archipy.helpers.errors.capture_exception")
        capture_exception(exception)

    @staticmethod
    async def async_handle_fastapi_exception(_request: Any, exception: BaseError) -> Any:  # noqa: ANN401
        """Deprecated: use ``archipy.helpers.errors.fastapi.handle_fastapi_exception``.

        Args:
            _request (Request): The incoming FastAPI request.
            exception (BaseError): The exception to handle.

        Returns:
            JSONResponse: A JSON response containing the exception details.
        """
        from archipy.helpers.errors.fastapi import handle_fastapi_exception

        warn_deprecated_name(
            "BaseUtils.async_handle_fastapi_exception",
            "archipy.helpers.errors.fastapi.handle_fastapi_exception",
        )
        return await handle_fastapi_exception(_request, exception)

    @staticmethod
    def get_fastapi_exception_responses(exceptions: list[type[BaseError]]) -> dict[int, dict[str, Any]]:
        """Deprecated: use ``archipy.helpers.errors.fastapi.get_fastapi_exception_responses``.

        Args:
            exceptions (list[type[BaseError]]): A list of exception types to generate responses for.

        Returns:
            dict[int, dict[str, Any]]: A dictionary mapping HTTP status codes to their corresponding response schemas.
        """
        from archipy.helpers.errors.fastapi import get_fastapi_exception_responses

        warn_deprecated_name(
            "BaseUtils.get_fastapi_exception_responses",
            "archipy.helpers.errors.fastapi.get_fastapi_exception_responses",
        )
        return get_fastapi_exception_responses(exceptions)
