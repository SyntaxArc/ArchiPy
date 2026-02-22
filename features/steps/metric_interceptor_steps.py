from unittest.mock import MagicMock

import grpc
from behave import given, then, when
from features.test_helpers import get_current_scenario_context
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


# Import for Temporal steps
def get_temporal_worker_manager(context):
    """Lazy import to avoid circular dependency."""
    from features.steps.temporal_adapter_steps import get_temporal_worker_manager as _get_manager

    return _get_manager(context)


# ===== GIVEN STEPS =====


@given("a {framework} app with Prometheus enabled")
def step_given_app_prometheus_enabled(context, framework):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True

    if framework == "FastAPI":
        app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
        scenario_context.store("app", app)
    elif framework == "gRPC" or framework == "AsyncgRPC":
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
    elif framework == "gRPC" or framework == "AsyncgRPC":
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
        assert any(isinstance(i, GrpcServerMetricInterceptor) for i in interceptors), (
            "gRPC metric interceptor not found"
        )
    elif framework == "AsyncgRPC":
        interceptors = scenario_context.get("interceptors")
        assert any(isinstance(i, AsyncGrpcServerMetricInterceptor) for i in interceptors), (
            "AsyncgRPC metric interceptor not found"
        )


@then("the {framework} app should not have the metric interceptor")
def step_then_app_no_metric_interceptor(context, framework):
    scenario_context = get_current_scenario_context(context)

    if framework == "FastAPI":
        app = scenario_context.get("app")
        middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
        assert "FastAPIMetricInterceptor" not in middleware_names, "FastAPI metric interceptor was added"
    elif framework == "gRPC":
        interceptors = scenario_context.get("interceptors")
        assert not any(isinstance(i, GrpcServerMetricInterceptor) for i in interceptors), (
            "gRPC metric interceptor was added"
        )
    elif framework == "AsyncgRPC":
        interceptors = scenario_context.get("interceptors")
        assert not any(isinstance(i, AsyncGrpcServerMetricInterceptor) for i in interceptors), (
            "AsyncgRPC metric interceptor was added"
        )


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


# ===== TEMPORAL METRIC STEPS =====


@given("a Temporal adapter with metrics enabled")
def step_given_temporal_adapter_metrics_enabled(context):
    """Configure Temporal adapter with Prometheus metrics enabled."""
    from archipy.adapters.temporal.adapters import TemporalAdapter
    from archipy.configs.base_config import BaseConfig

    scenario_context = get_current_scenario_context(context)

    # Use existing test config from BaseConfig which loads from .env.test
    test_config = BaseConfig.global_config()

    # Get the existing TemporalConfig from global config and enable metrics
    temporal_config = test_config.TEMPORAL
    temporal_config.ENABLE_METRICS = True

    # Create adapter
    temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.store("temporal_adapter", temporal_adapter)
    scenario_context.store("temporal_config", temporal_config)
    scenario_context.store("config", test_config)

    # Update the worker manager's config to use metrics-enabled config
    worker_manager = get_temporal_worker_manager(context)
    worker_manager.config.ENABLE_METRICS = True
    worker_manager.config.METRICS_PORT = temporal_config.METRICS_PORT
    # Force recreate the adapter with metrics enabled
    worker_manager._temporal_adapter = TemporalAdapter(worker_manager.config)

    context.logger.info(f"Temporal adapter configured with metrics enabled on port {temporal_config.METRICS_PORT}")


@given("a Temporal adapter with metrics disabled")
def step_given_temporal_adapter_metrics_disabled(context):
    """Configure Temporal adapter with Prometheus metrics disabled."""
    from archipy.adapters.temporal.adapters import TemporalAdapter
    from archipy.configs.base_config import BaseConfig

    scenario_context = get_current_scenario_context(context)

    # Use existing test config from BaseConfig which loads from .env.test
    test_config = BaseConfig.global_config()

    # Get the existing TemporalConfig from global config and disable metrics
    temporal_config = test_config.TEMPORAL
    temporal_config.ENABLE_METRICS = False

    # Create adapter
    temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.store("temporal_adapter", temporal_adapter)
    scenario_context.store("temporal_config", temporal_config)
    scenario_context.store("config", test_config)

    # Update the worker manager's config to disable metrics
    worker_manager = get_temporal_worker_manager(context)
    worker_manager.config.ENABLE_METRICS = False
    # Force recreate the adapter with metrics disabled
    worker_manager._temporal_adapter = TemporalAdapter(worker_manager.config)

    context.logger.info("Temporal adapter configured with metrics disabled")


