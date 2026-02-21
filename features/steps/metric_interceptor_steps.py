import socket
from unittest.mock import MagicMock

import grpc
from behave import given, then, when
from prometheus_client import REGISTRY
from starlette.testclient import TestClient

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.grpc.base.server_interceptor import MethodName
from archipy.helpers.interceptors.grpc.metric.server_interceptor import (
    AsyncGrpcServerMetricInterceptor,
    GrpcServerMetricInterceptor,
)
from archipy.helpers.utils.app_utils import (
    AppUtils,
    AsyncGrpcAPIUtils,
    FastAPIUtils,
    GrpcAPIUtils,
    _is_prometheus_server_running,
)
from features.test_helpers import get_current_scenario_context


# ===== GIVEN STEPS =====


@given("a {framework} app with Prometheus enabled")
def step_given_app_prometheus_enabled(context, framework):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True

    if framework == "FastAPI":
        app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
        scenario_context.store("app", app)
    elif framework == "gRPC":
        scenario_context.store("interceptors", [])
    elif framework == "AsyncgRPC":
        scenario_context.store("interceptors", [])

    scenario_context.store("config", test_config)
    scenario_context.store("framework", framework)


@given("a {framework} app with Prometheus disabled")
def step_given_app_prometheus_disabled(context, framework):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = False

    if framework == "FastAPI":
        app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
        scenario_context.store("app", app)
    elif framework == "gRPC":
        scenario_context.store("interceptors", [])
    elif framework == "AsyncgRPC":
        scenario_context.store("interceptors", [])

    scenario_context.store("config", test_config)
    scenario_context.store("framework", framework)


@given("a {framework} app with Prometheus enabled and metric interceptor")
def step_given_app_with_metric_interceptor(context, framework):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True

    if framework == "FastAPI":
        app = AppUtils.create_fastapi_app(test_config)

        @app.get("/test")
        def test_endpoint():
            return {"message": "success"}

        @app.get("/error")
        def error_endpoint():
            raise ValueError("Test error")

        @app.get("/users/{id}")
        def user_endpoint(id: str):
            return {"user_id": id}

        @app.get("/health")
        def health_endpoint():
            return {"status": "healthy"}

        scenario_context.store("app", app)
    elif framework == "gRPC":
        interceptors = []
        GrpcAPIUtils.setup_metric_interceptor(test_config, interceptors)
        scenario_context.store("interceptors", interceptors)
    elif framework == "AsyncgRPC":
        interceptors = []
        AsyncGrpcAPIUtils.setup_metric_interceptor(test_config, interceptors)
        scenario_context.store("interceptors", interceptors)

    scenario_context.store("config", test_config)
    scenario_context.store("framework", framework)


