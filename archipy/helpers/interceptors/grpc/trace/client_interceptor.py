import logging
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

logger = logging.getLogger(__name__)


class GrpcClientTraceInterceptor(BaseGrpcClientInterceptor):
    """A gRPC client interceptor for tracing requests using Elastic APM and Sentry APM.

    This interceptor injects the Elastic APM trace parent header into gRPC client requests
    to enable distributed tracing across services. It also creates Sentry transactions
    to monitor the performance of gRPC calls.
    """

    def intercept(self, method: Callable, request_or_iterator: Any, call_details: grpc.ClientCallDetails) -> Any:
        """Intercepts a gRPC client call to inject the Elastic APM trace parent header and monitor performance with Sentry.

        Args:
            method (Callable): The gRPC method being intercepted.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.ClientCallDetails): Details of the gRPC call.

        Returns:
            Any: The result of the intercepted gRPC method.

        Notes:
            - If both Elastic APM and Sentry are disabled, the interceptor passes the call through.
            - Creates Sentry spans for tracing gRPC client calls.
            - Injects Elastic APM trace parent header when available.
        """
        config = BaseConfig.global_config()

        # Skip tracing if both APM systems are disabled
        if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
            return method(request_or_iterator, call_details)

        # Initialize Sentry span if enabled
        sentry_span = None
        if config.SENTRY.IS_ENABLED:
            try:
                import sentry_sdk

                sentry_span = sentry_sdk.start_span(
                    op="grpc.client",
                    description=f"gRPC client call to {call_details.method}",
                )
                sentry_span.__enter__()
            except ImportError:
                logger.debug("sentry_sdk is not installed, skipping Sentry span creation.")
            except Exception:
                logger.exception("Failed to create Sentry span for gRPC client call")

        # Handle Elastic APM trace propagation
        metadata = list(call_details.metadata or [])
        if config.ELASTIC_APM.IS_ENABLED:
            trace_parent_id = elasticapm.get_trace_parent_header()
            if trace_parent_id:
                metadata.append((TRACEPARENT_HEADER_NAME, f"{trace_parent_id}"))

        # Create new call details with updated metadata
        new_details = ClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
            compression=call_details.compression,
        )

        try:
            # Execute the gRPC method with the updated call details
            result = method(request_or_iterator, new_details)
        except Exception as e:
            # Mark Sentry span as failed and capture exception
            if sentry_span:
                sentry_span.set_status("internal_error")
                sentry_span.set_tag("error", True)
                sentry_span.set_data("exception", str(e))
            raise
        else:
            # Mark Sentry span as successful
            if sentry_span:
                sentry_span.set_status("ok")
            return result
        finally:
            # Clean up Sentry span
            if sentry_span:
                try:
                    sentry_span.__exit__(None, None, None)
                except Exception:
                    logger.exception("Error closing Sentry span")


class AsyncGrpcClientTraceInterceptor(BaseAsyncGrpcClientInterceptor):
    """An asynchronous gRPC client interceptor for tracing requests using Elastic APM and Sentry APM.

    This interceptor injects the Elastic APM trace parent header into asynchronous gRPC client requests
    to enable distributed tracing across services. It also creates Sentry spans for monitoring performance.
    """

    async def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.aio.ClientCallDetails,
    ) -> Any:
        """Intercepts an asynchronous gRPC client call to inject the Elastic APM trace parent header and monitor with Sentry.

        Args:
            method (Callable): The asynchronous gRPC method being intercepted.
            request_or_iterator (Any): The request or request iterator.
            call_details (grpc.aio.ClientCallDetails): Details of the gRPC call.

        Returns:
            Any: The result of the intercepted gRPC method.

        Notes:
            - If both Elastic APM and Sentry are disabled, the interceptor passes the call through.
            - Creates Sentry spans for tracing async gRPC client calls.
            - Injects Elastic APM trace parent header when available.
        """
        config = BaseConfig.global_config()

        # Skip tracing if both APM systems are disabled
        if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
            return await method(request_or_iterator, call_details)

        # Initialize Sentry span if enabled
        sentry_span = None
        if config.SENTRY.IS_ENABLED:
            try:
                import sentry_sdk

                sentry_span = sentry_sdk.start_span(
                    op="grpc.client",
                    description=f"Async gRPC client call to {call_details.method}",
                )
                sentry_span.__enter__()
            except ImportError:
                logger.debug("sentry_sdk is not installed, skipping Sentry span creation.")
            except Exception:
                logger.exception("Failed to create Sentry span for async gRPC client call")

        # Handle Elastic APM trace propagation
        metadata = list(call_details.metadata or [])
        if config.ELASTIC_APM.IS_ENABLED:
            trace_parent_id = elasticapm.get_trace_parent_header()
            if trace_parent_id:
                metadata.append((TRACEPARENT_HEADER_NAME, f"{trace_parent_id}"))

        # Create new call details with updated metadata
        new_details = AsyncClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
        )

        try:
            # Execute the async gRPC method with the updated call details
            result = await method(request_or_iterator, new_details)
        except Exception as e:
            # Mark Sentry span as failed and capture exception
            if sentry_span:
                sentry_span.set_status("internal_error")
                sentry_span.set_tag("error", True)
                sentry_span.set_data("exception", str(e))
            raise
        else:
            # Mark Sentry span as successful
            if sentry_span:
                sentry_span.set_status("ok")
            return result
        finally:
            # Clean up Sentry span
            if sentry_span:
                try:
                    sentry_span.__exit__(None, None, None)
                except Exception:
                    logger.exception("Error closing Sentry span")
