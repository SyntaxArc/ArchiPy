"""gRPC server interceptors for OpenTelemetry RPC duration and active-request metrics."""

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

_RPC_DURATION_INSTRUMENT = "rpc.server.request.duration"
_RPC_ACTIVE_INSTRUMENT = "rpc.server.active_requests"
_RPC_METER_NAME = "archipy.grpc"


class _RpcDurationHistogram:
    """Lazy, process-wide RPC instruments bound to the current meter.

    Holds the ``rpc.server.request.duration`` histogram and the ``rpc.server.active_requests`` counter,
    mirroring FastAPI's ``http.server.request.duration`` / ``http.server.active_requests`` pair.
    """

    _histogram: ClassVar[Any | None] = None
    _active: ClassVar[Any | None] = None
    _provider_id: ClassVar[int | None] = None

    @classmethod
    def get(cls) -> tuple[Any, Any] | None:
        """Return the duration histogram and active-requests counter, recreating them after provider reset.

        Returns:
            ``(histogram, active_requests)``, or ``None`` when metrics are unavailable.
        """
        if OtelUtils.import_failed() or OtelUtils.meter_provider() is None:
            return None
        provider = OtelUtils.meter_provider()
        provider_id = id(provider)
        if cls._histogram is not None and cls._active is not None and cls._provider_id == provider_id:
            return cls._histogram, cls._active
        meter = OtelUtils.get_meter(_RPC_METER_NAME)
        cls._histogram = meter.create_histogram(
            _RPC_DURATION_INSTRUMENT,
            unit="s",
            description="gRPC server call duration",
            explicit_bucket_boundaries_advisory=DURATION_HISTOGRAM_BUCKETS_S,
        )
        cls._active = meter.create_up_down_counter(
            _RPC_ACTIVE_INSTRUMENT,
            unit="{request}",
            description="Number of active gRPC server requests",
        )
        cls._provider_id = provider_id
        return cls._histogram, cls._active

    @classmethod
    def clear(cls) -> None:
        """Drop the cached instruments (tests / provider reset)."""
        cls._histogram = None
        cls._active = None
        cls._provider_id = None


def _rpc_attributes(method_name_model: MethodName, status: str) -> dict[str, str]:
    """Build semantic-convention-ish attributes for an RPC metric recording."""
    return {
        "rpc.system": "grpc",
        "rpc.service": method_name_model.service,
        "rpc.method": method_name_model.method,
        "status": status,
    }


class _RpcCallRecorder:
    """Tracks one in-flight RPC: increments active requests on start, records duration on finish."""

    def __init__(self, histogram: Any, active: Any, method_name_model: MethodName) -> None:
        self._histogram = histogram
        self._active = active
        self._method_name_model = method_name_model
        self._active_attributes = {
            "rpc.system": "grpc",
            "rpc.service": method_name_model.service,
            "rpc.method": method_name_model.method,
        }
        self._active.add(1, self._active_attributes)
        self._start = time.perf_counter()

    @classmethod
    def start(cls, method_name_model: MethodName) -> _RpcCallRecorder | None:
        """Begin tracking a call, or return ``None`` when metrics are unavailable."""
        instruments = _RpcDurationHistogram.get()
        if instruments is None:
            return None
        histogram, active = instruments
        return cls(histogram, active, method_name_model)

    def finish(self, status: str) -> None:
        """Decrement active requests and record elapsed seconds with the call status."""
        self._active.add(-1, self._active_attributes)
        self._histogram.record(
            time.perf_counter() - self._start,
            _rpc_attributes(self._method_name_model, status),
        )


class GrpcServerOtelMetricsInterceptor(BaseGrpcServerInterceptor):
    """Sync gRPC interceptor that records ``rpc.server.request.duration`` and ``rpc.server.active_requests``."""

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
        recorder = _RpcCallRecorder.start(method_name_model)
        if recorder is None:
            return method(request, context)

        try:
            result = method(request, context)
        except Exception as exc:
            recorder.finish(OtelUtils.metric_status_for_exception(exc))
            raise
        if isinstance(result, Iterator):
            # Response-streaming handler: the RPC only finishes once the stream is consumed.
            return self._time_stream(result, recorder)
        recorder.finish("ok")
        return result

    @staticmethod
    def _time_stream(
        stream: Iterator[object],
        recorder: _RpcCallRecorder,
    ) -> Iterator[object]:
        """Relay a sync response stream and record the duration once it ends.

        Args:
            stream: The response iterator returned by the handler.
            recorder: Tracker for the in-flight call.

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
            recorder.finish(status)


class AsyncGrpcServerOtelMetricsInterceptor(BaseAsyncGrpcServerInterceptor):
    """Async gRPC interceptor that records ``rpc.server.request.duration`` and ``rpc.server.active_requests``."""

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
        recorder = _RpcCallRecorder.start(method_name_model)
        if recorder is None:
            return await method(request, context)

        status = "ok"
        try:
            return await method(request, context)
        except Exception as exc:
            status = OtelUtils.metric_status_for_exception(exc)
            raise
        finally:
            recorder.finish(status)

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
        recorder = _RpcCallRecorder.start(method_name_model)
        if recorder is None:
            async for item in iterate_stream_result(method(request, context)):
                yield item
            return

        status = "ok"
        try:
            async for item in iterate_stream_result(method(request, context)):
                yield item
        except Exception as exc:
            status = OtelUtils.metric_status_for_exception(exc)
            raise
        finally:
            recorder.finish(status)
