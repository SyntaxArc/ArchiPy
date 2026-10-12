"""gRPC server interceptor for exception mapping."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import grpc
from pydantic import ValidationError

from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
    iterate_stream_result,
)
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import InternalError, InvalidArgumentError
from archipy.models.errors.base_error import BaseError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Generator


def _invalid_argument_from_validation(validation_error: ValidationError) -> InvalidArgumentError:
    """Build the INVALID_ARGUMENT error that describes a request validation failure.

    Args:
        validation_error: The Pydantic validation error.

    Returns:
        InvalidArgumentError: The error carrying the (input-free) validation details.
    """
    validation_details = BaseUtils.format_validation_errors(validation_error, include_type=True)
    return InvalidArgumentError(
        argument_name="request_validation",
        additional_data={"validation_errors": validation_details, "error_count": len(validation_error.errors())},
    )


@contextmanager
def request_validation() -> Generator[None]:
    """Report a Pydantic ``ValidationError`` raised inside the block as INVALID_ARGUMENT.

    By default the exception interceptors treat a ``ValidationError`` escaping a handler as a server fault
    (INTERNAL), because it usually comes from building DTOs out of database rows or upstream responses. Wrap the
    code that parses the *client's request* in this context manager to blame the client instead.

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
        raise _invalid_argument_from_validation(validation_error) from validation_error


def _is_sync_abort(error: Exception, context: grpc.ServicerContext) -> bool:
    """Tell whether ``error`` is the bare exception raised by ``context.abort()``.

    ``ServicerContext.abort`` records the status on the context and then raises a plain ``Exception``. Mapping that
    exception again would overwrite the deliberate status (for example RESOURCE_EXHAUSTED) with INTERNAL.

    Args:
        error: The exception caught around the handler.
        context: The sync gRPC context of the call.

    Returns:
        bool: True when the context was aborted and ``error`` is the abort signal.
    """
    code = getattr(context, "code", None)
    return type(error) is Exception and callable(code) and code() not in {None, grpc.StatusCode.OK}


