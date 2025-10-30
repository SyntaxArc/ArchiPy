from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from concurrent import futures
from contextlib import AbstractAsyncContextManager
from http import HTTPStatus
from typing import Any, cast

from pydantic import ValidationError

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import (
    BaseError,
    InvalidArgumentError,
    UnavailableError,
    UnknownError,
)

try:
    import grpc
    from grpc.experimental.aio import server  # type: ignore[import-not-found]

    GRPC_APP = True
except ImportError:
    GRPC_APP = False

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.exceptions import RequestValidationError
    from fastapi.responses import JSONResponse
    from fastapi.routing import APIRoute
    from starlette.middleware.cors import CORSMiddleware

    FASTAPI_APP = True
except ImportError:
    FASTAPI_APP = False


class FastAPIExceptionHandler:
    """Handles various types of errors and converts them to appropriate JSON responses."""

    @staticmethod
    def create_error_response(exception: BaseError) -> JSONResponse:
        """Creates a standardized error response.

        Args:
            exception (BaseError): The exception to be converted into a response.

        Returns:
            JSONResponse: A JSON response containing the exception details.
        """
        BaseUtils.capture_exception(exception)
        # Default to internal server error if status code is not set
        status_code = (
            exception.http_status_code_value
            if exception.http_status_code_value
            else HTTPStatus.INTERNAL_SERVER_ERROR.value
        )
        return JSONResponse(status_code=status_code, content=exception.to_dict())

    @staticmethod
    async def custom_exception_handler(request: Request, exception: BaseError) -> JSONResponse:
        """Handles custom errors.

        Args:
            request (Request): The incoming request.
            exception (BaseError): The custom exception to handle.

        Returns:
            JSONResponse: A JSON response containing the exception details.
        """
        BaseUtils.capture_exception(exception)
        return FastAPIExceptionHandler.create_error_response(exception)

    @staticmethod
    async def generic_exception_handler(request: Request, exception: Exception) -> JSONResponse:
        """Handles generic errors.

        Args:
            request (Request): The incoming request.
            exception (Exception): The generic exception to handle.

        Returns:
            JSONResponse: A JSON response containing the exception details.
        """
        BaseUtils.capture_exception(exception)
        return FastAPIExceptionHandler.create_error_response(UnknownError())

    @staticmethod
    async def validation_exception_handler(
        request: Request,
        exception: ValidationError,
    ) -> JSONResponse:
        """Handles validation errors.

        Args:
            request (Request): The incoming request.
            exception (ValidationError): The validation exception to handle.

        Returns:
            JSONResponse: A JSON response containing the validation error details.
        """
        BaseUtils.capture_exception(exception)
        errors = BaseUtils.format_validation_errors(exception)
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content={"error": "VALIDATION_ERROR", "detail": errors},
        )


