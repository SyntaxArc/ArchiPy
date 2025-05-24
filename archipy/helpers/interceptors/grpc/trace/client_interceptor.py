from collections.abc import Callable
from typing import Any

import elasticapm
import grpc
from elasticapm.conf.constants import TRACEPARENT_HEADER_NAME

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.client_interceptor import (
    AsyncClientCallDetails,
    BaseAsyncGrpcClientInterceptor,
    BaseGrpcClientInterceptor,
    ClientCallDetails,
)


class GrpcClientTraceInterceptor(BaseGrpcClientInterceptor):
    """A gRPC client interceptor for tracing requests using Elastic APM and Sentry APM.

    This interceptor injects the Elastic APM trace parent header into gRPC client requests
    to enable distributed tracing across services. It also creates Sentry transactions
    to monitor the performance of gRPC calls.
    """

    def intercept(self, method: Callable, request_or_iterator: Any, call_details: grpc.ClientCallDetails):
        """Intercepts a gRPC client call to inject the Elastic APM trace parent header and monitor performance with Sentry.

        Args:
            method (Callable): The gRPC method being intercepted.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.ClientCallDetails): Details of the gRPC call.

        Returns:
            Any: The result of the intercepted gRPC method.

        Notes:
            - If Elastic APM is disabled, the interceptor does nothing and passes the call through.
            - If no trace parent header is available, the interceptor does nothing and passes the call through.
        """
        # Skip tracing if Elastic APM is disabled
        if not BaseConfig.global_config().ELASTIC_APM.IS_ENABLED:
            return method(request_or_iterator, call_details)

        # Skip tracing if no trace parent header is available
        if not (trace_parent_id := elasticapm.get_trace_parent_header()):
            return method(request_or_iterator, call_details)

        # Inject the trace parent header into the call details
        new_details = ClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=[(TRACEPARENT_HEADER_NAME, f"{trace_parent_id}")],
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
            compression=call_details.compression,
        )

        # Execute the gRPC method with the updated call details
        return method(request_or_iterator, new_details)


class AsyncGrpcClientTraceInterceptor(BaseAsyncGrpcClientInterceptor):
    """An asynchronous gRPC client interceptor for tracing requests using Elastic APM.

    This interceptor injects the Elastic APM trace parent header into asynchronous gRPC client requests
    to enable distributed tracing across services.
    """

    async def intercept(self, method: Callable, request_or_iterator: Any, call_details: grpc.aio.ClientCallDetails):
        """Intercepts an asynchronous gRPC client call to inject the Elastic APM trace parent header.

        Args:
            method (Callable): The asynchronous gRPC method being intercepted.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.aio.ClientCallDetails): Details of the gRPC call.

        Returns:
            Any: The result of the intercepted gRPC method.

        Notes:
            - If Elastic APM is disabled, the interceptor does nothing and passes the call through.
            - If no trace parent header is available, the interceptor does nothing and passes the call through.
        """
        # Skip tracing if Elastic APM is disabled
        if not BaseConfig.global_config().ELASTIC_APM.IS_ENABLED:
            return await method(request_or_iterator, call_details)

        # Skip tracing if no trace parent header is available
        if not (trace_parent_id := elasticapm.get_trace_parent_header()):
            return await method(request_or_iterator, call_details)

        # Inject the trace parent header into the call details
        new_details = AsyncClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=[(TRACEPARENT_HEADER_NAME, f"{trace_parent_id}")],
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
        )

        # Execute the gRPC method with the updated call details
        return await method(request_or_iterator, new_details)
