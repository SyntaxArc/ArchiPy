"""gRPC server interceptors for OpenTelemetry RPC duration and active-request metrics."""

from __future__ import annotations

import asyncio
import threading
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


class _RpcInstruments:
    """Lazy, process-wide RPC instruments bound to the current meter.

    Holds the ``rpc.server.request.duration`` histogram and the ``rpc.server.active_requests`` counter,
    mirroring FastAPI's ``http.server.request.duration`` / ``http.server.active_requests`` pair.
    """

    # One tuple (histogram, active, provider id) so readers never see a half-updated pair.
    _state: ClassVar[tuple[Any, Any, int] | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get(cls) -> tuple[Any, Any] | None:
        """Return the duration histogram and active-requests counter, recreating them after provider reset.

        Returns:
            ``(histogram, active_requests)``, or ``None`` when metrics are unavailable.
        """
        if OtelUtils.import_failed() or OtelUtils.meter_provider() is None:
            return None
        provider_id = id(OtelUtils.meter_provider())
        state = cls._state
        if state is not None and state[2] == provider_id:
            return state[0], state[1]
        with cls._lock:
            state = cls._state
            if state is not None and state[2] == provider_id:
                return state[0], state[1]
            meter = OtelUtils.get_meter(_RPC_METER_NAME)
            histogram = meter.create_histogram(
                _RPC_DURATION_INSTRUMENT,
                unit="s",
                description="gRPC server call duration",
                explicit_bucket_boundaries_advisory=DURATION_HISTOGRAM_BUCKETS_S,
            )
            active = meter.create_up_down_counter(
                _RPC_ACTIVE_INSTRUMENT,
                unit="{request}",
                description="Number of active gRPC server requests",
            )
            cls._state = (histogram, active, provider_id)
            return histogram, active

    @classmethod
    def clear(cls) -> None:
        """Drop the cached instruments (tests / provider reset)."""
        with cls._lock:
            cls._state = None


# gRPC codes that signal a handled caller error, recorded as ``ok`` like HTTP statuses below 500.
_CLIENT_FAULT_CODES = frozenset(
    {
        "INVALID_ARGUMENT",
        "NOT_FOUND",
        "ALREADY_EXISTS",
        "PERMISSION_DENIED",
        "UNAUTHENTICATED",
        "FAILED_PRECONDITION",
        "OUT_OF_RANGE",
        "RESOURCE_EXHAUSTED",
        "ABORTED",
    },
)


def _rpc_attributes(method_name_model: MethodName, status: str, grpc_code: str | None = None) -> dict[str, str]:
    """Build semantic-convention-ish attributes for an RPC metric recording."""
    attributes = {
        "rpc.system": "grpc",
        "rpc.service": method_name_model.service,
        "rpc.method": method_name_model.method,
        "status": status,
    }
    if grpc_code is not None:
        attributes["rpc.grpc.status_code"] = grpc_code
    return attributes


def _status_for_code(code_name: str) -> str:
    """Map a gRPC status code name to the ``status`` metric attribute."""
    if code_name == "OK" or code_name in _CLIENT_FAULT_CODES:
        return "ok"
    if code_name == "CANCELLED":
        return "cancelled"
    return "error"


def _classify_failure(exc: BaseException, context: object) -> tuple[str, str | None]:
    """Work out the metric status and gRPC code for a call that raised ``exc``.

    The metrics interceptor runs outside the exception interceptor, so ``exc`` is usually the abort signal rather
    than the domain error. The status the call finished with is on the context, so prefer it.

    Args:
        exc: The exception that escaped the handler.
        context: The gRPC context of the call.

    Returns:
        ``(status, grpc_code_name)``. The code name is ``None`` when the context holds no status.
    """
    code_getter = getattr(context, "code", None)
    code = code_getter() if callable(code_getter) else None
    code_name = getattr(code, "name", None)
    if isinstance(code_name, str) and code_name != "OK":
        return _status_for_code(code_name), code_name
    return OtelUtils.metric_status_for_exception(exc), None


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
        self._finished = False
        self._active.add(1, self._active_attributes)
        self._start = time.perf_counter()

    @classmethod
    def start(cls, method_name_model: MethodName) -> _RpcCallRecorder | None:
        """Begin tracking a call, or return ``None`` when metrics are unavailable."""
        instruments = _RpcInstruments.get()
        if instruments is None:
            return None
        histogram, active = instruments
        return cls(histogram, active, method_name_model)

    def finish(self, status: str, grpc_code: str | None = None) -> None:
        """Decrement active requests and record elapsed seconds with the call status.

        Idempotent: only the first call records, so a termination callback and the normal path cannot double count.
        """
        if self._finished:
            return
        self._finished = True
        self._active.add(-1, self._active_attributes)
        self._histogram.record(
            time.perf_counter() - self._start,
            _rpc_attributes(self._method_name_model, status, grpc_code),
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
            recorder.finish(*_classify_failure(exc, context))
            raise
        if isinstance(result, Iterator):
            # Response-streaming handler: the RPC only finishes once the stream is consumed. If the client
            # cancels or the stream is never iterated, the generator's ``finally`` never runs, so also finish
            # on RPC termination to keep the active-requests counter balanced.
            if not context.add_callback(lambda: recorder.finish("cancelled", "CANCELLED")):
                # The RPC already terminated: no callback will ever fire.
                recorder.finish("cancelled", "CANCELLED")
            return self._time_stream(result, recorder, context)
        recorder.finish("ok", "OK")
        return result

    @staticmethod
    def _time_stream(
        stream: Iterator[object],
        recorder: _RpcCallRecorder,
        context: grpc.ServicerContext,
    ) -> Iterator[object]:
        """Relay a sync response stream and record the duration once it ends.

        Args:
            stream: The response iterator returned by the handler.
            recorder: Tracker for the in-flight call.
            context: The context of the sync gRPC call.

        Yields:
            Each response message.
        """
        status, grpc_code = "ok", "OK"
        try:
            yield from stream
        except GeneratorExit:
            # The client went away and gRPC closed the generator.
            status, grpc_code = "cancelled", "CANCELLED"
            raise
        except Exception as exc:
            status, grpc_code = _classify_failure(exc, context)
            raise
        finally:
            recorder.finish(status, grpc_code)


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

        status, grpc_code = "ok", "OK"
        try:
            return await method(request, context)
        except asyncio.CancelledError:
            # Client cancellation or an expired deadline; ``CancelledError`` is not an ``Exception``.
            status, grpc_code = "cancelled", "CANCELLED"
            raise
        except Exception as exc:
            status, grpc_code = _classify_failure(exc, context)
            raise
        finally:
            recorder.finish(status, grpc_code)

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

        status, grpc_code = "ok", "OK"
        try:
            async for item in iterate_stream_result(method(request, context)):
                yield item
        except asyncio.CancelledError, GeneratorExit:
            status, grpc_code = "cancelled", "CANCELLED"
            raise
        except Exception as exc:
            status, grpc_code = _classify_failure(exc, context)
            raise
        finally:
            recorder.finish(status, grpc_code)
