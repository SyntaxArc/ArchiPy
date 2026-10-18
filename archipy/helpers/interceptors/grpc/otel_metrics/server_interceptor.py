"""gRPC server interceptors for OpenTelemetry RPC duration and active-request metrics."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
    iterate_stream_result,
)
from archipy.helpers.utils.otel_utils import OtelUtils

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    import grpc

_RPC_DURATION_INSTRUMENT = "rpc.server.call.duration"
_RPC_ACTIVE_INSTRUMENT = "rpc.server.active_requests"
_RPC_METER_NAME = "archipy.grpc"


class _Instruments(NamedTuple):
    """The RPC instruments of one meter provider."""

    duration: Any
    active: Any
    provider_id: int


class _RpcInstruments:
    """Lazy, process-wide RPC instruments bound to the current meter.

    Holds the OpenTelemetry ``rpc.server.call.duration`` histogram and the ``rpc.server.active_requests`` counter,
    which is an ArchiPy metric the specification does not define.
    """

    # One tuple so readers never see a half-updated pair.
    _state: ClassVar[_Instruments | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get(cls) -> _Instruments | None:
        """Return the RPC instruments, recreating them after a provider reset.

        Returns:
            The instruments, or ``None`` when metrics are unavailable.
        """
        if OtelUtils.import_failed() or OtelUtils.meter_provider() is None:
            return None
        provider_id = id(OtelUtils.meter_provider())
        state = cls._state
        if state is not None and state.provider_id == provider_id:
            return state
        with cls._lock:
            state = cls._state
            if state is not None and state.provider_id == provider_id:
                return state
            meter = OtelUtils.get_meter(_RPC_METER_NAME)
            cls._state = _Instruments(
                duration=meter.create_histogram(
                    _RPC_DURATION_INSTRUMENT,
                    unit="s",
                    description="gRPC server call duration",
                    explicit_bucket_boundaries_advisory=OtelUtils.duration_histogram_buckets(),
                ),
                active=meter.create_up_down_counter(
                    _RPC_ACTIVE_INSTRUMENT,
                    unit="{request}",
                    description="Number of active gRPC server requests",
                ),
                provider_id=provider_id,
            )
            return cls._state

    @classmethod
    def clear(cls) -> None:
        """Drop the cached instruments (tests / provider reset)."""
        with cls._lock:
            cls._state = None


# gRPC codes the semantic conventions treat as server-side failures, recorded as ``error.type``.
_SERVER_ERROR_CODES = frozenset(
    {"UNKNOWN", "DEADLINE_EXCEEDED", "UNIMPLEMENTED", "INTERNAL", "UNAVAILABLE", "DATA_LOSS"},
)


def _rpc_attributes(method_name_model: MethodName, grpc_code: str | None) -> dict[str, str]:
    """Build the OpenTelemetry RPC attributes: system name, fully qualified method, status code and error type."""
    attributes = {
        "rpc.system.name": "grpc",
        "rpc.method": method_name_model.full_name.lstrip("/"),
    }
    if grpc_code is not None:
        attributes["rpc.response.status_code"] = grpc_code
    if grpc_code in _SERVER_ERROR_CODES:
        attributes["error.type"] = grpc_code
    return attributes


def _classify_failure(context: object) -> str:
    """Return the gRPC code name of a call whose handler raised.

    The metrics interceptor runs outside the exception interceptor, so the exception is usually the abort signal
    rather than the domain error. The status the call finished with is on the context, so prefer it. A handler that
    raised without setting one is answered with ``UNKNOWN`` by gRPC, and that is what is recorded.

    Args:
        context: The gRPC context of the call.

    Returns:
        The gRPC status code name.
    """
    code_getter = getattr(context, "code", None)
    code = code_getter() if callable(code_getter) else None
    code_name = getattr(code, "name", None)
    if isinstance(code_name, str) and code_name != "OK":
        return code_name
    return "UNKNOWN"


class _RpcCallRecorder:
    """Tracks one in-flight RPC: increments active requests on start, records duration on finish."""

    def __init__(self, instruments: _Instruments, method_name_model: MethodName) -> None:
        self._histogram = instruments.duration
        self._active = instruments.active
        self._method_name_model = method_name_model
        self._active_attributes = _rpc_attributes(method_name_model, None)
        self._finished = False
        self._active.add(1, self._active_attributes)
        self._start = time.perf_counter()

    @classmethod
    def start(cls, method_name_model: MethodName) -> _RpcCallRecorder | None:
        """Begin tracking a call, or return ``None`` when metrics are unavailable."""
        instruments = _RpcInstruments.get()
        if instruments is None:
            return None
        return cls(instruments, method_name_model)

    def finish(self, grpc_code: str | None = None) -> None:
        """Decrement active requests and record elapsed seconds with the call outcome.

        Idempotent: only the first call records, so a termination callback and the normal path cannot double count.
        """
        if self._finished:
            return
        self._finished = True
        self._active.add(-1, self._active_attributes)
        self._histogram.record(
            time.perf_counter() - self._start,
            _rpc_attributes(self._method_name_model, grpc_code),
        )


class GrpcServerOtelMetricsInterceptor(BaseGrpcServerInterceptor):
    """Sync gRPC interceptor that records ``rpc.server.call.duration`` and ``rpc.server.active_requests``."""

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
        except Exception:
            recorder.finish(_classify_failure(context))
            raise
        if isinstance(result, Iterator):
            # Response-streaming handler: the RPC only finishes once the stream is consumed. If the client
            # cancels or the stream is never iterated, the generator's ``finally`` never runs, so also finish
            # on RPC termination to keep the active-requests counter balanced.
            if not context.add_callback(lambda: recorder.finish("CANCELLED")):
                # The RPC already terminated: no callback will ever fire.
                recorder.finish("CANCELLED")
            return self._time_stream(result, recorder, context)
        recorder.finish("OK")
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
        grpc_code = "OK"
        try:
            yield from stream
        except GeneratorExit:
            # The client went away and gRPC closed the generator.
            grpc_code = "CANCELLED"
            raise
        except Exception:
            grpc_code = _classify_failure(context)
            raise
        finally:
            recorder.finish(grpc_code)


class AsyncGrpcServerOtelMetricsInterceptor(BaseAsyncGrpcServerInterceptor):
    """Async gRPC interceptor that records ``rpc.server.call.duration`` and ``rpc.server.active_requests``."""

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

        grpc_code = "OK"
        try:
            return await method(request, context)
        except asyncio.CancelledError:
            # Client cancellation or an expired deadline; ``CancelledError`` is not an ``Exception``.
            grpc_code = "CANCELLED"
            raise
        except Exception:
            grpc_code = _classify_failure(context)
            raise
        finally:
            recorder.finish(grpc_code)

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

        grpc_code = "OK"
        try:
            async for item in iterate_stream_result(method(request, context)):
                yield item
        except asyncio.CancelledError, GeneratorExit:
            grpc_code = "CANCELLED"
            raise
        except Exception:
            grpc_code = _classify_failure(context)
            raise
        finally:
            recorder.finish(grpc_code)
