"""Shared formatting and error mapping for validation failures."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol

from pydantic import ValidationError

from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

    from pydantic_core import ErrorDetails


class SupportsErrors(Protocol):
    """A validation failure that lists its problems (pydantic and FastAPI request validation errors)."""

    def errors(self) -> Iterable[ErrorDetails]:
        """Return the individual validation problems."""
        ...


def format_validation_errors(
    validation_error: SupportsErrors,
    *,
    include_type: bool = False,
    include_input: bool = False,
) -> list[dict[str, str]]:
    """Formats validation errors into a structured format.

    Args:
        validation_error: The pydantic ``ValidationError`` or FastAPI ``RequestValidationError`` to format.
        include_type (bool): Whether to include the error type in the output. Defaults to False.
        include_input (bool): Whether to echo the rejected input value (as ``value``). Defaults to False,
            because the input may be a password, token or other secret and must not reach the client or logs.

    Returns:
        list[dict[str, str]]: A list of formatted validation error details.
    """
    formatted_errors = []
    for error in validation_error.errors():
        error_dict = {
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
        }
        if include_input:
            error_dict["value"] = str(error.get("input", ""))
        if include_type:
            error_dict["type"] = error["type"]
        formatted_errors.append(error_dict)

    return formatted_errors


def invalid_argument_from_validation(validation_error: ValidationError) -> InvalidArgumentError:
    """Build the INVALID_ARGUMENT error that describes a request validation failure.

    Args:
        validation_error: The Pydantic validation error.

    Returns:
        InvalidArgumentError: The error carrying the (input-free) validation details.
    """
    validation_details = format_validation_errors(validation_error, include_type=True)
    return InvalidArgumentError(
        argument_name="request_validation",
        additional_data={"validation_errors": validation_details, "error_count": len(validation_error.errors())},
    )


@contextmanager
def request_validation() -> Generator[None]:
    """Report a Pydantic ``ValidationError`` raised inside the block as INVALID_ARGUMENT.

    The gRPC exception interceptor already reports every ``ValidationError`` as INVALID_ARGUMENT by default. Use this
    context manager to mark the code that parses the *client's request* explicitly, which keeps that mapping when the
    interceptor is created with ``validation_errors_as_internal=True``.

    Example:
        ```python
        def Create(self, request, context):
            with request_validation():
                dto = CreateUserDTO(name=request.name, email=request.email)
        ```

    Raises:
        InvalidArgumentError: When the block raises ``pydantic.ValidationError``.
    """
    try:
        yield
    except ValidationError as validation_error:
        raise invalid_argument_from_validation(validation_error) from validation_error
