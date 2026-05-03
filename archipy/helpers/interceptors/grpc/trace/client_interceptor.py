"""gRPC client trace interceptors (Elastic APM + Sentry propagation)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

import grpc

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.client_interceptor import (
    AsyncClientCallDetails,
    BaseAsyncGrpcClientInterceptor,
    BaseGrpcClientInterceptor,
    ClientCallDetails,
    _swap_args,
)
from archipy.helpers.utils.tracing_utils import TracingUtils

logger = logging.getLogger(__name__)

_TRequest = TypeVar("_TRequest")


def _metadata_has_traceparent_key(metadata: list[tuple[str, str | bytes]]) -> bool:
    try:
        from elasticapm.conf import constants
    except ImportError:
        return False

    name = constants.TRACEPARENT_HEADER_NAME.lower()
    return any(bool(item) and str(item[0]).lower() == name for item in metadata)


def _streaming_client_metadata(
    call_details: grpc.ClientCallDetails | grpc.aio.ClientCallDetails,
    config: BaseConfig,
) -> list[tuple[str, str | bytes]]:
    """Headers for streaming RPCs: transaction-level traceparent + Sentry headers (no span)."""
    meta: list[tuple[str, str | bytes]] = list(cast("Any", call_details.metadata or []))
    if config.ELASTIC_APM.IS_ENABLED and not _metadata_has_traceparent_key(meta):
        try:
            import elasticapm
            from elasticapm.conf import constants

            trace_parent_id = elasticapm.get_trace_parent_header()
            if trace_parent_id:
                meta.append((constants.TRACEPARENT_HEADER_NAME, f"{trace_parent_id}"))
        except ImportError:
            logger.debug("elasticapm is not installed, skipping Elastic traceparent for streaming gRPC.")

    return TracingUtils.inject_outbound_metadata(meta, None, include_sentry=config.SENTRY.IS_ENABLED)


def _destination_extra(method: str) -> dict[str, Any]:
    """Span ``extra`` for gRPC client calls (APM destination; port unknown until channel introspection)."""
    return {
        "destination": {
            "address": "unknown",
            "port": 0,
            "service": {"name": "grpc", "resource": method, "type": "external"},
        },
    }


class GrpcClientTraceInterceptor(BaseGrpcClientInterceptor):
    """gRPC client interceptor: Elastic APM external span + W3C and Sentry trace headers."""

    def intercept(self, method: Callable, request_or_iterator: Any, call_details: grpc.ClientCallDetails) -> Any:
        """Intercept a unary-style client call with full APM span and trace propagation."""
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return method(request_or_iterator, call_details)

        TracingUtils.init_tracing_if_needed(config)

        if not config.ELASTIC_APM.IS_ENABLED:
            return self._intercept_sentry_headers_only(method, request_or_iterator, call_details, config)

        try:
            import elasticapm
            from elasticapm.traces import DroppedSpan
        except ImportError:
            logger.debug("elasticapm is not installed, using header-only tracing for gRPC client.")
            return self._intercept_sentry_headers_only(method, request_or_iterator, call_details, config)

        extra = _destination_extra(call_details.method)
        with elasticapm.capture_span(
            call_details.method,
            span_type="external",
            span_subtype="grpc",
            extra=extra,
            leaf=True,
        ) as apm_span:
            if not apm_span or isinstance(apm_span, DroppedSpan):
                return self._intercept_sentry_headers_only(method, request_or_iterator, call_details, config)
            metadata = TracingUtils.inject_outbound_metadata(
                call_details.metadata,
                apm_span,
                include_sentry=config.SENTRY.IS_ENABLED,
            )
            new_details = ClientCallDetails(
                method=call_details.method,
                timeout=call_details.timeout,
                metadata=metadata,
                credentials=call_details.credentials,
                wait_for_ready=call_details.wait_for_ready,
                compression=call_details.compression,
            )
            try:
                return method(request_or_iterator, new_details)
            except grpc.RpcError:
                apm_span.set_failure()
                raise

    def _intercept_sentry_headers_only(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.ClientCallDetails,
        config: BaseConfig,
    ) -> Any:
        metadata = TracingUtils.inject_outbound_metadata(
            call_details.metadata,
            None,
            include_sentry=config.SENTRY.IS_ENABLED,
        )
        new_details = ClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
            compression=call_details.compression,
        )
        return method(request_or_iterator, new_details)

    def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Propagate trace headers only (no APM span) for unary-stream RPCs."""
        return self._intercept_streaming(_swap_args(continuation), request, client_call_details)

    def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Any], Any],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Any,
    ) -> Any:
        """Propagate trace headers only (no APM span) for stream-unary RPCs."""
        return self._intercept_streaming(_swap_args(continuation), request_iterator, client_call_details)

    def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.ClientCallDetails, Any], Any],
        client_call_details: grpc.ClientCallDetails,
        request_iterator: Any,
    ) -> Any:
        """Propagate trace headers only (no APM span) for stream-stream RPCs."""
        return self._intercept_streaming(_swap_args(continuation), request_iterator, client_call_details)

    def _intercept_streaming(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.ClientCallDetails,
    ) -> Any:
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return method(request_or_iterator, call_details)
        TracingUtils.init_tracing_if_needed(config)
        metadata = _streaming_client_metadata(call_details, config)
        new_details = ClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
            compression=call_details.compression,
        )
        return method(request_or_iterator, new_details)


