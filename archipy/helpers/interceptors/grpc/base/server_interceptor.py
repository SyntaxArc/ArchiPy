"""Base gRPC server interceptor."""

from __future__ import annotations

import abc
import functools
import inspect
from typing import TYPE_CHECKING, cast

import grpc

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import InternalError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable


def _get_factory_and_method(
    rpc_handler: grpc.RpcMethodHandler,
) -> tuple[Callable, Callable]:
    """Determines the appropriate gRPC method handler factory and method based on the RPC type.

    Args:
        rpc_handler (grpc.RpcMethodHandler): The RPC method handler.

    Returns:
        tuple[Callable, Callable]: A tuple containing the method handler factory and the method itself.

    Raises:
        RuntimeError: If the RPC handler implementation does not exist.
    """
    if rpc_handler.unary_unary:
        return grpc.unary_unary_rpc_method_handler, rpc_handler.unary_unary
    if rpc_handler.unary_stream:
        return grpc.unary_stream_rpc_method_handler, rpc_handler.unary_stream
    if rpc_handler.stream_unary:
        return grpc.stream_unary_rpc_method_handler, rpc_handler.stream_unary
    if rpc_handler.stream_stream:
        return grpc.stream_stream_rpc_method_handler, rpc_handler.stream_stream
    # pragma: no cover
    raise InternalError(error_code="RPC_HANDLER_NOT_FOUND")


async def iterate_stream_result(result: object) -> AsyncIterator[object]:
    """Iterate the outcome of invoking a response-streaming async gRPC handler.

    Handlers are either async generators (yield responses) or coroutines that push
    responses through ``context.write`` and return ``None``.

    Args:
        result: The value returned by calling the handler.

    Yields:
        object: Each response message produced by the handler.
    """
    if inspect.isawaitable(result) and not hasattr(result, "__aiter__"):
        result = await result
    if result is None:
        return
    async for item in cast("AsyncIterator[object]", result):
        yield item


class MethodName(BaseDTO):
    """A data transfer object (DTO) representing the parsed method name of a gRPC call.

    Attributes:
        full_name (str): The full name of the method, including package, service, and method.
        package (str): The package name.
        service (str): The service name.
        method (str): The method name.
    """

    full_name: str
    package: str
    service: str
    method: str


def parse_method_name(method_name: str) -> MethodName:
    """Parses a gRPC method name into its components.

    Args:
        method_name (str): The full method name (e.g., "/package.service/method").

    Returns:
        MethodName: A `MethodName` object containing the parsed components.
    """
    method_full_name = method_name.replace("/", "", 1)
    package_and_service, method = method_full_name.split("/")
    *maybe_package, service = package_and_service.rsplit(".", maxsplit=1)
    package = maybe_package[0] if maybe_package else ""
    return MethodName(full_name=method_full_name, package=package, service=service, method=method)


