from __future__ import annotations

import logging
from concurrent import futures
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import (
    BaseError,
    ConfigurationError,
    InvalidArgumentError,
    UnavailableError,
    UnknownError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable
    from contextlib import AbstractAsyncContextManager

    from fastapi.routing import APIRoute
    from grpc import aio as grpc_aio
    from grpc.aio import Server as GrpcAioServer

    CreateGrpcServerType = Callable[..., GrpcAioServer]
else:
    GrpcAioServer = Any
    CreateGrpcServerType = Any

logger = logging.getLogger(__name__)

try:
    import grpc
    from grpc import aio as grpc_aio

    create_grpc_server: CreateGrpcServerType = grpc_aio.server
    GRPC_APP = True
except ImportError:
    GRPC_APP = False
    grpc_aio: Any = None
    create_grpc_server: CreateGrpcServerType | None = None

try:
    from fastapi import FastAPI, Request, Response
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from fastapi.responses import JSONResponse
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
        status_code = exception.http_status or HTTPStatus.INTERNAL_SERVER_ERROR.value
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
        tags = getattr(route, "tags", [])
        return f"{tags[0]}-{route.name}" if tags else route.name

    @staticmethod
    def setup_cors(app: FastAPI, config: BaseConfig) -> None:
        """Configures CORS middleware.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing CORS settings.
        """
        origins = [str(origin).strip("/") for origin in config.FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGINS]
        # Use app.add_middleware with CORSMiddleware directly
        # CORSMiddleware is compatible with FastAPI's middleware system at runtime
        app.add_middleware(
            CORSMiddleware,  # type: ignore[arg-type]
            allow_origins=origins,
            allow_credentials=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_CREDENTIALS,
            allow_methods=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_METHODS,
            allow_headers=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_HEADERS,
            allow_origin_regex=config.FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGIN_REGEX,
            expose_headers=config.FASTAPI.CORS_MIDDLEWARE_EXPOSE_HEADERS,
            max_age=config.FASTAPI.CORS_MIDDLEWARE_MAX_AGE,
        )

    @staticmethod
    def setup_gzip(app: FastAPI, config: BaseConfig) -> None:
        """Configures GZip response compression middleware if enabled.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing GZip middleware settings.
        """
        if not config.FASTAPI.GZIP_MIDDLEWARE_IS_ENABLED:
            return

        app.add_middleware(
            GZipMiddleware,  # type: ignore[arg-type]
            minimum_size=config.FASTAPI.GZIP_MIDDLEWARE_MINIMUM_SIZE,
            compresslevel=config.FASTAPI.GZIP_MIDDLEWARE_COMPRESSLEVEL,
        )

    @staticmethod
    def setup_trusted_host(app: FastAPI, config: BaseConfig) -> None:
        """Configures TrustedHost middleware if enabled.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing TrustedHost middleware settings.
        """
        if not config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED:
            return

        allowed_hosts = config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS
        if not allowed_hosts:
            logger.warning(
                "TrustedHost middleware enabled but TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS is empty; skipping",
            )
            return

        app.add_middleware(
            TrustedHostMiddleware,  # type: ignore[arg-type]
            allowed_hosts=allowed_hosts,
            www_redirect=config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_WWW_REDIRECT,
        )

    @staticmethod
    def setup_https_redirect(app: FastAPI, config: BaseConfig) -> None:
        """Configures HTTPS redirect middleware if enabled.

        Args:
            app (FastAPI): The FastAPI application instance.
            config (BaseConfig): The configuration object containing HTTPS redirect middleware settings.
        """
        if not config.FASTAPI.HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED:
            return

        app.add_middleware(HTTPSRedirectMiddleware)  # type: ignore[arg-type]

    @staticmethod
    def _fastapi_otel_instrument_kwargs(config: BaseConfig) -> dict[str, Any] | None:
        """Build FastAPIInstrumentor kwargs with real or NoOp providers.

        Returns:
            Kwargs for ``instrument_app``, or ``None`` when instrumentation
            should be skipped (no real providers available).
        """
        from opentelemetry.metrics import NoOpMeterProvider
        from opentelemetry.trace import NoOpTracerProvider

        from archipy.helpers.utils.otel_utils import OtelUtils

        instrument_kwargs: dict[str, Any] = {}
        has_real_provider = False

        if config.OTEL.TRACES_ENABLED:
            tracer_provider = OtelUtils.tracer_provider()
            if tracer_provider is None:
                logger.warning(
                    "OTEL traces enabled but no tracer provider is available; skipping FastAPI trace instrumentation",
                )
                instrument_kwargs["tracer_provider"] = NoOpTracerProvider()
            else:
                instrument_kwargs["tracer_provider"] = tracer_provider
                has_real_provider = True
        else:
            instrument_kwargs["tracer_provider"] = NoOpTracerProvider()

        if config.OTEL.METRICS_ENABLED:
            meter_provider = OtelUtils.meter_provider()
            if meter_provider is None:
                logger.warning(
                    "OTEL metrics enabled but no meter provider is available; skipping FastAPI metric instrumentation",
                )
                instrument_kwargs["meter_provider"] = NoOpMeterProvider()
            else:
                instrument_kwargs["meter_provider"] = meter_provider
                has_real_provider = True
        else:
            instrument_kwargs["meter_provider"] = NoOpMeterProvider()

        if not has_real_provider:
            return None

        if config.OTEL.FASTAPI_EXCLUDED_URLS is not None:
            instrument_kwargs["excluded_urls"] = config.OTEL.FASTAPI_EXCLUDED_URLS
        return instrument_kwargs

    @staticmethod
    def setup_otel(app: FastAPI, config: BaseConfig) -> None:
        """Configure OpenTelemetry instrumentation for a FastAPI application.

        Only passes providers for enabled signals. Never passes ``None`` providers
        (contrib instrumentors would fall back to global OTEL providers). Disabled
        signals receive explicit NoOp providers.

        Args:
            app: The FastAPI application instance.
            config: Application configuration containing OTel settings.
        """
        if not config.OTEL.IS_ENABLED:
            return
        if not config.OTEL.TRACES_ENABLED and not config.OTEL.METRICS_ENABLED:
            return

        from archipy.helpers.utils.otel_utils import OTEL_FASTAPI_INSTALL_HINT, OtelUtils

        try:
            OtelUtils.init_otel_if_needed(config)
            if OtelUtils.import_failed():
                return

            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            instrument_kwargs = FastAPIUtils._fastapi_otel_instrument_kwargs(config)
            if instrument_kwargs is None:
                return

            FastAPIInstrumentor.instrument_app(app, **instrument_kwargs)
        except ImportError:
            logger.warning("%s", OTEL_FASTAPI_INSTALL_HINT)
        except Exception:
            logger.exception("Failed to initialize OpenTelemetry for FastAPI")

    @staticmethod
    def setup_exception_handlers(app: FastAPI) -> None:
        """Configures exception handlers for the FastAPI application.

        Args:
            app (FastAPI): The FastAPI application instance.
        """

        # These handlers return JSONResponse which is a subclass of Response,
        # so they are compatible with FastAPI's exception handler requirements.
        # We create wrapper functions to match the expected signature
        async def validation_wrapper(request: Request, exception: Exception) -> Response:
            if isinstance(exception, ValidationError):
                return await FastAPIExceptionHandler.validation_exception_handler(request, exception)
            if isinstance(exception, RequestValidationError):
                # RequestValidationError has errors() method that returns validation errors
                # Format them directly since RequestValidationError has a similar structure
                BaseUtils.capture_exception(exception)
                formatted_errors = []
                for error in exception.errors():
                    error_dict = {
                        "field": ".".join(str(x) for x in error.get("loc", [])),
                        "message": error.get("msg", ""),
                        "value": str(error.get("input", "")),
                    }
                    if "type" in error:
                        error_dict["type"] = error["type"]
                    formatted_errors.append(error_dict)
                return JSONResponse(
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                    content={"error": "VALIDATION_ERROR", "detail": formatted_errors},
                )
            return await FastAPIExceptionHandler.generic_exception_handler(request, exception)

        async def custom_wrapper(request: Request, exception: Exception) -> Response:
            if isinstance(exception, BaseError):
                return await FastAPIExceptionHandler.custom_exception_handler(request, exception)
            return await FastAPIExceptionHandler.generic_exception_handler(request, exception)

        async def generic_wrapper(request: Request, exception: Exception) -> Response:
            return await FastAPIExceptionHandler.generic_exception_handler(request, exception)

        app.add_exception_handler(RequestValidationError, validation_wrapper)
        app.add_exception_handler(ValidationError, validation_wrapper)
        app.add_exception_handler(BaseError, custom_wrapper)
        app.add_exception_handler(Exception, generic_wrapper)


def _install_otel_grpc_interceptor(
    config: BaseConfig,
    interceptors: list,
    *,
    async_mode: bool,
) -> None:
    """Insert an OpenTelemetry gRPC server interceptor at position 0.

    Requires a concrete ArchiPy tracer provider. Does not pass ``None`` (which
    would fall back to the global OTEL provider).

    Args:
        config: Application configuration containing OTel settings.
        interceptors: Mutable list of gRPC interceptors.
        async_mode: When True, install the aio server interceptor.
    """
    if not config.OTEL.IS_ENABLED or not config.OTEL.TRACES_ENABLED:
        return

    from archipy.helpers.utils.otel_utils import OTEL_GRPC_INSTALL_HINT, OtelUtils

    try:
        OtelUtils.init_otel_if_needed(config)
        if OtelUtils.import_failed():
            return

        tracer_provider = OtelUtils.tracer_provider()
        if tracer_provider is None:
            logger.warning(
                "OTEL traces enabled but no tracer provider is available; skipping gRPC OTel interceptor",
            )
            return

        if async_mode:
            from opentelemetry.instrumentation.grpc import aio_server_interceptor

            otel_interceptor = aio_server_interceptor(tracer_provider=tracer_provider)
        else:
            from opentelemetry.instrumentation.grpc import server_interceptor

            otel_interceptor = server_interceptor(tracer_provider=tracer_provider)

        interceptors.insert(0, otel_interceptor)
    except ImportError:
        logger.warning("%s", OTEL_GRPC_INSTALL_HINT)
    except Exception:
        mode = "async gRPC" if async_mode else "gRPC"
        logger.exception("Failed to initialize OpenTelemetry interceptor for %s", mode)


class AsyncGrpcAPIUtils:
    """async grpc api utilities."""

    @staticmethod
    def setup_otel_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configure OpenTelemetry server interceptor for an async gRPC server.

        Inserts the OTel interceptor at position 0 so it wraps later interceptors.

        Args:
            config: Application configuration containing OTel settings.
            interceptors: Mutable list of gRPC interceptors.
        """
        _install_otel_grpc_interceptor(config, interceptors, async_mode=True)

    @staticmethod
    def setup_rate_limit_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures rate-limit interceptor for async gRPC server when enabled.

        Args:
            config (BaseConfig): The configuration object containing gRPC rate-limit settings.
            interceptors (List): List of gRPC interceptors to add the rate-limit interceptor to.
        """
        if not config.GRPC_RATE_LIMIT.IS_ENABLED:
            return

        try:
            from archipy.helpers.interceptors.grpc.rate_limit.grpc_rate_limit_interceptor import (
                AsyncGrpcServerRateLimitInterceptor,
            )

            interceptors.append(AsyncGrpcServerRateLimitInterceptor(rate_limit_config=config.GRPC_RATE_LIMIT))
        except Exception:
            logger.exception("Failed to initialize Rate Limit Interceptor")


class GrpcAPIUtils:
    """grpc api utilities."""

    @staticmethod
    def setup_otel_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configure OpenTelemetry server interceptor for a sync gRPC server.

        Inserts the OTel interceptor at position 0 so it wraps later interceptors.

        Args:
            config: Application configuration containing OTel settings.
            interceptors: Mutable list of gRPC interceptors.
        """
        _install_otel_grpc_interceptor(config, interceptors, async_mode=False)

    @staticmethod
    def setup_rate_limit_interceptor(config: BaseConfig, interceptors: list) -> None:
        """Configures rate-limit interceptor for gRPC server when enabled.

        Args:
            config (BaseConfig): The configuration object containing gRPC rate-limit settings.
            interceptors (List): List of gRPC interceptors to add the rate-limit interceptor to.
        """
        if not config.GRPC_RATE_LIMIT.IS_ENABLED:
            return

        try:
            from archipy.helpers.interceptors.grpc.rate_limit.grpc_rate_limit_interceptor import (
                GrpcServerRateLimitInterceptor,
            )

            interceptors.append(GrpcServerRateLimitInterceptor(rate_limit_config=config.GRPC_RATE_LIMIT))
        except Exception:
            logger.exception("Failed to initialize Rate Limit Interceptor")


class AppUtils:
    """Utility class for creating and configuring FastAPI applications."""

    @staticmethod
    def _compose_otel_lifespan(
        config: BaseConfig,
        lifespan: Callable[..., AbstractAsyncContextManager] | None,
    ) -> Callable[..., AbstractAsyncContextManager] | None:
        """Wrap a FastAPI lifespan so OTel force-flushes on exit.

        Args:
            config: Application configuration.
            lifespan: Optional caller-provided lifespan context manager factory.

        Returns:
            A lifespan factory that preserves the user lifespan and runs
            ``force_flush`` afterward, or ``None`` when OTel is off and no user
            lifespan was provided. Provider shutdown remains on process atexit.
        """
        if not config.OTEL.IS_ENABLED:
            return lifespan

        from contextlib import asynccontextmanager

        from archipy.helpers.utils.otel_utils import OtelUtils

        @asynccontextmanager
        async def otel_lifespan(app: FastAPI) -> AsyncIterator[None]:
            try:
                if lifespan is not None:
                    async with lifespan(app):
                        yield
                else:
                    yield
            finally:
                # Flush only — do not shutdown here. Multiple apps / TestClient
                # share process-wide OtelUtils; full shutdown stays on atexit.
                try:
                    OtelUtils.force_flush()
                except Exception:
                    logger.debug("Error during OTel force_flush in FastAPI lifespan", exc_info=True)

        return otel_lifespan

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
        # Convert dict[int, ...] to dict[int | str, ...] for FastAPI compatibility
        responses_dict: dict[int | str, dict[str, Any]] | None = None
        if include_common_responses and common_responses:
            responses_dict = dict(common_responses.items())

        resolved_lifespan = cls._compose_otel_lifespan(config, lifespan)
        app = FastAPI(
            title=config.FASTAPI.PROJECT_NAME,
            openapi_url=config.FASTAPI.OPENAPI_URL,
            generate_unique_id_function=FastAPIUtils.custom_generate_unique_id,
            swagger_ui_parameters=config.FASTAPI.SWAGGER_UI_PARAMS,
            docs_url=config.FASTAPI.DOCS_URL,
            redoc_url=config.FASTAPI.RE_DOC_URL,
            responses=responses_dict,
            lifespan=resolved_lifespan,
        )

        FastAPIUtils.setup_cors(app, config)
        FastAPIUtils.setup_gzip(app, config)
        FastAPIUtils.setup_https_redirect(app, config)
        FastAPIUtils.setup_trusted_host(app, config)
        FastAPIUtils.setup_otel(app, config)

        if configure_exception_handlers:
            FastAPIUtils.setup_exception_handlers(app)

        return app

    @classmethod
    def create_async_grpc_app(
        cls,
        config: BaseConfig,
        customized_interceptors: set[Any] | None = None,
        compression: grpc.Compression | None = None,
    ) -> GrpcAioServer:
        """Create and configure an async gRPC application."""
        from archipy.helpers.interceptors.grpc.exception import AsyncGrpcServerExceptionInterceptor

        async_interceptors = [AsyncGrpcServerExceptionInterceptor()]

        # OTel inserts at 0 → order: OTel → exception → rate-limit → custom
        AsyncGrpcAPIUtils.setup_otel_interceptor(config, async_interceptors)
        AsyncGrpcAPIUtils.setup_rate_limit_interceptor(config, async_interceptors)

        if customized_interceptors:
            async_interceptors.extend(customized_interceptors)

        if create_grpc_server is None:
            raise ConfigurationError(operation="import", reason="grpc_aio_extra_required")
        return create_grpc_server(
            futures.ThreadPoolExecutor(max_workers=config.GRPC.THREAD_WORKER_COUNT),
            interceptors=async_interceptors,
            compression=compression,
            options=config.GRPC.SERVER_OPTIONS_CONFIG_LIST,
            maximum_concurrent_rpcs=config.GRPC.MAX_CONCURRENT_RPCS,
        )

    @classmethod
    def create_grpc_app(
        cls,
        config: BaseConfig,
        customized_interceptors: set[Any] | None = None,
        compression: grpc.Compression | None = None,
    ) -> grpc.Server:
        """Create and configure a synchronous gRPC server."""
        from archipy.helpers.interceptors.grpc.exception import GrpcServerExceptionInterceptor

        interceptors: list[grpc.ServerInterceptor] = [GrpcServerExceptionInterceptor()]

        # OTel inserts at 0 → order: OTel → exception → rate-limit → custom
        GrpcAPIUtils.setup_otel_interceptor(config, interceptors)
        GrpcAPIUtils.setup_rate_limit_interceptor(config, interceptors)
        if customized_interceptors:
            interceptors.extend(customized_interceptors)

        return grpc.server(
            futures.ThreadPoolExecutor(max_workers=config.GRPC.THREAD_WORKER_COUNT),
            interceptors=interceptors,
            compression=compression,
            options=config.GRPC.SERVER_OPTIONS_CONFIG_LIST,
            maximum_concurrent_rpcs=config.GRPC.MAX_CONCURRENT_RPCS,
        )
