"""FastAPI error handling (requires the ``fastapi`` extra)."""

from archipy.helpers.errors.fastapi.handlers import (
    create_error_response,
    handle_fastapi_exception,
    handle_unexpected_exception,
    setup_exception_handlers,
)
from archipy.helpers.errors.fastapi.openapi import get_fastapi_exception_responses

__all__ = [
    "create_error_response",
    "get_fastapi_exception_responses",
    "handle_fastapi_exception",
    "handle_unexpected_exception",
    "setup_exception_handlers",
]