class BaseGrpcServerInterceptor(grpc.ServerInterceptor, metaclass=abc.ABCMeta):
    """Base class for gRPC server interceptors.

    This class provides a base implementation for intercepting gRPC server calls.
    It allows custom logic to be injected into the request/response flow.
    """

    @abc.abstractmethod
    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts a gRPC server call.

        Args:
            method (Callable): The method to be intercepted.
            request (object): The request object.
            context (grpc.ServicerContext): The context of the RPC call.
            method_name_model (str): The full method name (e.g., "/package.Service/Method").

        Returns:
            object: The result of the intercepted method.
        """
        return method(request, context)

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler | None],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        """Intercepts the service call and wraps the handler with custom logic.

        Args:
            continuation: The continuation function to call.
            handler_call_details: Details of the handler call.

        Returns:
            grpc.RpcMethodHandler: The wrapped RPC method handler.
        """
        next_handler = continuation(handler_call_details)
        if next_handler is None:
            return None

        handler_factory, next_handler_method = _get_factory_and_method(next_handler)

        def invoke_intercept_method(request: object, context: grpc.ServicerContext) -> object:
            """Invokes the intercepted method.

            Args:
                request (object): The request object.
                context (grpc.ServicerContext): The context of the RPC call.

            Returns:
                object: The result of the intercepted method.
            """
            method_name_model = parse_method_name(handler_call_details.method)
            return self.intercept(next_handler_method, request, context, method_name_model)

        return handler_factory(
            invoke_intercept_method,
            request_deserializer=next_handler.request_deserializer,
            response_serializer=next_handler.response_serializer,
        )


class BaseAsyncGrpcServerInterceptor(grpc.aio.ServerInterceptor, metaclass=abc.ABCMeta):
    """Base class for asynchronous gRPC server interceptors.

    This class provides a simplified base implementation for intercepting async gRPC server calls.
    Unlike the synchronous version, async interceptors work differently and don't need the complex
    handler wrapping logic.
    """

    @abc.abstractmethod
    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts an async gRPC server call.

        Args:
            method (Callable): The method to be intercepted.
            request (object): The request object.
            context (grpc.aio.ServicerContext): The context of the RPC call.
            method_name_model (MethodName): The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted method.
        """
        return await method(request, context)

    async def intercept_stream(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> AsyncIterator[object]:
        """Intercepts an async gRPC call whose response is a stream.

        Response-streaming handlers must stay async generators, so they cannot go through
        the coroutine-based ``intercept``. The default runs ``intercept`` around the handler
        *invocation* (enough for pre-call checks) and then relays the produced stream.
        Override to wrap the iteration itself (e.g. for error handling or metrics).

        Args:
            method (Callable): The streaming method to be intercepted.
            request (object): The request object (or async iterator for stream requests).
            context (grpc.aio.ServicerContext): The context of the RPC call.
            method_name_model (MethodName): The parsed method name.

        Yields:
            object: Each response message.
        """

        @functools.wraps(method)
        async def start_stream(req: object, ctx: grpc.aio.ServicerContext) -> object:
            return method(req, ctx)

        result = await self.intercept(start_stream, request, context, method_name_model)
        async for item in iterate_stream_result(result):
            yield item

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler | None]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        """Intercepts the service call using the simplified async pattern.

        For async gRPC, we don't need the complex handler wrapping that sync interceptors require.
        Instead, we can use a much simpler pattern where we just await the continuation and
        then wrap the actual method call.

        Args:
            continuation: The continuation function to call.
            handler_call_details: Details of the handler call.

        Returns:
            grpc.RpcMethodHandler: The wrapped RPC method handler.
        """
        next_handler = await continuation(handler_call_details)
        if next_handler is None:
            return None

        handler_factory, next_handler_method = _get_factory_and_method(next_handler)

        async def invoke_intercept_method(request: object, context: grpc.aio.ServicerContext) -> object:
            """Invokes the intercepted async method.

            Args:
                request (object): The request object.
                context (grpc.aio.ServicerContext): The context of the async RPC call.

            Returns:
                object: The result of the intercepted method.
            """
            method_name_model = parse_method_name(handler_call_details.method)
            return await self.intercept(next_handler_method, request, context, method_name_model)

        async def invoke_intercept_stream(
            request: object,
            context: grpc.aio.ServicerContext,
        ) -> AsyncIterator[object]:
            """Invokes the intercepted async streaming method as an async generator.

            Args:
                request (object): The request object.
                context (grpc.aio.ServicerContext): The context of the async RPC call.

            Yields:
                object: Each response message.
            """
            method_name_model = parse_method_name(handler_call_details.method)
            async for item in self.intercept_stream(next_handler_method, request, context, method_name_model):
                yield item

        return handler_factory(
            invoke_intercept_stream if next_handler.response_streaming else invoke_intercept_method,
            request_deserializer=getattr(next_handler, "request_deserializer", None),
            response_serializer=getattr(next_handler, "response_serializer", None),
        )
