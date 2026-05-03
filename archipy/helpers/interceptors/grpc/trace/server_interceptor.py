"""gRPC server trace interceptors (Elastic APM + Sentry)."""

from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, cast

import grpc

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
    _get_factory_and_method,
    parse_method_name,
)
from archipy.helpers.utils.tracing_utils import TracingUtils

logger = logging.getLogger(__name__)


def _invocation_metadata_to_dict(metadata_items: Iterable[Any]) -> dict[str, str]:
    """Normalize gRPC invocation metadata to a string dict for tracers."""
    metadata_dict: dict[str, str] = {}
    for item in metadata_items:
        if hasattr(item, "key") and hasattr(item, "value"):
            key, value = item.key, item.value
        elif isinstance(item, tuple) and len(item) >= 2:
            key, value = item[0], item[1]
        else:
            continue
        if isinstance(value, bytes):
            metadata_dict[str(key)] = value.decode("utf-8", errors="ignore")
        else:
            metadata_dict[str(key)] = str(value)
    return metadata_dict


class _ServicerContextWrapper:
    """Wraps ``ServicerContext`` to map ``set_code`` / ``abort`` to APM and Sentry outcomes."""

    def __init__(self, wrapped: Any, sentry_transaction: Any | None) -> None:
        self._wrapped = wrapped
        self._sentry_transaction = sentry_transaction

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def set_code(self, code: grpc.StatusCode) -> None:
        """Forward to the real context after updating Elastic and Sentry outcomes."""
        try:
            import elasticapm
            from elasticapm.conf.constants import OUTCOME

            if TracingUtils.grpc_status_indicates_success(code):
                elasticapm.set_transaction_outcome(OUTCOME.SUCCESS)
            else:
                elasticapm.set_transaction_outcome(OUTCOME.FAILURE)
        except ImportError:
            pass
        if self._sentry_transaction is not None:
            self._sentry_transaction.set_status(
                "ok" if TracingUtils.grpc_status_indicates_success(code) else "internal_error",
            )
        return self._wrapped.set_code(code)

    def abort(self, code: grpc.StatusCode, details: str) -> None:
        """Forward to the real context after marking failure."""
        try:
            import elasticapm
            from elasticapm.conf.constants import OUTCOME

            elasticapm.set_transaction_outcome(OUTCOME.FAILURE)
        except ImportError:
            pass
        if self._sentry_transaction is not None:
            self._sentry_transaction.set_status("internal_error")
        return self._wrapped.abort(code, details)


class _AsyncServicerContextWrapper(_ServicerContextWrapper):
    """Async variant of ``_ServicerContextWrapper``.

    ``grpc.aio.ServicerContext.abort`` is a coroutine; calling it without
    ``await`` silently drops the abort in the async server case.  This
    subclass overrides ``abort`` as an ``async def`` so callers inside
    async servicer methods can properly await it.
    """

    async def abort(self, code: grpc.StatusCode, details: str) -> None:  # type: ignore[override]  # ty: ignore[invalid-method-override]
        """Await the real async context ``abort`` after marking failure."""
        try:
            import elasticapm
            from elasticapm.conf.constants import OUTCOME

            elasticapm.set_transaction_outcome(OUTCOME.FAILURE)
        except ImportError:
            pass
        if self._sentry_transaction is not None:
            self._sentry_transaction.set_status("internal_error")
        await self._wrapped.abort(code, details)