class FastAPIUtils:
    """Utility class for FastAPI configuration and setup."""

    @staticmethod
    def custom_generate_unique_id(route: APIRoute) -> str:
        """Generates a unique ID for API routes.

        Args:
            route (APIRoute): The route for which to generate a unique ID.

        Returns:
            str: A unique ID for the route.
        """
        return f"{route.tags[0]}-{route.name}" if route.tags else route.name

    @staticmethod
    def setup_sentry(config: BaseConfig) -> None:
        """Initializes Sentry configuration if enabled.

        Args:
            config (BaseConfig): The configuration object containing Sentry settings.
        """
        if not config.SENTRY.IS_ENABLED:
            return

        try:
            import sentry_sdk

            sentry_sdk.init(
                dsn=config.SENTRY.DSN,
                debug=config.SENTRY.DEBUG,
                release=config.SENTRY.RELEASE,
                sample_rate=config.SENTRY.SAMPLE_RATE,
                traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                environment=config.ENVIRONMENT,
            )
        except Exception:
            logging.exception("Failed to initialize Sentry")

    @staticmethod
    def setup_cors(app: FastAPI, config: BaseConfig) -> None:
        """Configures CORS middleware.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing CORS settings.
        """
        origins = [str(origin).strip("/") for origin in config.FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGINS]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_CREDENTIALS,
            allow_methods=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_METHODS,
            allow_headers=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_HEADERS,
        )

    @staticmethod
    def setup_elastic_apm(app: FastAPI, config: BaseConfig) -> None:
        """Configures Elastic APM if enabled.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing Elastic APM settings.
        """
        if not config.ELASTIC_APM.IS_ENABLED:
            return

        try:
            from elasticapm.contrib.starlette import ElasticAPM, make_apm_client

            apm_client = make_apm_client(config.ELASTIC_APM.model_dump())
            app.add_middleware(ElasticAPM, client=apm_client)  # type: ignore[arg-type]
        except Exception:
            logging.exception("Failed to initialize Elastic APM")

    @staticmethod
    def setup_exception_handlers(app: FastAPI) -> None:
        """Configures exception handlers for the FastAPI application.

        Args:
            app (FastAPI): The FastAPI application instance.
        """
        # While these handlers don't match the exact type signatures expected by FastAPI,
        # they are compatible in practice as they return JSONResponse objects.
        # We need to use a more general type cast to bypass the strict type checking.
        validation_handler = cast(
            Callable[[Request, Exception], Awaitable[Response]],
            FastAPIExceptionHandler.validation_exception_handler,
        )
        custom_handler = cast(
            Callable[[Request, Exception], Awaitable[Response]],
            FastAPIExceptionHandler.custom_exception_handler,
        )
        generic_handler = cast(
            Callable[[Request, Exception], Awaitable[Response]],
            FastAPIExceptionHandler.generic_exception_handler,
        )

        app.add_exception_handler(RequestValidationError, validation_handler)
        app.add_exception_handler(ValidationError, validation_handler)
        app.add_exception_handler(BaseError, custom_handler)
        app.add_exception_handler(Exception, generic_handler)


class AsyncGrpcAPIUtils:
    """async grpc api utilities."""

    @staticmethod
    def setup_trace_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures trace interceptor for gRPC server if tracing is enabled.

        Args:
            config (BaseConfig): The configuration object containing tracing settings.
            interceptors (List): List of gRPC interceptors to add the trace interceptor to.
        """
        if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
            return

        try:
            from archipy.helpers.interceptors.grpc.trace.server_interceptor import AsyncGrpcServerTraceInterceptor

            interceptors.append(AsyncGrpcServerTraceInterceptor())
        except Exception:
            logging.exception("Failed to initialize Trace Interceptor")

    @staticmethod
    def setup_metric_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures metric interceptor for gRPC server if Prometheus is enabled.

        Args:
            config (BaseConfig): The configuration object containing Prometheus settings.
            interceptors (List): List of gRPC interceptors to add the metric interceptor to.
        """
        if not config.PROMETHEUS.IS_ENABLED:
            return

        try:
            from prometheus_client import start_http_server

            from archipy.helpers.interceptors.grpc.metric.server_interceptor import AsyncGrpcServerMetricInterceptor

            start_http_server(config.PROMETHEUS.SERVER_PORT)
            interceptors.append(AsyncGrpcServerMetricInterceptor())

        except Exception:
            logging.exception("Failed to initialize Metric Interceptor")


class GrpcAPIUtils:
    """grpc api utilities."""

    @staticmethod
    def setup_trace_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures trace interceptor for gRPC server if tracing is enabled.

        Args:
            config (BaseConfig): The configuration object containing tracing settings.
            interceptors (List): List of gRPC interceptors to add the trace interceptor to.
        """
        if not config.ELASTIC_APM.IS_ENABLED and not config.SENTRY.IS_ENABLED:
            return

        try:
            from archipy.helpers.interceptors.grpc.trace.server_interceptor import GrpcServerTraceInterceptor

            interceptors.append(GrpcServerTraceInterceptor())
        except Exception:
            logging.exception("Failed to initialize Trace Interceptor")

    @staticmethod
    def setup_metric_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures metric interceptor for gRPC server if Prometheus is enabled.

        Args:
            config (BaseConfig): The configuration object containing Prometheus settings.
            interceptors (List): List of gRPC interceptors to add the metric interceptor to.
        """
        if not config.PROMETHEUS.IS_ENABLED:
            return

        try:
            from prometheus_client import start_http_server

            from archipy.helpers.interceptors.grpc.metric.server_interceptor import GrpcServerMetricInterceptor

            start_http_server(config.PROMETHEUS.SERVER_PORT)
            interceptors.append(GrpcServerMetricInterceptor())

        except Exception:
            logging.exception("Failed to initialize Metric Interceptor")


