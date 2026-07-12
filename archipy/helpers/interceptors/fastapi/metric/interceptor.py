from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from prometheus_client import Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.base_utils import BaseUtils

if TYPE_CHECKING:
    from fastapi import Request, Response
    from starlette.types import ASGIApp

try:
    from fastapi.routing import iter_route_contexts
except ImportError:
    iter_route_contexts: Callable[..., Any] | None = None


def _flatten_routes(routes: list[Any]) -> Iterator[Any]:
    """Yield routes in the shape expected by Starlette's route matching.

    FastAPI 0.137 changed include_router() to keep nested routers as
    _IncludedRouter entries. Those entries do not expose ``path`` directly, so
    they need to be expanded into effective route contexts before matching.

    FastAPI >= 0.137.2 provides iter_route_contexts() for that expansion. For
    0.137.0 and 0.137.1, use _IncludedRouter.effective_route_contexts(). Older
    FastAPI versions and plain Starlette already expose matchable route objects.
    """
    if any(hasattr(route, "effective_route_contexts") for route in routes):
        if iter_route_contexts is not None:
            yield from iter_route_contexts(routes)
            return
        for route in routes:
            if hasattr(route, "effective_route_contexts"):
                yield from route.effective_route_contexts()
            else:
                yield route
        return

    for route in routes:
        yield route


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

        for route in _flatten_routes(request.app.routes):
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                path_template = route.path
                self._path_template_cache[cache_key] = path_template
                return path_template

        self._path_template_cache[cache_key] = path
        return path
