"""Error handling helpers shared by the FastAPI and gRPC transports.

The transport specific parts live in ``archipy.helpers.errors.fastapi`` and ``archipy.helpers.errors.grpc``; they
need the matching optional extra and are imported on demand.
"""

from archipy.helpers.errors.capture import capture_exception
from archipy.helpers.errors.mapping import resolve_error
from archipy.helpers.errors.validation import (
    format_validation_errors,
    invalid_argument_from_validation,
    request_validation,
)

__all__ = [
    "capture_exception",
    "format_validation_errors",
    "invalid_argument_from_validation",
    "request_validation",
    "resolve_error",
]
