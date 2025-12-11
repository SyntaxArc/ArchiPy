import abc
from collections.abc import AsyncIterable, Callable, Iterable, Iterator, Sequence
from typing import Any, NamedTuple, TypeVar

import grpc

_TRequest = TypeVar("_TRequest")


class _ClientCallDetailsFields(NamedTuple):
    """A named tuple containing fields for `ClientCallDetails`.

    Attributes:
        method (str): The RPC method name.
        timeout (float | None): The timeout for the RPC call.
        metadata (Sequence[tuple[str, str | bytes]] | None): Metadata for the RPC call.
        credentials (grpc.CallCredentials | None): Call credentials for the RPC.
        wait_for_ready (bool | None): Whether to wait for the server to be ready.
        compression (grpc.Compression | None): The compression method for the RPC.
    """

    method: str
    timeout: float | None
    metadata: Sequence[tuple[str, str | bytes]] | None
    credentials: grpc.CallCredentials | None
    wait_for_ready: bool | None
    compression: grpc.Compression | None


class ClientCallDetails(_ClientCallDetailsFields, grpc.ClientCallDetails):
    """Describes an RPC to be invoked.

    This class extends `grpc.ClientCallDetails` and provides additional fields for RPC details.
    See https://grpc.github.io/grpc/python/grpc.html#grpc.ClientCallDetails
    """


def _swap_args(fn: Callable[[Any, Any], Any]) -> Callable[[Any, Any], Any]:
    """Swaps the arguments of a function.

    Args:
        fn (Callable[[Any, Any], Any]): The function whose arguments need to be swapped.

    Returns:
        Callable[[Any, Any], Any]: A new function with swapped arguments.
    """

    def new_fn(x: Any, y: Any) -> Any:
        return fn(y, x)

    return new_fn


class BaseGrpcClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor,
    metaclass=abc.ABCMeta,
):
    """Base class for gRPC client interceptors.

    This class provides a base implementation for intercepting gRPC client calls.
    It supports unary-unary, unary-stream, stream-unary, and stream-stream RPCs.
    """

    @abc.abstractmethod
    def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.ClientCallDetails,
    ) -> Any:
        """Intercepts a gRPC client call.

        Args:
            method (Callable): The continuation function to call.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.ClientCallDetails): Details of the RPC call.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        return method(request_or_iterator, call_details)

    def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Intercepts a unary-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request (Any): The request object.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = self.intercept(_swap_args(continuation), request, client_call_details)
        return result

    def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Intercepts a unary-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request (Any): The request object.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = self.intercept(_swap_args(continuation), request, client_call_details)
        return result

    def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Iterator[_TRequest]], Any],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Iterator[_TRequest],
    ) -> Any:
        """Intercepts a stream-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[Any]): The request iterator.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = self.intercept(_swap_args(continuation), request_iterator, client_call_details)
        return result

    def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Iterator[_TRequest]], Any],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Iterator[_TRequest],
    ) -> Any:
        """Intercepts a stream-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[Any]): The request iterator.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = self.intercept(_swap_args(continuation), request_iterator, client_call_details)
        return result


class _AsyncClientCallDetailsFields(NamedTuple):
    """A named tuple containing fields for `AsyncClientCallDetails`.

    Attributes:
        method (str): The RPC method name.
        timeout (float | None): The timeout for the RPC call.
        metadata (Sequence[tuple[str, str | bytes]] | None): Metadata for the RPC call.
        credentials (grpc.CallCredentials | None): Call credentials for the RPC.
        wait_for_ready (bool | None): Whether to wait for the server to be ready.
    """

    method: str
    timeout: float | None
    metadata: Sequence[tuple[str, str | bytes]] | None
    credentials: grpc.CallCredentials | None
    wait_for_ready: bool | None


class AsyncClientCallDetails(_AsyncClientCallDetailsFields, grpc.aio.ClientCallDetails):
    """Describes an RPC to be invoked in an asynchronous context.

    This class extends `grpc.aio.ClientCallDetails` and provides additional fields for RPC details.
    See https://grpc.github.io/grpc/python/grpc.html#grpc.ClientCallDetails
    """


class BaseAsyncGrpcClientInterceptor(
    grpc.aio.UnaryUnaryClientInterceptor,
    grpc.aio.UnaryStreamClientInterceptor,
    grpc.aio.StreamUnaryClientInterceptor,
    grpc.aio.StreamStreamClientInterceptor,
    metaclass=abc.ABCMeta,
):
    """Base class for asynchronous gRPC client interceptors.

    This class provides a base implementation for intercepting asynchronous gRPC client calls.
    It supports unary-unary, unary-stream, stream-unary, and stream-stream RPCs.
    """

    @abc.abstractmethod
    async def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.aio.ClientCallDetails,
    ) -> Any:
        """Intercepts an asynchronous gRPC client call.

        Args:
            method (Callable): The continuation function to call.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.aio.ClientCallDetails): Details of the RPC call.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        return await method(request_or_iterator, call_details)

    async def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Intercepts an asynchronous unary-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request (Any): The request object.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = await self.intercept(_swap_args(continuation), request, client_call_details)
        return result

    async def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Intercepts an asynchronous unary-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request (Any): The request object.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = await self.intercept(_swap_args(continuation), request, client_call_details)
        return result

    async def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, AsyncIterable[_TRequest] | Iterable[_TRequest]], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: AsyncIterable[_TRequest] | Iterable[_TRequest],
    ) -> Any:
        """Intercepts an asynchronous stream-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[Any]): The request iterator.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = await self.intercept(_swap_args(continuation), request_iterator, client_call_details)
        return result

    async def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, AsyncIterable[_TRequest] | Iterable[_TRequest]], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: AsyncIterable[_TRequest] | Iterable[_TRequest],
    ) -> Any:
        """Intercepts an asynchronous stream-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[Any]): The request iterator.

        Returns:
            Any: The result of the intercepted RPC call.
        """
        result = await self.intercept(_swap_args(continuation), request_iterator, client_call_details)
        return result