class GrpcServerExceptionInterceptor(BaseGrpcServerInterceptor):
    """A sync gRPC server interceptor for centralized exception handling.

    This interceptor catches all exceptions thrown by gRPC service methods and
    converts them to appropriate gRPC errors, eliminating the need for repetitive
    try-catch blocks in each service method.

    A Pydantic ``ValidationError`` escaping a handler is reported as INTERNAL, since it normally signals a server
    bug. Use ``request_validation()`` around request parsing to report INVALID_ARGUMENT, or pass
    ``validation_errors_as_invalid_argument=True`` to restore the previous mapping for every ``ValidationError``.
    """

    def __init__(self, validation_errors_as_invalid_argument: bool = False) -> None:
        """Initialize the interceptor.

        Args:
            validation_errors_as_invalid_argument: When True, every Pydantic ``ValidationError`` raised by a handler
                is reported as INVALID_ARGUMENT (the pre-5.10 behavior). Defaults to False (INTERNAL).
        """
        self._validation_errors_as_invalid_argument = validation_errors_as_invalid_argument

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
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
            # Execute the gRPC method
            result = method(request, context)

        except Exception as error:
            if _is_sync_abort(error, context):
                raise
            self._abort_for_error(error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy
        else:
            if isinstance(result, Iterator):
                # Response-streaming handler: errors surface while iterating, so keep guarding.
                return self._guard_stream(result, context, method_name_model)
            return result

    def _guard_stream(
        self,
        stream: Iterator[object],
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> Iterator[object]:
        """Relay a sync response stream, mapping exceptions raised while iterating.

        Args:
            stream: The response iterator returned by the handler.
            context: The context of the sync gRPC call.
            method_name_model: The parsed method name.

        Yields:
            object: Each response message.
        """
        try:
            yield from stream
        except Exception as error:
            if _is_sync_abort(error, context):
                raise
            self._abort_for_error(error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy

    def _abort_for_error(self, error: Exception, context: grpc.ServicerContext, method_name_model: MethodName) -> None:
        """Capture ``error`` and abort the context with the matching gRPC status.

        Args:
            error: The exception raised by the handler.
            context: The gRPC context to abort.
            method_name_model: The method name information for better error tracking.
        """
        BaseUtils.capture_exception(error)
        if isinstance(error, ValidationError) and self._validation_errors_as_invalid_argument:
            self._handle_validation_error(error, context)
        elif isinstance(error, BaseError):
            error.abort_grpc_sync(context)
        else:
            self._handle_unexpected_error(error, context, method_name_model)

    @staticmethod
    def _handle_validation_error(validation_error: ValidationError, context: grpc.ServicerContext) -> None:
        """Handle Pydantic validation errors.

        Args:
            validation_error: The validation error to handle.
            context: The gRPC context to abort.
        """
        _invalid_argument_from_validation(validation_error).abort_grpc_sync(context)

    @staticmethod
    def _handle_unexpected_error(
        error: Exception,  # noqa: ARG004 - kept for subclass overrides
        context: grpc.ServicerContext,
        method_name_model: MethodName,  # noqa: ARG004 - kept for subclass overrides
    ) -> None:
        """Handle unexpected errors by converting them to internal errors.

        Args:
            error: The unexpected error to handle.
            context: The gRPC context to abort.
            method_name_model: The method name information (kept for subclass overrides).
        """
        # The cause was already logged by ``capture_exception``; never send internals to the client.
        InternalError().abort_grpc_sync(context)


class AsyncGrpcServerExceptionInterceptor(BaseAsyncGrpcServerInterceptor):
    """An async gRPC server interceptor for centralized exception handling.

    This interceptor catches all exceptions thrown by gRPC service methods and
    converts them to appropriate gRPC errors, eliminating the need for repetitive
    try-catch blocks in each service method.

    A Pydantic ``ValidationError`` escaping a handler is reported as INTERNAL, since it normally signals a server
    bug. Use ``request_validation()`` around request parsing to report INVALID_ARGUMENT, or pass
    ``validation_errors_as_invalid_argument=True`` to restore the previous mapping for every ``ValidationError``.
    """

    def __init__(self, validation_errors_as_invalid_argument: bool = False) -> None:
        """Initialize the interceptor.

        Args:
            validation_errors_as_invalid_argument: When True, every Pydantic ``ValidationError`` raised by a handler
                is reported as INVALID_ARGUMENT (the pre-5.10 behavior). Defaults to False (INTERNAL).
        """
        self._validation_errors_as_invalid_argument = validation_errors_as_invalid_argument

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
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
            # Execute the gRPC method
            result = await method(request, context)

        except grpc.aio.AbortError:
            # The handler or an inner interceptor already aborted the call with a deliberate status.
            raise

        except ValidationError as validation_error:
            BaseUtils.capture_exception(validation_error)
            if self._validation_errors_as_invalid_argument:
                await self._handle_validation_error(validation_error, context)
            else:
                await self._handle_unexpected_error(validation_error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy

        except BaseError as base_error:
            BaseUtils.capture_exception(base_error)
            await base_error.abort_grpc_async(context)
            raise  # This will never be reached, but satisfies MyPy

        except Exception as unexpected_error:
            BaseUtils.capture_exception(unexpected_error)
            await self._handle_unexpected_error(unexpected_error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

    async def intercept_stream(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
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

        except ValidationError as validation_error:
            BaseUtils.capture_exception(validation_error)
            if self._validation_errors_as_invalid_argument:
                await self._handle_validation_error(validation_error, context)
            else:
                await self._handle_unexpected_error(validation_error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy

        except BaseError as base_error:
            BaseUtils.capture_exception(base_error)
            await base_error.abort_grpc_async(context)
            raise  # This will never be reached, but satisfies MyPy

        except Exception as unexpected_error:
            BaseUtils.capture_exception(unexpected_error)
            await self._handle_unexpected_error(unexpected_error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy

    @staticmethod
    async def _handle_validation_error(validation_error: ValidationError, context: grpc.aio.ServicerContext) -> None:
        """Handle Pydantic validation errors.

        Args:
            validation_error: The validation error to handle.
            context: The gRPC context to abort.
        """
        await _invalid_argument_from_validation(validation_error).abort_grpc_async(context)

    @staticmethod
    async def _handle_unexpected_error(
        error: Exception,  # noqa: ARG004 - kept for subclass overrides
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,  # noqa: ARG004 - kept for subclass overrides
    ) -> None:
        """Handle unexpected errors by converting them to internal errors.

        Args:
            error: The unexpected error to handle.
            context: The gRPC context to abort.
            method_name_model: The method name information (kept for subclass overrides).
        """
        # The cause was already logged by ``capture_exception``; never send internals to the client.
        await InternalError().abort_grpc_async(context)