class AppUtils:
    """Utility class for creating and configuring FastAPI applications."""

    @classmethod
    def create_fastapi_app(
        cls,
        config: BaseConfig | None = None,
        *,
        configure_exception_handlers: bool = True,
        include_common_responses: bool = True,
        lifespan: Callable[..., AbstractAsyncContextManager] | None = None,
    ) -> FastAPI:
        """Create and configure a FastAPI application.

        Args:
            config (BaseConfig | None, optional): Custom configuration. If not provided, uses global config.
            configure_exception_handlers (bool, optional): Whether to configure exception handlers. Defaults to True.
            include_common_responses (bool, optional): Whether to configure common response definitions for all endpoints.
                                                Defaults to True.
            lifespan (Callable[..., AbstractAsyncContextManager] | None, optional): Custom lifespan context manager for the app.
                                                                          Defaults to None.

        Returns:
            FastAPI: The configured FastAPI application instance.
        """
        config = config or BaseConfig.global_config()

        # Define common responses for all endpoints
        common_responses = BaseUtils.get_fastapi_exception_responses(
            [UnknownError, UnavailableError, InvalidArgumentError],
        )
        app = FastAPI(
            title=config.FASTAPI.PROJECT_NAME,
            openapi_url=config.FASTAPI.OPENAPI_URL,
            generate_unique_id_function=FastAPIUtils.custom_generate_unique_id,
            swagger_ui_parameters=config.FASTAPI.SWAGGER_UI_PARAMS,
            docs_url=config.FASTAPI.DOCS_URL,
            redoc_url=config.FASTAPI.RE_DOC_URL,
            responses=cast(dict[int | str, Any], common_responses) if include_common_responses else None,
            lifespan=lifespan,
        )

        FastAPIUtils.setup_sentry(config)
        FastAPIUtils.setup_cors(app, config)
        FastAPIUtils.setup_elastic_apm(app, config)

        if configure_exception_handlers:
            FastAPIUtils.setup_exception_handlers(app)

        return app

    @classmethod
    def create_async_grpc_app(
        cls,
        config: BaseConfig,
        customized_interceptors: set[Any] | None = None,
        compression: grpc.Compression | None = None,
    ) -> server:
        """Create and configure an async gRPC application."""
        from archipy.helpers.interceptors.grpc.exception import AsyncGrpcServerExceptionInterceptor

        async_interceptors = [AsyncGrpcServerExceptionInterceptor()]

        AsyncGrpcAPIUtils.setup_trace_interceptor(config, async_interceptors)
        AsyncGrpcAPIUtils.setup_metric_interceptor(config, async_interceptors)

        app = server(
            futures.ThreadPoolExecutor(max_workers=config.GRPC.THREAD_WORKER_COUNT),
            interceptors=async_interceptors,
            compression=compression,
            options=config.GRPC.SERVER_OPTIONS_CONFIG_LIST,
            maximum_concurrent_rpcs=config.GRPC.MAX_CONCURRENT_RPCS,
        )
        if customized_interceptors:
            async_interceptors.extend(customized_interceptors)
        return app

    @classmethod
    def create_grpc_app(
        cls,
        config: BaseConfig,
        customized_interceptors: set[Any] | None = None,
        compression: grpc.Compression | None = None,
    ) -> grpc.Server:
        """Create and configure an async gRPC application."""
        from archipy.helpers.interceptors.grpc.exception import GrpcServerExceptionInterceptor

        interceptors = [GrpcServerExceptionInterceptor()]

        GrpcAPIUtils.setup_trace_interceptor(config, interceptors)
        GrpcAPIUtils.setup_metric_interceptor(config, interceptors)
        if customized_interceptors:
            interceptors.extend(customized_interceptors)

        app = grpc.server(
            futures.ThreadPoolExecutor(max_workers=config.GRPC.THREAD_WORKER_COUNT),
            interceptors=interceptors,  # type: ignore
            compression=compression,
            options=config.GRPC.SERVER_OPTIONS_CONFIG_LIST,
            maximum_concurrent_rpcs=config.GRPC.MAX_CONCURRENT_RPCS,
        )

        return app
