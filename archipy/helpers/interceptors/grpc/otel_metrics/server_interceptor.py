"""gRPC server interceptors for OpenTelemetry RPC duration metrics."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
    iterate_stream_result,
)
from archipy.helpers.utils.otel_utils import DURATION_HISTOGRAM_BUCKETS_S, OtelUtils

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    import grpc

_RPC_DURATION_INSTRUMENT = "rpc.server.duration"
_RPC_METER_NAME = "archipy.grpc"


class _RpcDurationHistogram:
    """Lazy, process-wide ``rpc.server.duration`` histogram bound to the current meter."""

    _histogram: ClassVar[Any | None] = None
    _provider_id: ClassVar[int | None] = None

    @classmethod
    def get(cls) -> Any | None:
        """Return the duration histogram, recreating it after provider reset.

        Returns:
            An OpenTelemetry histogram, or ``None`` when metrics are unavailable.
        """
        if OtelUtils.import_failed() or OtelUtils.meter_provider() is None:
            return None
        provider = OtelUtils.meter_provider()
        provider_id = id(provider)
        if cls._histogram is not None and cls._provider_id == provider_id:
            return cls._histogram
        meter = OtelUtils.get_meter(_RPC_METER_NAME)
        cls._histogram = meter.create_histogram(
            _RPC_DURATION_INSTRUMENT,
            unit="s",
            description="gRPC server call duration",
            explicit_bucket_boundaries_advisory=DURATION_HISTOGRAM_BUCKETS_S,
        )
        cls._provider_id = provider_id
        return cls._histogram

    @classmethod
    def clear(cls) -> None:
        """Drop the cached histogram (tests / provider reset)."""
        cls._histogram = None
        cls._provider_id = None


def _rpc_attributes(method_name_model: MethodName, status: str) -> dict[str, str]:
    """Build semantic-convention-ish attributes for an RPC metric recording."""
    return {
        "rpc.system": "grpc",
        "rpc.service": method_name_model.service,
        "rpc.method": method_name_model.method,
        "status": status,
    }


def _record_rpc_duration(
    histogram: Any,
    start: float,
    method_name_model: MethodName,
    status: str,
) -> None:
    """Record elapsed seconds on the RPC duration histogram."""
    histogram.record(
        time.perf_counter() - start,
        _rpc_attributes(method_name_model, status),
    )


class GrpcServerOtelMetricsInterceptor(BaseGrpcServerInterceptor):
    """Sync gRPC interceptor that records ``rpc.server.duration`` histograms."""

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Time a sync gRPC handler and record duration with status.

        Args:
            method: The sync gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the sync gRPC call.
            method_name_model: Parsed package/service/method components.

        Returns:
            The result of the intercepted gRPC method.
        """
        histogram = _RpcDurationHistogram.get()
        if histogram is None:
            return method(request, context)

        start = time.perf_counter()
        try:
            result = method(request, context)
        except Exception as exc:
            _record_rpc_duration(histogram, start, method_name_model, OtelUtils.metric_status_for_exception(exc))
            raise
        if isinstance(result, Iterator):
            # Response-streaming handler: the RPC only finishes once the stream is consumed.
            return self._time_stream(result, histogram, start, method_name_model)
        _record_rpc_duration(histogram, start, method_name_model, "ok")
        return result

    @staticmethod
    def _time_stream(
        stream: Iterator[object],
        histogram: Any,
        start: float,
        method_name_model: MethodName,
    ) -> Iterator[object]:
        """Relay a sync response stream and record the duration once it ends.

        Args:
            stream: The response iterator returned by the handler.
            histogram: The RPC duration histogram.
            start: ``time.perf_counter()`` value taken when the call began.
            method_name_model: Parsed package/service/method components.

        Yields:
            Each response message.
        """
        status = "ok"
        try:
            yield from stream
        except Exception as exc:
            status = OtelUtils.metric_status_for_exception(exc)
            raise
        finally:
            _record_rpc_duration(histogram, start, method_name_model, status)


class AsyncGrpcServerOtelMetricsInterceptor(BaseAsyncGrpcServerInterceptor):
    """Async gRPC interceptor that records ``rpc.server.duration`` histograms."""

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Time an async gRPC handler and record duration with status.

        Args:
            method: The async gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the async gRPC call.
            method_name_model: Parsed package/service/method components.

        Returns:
            The result of the intercepted gRPC method.
        """
        histogram = _RpcDurationHistogram.get()
        if histogram is None:
            return await method(request, context)

        start = time.perf_counter()
        status = "ok"
        try:
            return await method(request, context)
        except Exception as exc:
            status = OtelUtils.metric_status_for_exception(exc)
            raise
        finally:
            _record_rpc_duration(histogram, start, method_name_model, status)

    async def intercept_stream(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> AsyncIterator[object]:
        """Time an async streaming gRPC handler across the whole stream and record duration.

        Args:
            method: The async streaming gRPC method being intercepted.
            request: The request object passed to the method.
            context: The context of the async gRPC call.
            method_name_model: Parsed package/service/method components.

        Yields:
            Each response message produced by the method.
        """
        histogram = _RpcDurationHistogram.get()
        if histogram is None:
            async for item in iterate_stream_result(method(request, context)):
                yield item
            return

        start = time.perf_counter()
        status = "ok"
        try:
            async for item in iterate_stream_result(method(request, context)):
                yield item
        except Exception as exc:
            status = OtelUtils.metric_status_for_exception(exc)
            raise
        finally:
            _record_rpc_duration(histogram, start, method_name_model, status)