class AsyncGrpcClientTraceInterceptor(BaseAsyncGrpcClientInterceptor):
    """Async gRPC client interceptor: Elastic APM external span + W3C and Sentry trace headers."""

    async def intercept(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.aio.ClientCallDetails,
    ) -> Any:
        """Intercept an async unary-style client call with full APM span and trace propagation."""
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return await method(request_or_iterator, call_details)

        TracingUtils.init_tracing_if_needed(config)

        if not config.ELASTIC_APM.IS_ENABLED:
            return await self._intercept_sentry_headers_only_async(method, request_or_iterator, call_details, config)

        try:
            import elasticapm
            from elasticapm.traces import DroppedSpan
        except ImportError:
            logger.debug("elasticapm is not installed, using header-only tracing for async gRPC client.")
            return await self._intercept_sentry_headers_only_async(method, request_or_iterator, call_details, config)

        extra = _destination_extra(call_details.method)
        async with elasticapm.async_capture_span(
            call_details.method,
            span_type="external",
            span_subtype="grpc",
            extra=extra,
            leaf=True,
        ) as apm_span:
            if not apm_span or isinstance(apm_span, DroppedSpan):
                return await self._intercept_sentry_headers_only_async(
                    method,
                    request_or_iterator,
                    call_details,
                    config,
                )
            metadata = TracingUtils.inject_outbound_metadata(
                call_details.metadata,
                apm_span,
                include_sentry=config.SENTRY.IS_ENABLED,
            )
            new_details = AsyncClientCallDetails(
                method=call_details.method,
                timeout=call_details.timeout,
                metadata=metadata,
                credentials=call_details.credentials,
                wait_for_ready=call_details.wait_for_ready,
            )
            try:
                return await method(request_or_iterator, new_details)
            except grpc.RpcError:
                apm_span.set_failure()
                raise

    async def _intercept_sentry_headers_only_async(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.aio.ClientCallDetails,
        config: BaseConfig,
    ) -> Any:
        metadata = TracingUtils.inject_outbound_metadata(
            call_details.metadata,
            None,
            include_sentry=config.SENTRY.IS_ENABLED,
        )
        new_details = AsyncClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
        )
        return await method(request_or_iterator, new_details)

    async def intercept_unary_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, _TRequest], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request: _TRequest,
    ) -> Any:
        """Propagate trace headers only (no APM span) for async unary-stream RPCs."""
        return await self._intercept_streaming_async(_swap_args(continuation), request, client_call_details)

    async def intercept_stream_unary(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> Any:
        """Propagate trace headers only (no APM span) for async stream-unary RPCs."""
        return await self._intercept_streaming_async(_swap_args(continuation), request_iterator, client_call_details)

    async def intercept_stream_stream(
        self,
        continuation: Callable[[grpc.aio.ClientCallDetails, Any], Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request_iterator: Any,
    ) -> Any:
        """Propagate trace headers only (no APM span) for async stream-stream RPCs."""
        return await self._intercept_streaming_async(_swap_args(continuation), request_iterator, client_call_details)

    async def _intercept_streaming_async(
        self,
        method: Callable,
        request_or_iterator: Any,
        call_details: grpc.aio.ClientCallDetails,
    ) -> Any:
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return await method(request_or_iterator, call_details)
        TracingUtils.init_tracing_if_needed(config)
        metadata = _streaming_client_metadata(call_details, config)
        new_details = AsyncClientCallDetails(
            method=call_details.method,
            timeout=call_details.timeout,
            metadata=metadata,
            credentials=call_details.credentials,
            wait_for_ready=call_details.wait_for_ready,
        )
        return await method(request_or_iterator, new_details)
