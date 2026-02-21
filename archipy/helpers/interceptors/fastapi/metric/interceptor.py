from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, ClassVar

from prometheus_client import Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.base_utils import BaseUtils

if TYPE_CHECKING:
    from fastapi import Request, Response
    from starlette.types import ASGIApp


class FastAPIMetricInterceptor(BaseHTTPMiddleware):
    """A FastAPI interceptor for collecting and reporting metrics using Prometheus.

    This interceptor measures the response time of HTTP requests and records it in a Prometheus histogram.
    It also tracks the number of active requests using a Prometheus gauge.
    The interceptor captures errors and logs them for monitoring purposes.
    """

    ZERO_TO_ONE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 1000 for i in range(0, 1000, 5)]
    ONE_TO_FIVE_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(100, 500, 20)]
    FIVE_TO_THIRTY_SECONDS_BUCKETS: ClassVar[list[float]] = [i / 100 for i in range(500, 3000, 50)]
    TOTAL_BUCKETS: ClassVar[list[float]] = (
        ZERO_TO_ONE_SECONDS_BUCKETS + ONE_TO_FIVE_SECONDS_BUCKETS + FIVE_TO_THIRTY_SECONDS_BUCKETS + [float("inf")]
    )

    RESPONSE_TIME_SECONDS: ClassVar[Histogram] = Histogram(
        "fastapi_response_time_seconds",
        "Time spent processing HTTP request",
        labelnames=("method", "status_code", "path_template"),
        buckets=TOTAL_BUCKETS,
    )

    ACTIVE_REQUESTS: ClassVar[Gauge] = Gauge(
        "fastapi_active_requests",
        "Number of active HTTP requests",
        labelnames=("method", "path_template"),
    )

    _path_template_cache: ClassVar[dict[str, str]] = {}

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the FastAPI metric interceptor.

        Args:
            app (ASGIApp): The ASGI application to wrap.
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Intercept HTTP requests to measure response time and track active requests.

        Args:
            request (Request): The incoming HTTP request.
            call_next (Callable[[Request], Awaitable[Response]]): The next interceptor or endpoint to call.

        Returns:
            Response: The HTTP response from the endpoint.

        Raises:
            Exception: If an exception occurs during request processing, it is captured and re-raised.
        """
        if not BaseConfig.global_config().PROMETHEUS.IS_ENABLED:
            return await call_next(request)

        path_template = self._get_path_template(request)
        method = request.method

        self.ACTIVE_REQUESTS.labels(method=method, path_template=path_template).inc()

        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exception:
            BaseUtils.capture_exception(exception)
            raise
        else:
            return response
        finally:
            duration = time.time() - start_time
            self.RESPONSE_TIME_SECONDS.labels(
                method=method,
                status_code=status_code,
                path_template=path_template,
            ).observe(duration)
            self.ACTIVE_REQUESTS.labels(method=method, path_template=path_template).dec()

    def _get_path_template(self, request: Request) -> str:
        """Extract path template from request by matching against app routes with in-memory caching.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            str: Path template (e.g., /users/{id}) or raw path if no route found.
        """
        path = request.url.path
        method = request.method
        cache_key = f"{method}:{path}"

        if cache_key in self._path_template_cache:
            return self._path_template_cache[cache_key]

        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                path_template = route.path
                self._path_template_cache[cache_key] = path_template
                return path_template

        self._path_template_cache[cache_key] = path
        return path
