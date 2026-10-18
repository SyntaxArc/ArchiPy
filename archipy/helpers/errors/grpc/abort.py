"""Abort gRPC calls with the status and message of a ``BaseError``."""

from __future__ import annotations

import inspect
import json
from typing import TYPE_CHECKING, NoReturn, overload

import grpc

from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping

    from grpc.aio import ServicerContext as AsyncServicerContext

    from archipy.models.errors import BaseError

_MAX_TRAILING_METADATA_BYTES = 4096
_STATUS_CODES = {code.value[0]: code for code in grpc.StatusCode}


def grpc_status_code(status: int) -> grpc.StatusCode:
    """Convert an integer status (``BaseError.grpc_status``) to the gRPC ``StatusCode`` member.

    Args:
        status: The integer gRPC status.

    Returns:
        grpc.StatusCode: The matching member, INTERNAL for an unknown integer.
    """
    return _STATUS_CODES.get(status, grpc.StatusCode.INTERNAL)


def _encode_additional_data(additional_data: Mapping[str, object]) -> str:
    """Serialize ``additional_data`` for gRPC trailing metadata.

    Values that are not JSON native (UUID, datetime, Decimal, ...) fall back to ``str``. Payloads larger than
    ``_MAX_TRAILING_METADATA_BYTES`` are replaced by a marker so the abort never fails on the metadata size limit.

    Args:
        additional_data: The error context data.

    Returns:
        str: JSON text that is safe to send as trailing metadata.
    """
    encoded = json.dumps(additional_data, default=str)
    if len(encoded.encode("utf-8")) > _MAX_TRAILING_METADATA_BYTES:
        return json.dumps({"truncated": True})
    return encoded


def _raise_invalid_context(reason: str) -> NoReturn:
    raise InvalidArgumentError(argument_name="grpc_context", additional_data={"reason": reason})


def _set_error_metadata(error: BaseError, context: grpc.ServicerContext | AsyncServicerContext) -> None:
    if error.additional_data and hasattr(context, "set_trailing_metadata"):
        context.set_trailing_metadata((("additional_data", _encode_additional_data(error.additional_data)),))


async def _abort_async(
    error: BaseError,
    context: grpc.ServicerContext | AsyncServicerContext,
    abort: Callable[[grpc.StatusCode, str], Awaitable[object]],
) -> None:
    _set_error_metadata(error, context)
    await abort(grpc_status_code(error.grpc_status), error.get_message())


@overload
def abort_grpc(error: BaseError, context: AsyncServicerContext) -> Awaitable[None]: ...


@overload
def abort_grpc(error: BaseError, context: grpc.ServicerContext) -> None: ...


def abort_grpc(
    error: BaseError,
    context: grpc.ServicerContext | AsyncServicerContext | None,
) -> Awaitable[None] | None:
    """Abort a gRPC call with the status code and message of ``error``.

    The context kind is detected automatically. On a sync context the call is aborted immediately. On an
    ``grpc.aio`` context the abort is returned as an awaitable, so write ``await abort_grpc(error, context)``.
    When ``error`` carries ``additional_data`` it is sent as the ``additional_data`` trailing metadata entry.

    Args:
        error: The error to report.
        context: The sync or async gRPC servicer context to abort.

    Returns:
        Awaitable[None] | None: An awaitable for async contexts, None for sync contexts.

    Raises:
        InvalidArgumentError: If the context is None or cannot be aborted.
    """
    if context is None:
        _raise_invalid_context("context_is_none")
    abort = getattr(context, "abort", None)
    if abort is None:
        _raise_invalid_context("missing_abort_method")
    if not callable(abort):
        _raise_invalid_context("abort_not_callable")

    if inspect.iscoroutinefunction(abort):
        return _abort_async(error, context, abort)

    _set_error_metadata(error, context)
    abort(grpc_status_code(error.grpc_status), error.get_message())
    return None


__all__ = ["abort_grpc", "grpc_status_code"]
