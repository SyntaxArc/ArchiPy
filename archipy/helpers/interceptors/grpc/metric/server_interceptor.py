import asyncio
import time
from collections.abc import Callable
from typing import ClassVar

import grpc

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.utils.base_utils import BaseUtils


class GrpcServerMetricInterceptor(BaseGrpcServerInterceptor):
    """A gRPC server interceptor for collecting and reporting metrics using Prometheus.

    This interceptor measures the response time of gRPC methods and records it in a Prometheus histogram.
    It also captures errors and logs them for monitoring purposes.
    """

    from prometheus_client import Histogram

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
        "response_time_seconds",
        "Time spent processing request",
        labelnames=("package", "service", "method", "status_code"),
        buckets=TOTAL_BUCKETS,
    )

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts a gRPC server call to measure response time and capture errors.

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
        try:
            # Skip metric collection if Prometheus is disabled
            if not BaseConfig.global_config().PROMETHEUS.IS_ENABLED:
                return method(request, context)

            # Measure the start time
            start_time = time.time()

            # Execute the gRPC method
            result = method(request, context)

            # Record the response time in the Prometheus histogram
            status_code = "OK"
            if hasattr(context, "code") and callable(context.code):
                code_obj = context.code()
                if code_obj is not None:
                    code_name = getattr(code_obj, "name", None)
                    if code_name is not None:
                        status_code = code_name
            self.RESPONSE_TIME_SECONDS.labels(
                package=method_name_model.package,
                service=method_name_model.service,
                method=method_name_model.method,
                status_code=status_code,
            ).observe(time.time() - start_time)
        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
        else:
            return result


class AsyncGrpcServerMetricInterceptor(BaseAsyncGrpcServerInterceptor):
    """An async gRPC server interceptor for collecting and reporting metrics using Prometheus.

    This interceptor measures the response time of async gRPC methods and records it in a Prometheus histogram.
    It also captures errors and logs them for monitoring purposes.
    """

    from prometheus_client import Histogram

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
        "grpc_async_server_response_time_seconds",
        "Time spent processing async gRPC request",
        labelnames=("package", "service", "method", "status_code"),
        buckets=TOTAL_BUCKETS,
    )

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts an async gRPC server call to measure response time and capture errors.

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
        try:
            # Skip metric collection if Prometheus is disabled
            if not BaseConfig.global_config().PROMETHEUS.IS_ENABLED:
                return await method(request, context)

            # Measure the start time using asyncio event loop time for better precision
            start_time = asyncio.get_event_loop().time()
            status_code = "OK"

            try:
                # Execute the async gRPC method
                result = await method(request, context)

                # Get the actual status code from context
                if hasattr(context, "code") and context.code():
                    status_code = context.code().name
            except Exception as e:
                # Determine error status code
                if isinstance(e, grpc.aio.AioRpcError):
                    code_obj = e.code()
                    if code_obj is not None:
                        code_name = getattr(code_obj, "name", None)
                        if code_name is not None:
                            status_code = code_name
                elif hasattr(e, "code") and callable(e.code):
                    code_method = e.code
                    code_obj = code_method()
                    if code_obj is not None:
                        code_name = getattr(code_obj, "name", None)
                        if code_name is not None:
                            status_code = code_name
                else:
                    status_code = "INTERNAL"
                raise
            else:
                return result
            finally:
                # Record the response time in the Prometheus histogram
                duration = asyncio.get_event_loop().time() - start_time
                self.RESPONSE_TIME_SECONDS.labels(
                    package=method_name_model.package,
                    service=method_name_model.service,
                    method=method_name_model.method,
                    status_code=status_code,
                ).observe(duration)

        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
