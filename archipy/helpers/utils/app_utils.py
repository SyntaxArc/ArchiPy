import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.dtos.exception_dto import ExceptionDetailDTO
from archipy.models.exceptions import (
    CommonsBaseException,
    InvalidArgumentException,
    UnavailableException,
    UnknownException,
)


class FastAPIExceptionHandler:
    """Handles various types of exceptions and converts them to appropriate JSON responses"""

    @staticmethod
    def create_error_response(exception: CommonsBaseException) -> JSONResponse:
        """Creates a standardized error response"""
        BaseUtils.capture_exception(exception)
        return JSONResponse(status_code=exception.http_status_code, content=exception.to_dict())

    @staticmethod
    async def custom_exception_handler(request: Request, exception: CommonsBaseException) -> JSONResponse:
        """Handle custom exceptions"""
        return FastAPIExceptionHandler.create_error_response(exception)

    # TODO Remove http_exception_handler
    @staticmethod
    async def http_exception_handler(request: Request, exception: HTTPException) -> JSONResponse:
        detail = ExceptionDetailDTO(
            code="TODO_REMOVE_ME",
            http_status=exception.status_code,
            message_en=exception.detail,
            message_fa=exception.detail,
        )
        exception = CommonsBaseException(detail, lang="en")
        return FastAPIExceptionHandler.create_error_response(exception)

    @staticmethod
    async def generic_exception_handler(request: Request, exception: Exception) -> JSONResponse:
        return FastAPIExceptionHandler.create_error_response(UnknownException())

    @staticmethod
    async def validation_exception_handler(request: Request, exception: ValidationError) -> JSONResponse:
        errors = []
        for error in exception.errors():
            errors.append(
                {
                    "field": ".".join(str(x) for x in error["loc"]),
                    "message": error["msg"],
                    "value": str(error.get("input", "")),
                },
            )

        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content={"error": "VALIDATION_ERROR", "detail": errors},
        )


class FastAPIUtils:
    """Utility class for FastAPI configuration and setup"""

    @staticmethod
    def custom_generate_unique_id(route: APIRoute) -> str:
        """Generate a unique ID for API routes."""
        return f"{route.tags[0]}-{route.name}" if route.tags else route.name

    @staticmethod
    def setup_sentry(config: BaseConfig) -> None:
        """Initialize Sentry configuration if enabled."""
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
        except Exception as e:
            logging.exception(f"Failed to initialize Sentry: {e}")

    @staticmethod
    def setup_cors(app: FastAPI, config: BaseConfig) -> None:
        """Configure CORS middleware."""
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
        """Configure Elastic APM if enabled."""
        if not config.ELASTIC_APM.IS_ENABLED:
            return

        try:
            import elasticapm
            from elasticapm.contrib.starlette import ElasticAPM

            apm_client = elasticapm.get_client()
            app.add_middleware(ElasticAPM, client=apm_client)
        except Exception as e:
            logging.exception(f"Failed to initialize Elastic APM: {e}")

    @staticmethod
    def setup_exception_handlers(app: FastAPI) -> None:
        """Configure exception handlers."""
        app.add_exception_handler(RequestValidationError, FastAPIExceptionHandler.validation_exception_handler)
        app.add_exception_handler(ValidationError, FastAPIExceptionHandler.validation_exception_handler)
        app.add_exception_handler(CommonsBaseException, FastAPIExceptionHandler.custom_exception_handler)
        app.add_exception_handler(HTTPException, FastAPIExceptionHandler.http_exception_handler)
        app.add_exception_handler(Exception, FastAPIExceptionHandler.generic_exception_handler)


class AppUtils:

    @classmethod
    def create_fastapi_app(cls, config: BaseConfig | None = None, configure_exception_handlers: bool = True) -> FastAPI:
        """
        Create and configure FastAPI application.

        Args:
            config: Optional custom configuration. If not provided, uses global config.
            configure_exception_handlers: Whether to configure exception handlers.
        """
        config = config or BaseConfig.global_config()

        # Define common responses for all endpoints
        common_responses = BaseUtils.get_fastapi_exception_responses(
            [UnknownException, UnavailableException, InvalidArgumentException],
        )
        app = FastAPI(
            title=config.FASTAPI.PROJECT_NAME,
            openapi_url=config.FASTAPI.OPENAPI_URL,
            generate_unique_id_function=FastAPIUtils.custom_generate_unique_id,
            swagger_ui_parameters=config.FASTAPI.SWAGGER_UI_PARAMS,
            docs_url=config.FASTAPI.DOCS_URL,
            redocs_url=config.FASTAPI.RE_DOCS_URL,
            responses=common_responses,
        )

        FastAPIUtils.setup_sentry(config)
        FastAPIUtils.setup_cors(app, config)
        FastAPIUtils.setup_elastic_apm(app, config)

        if configure_exception_handlers:
            FastAPIUtils.setup_exception_handlers(app)

        return app
