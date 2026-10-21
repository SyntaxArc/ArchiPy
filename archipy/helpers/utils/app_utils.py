"""Application bootstrap and lifecycle utilities."""

from __future__ import annotations

import logging
import re
from concurrent import futures
from typing import TYPE_CHECKING, Any

from archipy.configs.base_config import BaseConfig
from archipy.models.errors import (
    ConfigurationError,
    InvalidArgumentError,
    UnavailableError,
    UnknownError,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Sequence, Set as AbstractSet
    from contextlib import AbstractAsyncContextManager

    from fastapi.routing import APIRoute
    from fastapi.telemetry import TelemetryConfig
    from grpc.aio import Server as GrpcAioServer
    from opentelemetry.sdk._logs import LoggerProvider
    from starlette.types import Scope

    from archipy.helpers.utils._otel.provider_types import OwnedMeterProvider, OwnedTracerProvider

    CreateGrpcServerType = Callable[..., GrpcAioServer]
else:
    GrpcAioServer = Any  # Runtime stand-in for the annotation-only alias; the type checker never sees this branch
    CreateGrpcServerType = (
        Any  # Runtime stand-in for the annotation-only alias; the type checker never sees this branch
    )

logger = logging.getLogger(__name__)

try:
    import grpc
    from grpc import aio as grpc_aio

    create_grpc_server: CreateGrpcServerType = grpc_aio.server
    GRPC_APP = True
except ImportError:
    GRPC_APP = False
    grpc_aio = None
    create_grpc_server: CreateGrpcServerType | None = None

try:
    from fastapi import FastAPI
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from starlette.middleware.cors import CORSMiddleware

    FASTAPI_APP = True
except ImportError:
    FASTAPI_APP = False


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
            CORSMiddleware,
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
            GZipMiddleware,
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
            TrustedHostMiddleware,
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

        app.add_middleware(HTTPSRedirectMiddleware)

    @staticmethod
    def _fastapi_otel_excluded(patterns: str | None) -> Callable[[Scope], bool] | None:
        """Build a native-telemetry ``exclude`` callable from comma-separated URL patterns.

        Args:
            patterns: Comma-separated regular expressions searched against the request path.

        Returns:
            A callable receiving the ASGI scope, or ``None`` when no patterns are configured.
        """
        compiled = [re.compile(item.strip()) for item in (patterns or "").split(",") if item.strip()]
        if not compiled:
            return None

        def exclude(scope: Scope) -> bool:
            path = scope.get("path", "")
            return any(pattern.search(path) for pattern in compiled)

        return exclude

    @staticmethod
    def _resolve_otel_providers(
        config: BaseConfig,
    ) -> tuple[OwnedTracerProvider | None, OwnedMeterProvider | None, LoggerProvider | None]:
        """Return the tracer, meter and logger providers FastAPI should use.

        A provider is ``None`` when its signal is disabled or ``OtelUtils`` has none; an enabled
        signal without a provider logs a warning.

        Args:
            config: Application configuration containing OTel settings.

        Returns:
            Tuple of ``(tracer_provider, meter_provider, logger_provider)``.
        """
        from archipy.helpers.utils.otel_utils import OtelUtils

        tracer_provider = OtelUtils.tracer_provider() if config.OTEL.TRACES_ENABLED else None
        meter_provider = OtelUtils.meter_provider() if config.OTEL.METRICS_ENABLED else None
        logger_provider = OtelUtils.logger_provider() if config.OTEL.FASTAPI_LOGS_ENABLED else None
        if config.OTEL.TRACES_ENABLED and tracer_provider is None:
            logger.warning("OTEL traces enabled but no tracer provider is available; skipping FastAPI tracing")
        if config.OTEL.METRICS_ENABLED and meter_provider is None:
            logger.warning("OTEL metrics enabled but no meter provider is available; skipping FastAPI metrics")
        if config.OTEL.FASTAPI_LOGS_ENABLED and logger_provider is None:
            logger.warning("OTEL FastAPI logs enabled but no logger provider is available; skipping FastAPI logs")
        return tracer_provider, meter_provider, logger_provider

    @staticmethod
    def build_otel_telemetry_config(config: BaseConfig) -> TelemetryConfig:
        """Build the ``telemetry`` argument for ``FastAPI(...)`` from ArchiPy OTel settings.

        FastAPI instruments requests natively, so the config must be passed to the constructor.
        Providers come from ``OtelUtils`` and are never replaced by globals. Signals without a
        real provider are disabled. ``auto_configure`` is off because ArchiPy owns the exporters.
        FastAPI log records (which carry stack traces) are opt-in via ``OTEL.FASTAPI_LOGS_ENABLED``.

        Args:
            config: Application configuration containing OTel settings.

        Returns:
            Telemetry settings for ``FastAPI(telemetry=...)``.
        """
        from archipy.helpers.utils.otel_utils import OTEL_FASTAPI_INSTALL_HINT, OtelUtils

        disabled: TelemetryConfig = {
            "tracing": False,
            "metrics": False,
            "logs": False,
            "operation_spans": False,
            "auto_configure": False,
        }
        if not config.OTEL.IS_ENABLED:
            return disabled

        try:
            OtelUtils.init_otel_if_needed(config)
            if OtelUtils.import_failed():
                return disabled
            tracer_provider, meter_provider, logger_provider = FastAPIUtils._resolve_otel_providers(config)
        except ImportError:
            logger.warning("%s", OTEL_FASTAPI_INSTALL_HINT)
            return disabled
        # Observability is optional: a failed init must not stop the app.
        except Exception:
            logger.exception("Failed to initialize OpenTelemetry for FastAPI")
            return disabled

        telemetry: TelemetryConfig = {
            "tracing": tracer_provider is not None,
            "metrics": meter_provider is not None,
            "logs": logger_provider is not None,
            "operation_spans": tracer_provider is not None and config.OTEL.FASTAPI_OPERATION_SPANS_ENABLED,
            "auto_configure": False,
        }
        if tracer_provider is not None:
            telemetry["tracer_provider"] = tracer_provider
        if meter_provider is not None:
            telemetry["meter_provider"] = meter_provider
        if logger_provider is not None:
            telemetry["logger_provider"] = logger_provider
        exclude = FastAPIUtils._fastapi_otel_excluded(config.OTEL.FASTAPI_EXCLUDED_URLS)
        if exclude is not None:
            telemetry["exclude"] = exclude
        return telemetry


def _prepend_otel_grpc_metrics_interceptor(interceptors: list, *, async_mode: bool) -> None:
    """Prepend the ArchiPy gRPC metrics interceptor when a meter provider exists."""
    from archipy.helpers.utils.otel_utils import OtelUtils

    if OtelUtils.meter_provider() is None:
        logger.warning(
            "OTEL metrics enabled but no meter provider is available; skipping gRPC metrics interceptor",
        )
        return
    if async_mode:
        from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
            AsyncGrpcServerOtelMetricsInterceptor,
        )

        interceptors.insert(0, AsyncGrpcServerOtelMetricsInterceptor())
        return
    from archipy.helpers.interceptors.grpc.otel_metrics.server_interceptor import (
        GrpcServerOtelMetricsInterceptor,
    )

    interceptors.insert(0, GrpcServerOtelMetricsInterceptor())


