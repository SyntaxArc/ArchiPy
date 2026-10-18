"""Base gRPC client interceptor."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, NamedTuple, TypeVar

import grpc

if TYPE_CHECKING:
    from collections.abc import AsyncIterable, Awaitable, Callable, Iterable, Iterator, Sequence

_TRequest = TypeVar("_TRequest")
_TResult = TypeVar("_TResult")


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


def _swap_args[X, Y, R](fn: Callable[[X, Y], R]) -> Callable[[Y, X], R]:
    """Swaps the arguments of a function.

    Args:
        fn (Callable[[X, Y], R]): The function whose arguments need to be swapped.

    Returns:
        Callable[[Y, X], R]: A new function with swapped arguments.
    """

    def new_fn(x: Y, y: X) -> R:
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
    def intercept[TRequest, TResult](
        self,
        method: Callable[[TRequest, grpc.ClientCallDetails], TResult],
        request_or_iterator: TRequest,
        call_details: grpc.ClientCallDetails,
    ) -> TResult:
        """Intercepts a gRPC client call.

        Args:
            method (Callable): The continuation function to call.
            request_or_iterator (TRequest): The request or request iterator.
            call_details (grpc.ClientCallDetails): Details of the RPC call.

        Returns:
            TResult: The result of the intercepted RPC call.
        """
        return method(request_or_iterator, call_details)

    def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, _TRequest], _TResult],
        client_call_details: grpc.ClientCallDetails,
        request: _TRequest,
    ) -> _TResult:
        """Intercepts a unary-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request (_TRequest): The request object.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return self.intercept(_swap_args(continuation), request, client_call_details)

    def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, _TRequest], _TResult],
        client_call_details: grpc.ClientCallDetails,
        request: _TRequest,
    ) -> _TResult:
        """Intercepts a unary-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request (_TRequest): The request object.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return self.intercept(_swap_args(continuation), request, client_call_details)

    def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Iterator[_TRequest]], _TResult],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Iterator[_TRequest],
    ) -> _TResult:
        """Intercepts a stream-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[_TRequest]): The request iterator.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return self.intercept(_swap_args(continuation), request_iterator, client_call_details)

    def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Iterator[_TRequest]], _TResult],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Iterator[_TRequest],
    ) -> _TResult:
        """Intercepts a stream-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[_TRequest]): The request iterator.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return self.intercept(_swap_args(continuation), request_iterator, client_call_details)


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
    async def intercept[TRequest, TResult](
        self,
        method: Callable[[TRequest, grpc.aio.ClientCallDetails], Awaitable[TResult]],
        request_or_iterator: TRequest,
        call_details: grpc.aio.ClientCallDetails,
    ) -> TResult:
        """Intercepts an asynchronous gRPC client call.

        Args:
            method (Callable): The continuation function to call.
            request_or_iterator (TRequest): The request or request iterator.
            call_details (grpc.aio.ClientCallDetails): Details of the RPC call.

        Returns:
            TResult: The result of the intercepted RPC call.
        """
        return await method(request_or_iterator, call_details)

    async def intercept_unary_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, _TRequest], Awaitable[_TResult]],
        client_call_details: grpc.aio.ClientCallDetails,
        request: _TRequest,
    ) -> _TResult:
        """Intercepts an asynchronous unary-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request (_TRequest): The request object.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return await self.intercept(_swap_args(continuation), request, client_call_details)

    async def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, _TRequest], Awaitable[_TResult]],
        client_call_details: grpc.aio.ClientCallDetails,
        request: _TRequest,
    ) -> _TResult:
        """Intercepts an asynchronous unary-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request (_TRequest): The request object.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return await self.intercept(_swap_args(continuation), request, client_call_details)

    async def intercept_stream_unary(
        self,
        continuation: Callable[
            [grpc.aio.ClientCallDetails, AsyncIterable[_TRequest] | Iterable[_TRequest]],
            Awaitable[_TResult],
        ],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: AsyncIterable[_TRequest] | Iterable[_TRequest],
    ) -> _TResult:
        """Intercepts an asynchronous stream-unary RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[_TRequest]): The request iterator.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return await self.intercept(_swap_args(continuation), request_iterator, client_call_details)

    async def intercept_stream_stream(
        self,
        continuation: Callable[
            [grpc.aio.ClientCallDetails, AsyncIterable[_TRequest] | Iterable[_TRequest]],
            Awaitable[_TResult],
        ],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: AsyncIterable[_TRequest] | Iterable[_TRequest],
    ) -> _TResult:
        """Intercepts an asynchronous stream-stream RPC call.

        Args:
            continuation (Callable): The continuation function to call.
            client_call_details (grpc.aio.ClientCallDetails): Details of the RPC call.
            request_iterator (Iterator[_TRequest]): The request iterator.

        Returns:
            _TResult: The result of the intercepted RPC call.
        """
        return await self.intercept(_swap_args(continuation), request_iterator, client_call_details)
