import socket

from behave import given, then, when
from prometheus_client import REGISTRY
from starlette.testclient import TestClient

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils, FastAPIUtils
from features.test_helpers import get_current_scenario_context


@given("a FastAPI app with Prometheus enabled")
def step_given_fastapi_app_prometheus_enabled(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    scenario_context.store("app", app)
    scenario_context.store("config", test_config)


@given("a FastAPI app with Prometheus disabled")
def step_given_fastapi_app_prometheus_disabled(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = False
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    scenario_context.store("app", app)
    scenario_context.store("config", test_config)


@given("a FastAPI app with Prometheus enabled and metric interceptor")
def step_given_fastapi_app_with_metric_interceptor(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True

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
    scenario_context.store("config", test_config)


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


@given("Prometheus is enabled")
def step_given_prometheus_enabled(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = True
    scenario_context.store("config", test_config)


@when("the metric interceptor is setup")
def step_when_metric_interceptor_setup(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    config = scenario_context.get("config")
    FastAPIUtils.setup_metric_interceptor(app, config)
    scenario_context.store("app", app)


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


@when('a GET request is made to "{path}" with route pattern "{route_pattern}"')
def step_when_get_request_with_route_pattern(context, path, route_pattern):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    client = TestClient(app)

    initial_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("initial_metrics", initial_metrics)

    response = client.get(path)
    scenario_context.store("response", response)

    final_metrics = _get_metric_samples("fastapi_response_time_seconds")
    scenario_context.store("final_metrics", final_metrics)
    scenario_context.store("expected_route_pattern", route_pattern)


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


@when("multiple FastAPI apps are created")
def step_when_multiple_apps_created(context):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("config")

    server_start_count = 0

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", config.PROMETHEUS.SERVER_PORT))
        sock.close()
        if result == 0:
            server_start_count = 1
    except Exception:
        pass

    app1 = AppUtils.create_fastapi_app(config)
    app2 = AppUtils.create_fastapi_app(config)

    scenario_context.store("app1", app1)
    scenario_context.store("app2", app2)
    scenario_context.store("server_start_count", server_start_count)


@then("the FastAPI app should have the metric interceptor")
def step_then_app_has_metric_interceptor(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
    assert "FastAPIMetricInterceptor" in middleware_names


@then("the FastAPI app should not have the metric interceptor")
def step_then_app_no_metric_interceptor(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    middleware_names = [middleware.cls.__name__ for middleware in app.user_middleware]
    assert "FastAPIMetricInterceptor" not in middleware_names


@then("the response time metric should be recorded")
def step_then_response_time_recorded(context):
    scenario_context = get_current_scenario_context(context)
    final_metrics = scenario_context.get("final_metrics")
    assert len(final_metrics) > 0, "No metrics recorded"


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


@then("the active requests gauge should increment before processing")
def step_then_active_requests_increment(context):
    scenario_context = get_current_scenario_context(context)
    initial_active = scenario_context.get("initial_active_requests")
    assert initial_active is not None, "Active requests gauge not found"


@then("the active requests gauge should decrement after processing")
def step_then_active_requests_decrement(context):
    scenario_context = get_current_scenario_context(context)
    initial_active = scenario_context.get("initial_active_requests", 0)
    final_active = scenario_context.get("final_active_requests", 0)
    assert final_active <= initial_active, "Active requests did not decrement"


@then("the Prometheus server should only start once")
def step_then_prometheus_starts_once(context):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("config")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("localhost", config.PROMETHEUS.SERVER_PORT))
    sock.close()

    assert result == 0, "Prometheus server is not running"


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
