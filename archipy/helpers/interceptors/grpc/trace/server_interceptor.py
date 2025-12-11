import logging
from collections.abc import Callable
from typing import Any

import elasticapm
import grpc

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.utils.base_utils import BaseUtils

logger = logging.getLogger(__name__)


class GrpcServerTraceInterceptor(BaseGrpcServerInterceptor):
    """A gRPC server interceptor for tracing requests using Elastic APM and Sentry APM.

    This interceptor captures and traces gRPC server requests, enabling distributed tracing
    across services. It integrates with both Elastic APM and Sentry to monitor and log transactions.
    """

    def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts a gRPC server call to trace the request using Elastic APM and Sentry APM.

        Args:
            method (Callable): The gRPC method being intercepted.
            request (object): The request object passed to the method.
            context (grpc.ServicerContext): The context of the gRPC call.
            method_name_model (MethodName): The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Raises:
            Exception: If an exception occurs during the method execution, it is captured and logged.

        Notes:
            - If both Elastic APM and Sentry are disabled, the interceptor passes the call through.
            - Creates Sentry transactions for tracing gRPC server calls.
            - Handles Elastic APM distributed tracing with trace parent headers.
        """
        try:
            config = BaseConfig.global_config()

            # Skip tracing if both APM systems are disabled
            if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
                return method(request, context)

            # Convert metadata to a dictionary for easier access
            metadata_items = list(context.invocation_metadata())
            metadata_dict: dict[str, str] = {}
            for key, value in metadata_items:
                if isinstance(value, bytes):
                    metadata_dict[key] = value.decode("utf-8", errors="ignore")
                else:
                    metadata_dict[key] = str(value)

            # Initialize Sentry transaction if enabled
            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    # Initialize Sentry if not already done
                    current_hub = sentry_sdk.Hub.current
                    if not getattr(current_hub, "client", None):
                        sentry_sdk.init(
                            dsn=config.SENTRY.DSN,
                            debug=config.SENTRY.DEBUG,
                            release=config.SENTRY.RELEASE,
                            sample_rate=config.SENTRY.SAMPLE_RATE,
                            traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                            environment=getattr(config, "ENVIRONMENT", None),
                        )

                    sentry_transaction = sentry_sdk.start_transaction(
                        name=method_name_model.full_name,
                        op="grpc.server",
                        description=f"gRPC server call {method_name_model.full_name}",
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry transaction creation.")
                except Exception:
                    logger.exception("Failed to create Sentry transaction for gRPC server call")

            # Handle Elastic APM if enabled
            elastic_client: Any = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    # Get the Elastic APM client
                    elastic_client = elasticapm.get_client()
                    if not elastic_client:
                        elastic_client = elasticapm.Client(config.ELASTIC_APM.model_dump())
                    # Check if a trace parent header is present in the metadata
                    if parent := elasticapm.trace_parent_from_headers(metadata_dict):
                        # Start a transaction linked to the distributed trace
                        elastic_client.begin_transaction(transaction_type="request", trace_parent=parent)
                    else:
                        # Start a new transaction if no trace parent header is present
                        elastic_client.begin_transaction(transaction_type="request")
                except Exception:
                    logger.exception("Failed to initialize Elastic APM transaction")
                    elastic_client = None

            try:
                # Execute the gRPC method
                result = method(request, context)
            except Exception:
                # Mark transactions as failed and capture exception
                if sentry_transaction:
                    sentry_transaction.set_status("internal_error")
                if elastic_client is not None:
                    elastic_client.end_transaction(name=method_name_model.full_name, result="failure")
                raise
            else:
                # Mark transactions as successful
                if sentry_transaction:
                    sentry_transaction.set_status("ok")
                if elastic_client is not None:
                    elastic_client.end_transaction(name=method_name_model.full_name, result="success")
                return result
            finally:
                # Clean up Sentry transaction
                if sentry_transaction:
                    try:
                        sentry_transaction.__exit__(None, None, None)
                    except Exception:
                        logger.exception("Error closing Sentry transaction")

        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise


class AsyncGrpcServerTraceInterceptor(BaseAsyncGrpcServerInterceptor):
    """An async gRPC server interceptor for tracing requests using Elastic APM and Sentry APM.

    This interceptor captures and traces async gRPC server requests, enabling distributed tracing
    across services. It integrates with both Elastic APM and Sentry to monitor and log transactions.
    """

    async def intercept(
        self,
        method: Callable,
        request: object,
        context: grpc.aio.ServicerContext,
        method_name_model: MethodName,
    ) -> object:
        """Intercepts an async gRPC server call to trace the request using Elastic APM and Sentry APM.

        Args:
            method (Callable): The async gRPC method being intercepted.
            request (object): The request object passed to the method.
            context (grpc.aio.ServicerContext): The context of the async gRPC call.
            method_name_model (MethodName): The parsed method name containing package, service, and method components.

        Returns:
            object: The result of the intercepted gRPC method.

        Raises:
            Exception: If an exception occurs during the method execution, it is captured and logged.

        Notes:
            - If both Elastic APM and Sentry are disabled, the interceptor passes the call through.
            - Creates Sentry transactions for tracing async gRPC server calls.
            - Handles Elastic APM distributed tracing with trace parent headers.
        """
        try:
            config = BaseConfig.global_config()

            # Skip tracing if both APM systems are disabled
            if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
                return await method(request, context)

            # Convert metadata to a dictionary for easier access
            invocation_metadata = context.invocation_metadata()
            if invocation_metadata is not None:
                metadata_items = list(invocation_metadata)
            else:
                metadata_items = []
            metadata_dict: dict[str, str] = {}
            for key, value in metadata_items:
                if isinstance(value, bytes):
                    metadata_dict[key] = value.decode("utf-8", errors="ignore")
                else:
                    metadata_dict[key] = str(value)

            # Initialize Sentry transaction if enabled
            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    # Initialize Sentry if not already done
                    current_hub = sentry_sdk.Hub.current
                    if not getattr(current_hub, "client", None):
                        sentry_sdk.init(
                            dsn=config.SENTRY.DSN,
                            debug=config.SENTRY.DEBUG,
                            release=config.SENTRY.RELEASE,
                            sample_rate=config.SENTRY.SAMPLE_RATE,
                            traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                            environment=getattr(config, "ENVIRONMENT", None),
                        )

                    sentry_transaction = sentry_sdk.start_transaction(
                        name=method_name_model.full_name,
                        op="grpc.server",
                        description=f"Async gRPC server call {method_name_model.full_name}",
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry transaction creation.")
                except Exception:
                    logger.exception("Failed to create Sentry transaction for async gRPC server call")

            # Handle Elastic APM if enabled
            elastic_client: Any = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    # Get the Elastic APM client
                    elastic_client = elasticapm.get_client()
                    if not elastic_client:
                        elastic_client = elasticapm.Client(config.ELASTIC_APM.model_dump())

                    # Check if a trace parent header is present in the metadata
                    if parent := elasticapm.trace_parent_from_headers(metadata_dict):
                        # Start a transaction linked to the distributed trace
                        elastic_client.begin_transaction(transaction_type="request", trace_parent=parent)
                    else:
                        # Start a new transaction if no trace parent header is present
                        elastic_client.begin_transaction(transaction_type="request")
                except Exception:
                    logger.exception("Failed to initialize Elastic APM transaction")
                    elastic_client = None

            try:
                # Execute the async gRPC method
                result = await method(request, context)
            except Exception:
                # Mark transactions as failed and capture exception
                if sentry_transaction:
                    sentry_transaction.set_status("internal_error")
                if elastic_client is not None:
                    elastic_client.end_transaction(name=method_name_model.full_name, result="failure")
                raise
            else:
                # Mark transactions as successful
                if sentry_transaction:
                    sentry_transaction.set_status("ok")
                if elastic_client is not None:
                    elastic_client.end_transaction(name=method_name_model.full_name, result="success")
                return result
            finally:
                # Clean up Sentry transaction
                if sentry_transaction:
                    try:
                        sentry_transaction.__exit__(None, None, None)
                    except Exception:
                        logger.exception("Error closing Sentry transaction")

        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
