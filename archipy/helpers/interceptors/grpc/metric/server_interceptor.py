import asyncio
import time
from typing import TYPE_CHECKING, ClassVar

import grpc

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.utils.base_utils import BaseUtils

if TYPE_CHECKING:
    from collections.abc import Callable


def _status_code_from_context(context: grpc.ServicerContext | grpc.aio.ServicerContext) -> str:
    """Extract a gRPC status code name from a servicer context."""
    if not hasattr(context, "code") or not callable(context.code):
        return "OK"
    code_obj = context.code()  # ty: ignore[call-top-callable]
    if code_obj is None:
        return "OK"
    code_name = getattr(code_obj, "name", None)
    return code_name if code_name is not None else "OK"


def _status_code_from_async_exception(exception: Exception) -> str:
    """Extract a gRPC status code name from an async RPC exception."""
    if isinstance(exception, grpc.aio.AioRpcError):
        code_obj = exception.code()
        if code_obj is not None:
            code_name = getattr(code_obj, "name", None)
            if code_name is not None:
                return code_name
    if hasattr(exception, "code") and callable(exception.code):
        code_obj = exception.code()  # ty: ignore[call-top-callable]
        if code_obj is not None:
            code_name = getattr(code_obj, "name", None)
            if code_name is not None:
                return code_name
    return "INTERNAL"


class GrpcServerMetricInterceptor(BaseGrpcServerInterceptor):
    """A gRPC server interceptor for collecting and reporting metrics using Prometheus.

    This interceptor measures the response time of gRPC methods and records it in a Prometheus histogram.
    It also tracks the number of active requests using a Prometheus gauge.
    It also captures errors and logs them for monitoring purposes.
    """

    from prometheus_client import Gauge, Histogram

    "Buckets for measuring response times between 0 and 1 second."
    ZERO_TO_ONE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 1000 for i in range(0, 1000, 5)]

    "Buckets for measuring response times between 1 and 5 seconds."
    ONE_TO_FIVE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(100, 500, 20)]

    "Buckets for measuring response times between 5 and 30 seconds."
    FIVE_TO_THIRTY_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(500, 3000, 50)]

    "Combined buckets for measuring response times from 0 to 30 seconds and beyond."
    TOTAL_BUCKETS = (
        ZERO_TO_ONE_SECONDS_BUCKETS + ONE_TO_FIVE_SECONDS_BUCKETS + FIVE_TO_THIRTY_SECONDS_BUCKETS + [float("inf")]
    )

    "Prometheus histogram for tracking response times of gRPC methods."
    RESPONSE_TIME_SECONDS = Histogram(
        "grpc_response_time_seconds",
        "Time spent processing gRPC request",
        labelnames=("package", "service", "method", "status_code"),
        buckets=TOTAL_BUCKETS,
    )

    "Prometheus gauge for tracking active gRPC requests."
    ACTIVE_REQUESTS = Gauge(
        "grpc_active_requests",
        "Number of active gRPC requests",
        labelnames=("package", "service", "method"),
    )

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts a gRPC server call to measure response time and track active requests.

        Args:
            method (Callable): The gRPC method being intercepted.
            request (object): The request object passed to the method.
            context (grpc.ServicerContext): The context of the gRPC call.
            method_name_model (MethodName): The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Raises:
            Exception: If an exception occurs during the method execution, it is captured and logged.
        """
        if not BaseConfig.global_config().PROMETHEUS.IS_ENABLED:
            return method(request, context)

        package = method_name_model.package
        service = method_name_model.service
        method_name = method_name_model.method

        self.ACTIVE_REQUESTS.labels(package=package, service=service, method=method_name).inc()

        start_time = time.time()
        status_code = "OK"

        try:
            result = method(request, context)
            status_code = _status_code_from_context(context)
        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
        else:
            return result
        finally:
            duration = time.time() - start_time
            self.RESPONSE_TIME_SECONDS.labels(
                package=package,
                service=service,
                method=method_name,
                status_code=status_code,
            ).observe(duration)
            self.ACTIVE_REQUESTS.labels(package=package, service=service, method=method_name).dec()


class AsyncGrpcServerMetricInterceptor(BaseAsyncGrpcServerInterceptor):
    """An async gRPC server interceptor for collecting and reporting metrics using Prometheus.

    This interceptor measures the response time of async gRPC methods and records it in a Prometheus histogram.
    It also tracks the number of active requests using a Prometheus gauge.
    It also captures errors and logs them for monitoring purposes.
    """

    from prometheus_client import Gauge, Histogram

    "Buckets for measuring response times between 0 and 1 second."
    ZERO_TO_ONE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 1000 for i in range(0, 1000, 5)]

    "Buckets for measuring response times between 1 and 5 seconds."
    ONE_TO_FIVE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(100, 500, 20)]

    "Buckets for measuring response times between 5 and 30 seconds."
    FIVE_TO_THIRTY_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(500, 3000, 50)]

    "Combined buckets for measuring response times from 0 to 30 seconds and beyond."
    TOTAL_BUCKETS = (
        ZERO_TO_ONE_SECONDS_BUCKETS + ONE_TO_FIVE_SECONDS_BUCKETS + FIVE_TO_THIRTY_SECONDS_BUCKETS + [float("inf")]
    )

    "Prometheus histogram for tracking response times of async gRPC methods."
    RESPONSE_TIME_SECONDS = Histogram(
        "grpc_async_response_time_seconds",
        "Time spent processing async gRPC request",
        labelnames=("package", "service", "method", "status_code"),
        buckets=TOTAL_BUCKETS,
    )

    "Prometheus gauge for tracking active async gRPC requests."
    ACTIVE_REQUESTS = Gauge(
        "grpc_async_active_requests",
        "Number of active async gRPC requests",
        labelnames=("package", "service", "method"),
    )

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts an async gRPC server call to measure response time and track active requests.

        Args:
            method (Callable): The async gRPC method being intercepted.
            request (object): The request object passed to the method.
            context (grpc.aio.ServicerContext): The context of the async gRPC call.
            method_name_model (MethodName): The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Raises:
            Exception: If an exception occurs during the method execution, it is captured and logged.
        """
        if not BaseConfig.global_config().PROMETHEUS.IS_ENABLED:
            return await method(request, context)

        package = method_name_model.package
        service = method_name_model.service
        method_name = method_name_model.method

        self.ACTIVE_REQUESTS.labels(package=package, service=service, method=method_name).inc()

        start_time = asyncio.get_event_loop().time()
        status_code = "OK"

        try:
            try:
                result = await method(request, context)
                status_code = _status_code_from_context(context)
            except Exception as exception:
                status_code = _status_code_from_async_exception(exception)
                raise
            else:
                return result
            finally:
                duration = asyncio.get_event_loop().time() - start_time
                self.RESPONSE_TIME_SECONDS.labels(
                    package=package,
                    service=service,
                    method=method_name,
                    status_code=status_code,
                ).observe(duration)
                self.ACTIVE_REQUESTS.labels(package=package, service=service, method=method_name).dec()

        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