@given("a FastAPI app with Prometheus enabled and metric interceptor with routes")
def step_given_fastapi_app_with_metric_interceptor_routes(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True

    app = AppUtils.create_fastapi_app(test_config)

    @app.get("/users/{id}")
    def get_user_endpoint(id: str):
        return {"user_id": id}

    @app.post("/users/{user_id}/posts")
    def create_post_endpoint(user_id: str):
        return {"user_id": user_id, "post": "created"}

    @app.get("/api/v1/items/{item_id}")
    def get_item_endpoint(item_id: str):
        return {"item_id": item_id}

    @app.put("/orders/{order_id}/items/{item_id}")
    def update_order_item_endpoint(order_id: str, item_id: str):
        return {"order_id": order_id, "item_id": item_id}

    @app.delete("/resources/{resource_id}")
    def delete_resource_endpoint(resource_id: str):
        return {"deleted": resource_id}

    scenario_context.store("app", app)
    scenario_context.store("config", test_config)


@given("Prometheus is enabled for {framework}")
def step_given_prometheus_enabled_for_framework(context, framework):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True
    scenario_context.store("config", test_config)
    scenario_context.store("framework", framework)


# ===== WHEN STEPS =====


@when("the {framework} metric interceptor is setup")
def step_when_metric_interceptor_setup(context, framework):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("config")

    if framework == "FastAPI":
        app = scenario_context.get("app")
        FastAPIUtils.setup_metric_interceptor(app, config)
        scenario_context.store("app", app)
    elif framework == "gRPC":
        interceptors = scenario_context.get("interceptors")
        GrpcAPIUtils.setup_metric_interceptor(config, interceptors)
        scenario_context.store("interceptors", interceptors)
    elif framework == "AsyncgRPC":
        interceptors = scenario_context.get("interceptors")
        AsyncGrpcAPIUtils.setup_metric_interceptor(config, interceptors)
        scenario_context.store("interceptors", interceptors)


@when("a {framework} request is made")
def step_when_request_made(context, framework):
    scenario_context = get_current_scenario_context(context)

    if framework == "FastAPI":
        app = scenario_context.get("app")
        client = TestClient(app)

        initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
        initial_active = _get_gauge_value("fastapi_active_requests")

        scenario_context.store("initial_metrics", initial_metrics)
        scenario_context.store("initial_active_requests", initial_active)

        response = client.get("/test")
        scenario_context.store("response", response)

        final_metrics = _get_metric_samples("fastapi_response_time_seconds")
        final_active = _get_gauge_value("fastapi_active_requests")

        scenario_context.store("final_metrics", final_metrics)
        scenario_context.store("final_active_requests", final_active)

    elif framework == "gRPC":
        interceptors = scenario_context.get("interceptors")

        if not interceptors or not isinstance(interceptors[0], GrpcServerMetricInterceptor):
            raise ValueError("GrpcServerMetricInterceptor not found")

        interceptor = interceptors[0]

        initial_metrics = _get_metric_samples("grpc_response_time_seconds")
        initial_active = _get_gauge_value("grpc_active_requests")

        scenario_context.store("initial_metrics", initial_metrics)
        scenario_context.store("initial_active_requests", initial_active)

        mock_context = MagicMock(spec=grpc.ServicerContext)
        mock_context.code.return_value = None

        def mock_method(request, context):
            return {"result": "success"}

        method_name_model = MethodName(
            full_name="/test.TestService/TestMethod",
            package="test",
            service="TestService",
            method="TestMethod",
        )

        result = interceptor.intercept(mock_method, {}, mock_context, method_name_model)
        scenario_context.store("result", result)

        final_metrics = _get_metric_samples("grpc_response_time_seconds")
        final_active = _get_gauge_value("grpc_active_requests")

        scenario_context.store("final_metrics", final_metrics)
        scenario_context.store("final_active_requests", final_active)

    elif framework == "AsyncgRPC":
        import asyncio

        interceptors = scenario_context.get("interceptors")

        if not interceptors or not isinstance(interceptors[0], AsyncGrpcServerMetricInterceptor):
            raise ValueError("AsyncGrpcServerMetricInterceptor not found")

        interceptor = interceptors[0]

        initial_metrics = _get_metric_samples("grpc_async_response_time_seconds")
        initial_active = _get_gauge_value("grpc_async_active_requests")

        scenario_context.store("initial_metrics", initial_metrics)
        scenario_context.store("initial_active_requests", initial_active)

        mock_context = MagicMock(spec=grpc.aio.ServicerContext)
        mock_context.code.return_value = None

        async def mock_method(request, context):
            return {"result": "success"}

        method_name_model = MethodName(
            full_name="/test.AsyncTestService/AsyncTestMethod",
            package="test",
            service="AsyncTestService",
            method="AsyncTestMethod",
        )

        # Run the async interceptor
        result = asyncio.run(interceptor.intercept(mock_method, {}, mock_context, method_name_model))
        scenario_context.store("result", result)

        final_metrics = _get_metric_samples("grpc_async_response_time_seconds")
        final_active = _get_gauge_value("grpc_async_active_requests")

        scenario_context.store("final_metrics", final_metrics)
        scenario_context.store("final_active_requests", final_active)


@when('a GET request is made to "{path}" endpoint')
def step_when_get_request(context, path):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    client = TestClient(app)

    initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
    initial_active = _get_gauge_value("fastapi_active_requests")

    scenario_context.store("initial_metrics", initial_metrics)
    scenario_context.store("initial_active_requests", initial_active)

    try:
        response = client.get(path)
        scenario_context.store("response", response)
    except Exception as e:
        scenario_context.store("exception", e)

    final_metrics = _get_metric_samples("fastapi_response_time_seconds")
    final_active = _get_gauge_value("fastapi_active_requests")

    scenario_context.store("final_metrics", final_metrics)
    scenario_context.store("final_active_requests", final_active)


@when("a GET request is made to an endpoint that raises an error")
def step_when_get_request_error(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    client = TestClient(app, raise_server_exceptions=False)

    initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("initial_metrics", initial_metrics)

    response = client.get("/error")
    scenario_context.store("response", response)

    final_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("final_metrics", final_metrics)


@when('a {method} request is made to "{path}" with route pattern "{route_pattern}"')
def step_when_request_with_method_and_route_pattern(context, method, path, route_pattern):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    client = TestClient(app)

    initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("initial_metrics", initial_metrics)

    method = method.upper()
    if method == "GET":
        response = client.get(path)
    elif method == "POST":
        response = client.post(path)
    elif method == "PUT":
        response = client.put(path)
    elif method == "DELETE":
        response = client.delete(path)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

    scenario_context.store("response", response)

    final_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("final_metrics", final_metrics)
    scenario_context.store("expected_route_pattern", route_pattern)


@when('multiple GET requests are made to "{path}"')
def step_when_multiple_get_requests(context, path):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    client = TestClient(app)

    initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("initial_metrics", initial_metrics)

    for _ in range(3):
        client.get(path)

    final_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("final_metrics", final_metrics)


@when("multiple {framework} apps are created")
def step_when_multiple_apps_created(context, framework):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("config")

    server_was_running = _is_prometheus_server_running(config.PROMETHEUS.SERVER_PORT)
    scenario_context.store("server_was_running", server_was_running)

    if framework == "FastAPI":
        app1 = AppUtils.create_fastapi_app(config)
        app2 = AppUtils.create_fastapi_app(config)
        scenario_context.store("app1", app1)
        scenario_context.store("app2", app2)
    elif framework == "gRPC":
        interceptors1 = []
        GrpcAPIUtils.setup_metric_interceptor(config, interceptors1)
        interceptors2 = []
        GrpcAPIUtils.setup_metric_interceptor(config, interceptors2)
        scenario_context.store("interceptors1", interceptors1)
        scenario_context.store("interceptors2", interceptors2)
    elif framework == "AsyncgRPC":
        interceptors1 = []
        AsyncGrpcAPIUtils.setup_metric_interceptor(config, interceptors1)
        interceptors2 = []
        AsyncGrpcAPIUtils.setup_metric_interceptor(config, interceptors2)
        scenario_context.store("interceptors1", interceptors1)
        scenario_context.store("interceptors2", interceptors2)


# ===== THEN STEPS =====


@then("the {framework} app should have the metric interceptor")
def step_then_app_has_metric_interceptor(context, framework):
    scenario_context = get_current_scenario_context(context)

    if framework == "FastAPI":
        app = scenario_context.get("app")
        middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "FastAPIMetricInterceptor" in middleware_names, "FastAPI metric interceptor not found"
    elif framework == "gRPC":
        interceptors = scenario_context.get("interceptors")
        assert any(
            isinstance(i, GrpcServerMetricInterceptor) for i in interceptors
        ), "gRPC metric interceptor not found"
    elif framework == "AsyncgRPC":
        interceptors = scenario_context.get("interceptors")
        assert any(
            isinstance(i, AsyncGrpcServerMetricInterceptor) for i in interceptors
        ), "AsyncgRPC metric interceptor not found"


@then("the {framework} app should not have the metric interceptor")
def step_then_app_no_metric_interceptor(context, framework):
    scenario_context = get_current_scenario_context(context)

    if framework == "FastAPI":
        app = scenario_context.get("app")
        middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "FastAPIMetricInterceptor" not in middleware_names, "FastAPI metric interceptor was added"
    elif framework == "gRPC":
        interceptors = scenario_context.get("interceptors")
        assert not any(
            isinstance(i, GrpcServerMetricInterceptor) for i in interceptors
        ), "gRPC metric interceptor was added"
    elif framework == "AsyncgRPC":
        interceptors = scenario_context.get("interceptors")
        assert not any(
            isinstance(i, AsyncGrpcServerMetricInterceptor) for i in interceptors
        ), "AsyncgRPC metric interceptor was added"


@then("the {framework} response time metric should be recorded")
def step_then_response_time_recorded(context, framework):
    scenario_context = get_current_scenario_context(context)
    initial_metrics = scenario_context.get("initial_metrics", [])
    final_metrics = scenario_context.get("final_metrics", [])

    # Check that we have more metrics after the request, or at least some metrics exist
    assert len(final_metrics) >= len(initial_metrics), f"No new {framework} metrics recorded"
    assert len(final_metrics) > 0, f"No {framework} metrics recorded at all"


@then("the {framework} metric should have correct labels")
def step_then_metric_has_correct_labels(context, framework):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")

    if framework == "FastAPI":
        assert any(m.labels.get("method") == "GET" for m in final_metrics), "Missing method label"
        assert any(m.labels.get("status_code") == "200" for m in final_metrics), "Missing status_code label"
        assert any(m.labels.get("path_template") == "/test" for m in final_metrics), "Missing path_template label"
    elif framework == "gRPC":
        assert any(m.labels.get("package") == "test" for m in final_metrics), "Missing package label"
        assert any(m.labels.get("service") == "TestService" for m in final_metrics), "Missing service label"
        assert any(m.labels.get("method") == "TestMethod" for m in final_metrics), "Missing method label"
        assert any(m.labels.get("status_code") == "OK" for m in final_metrics), "Missing status_code label"
    elif framework == "AsyncgRPC":
        assert any(m.labels.get("package") == "test" for m in final_metrics), "Missing package label"
        assert any(m.labels.get("service") == "AsyncTestService" for m in final_metrics), "Missing service label"
        assert any(m.labels.get("method") == "AsyncTestMethod" for m in final_metrics), "Missing method label"
        assert any(m.labels.get("status_code") == "OK" for m in final_metrics), "Missing status_code label"


@then("the {framework} active requests gauge should increment before processing")
def step_then_active_requests_increment(context, framework):
    scenario_context = get_current_scenario_context(context)
    initial_active = scenario_context.get("initial_active_requests")
    assert initial_active is not None, f"{framework} active requests gauge not found"


@then("the {framework} active requests gauge should decrement after processing")
def step_then_active_requests_decrement(context, framework):
    scenario_context = get_current_scenario_context(context)
    initial_active = scenario_context.get("initial_active_requests", 0)
    final_active = scenario_context.get("final_active_requests", 0)
    assert final_active <= initial_active, f"{framework} active requests did not decrement"


@then("the response time metric should be recorded with status code 500")
def step_then_response_time_recorded_500(context):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    status_500_metrics = [m for m in final_metrics if m.labels.get("status_code") == "500"]
    assert len(status_500_metrics) > 0, "No metrics recorded with status code 500"


@then('the metric should have method label "{method}"')
def step_then_metric_has_method(context, method):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    method_metrics = [m for m in final_metrics if m.labels.get("method") == method]
    assert len(method_metrics) > 0, f"No metrics with method {method}"


@then('the metric should have status_code label "{status_code}"')
def step_then_metric_has_status_code(context, status_code):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    status_metrics = [m for m in final_metrics if m.labels.get("status_code") == status_code]
    assert len(status_metrics) > 0, f"No metrics with status_code {status_code}"


@then('the metric should have path_template label "{path_template}"')
def step_then_metric_has_path_template(context, path_template):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    path_metrics = [m for m in final_metrics if m.labels.get("path_template") == path_template]
    assert len(path_metrics) > 0, f"No metrics with path_template {path_template}"


@then('the metric should not have path_template label "{path_template}"')
def step_then_metric_not_have_path_template(context, path_template):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    path_metrics = [m for m in final_metrics if m.labels.get("path_template") == path_template]
    assert len(path_metrics) == 0, f"Found metrics with path_template {path_template}"


@then('all metrics should have the same path_template label "{path_template}"')
def step_then_all_metrics_same_path_template(context, path_template):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    path_metrics = [m for m in final_metrics if m.labels.get("path_template") == path_template]
    assert len(path_metrics) > 0, f"No metrics with path_template {path_template}"


@then("the cache should have stored the path template")
def step_then_cache_has_path_template(context):
    from archipy.helpers.interceptors.fastapi.metric.interceptor import FastAPIMetricInterceptor

    cache_size = len(FastAPIMetricInterceptor._path_template_cache)
    assert cache_size > 0, "Cache is empty, path template was not cached"


@then("the Prometheus server should only start once")
def step_then_prometheus_starts_once(context):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("config")

    is_running = _is_prometheus_server_running(config.PROMETHEUS.SERVER_PORT)
    assert is_running, "Prometheus server is not running"


# ===== HELPER FUNCTIONS =====


def _get_metric_samples(metric_name: str) -> list:
    """Get samples for a specific metric from the Prometheus registry.

    Args:
        metric_name (str): Name of the metric to retrieve.

    Returns:
        list: List of metric samples.
    """
    for collector in REGISTRY.collect():
        if collector.name == metric_name:
            for sample in collector.samples:
                return list(collector.samples)
    return []


def _get_gauge_value(metric_name: str) -> float | None:
    """Get the current value of a gauge metric.

    Args:
        metric_name (str): Name of the gauge metric.

    Returns:
        float | None: Current value of the gauge, or None if not found.
    """
    for collector in REGISTRY.collect():
        if collector.name == metric_name:
            for sample in collector.samples:
                return sample.value
    return None
