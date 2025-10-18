from collections.abc import Callable

import grpc
from pydantic import ValidationError

from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import InternalError, InvalidArgumentError
from archipy.models.errors.base_error import BaseError


class GrpcServerExceptionInterceptor(BaseGrpcServerInterceptor):
    """A sync gRPC server interceptor for centralized exception handling.

    This interceptor catches all exceptions thrown by gRPC service methods and
    converts them to appropriate gRPC errors, eliminating the need for repetitive
    try-catch blocks in each service method.
    """

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

        except ValidationError as validation_error:
            BaseUtils.capture_exception(validation_error)
            self._handle_validation_error(validation_error, context)
            raise  # This will never be reached, but satisfies MyPy

        except BaseError as base_error:
            BaseUtils.capture_exception(base_error)
            base_error.abort_grpc_sync(context)
            raise  # This will never be reached, but satisfies MyPy

        except Exception as unexpected_error:
            BaseUtils.capture_exception(unexpected_error)
            self._handle_unexpected_error(unexpected_error, context, method_name_model)
            raise  # This will never be reached, but satisfies MyPy
        else:
            return result

    @staticmethod
    def _handle_validation_error(validation_error: ValidationError, context: grpc.ServicerContext) -> None:
        """Handle Pydantic validation errors.

        Args:
            validation_error: The validation error to handle.
            context: The gRPC context to abort.
        """
        # Format validation errors for better debugging
        validation_details = BaseUtils.format_validation_errors(validation_error, include_type=True)

        InvalidArgumentError(
            argument_name="request_validation",
            additional_data={"validation_errors": validation_details, "error_count": len(validation_error.errors())},
        ).abort_grpc_sync(context)

    @staticmethod
    def _handle_unexpected_error(
        error: Exception,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> None:
        """Handle unexpected errors by converting them to internal errors.

        Args:
            error: The unexpected error to handle.
            context: The gRPC context to abort.
            method_name_model: The method name information for better error tracking.
        """
        # Capture the exception for monitoring
        InternalError(
            additional_data={
                "original_error": str(error),
                "error_type": type(error).__name__,
                "service": method_name_model.service,
                "method": method_name_model.method,
                "package": method_name_model.package,
            },
        ).abort_grpc_sync(context)

    @staticmethod
    def _format_validation_errors(validation_error: ValidationError) -> list[dict[str, str]]:
        """Format Pydantic validation errors into a structured format.

        Args:
            validation_error: The validation error to format.

        Returns:
            A list of formatted validation error details.

        Note:
            This method is deprecated. Use BaseUtils.format_validation_errors instead.
        """
        return BaseUtils.format_validation_errors(validation_error, include_type=True)


class AsyncGrpcServerExceptionInterceptor(BaseAsyncGrpcServerInterceptor):
    """An async gRPC server interceptor for centralized exception handling.

    This interceptor catches all exceptions thrown by gRPC service methods and
    converts them to appropriate gRPC errors, eliminating the need for repetitive
    try-catch blocks in each service method.
    """

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
            result = method(request, context)

        except ValidationError as validation_error:
            BaseUtils.capture_exception(validation_error)
            await self._handle_validation_error(validation_error, context)
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

    @staticmethod
    async def _handle_validation_error(validation_error: ValidationError, context: grpc.aio.ServicerContext) -> None:
        """Handle Pydantic validation errors.

        Args:
            validation_error: The validation error to handle.
            context: The gRPC context to abort.
        """
        # Format validation errors for better debugging
        validation_details = BaseUtils.format_validation_errors(validation_error, include_type=True)

        await InvalidArgumentError(
            argument_name="request_validation",
            additional_data={"validation_errors": validation_details, "error_count": len(validation_error.errors())},
        ).abort_grpc_async(context)

    @staticmethod
    async def _handle_unexpected_error(
        error: Exception,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> None:
        """Handle unexpected errors by converting them to internal errors.

        Args:
            error: The unexpected error to handle.
            context: The gRPC context to abort.
            method_name_model: The method name information for better error tracking.
        """
        # Capture the exception for monitoring
        await InternalError(
            additional_data={
                "original_error": str(error),
                "error_type": type(error).__name__,
                "service": method_name_model.service,
                "method": method_name_model.method,
                "package": method_name_model.package,
            },
        ).abort_grpc_async(context)

    @staticmethod
    def _format_validation_errors(validation_error: ValidationError) -> list[dict[str, str]]:
        """Format Pydantic validation errors into a structured format.

        Args:
            validation_error: The validation error to format.

        Returns:
            A list of formatted validation error details.

        Note:
            This method is deprecated. Use BaseUtils.format_validation_errors instead.
        """
        return BaseUtils.format_validation_errors(validation_error, include_type=True)
