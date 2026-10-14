"""FastAPI exception handlers that turn errors into JSON responses."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from archipy.helpers.errors.capture import capture_exception
from archipy.helpers.errors.validation import format_validation_errors
from archipy.models.errors import BaseError, UnknownError

if TYPE_CHECKING:
    from fastapi import FastAPI, Request, Response


def create_error_response(exception: BaseError, *, capture: bool = True) -> JSONResponse:
    """Creates a standardized error response.

    Args:
        exception (BaseError): The exception to be converted into a response.
        capture (bool): Whether to log and record ``exception`` first. Pass False when the underlying
            cause was already captured. Defaults to True.

    Returns:
        JSONResponse: A JSON response containing the exception details.
    """
    if capture:
        capture_exception(exception)
    status_code = exception.http_status or HTTPStatus.INTERNAL_SERVER_ERROR.value
    return JSONResponse(status_code=status_code, content=exception.to_dict())


def validation_response(exception: ValidationError | RequestValidationError) -> JSONResponse:
    """Creates the 422 response for a validation failure.

    Args:
        exception: The pydantic or FastAPI request validation error.

    Returns:
        JSONResponse: A 422 response listing the invalid fields.
    """
    capture_exception(exception)
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "detail": format_validation_errors(exception, include_type=isinstance(exception, RequestValidationError)),
        },
    )


async def handle_fastapi_exception(_request: Request, exception: BaseError) -> JSONResponse:
    """Handles a ``BaseError`` and returns its JSON response.

    Args:
        _request (Request): The incoming request.
        exception (BaseError): The exception to handle.

    Returns:
        JSONResponse: A JSON response containing the exception details.
    """
    return create_error_response(exception)


async def handle_unexpected_exception(_request: Request, exception: Exception) -> JSONResponse:
    """Handles any other exception; the client only gets a generic error.

    Args:
        _request (Request): The incoming request.
        exception (Exception): The exception to handle.

    Returns:
        JSONResponse: A JSON response holding the generic error.
    """
    # Record the real failure (with its traceback); the client only gets the generic error.
    capture_exception(exception)
    return create_error_response(UnknownError(), capture=False)


def setup_exception_handlers(app: FastAPI) -> None:
    """Configures exception handlers for the FastAPI application.

    Args:
        app (FastAPI): The FastAPI application instance.
    """

    # The wrappers match the (Request, Exception) -> Response signature that FastAPI expects.
    async def validation_wrapper(request: Request, exception: Exception) -> Response:
        if isinstance(exception, ValidationError | RequestValidationError):
            return validation_response(exception)
        return await handle_unexpected_exception(request, exception)

    async def base_error_wrapper(request: Request, exception: Exception) -> Response:
        if isinstance(exception, BaseError):
            return await handle_fastapi_exception(request, exception)
        return await handle_unexpected_exception(request, exception)

    app.add_exception_handler(RequestValidationError, validation_wrapper)
    app.add_exception_handler(ValidationError, validation_wrapper)
    app.add_exception_handler(BaseError, base_error_wrapper)
    app.add_exception_handler(Exception, handle_unexpected_exception)
