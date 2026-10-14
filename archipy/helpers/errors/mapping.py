"""Transport-agnostic mapping from any exception to the ``BaseError`` a client should see."""

from __future__ import annotations

from pydantic import ValidationError

from archipy.helpers.errors.validation import invalid_argument_from_validation
from archipy.models.errors import BaseError, InternalError


def resolve_error(error: Exception, *, validation_errors_as_internal: bool = False) -> BaseError:
    """Return the ``BaseError`` to send to the client for ``error``.

    A ``BaseError`` passes through. A pydantic ``ValidationError`` becomes INVALID_ARGUMENT (the gRPC counterpart of
    HTTP 422), or INTERNAL when ``validation_errors_as_internal`` is set. Anything else becomes a generic INTERNAL
    error, so internals never reach the client.

    Args:
        error: The exception raised by the handler.
        validation_errors_as_internal: Report a ``ValidationError`` as INTERNAL instead of INVALID_ARGUMENT.

    Returns:
        BaseError: The error to report.
    """
    if isinstance(error, BaseError):
        return error
    if isinstance(error, ValidationError) and not validation_errors_as_internal:
        return invalid_argument_from_validation(error)
    return InternalError()