@then("Temporal metrics should be present in Prometheus registry")
def step_then_temporal_metrics_present(context):
    """Verify that Temporal metrics are present in Prometheus HTTP endpoint."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    # Query the Prometheus HTTP endpoint directly
    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for Temporal metrics in the response
        temporal_metrics_found = "temporal_" in metrics_text

        assert temporal_metrics_found, "No Temporal metrics found in Prometheus HTTP endpoint"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("Temporal metrics should not be present in Prometheus registry")
def step_then_temporal_metrics_not_present(context):
    """Verify that Temporal metrics are NOT present in Prometheus HTTP endpoint."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    # Query the Prometheus HTTP endpoint directly
    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        if response.status_code == 200:
            metrics_text = response.text
            # Check that no Temporal metrics are present
            temporal_metrics_found = "temporal_" in metrics_text
            assert not temporal_metrics_found, "Temporal metrics found when disabled"
    except httpx.ConnectError:
        # If server is not running, that's fine for disabled metrics
        pass


@then("Temporal client metrics should include workflow operations")
def step_then_temporal_client_metrics_workflow_ops(context):
    """Verify that Temporal client metrics include workflow-related operations."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for workflow-related metrics
        workflow_metric_found = (
            "temporal_workflow" in metrics_text
            or "temporal_request" in metrics_text
            or "temporal_long_request" in metrics_text
        )

        assert workflow_metric_found, "No workflow operation metrics found in Temporal client metrics"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("Temporal worker metrics should include task execution")
def step_then_temporal_worker_metrics_task_execution(context):
    """Verify that Temporal worker metrics include task execution metrics."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for worker-related metrics
        worker_metric_found = (
            "temporal_worker" in metrics_text
            or "temporal_activity" in metrics_text
            or "temporal_workflow_task" in metrics_text
        )

        assert worker_metric_found, "No worker task execution metrics found in Temporal worker metrics"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("Temporal worker task execution metrics should be recorded")
def step_then_temporal_worker_task_execution_recorded(context):
    """Verify that worker task execution metrics are recorded."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for task execution metrics
        task_metrics_found = "worker" in metrics_text and "task" in metrics_text and "temporal_" in metrics_text

        assert task_metrics_found, "No worker task execution metrics recorded"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("worker metrics should include task queue labels")
def step_then_worker_metrics_include_task_queue_labels(context):
    """Verify that worker metrics include task queue label information."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for task_queue label in worker metrics
        metrics_with_task_queue = "task_queue=" in metrics_text and "temporal_worker" in metrics_text

        assert metrics_with_task_queue, "No worker metrics with task_queue labels found"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("Temporal activity execution metrics should be recorded")
def step_then_temporal_activity_execution_metrics_recorded(context):
    """Verify that activity execution metrics are recorded."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for activity-related metrics
        activity_metrics_found = "temporal_activity" in metrics_text

        assert activity_metrics_found, "No activity execution metrics recorded"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@then("activity metrics should include activity type information")
def step_then_activity_metrics_include_type_info(context):
    """Verify that activity metrics include activity type labels."""
    import httpx

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Check for activity_type label in metrics
        has_activity_type = "activity_type=" in metrics_text or "activity" in metrics_text.lower()

        assert has_activity_type, "Activity metrics missing type information"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e


@when("I execute {count:d} workflows of type {workflow_name}")
def step_when_execute_multiple_workflows(context, count, workflow_name):
    """Execute multiple workflows of the same type."""
    from features.steps.temporal_adapter_steps import GreetingWorkflow, get_temporal_adapter, run_async

    scenario_context = get_current_scenario_context(context)
    adapter = get_temporal_adapter(context)

    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    # Get the task queue from the last started worker
    worker_manager = scenario_context.get("worker_manager")
    if worker_manager and hasattr(worker_manager, "_workers") and worker_manager._workers:
        task_queue = list(worker_manager._workers.keys())[0]
    else:
        task_queue = "test-queue"

    async def run_workflows():
        results = []
        for i in range(count):
            result = await adapter.execute_workflow(workflow_class, f"User{i}", task_queue=task_queue)
            results.append(result)
        return results

    results = run_async(context, run_workflows())
    scenario_context.store("workflow_results", results)
    context.logger.info(f"Executed {count} workflows of type {workflow_name}")


@then("Temporal workflow execution count metrics should show at least {min_count:d} executions")
def step_then_workflow_execution_count(context, min_count):
    """Verify that workflow execution count meets minimum threshold."""
    import httpx
    import re

    scenario_context = get_current_scenario_context(context)
    temporal_config = scenario_context.get("temporal_config")
    metrics_port = temporal_config.METRICS_PORT

    try:
        response = httpx.get(f"http://localhost:{metrics_port}/metrics", timeout=5.0)
        response.raise_for_status()
        metrics_text = response.text

        # Look for workflow-related counter metrics
        # Temporal SDK uses various metric names, look for any with counts
        found_sufficient_count = False

        # Parse counter values from metrics
        for line in metrics_text.split("\n"):
            if "temporal_" in line and not line.startswith("#"):
                # Try to extract numeric values from metric lines
                numbers = re.findall(r"\s+(\d+(?:\.\d+)?)\s*$", line)
                if numbers:
                    value = float(numbers[0])
                    if value >= min_count:
                        found_sufficient_count = True
                        break

        assert found_sufficient_count, f"No workflow execution count >= {min_count} found in metrics"
    except httpx.RequestError as e:
        raise AssertionError(f"Failed to query Prometheus endpoint: {e}") from e