def _prepend_otel_grpc_traces_interceptor(interceptors: list, *, async_mode: bool) -> None:
    """Prepend the contrib gRPC traces interceptor when a tracer provider exists."""
    from archipy.helpers.utils.otel_utils import OtelUtils

    tracer_provider = OtelUtils.tracer_provider()
    if tracer_provider is None:
        logger.warning(
            "OTEL traces enabled but no tracer provider is available; skipping gRPC OTel interceptor",
        )
        return
    if async_mode:
        from opentelemetry.instrumentation.grpc import aio_server_interceptor

        interceptors.insert(0, aio_server_interceptor(tracer_provider=tracer_provider))
        return
    from opentelemetry.instrumentation.grpc import server_interceptor

    interceptors.insert(0, server_interceptor(tracer_provider=tracer_provider))


def _install_otel_grpc_interceptor(
    config: BaseConfig,
    interceptors: list,
    *,
    async_mode: bool,
) -> None:
    """Insert OpenTelemetry gRPC server interceptors at the front of the list.

    Installs the contrib traces interceptor when traces are enabled and an
    ArchiPy metrics interceptor when metrics are enabled. Does not pass
    ``None`` providers (which would fall back to the global OTEL provider).

    Args:
        config: Application configuration containing OTel settings.
        interceptors: Mutable list of gRPC interceptors.
        async_mode: When True, install aio server interceptors.
    """
    if not config.OTEL.IS_ENABLED:
        return
    if not config.OTEL.TRACES_ENABLED and not config.OTEL.METRICS_ENABLED:
        return

    from archipy.helpers.utils.otel_utils import OTEL_GRPC_INSTALL_HINT, OtelUtils

    try:
        OtelUtils.init_otel_if_needed(config)
        if OtelUtils.import_failed():
            return

        # Insert metrics first so it ends up outer after traces prepend (or alone).
        # Final order with both: traces → metrics → exception → rate-limit → custom.
        if config.OTEL.METRICS_ENABLED:
            _prepend_otel_grpc_metrics_interceptor(interceptors, async_mode=async_mode)
        if config.OTEL.TRACES_ENABLED:
            _prepend_otel_grpc_traces_interceptor(interceptors, async_mode=async_mode)
    except ImportError:
        logger.warning("%s", OTEL_GRPC_INSTALL_HINT)
    # Optional interceptor: a failed init must not stop server startup.
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
        # A fail-open limiter must not stop startup; a fail-closed one must not leave the server unprotected.
        except Exception:
            logger.exception("Failed to initialize Rate Limit Interceptor")
            if config.GRPC_RATE_LIMIT.FAIL_CLOSED:
                raise


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
        # A fail-open limiter must not stop startup; a fail-closed one must not leave the server unprotected.
        except Exception:
            logger.exception("Failed to initialize Rate Limit Interceptor")
            if config.GRPC_RATE_LIMIT.FAIL_CLOSED:
                raise


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
        async def otel_lifespan(app: FastAPI) -> AsyncGenerator[None]:
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
                # Best-effort flush on shutdown: never block app teardown.
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
            configure_exception_handlers (bool, optional): Whether to configure exception handlers.
                Defaults to True.
            include_common_responses (bool, optional): Whether to configure common response definitions
                for all endpoints. Defaults to True.
            lifespan (Callable[..., AbstractAsyncContextManager] | None, optional): Custom lifespan
                context manager for the app. Defaults to None.

        Returns:
            FastAPI: The configured FastAPI application instance.
        """
        from archipy.helpers.errors.fastapi import get_fastapi_exception_responses, setup_exception_handlers

        config = config or BaseConfig.global_config()

        # Define common responses for all endpoints
        common_responses = get_fastapi_exception_responses(
            [UnknownError, UnavailableError, InvalidArgumentError],
        )
        # Convert dict[int, ...] to dict[int | str, ...] for FastAPI compatibility
        responses_dict: dict[int | str, dict[str, object]] | None = None
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
            telemetry=FastAPIUtils.build_otel_telemetry_config(config),
        )

        FastAPIUtils.setup_cors(app, config)
        FastAPIUtils.setup_gzip(app, config)
        FastAPIUtils.setup_https_redirect(app, config)
        FastAPIUtils.setup_trusted_host(app, config)

        if configure_exception_handlers:
            setup_exception_handlers(app)

        return app

    @staticmethod
    def _ordered_interceptors(customized_interceptors: Sequence[object] | AbstractSet[object]) -> list[object]:
        """Return custom interceptors in the order they run.

        Pass a ``list`` or ``tuple`` to control the order (first runs outermost). A ``set`` is still accepted for
        backward compatibility, but its iteration order is arbitrary.

        Args:
            customized_interceptors: The interceptors supplied by the caller.

        Returns:
            list[object]: The interceptors as a list.
        """
        return list(customized_interceptors)

    @classmethod
    def create_async_grpc_app(
        cls,
        config: BaseConfig,
        customized_interceptors: Sequence[object] | AbstractSet[object] | None = None,
        compression: grpc.Compression | None = None,
        *,
        validation_errors_as_internal: bool = False,
    ) -> GrpcAioServer:
        """Create and configure an async gRPC application.

        Args:
            config: The application config.
            customized_interceptors: Extra interceptors appended after the built-in ones.
            compression: The server compression.
            validation_errors_as_internal: Report a pydantic ``ValidationError`` raised by a handler as INTERNAL
                instead of INVALID_ARGUMENT. Defaults to False.
        """
        from archipy.helpers.errors.grpc import GrpcExceptionInterceptor

        # grpc-stubs want grpc.aio.ServerInterceptor items, which the GrpcExceptionInterceptor factory and the
        # untyped custom interceptors are not declared as
        async_interceptors: list[Any] = [
            GrpcExceptionInterceptor(aio=True, validation_errors_as_internal=validation_errors_as_internal),
        ]

        # OTel inserts at 0 → order: OTel → exception → rate-limit → custom
        AsyncGrpcAPIUtils.setup_otel_interceptor(config, async_interceptors)
        AsyncGrpcAPIUtils.setup_rate_limit_interceptor(config, async_interceptors)

        if customized_interceptors:
            async_interceptors.extend(cls._ordered_interceptors(customized_interceptors))

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
        customized_interceptors: Sequence[object] | AbstractSet[object] | None = None,
        compression: grpc.Compression | None = None,
        *,
        validation_errors_as_internal: bool = False,
    ) -> grpc.Server:
        """Create and configure a synchronous gRPC server.

        Args:
            config: The application config.
            customized_interceptors: Extra interceptors appended after the built-in ones.
            compression: The server compression.
            validation_errors_as_internal: Report a pydantic ``ValidationError`` raised by a handler as INTERNAL
                instead of INVALID_ARGUMENT. Defaults to False.
        """
        from archipy.helpers.errors.grpc import GrpcExceptionInterceptor

        # grpc-stubs want grpc.ServerInterceptor items, which the GrpcExceptionInterceptor factory and the
        # untyped custom interceptors are not declared as
        interceptors: list[Any] = [
            GrpcExceptionInterceptor(validation_errors_as_internal=validation_errors_as_internal),
        ]

        # OTel inserts at 0 → order: OTel → exception → rate-limit → custom
        GrpcAPIUtils.setup_otel_interceptor(config, interceptors)
        GrpcAPIUtils.setup_rate_limit_interceptor(config, interceptors)
        if customized_interceptors:
            interceptors.extend(cls._ordered_interceptors(customized_interceptors))

        return grpc.server(
            futures.ThreadPoolExecutor(max_workers=config.GRPC.THREAD_WORKER_COUNT),
            interceptors=interceptors,
            compression=compression,
            options=config.GRPC.SERVER_OPTIONS_CONFIG_LIST,
            maximum_concurrent_rpcs=config.GRPC.MAX_CONCURRENT_RPCS,
        )