class GrpcServerTraceInterceptor(BaseGrpcServerInterceptor):
    """Sync gRPC server interceptor: unary-unary only; Elastic transaction + Sentry trace continuation."""

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler | None],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        """Skip tracing for streaming RPCs (matches ``elasticapm`` gRPC server interceptor)."""
        next_handler = continuation(handler_call_details)
        if next_handler is None:
            return None
        if next_handler.request_streaming or next_handler.response_streaming:
            return next_handler

        handler_factory, next_handler_method = _get_factory_and_method(next_handler)

        def invoke_intercept_method(request: object, context: grpc.ServicerContext) -> object:
            method_name_model = parse_method_name(handler_call_details.method)
            return self.intercept(next_handler_method, request, context, method_name_model)

        return handler_factory(
            invoke_intercept_method,
            request_deserializer=next_handler.request_deserializer,
            response_serializer=next_handler.response_serializer,
        )

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Run unary-unary handler inside Elastic and Sentry transactions."""
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return method(request, context)

        TracingUtils.init_tracing_if_needed(config)

        metadata_items = list(context.invocation_metadata())
        metadata_dict = _invocation_metadata_to_dict(metadata_items)

        sentry_transaction = None
        if config.SENTRY.IS_ENABLED:
            try:
                import sentry_sdk

                _, sentry_headers = TracingUtils.extract_inbound_trace(metadata_dict)
                sentry_transaction = sentry_sdk.continue_trace(
                    sentry_headers,
                    op="grpc.server",
                    name=method_name_model.full_name,
                )
                sentry_transaction.__enter__()
            except ImportError:
                logger.debug("sentry_sdk is not installed, skipping Sentry transaction for gRPC server.")
            except Exception:
                logger.exception("Failed to start Sentry transaction for gRPC server call")

        elastic_client: Any = None
        if config.ELASTIC_APM.IS_ENABLED:
            try:
                import elasticapm

                elastic_client = elasticapm.get_client()
                if elastic_client is None:
                    logger.warning("Elastic APM client is not initialized; skipping APM transaction for gRPC.")
                elif (parent := elasticapm.trace_parent_from_headers(metadata_dict)) is not None:
                    elastic_client.begin_transaction(transaction_type="request", trace_parent=parent)
                else:
                    elastic_client.begin_transaction(transaction_type="request")
            except ImportError:
                logger.debug("elasticapm is not installed, skipping Elastic APM transaction for gRPC server.")
            except Exception:
                logger.exception("Failed to begin Elastic APM transaction for gRPC server call")
                elastic_client = None

        wrapped_ctx = _ServicerContextWrapper(context, sentry_transaction)

        exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
        try:
            result = method(request, wrapped_ctx)
        except Exception as exception:
            exc_info = (type(exception), exception, exception.__traceback__)
            if sentry_transaction is not None:
                sentry_transaction.set_status("internal_error")
            if elastic_client is not None:
                try:
                    import elasticapm

                    elasticapm.set_transaction_outcome(TracingUtils.outcome_for_exception(exception))
                except ImportError:
                    pass
                elastic_client.end_transaction(name=method_name_model.full_name, result="failure")
            raise
        else:
            try:
                import elasticapm
                from elasticapm.conf.constants import OUTCOME

                elasticapm.set_transaction_outcome(OUTCOME.SUCCESS, override=False)
            except ImportError:
                pass
            if sentry_transaction is not None and sentry_transaction.status is None:
                sentry_transaction.set_status("ok")
            if elastic_client is not None:
                elastic_client.end_transaction(name=method_name_model.full_name, result="success")
            return result
        finally:
            if sentry_transaction is not None:
                try:
                    sentry_transaction.__exit__(exc_info[0], exc_info[1], exc_info[2])
                except Exception:
                    logger.exception("Error closing Sentry transaction for gRPC server call")


class AsyncGrpcServerTraceInterceptor(BaseAsyncGrpcServerInterceptor):
    """Async gRPC server interceptor: unary-unary only; Elastic transaction + Sentry trace continuation."""

    async def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], Awaitable[grpc.RpcMethodHandler]],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Skip tracing for streaming RPCs (matches ``elasticapm`` async gRPC server interceptor)."""
        next_handler = await continuation(handler_call_details)
        if next_handler is None:
            # grpc stubs omit None; continuation may return no handler for unknown methods.
            return cast("grpc.RpcMethodHandler", None)
        if next_handler.request_streaming or next_handler.response_streaming:
            return next_handler

        handler_factory, next_handler_method = _get_factory_and_method(next_handler)

        async def invoke_intercept_method(request: object, context: grpc.aio.ServicerContext) -> object:
            method_name_model = parse_method_name(handler_call_details.method)
            return await self.intercept(next_handler_method, request, context, method_name_model)

        return handler_factory(
            invoke_intercept_method,
            request_deserializer=getattr(next_handler, "request_deserializer", None),
            response_serializer=getattr(next_handler, "response_serializer", None),
        )

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Run async unary-unary handler inside Elastic and Sentry transactions."""
        config = BaseConfig.global_config()
        if not TracingUtils.is_tracing_enabled(config):
            return await method(request, context)

        TracingUtils.init_tracing_if_needed(config)

        invocation_metadata = context.invocation_metadata()
        if invocation_metadata is not None:
            metadata_items = list(invocation_metadata)
        else:
            metadata_items = []
        metadata_dict = _invocation_metadata_to_dict(metadata_items)

        sentry_transaction = None
        if config.SENTRY.IS_ENABLED:
            try:
                import sentry_sdk

                _, sentry_headers = TracingUtils.extract_inbound_trace(metadata_dict)
                sentry_transaction = sentry_sdk.continue_trace(
                    sentry_headers,
                    op="grpc.server",
                    name=method_name_model.full_name,
                )
                sentry_transaction.__enter__()
            except ImportError:
                logger.debug("sentry_sdk is not installed, skipping Sentry transaction for async gRPC server.")
            except Exception:
                logger.exception("Failed to start Sentry transaction for async gRPC server call")

        elastic_client: Any = None
        if config.ELASTIC_APM.IS_ENABLED:
            try:
                import elasticapm

                elastic_client = elasticapm.get_client()
                if elastic_client is None:
                    logger.warning("Elastic APM client is not initialized; skipping APM transaction for gRPC.")
                elif (parent := elasticapm.trace_parent_from_headers(metadata_dict)) is not None:
                    elastic_client.begin_transaction(transaction_type="request", trace_parent=parent)
                else:
                    elastic_client.begin_transaction(transaction_type="request")
            except ImportError:
                logger.debug("elasticapm is not installed, skipping Elastic APM transaction for async gRPC server.")
            except Exception:
                logger.exception("Failed to begin Elastic APM transaction for async gRPC server call")
                elastic_client = None

        wrapped_ctx = _AsyncServicerContextWrapper(context, sentry_transaction)

        exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
        try:
            result = method(request, wrapped_ctx)
            if inspect.isawaitable(result):
                result = await result
        except Exception as exception:
            exc_info = (type(exception), exception, exception.__traceback__)
            if sentry_transaction is not None:
                sentry_transaction.set_status("internal_error")
            if elastic_client is not None:
                try:
                    import elasticapm

                    elasticapm.set_transaction_outcome(TracingUtils.outcome_for_exception(exception))
                except ImportError:
                    pass
                elastic_client.end_transaction(name=method_name_model.full_name, result="failure")
            raise
        else:
            try:
                import elasticapm
                from elasticapm.conf.constants import OUTCOME

                elasticapm.set_transaction_outcome(OUTCOME.SUCCESS, override=False)
            except ImportError:
                pass
            if sentry_transaction is not None and sentry_transaction.status is None:
                sentry_transaction.set_status("ok")
            if elastic_client is not None:
                elastic_client.end_transaction(name=method_name_model.full_name, result="success")
            return result
        finally:
            if sentry_transaction is not None:
                try:
                    sentry_transaction.__exit__(exc_info[0], exc_info[1], exc_info[2])
                except Exception:
                    logger.exception("Error closing Sentry transaction for async gRPC server call")
