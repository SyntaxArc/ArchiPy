"""gRPC server interceptor for exception mapping."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Self

import grpc

from archipy.helpers.errors.capture import capture_exception
from archipy.helpers.errors.grpc.abort import abort_grpc
from archipy.helpers.errors.mapping import resolve_error
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
    iterate_stream_result,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from archipy.models.errors import BaseError


def _is_sync_abort(error: Exception, context: grpc.ServicerContext) -> bool:
    """Tell whether ``error`` is the bare exception raised by ``context.abort()``.

    ``ServicerContext.abort`` records the status on the context and then raises ``Exception()`` with no arguments.
    Mapping that exception again would overwrite the deliberate status (for example RESOURCE_EXHAUSTED) with INTERNAL.

    Args:
        error: The exception caught around the handler.
        context: The sync gRPC context of the call.

    Returns:
        bool: True when the context was aborted and ``error`` is the abort signal.
    """
    code = getattr(context, "code", None)
    return type(error) is Exception and not error.args and callable(code) and code() not in {None, grpc.StatusCode.OK}


class GrpcExceptionInterceptor:
    """A gRPC server interceptor for centralized exception handling.

    Catches the exceptions thrown by gRPC service methods and aborts the call with the matching gRPC status, so
    service methods need no try/except blocks. ``BaseError`` keeps its own status, a pydantic ``ValidationError`` is
    reported as INVALID_ARGUMENT (the counterpart of HTTP 422) and anything else as a generic INTERNAL error.

    ``GrpcExceptionInterceptor()`` creates the sync interceptor and ``GrpcExceptionInterceptor(aio=True)`` the one for
    ``grpc.aio`` servers.
    """

    def __new__(cls, *, aio: bool = False, **_kwargs: object) -> Self:
        """Pick the sync or the aio variant.

        Args:
            aio: Create the interceptor for a ``grpc.aio`` server.
            **_kwargs: Forwarded to ``__init__``.

        Returns:
            Self: The interceptor instance.
        """
        if cls is GrpcExceptionInterceptor:
            variant = _AioGrpcExceptionInterceptor if aio else _SyncGrpcExceptionInterceptor
            return super().__new__(variant)  # ty: ignore[invalid-return-type]
        return super().__new__(cls)

    def __init__(self, *, aio: bool = False, validation_errors_as_internal: bool = False) -> None:  # noqa: ARG002
        """Initialize the interceptor.

        Args:
            aio: Create the interceptor for a ``grpc.aio`` server.
            validation_errors_as_internal: When True, a pydantic ``ValidationError`` is reported as INTERNAL instead
                of INVALID_ARGUMENT (the behavior before 5.15). Defaults to False.
        """
        self._validation_errors_as_internal = validation_errors_as_internal

    def _error_for(self, error: Exception) -> BaseError:
        """Capture ``error`` and return the ``BaseError`` to report."""
        capture_exception(error)
        return resolve_error(error, validation_errors_as_internal=self._validation_errors_as_internal)


class _SyncGrpcExceptionInterceptor(GrpcExceptionInterceptor, BaseGrpcServerInterceptor):
    """The sync variant of ``GrpcExceptionInterceptor``."""

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,  # noqa: ARG002 - part of the base interceptor signature
    ) -> object:
        """Intercepts a sync gRPC server call and handles exceptions.

        Args:
            method: The sync gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the sync gRPC call.
            method_name_model: The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Note:
            This method will not return anything if an exception is handled,
            as the exception handling will abort the gRPC context.
        """
        try:
            result = method(request, context)
        except Exception as error:
            if _is_sync_abort(error, context):
                raise
            abort_grpc(self._error_for(error), context)
            raise  # This will never be reached, but satisfies MyPy
        if isinstance(result, Iterator):
            # Response-streaming handler: errors surface while iterating, so keep guarding.
            return self._guard_stream(result, context)
        return result

    def _guard_stream(self, stream: Iterator[object], context: grpc.ServicerContext) -> Iterator[object]:
        """Relay a sync response stream, mapping exceptions raised while iterating.

        Args:
            stream: The response iterator returned by the handler.
            context: The context of the sync gRPC call.

        Yields:
            object: Each response message.
        """
        try:
            yield from stream
        except Exception as error:
            if _is_sync_abort(error, context):
                raise
            abort_grpc(self._error_for(error), context)
            raise  # This will never be reached, but satisfies MyPy


class _AioGrpcExceptionInterceptor(GrpcExceptionInterceptor, BaseAsyncGrpcServerInterceptor):
    """The ``grpc.aio`` variant of ``GrpcExceptionInterceptor``."""

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,  # noqa: ARG002 - part of the base interceptor signature
    ) -> object:
        """Intercepts an async gRPC server call and handles exceptions.

        Args:
            method: The async gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the async gRPC call.
            method_name_model: The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Note:
            This method will not return anything if an exception is handled,
            as the exception handling will abort the gRPC context.
        """
        try:
            return await method(request, context)
        except grpc.aio.AbortError:
            # The handler or an inner interceptor already aborted the call with a deliberate status.
            raise
        except Exception as error:
            await abort_grpc(self._error_for(error), context)
            raise  # This will never be reached, but satisfies MyPy

    async def intercept_stream(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,  # noqa: ARG002 - part of the base interceptor signature
    ) -> AsyncIterator[object]:
        """Intercepts an async streaming gRPC call and handles exceptions raised while streaming.

        Args:
            method: The async streaming gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the async gRPC call.
            method_name_model: The parsed method name containing package, service, and method components.

        Yields:
            object: Each response message produced by the method.
        """
        try:
            async for item in iterate_stream_result(method(request, context)):
                yield item
        except grpc.aio.AbortError:
            # The handler or an inner interceptor already aborted the call with a deliberate status.
            raise
        except Exception as error:
            await abort_grpc(self._error_for(error), context)
            raise  # This will never be reached, but satisfies MyPy
