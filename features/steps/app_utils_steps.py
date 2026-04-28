from behave import given, then, when
from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from pydantic import BaseModel, ValidationError
from starlette.testclient import TestClient

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils, FastAPIExceptionHandler, FastAPIUtils
from archipy.models.errors import BaseError
from features.test_helpers import get_current_scenario_context


@given("a FastAPI app")
def step_given_fastapi_app(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    app = AppUtils.create_fastapi_app(test_config)
    scenario_context.store("app", app)


@when("a FastAPI app is created")
def step_when_fastapi_app_created(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    app = AppUtils.create_fastapi_app(test_config)
    scenario_context.store("app", app)


@then("the app should have the correct title")
def step_then_check_app_title(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    assert app.title == "Test API"


@then("exception handlers should be registered")
def step_then_check_exception_handlers(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    assert BaseError in app.exception_handlers
    assert ValidationError in app.exception_handlers


@given('a FastAPI route with tag "{tag}" and name "{route_name}"')
def step_given_fastapi_route(context, tag, route_name):
    scenario_context = get_current_scenario_context(context)
    route = APIRoute(path="/users", endpoint=lambda: None, name=route_name, tags=[tag])
    scenario_context.store("route", route)


@when("a unique ID is generated")
def step_when_generate_unique_id(context):
    scenario_context = get_current_scenario_context(context)
    route = scenario_context.get("route")
    unique_id = FastAPIUtils.custom_generate_unique_id(route)
    scenario_context.store("unique_id", unique_id)


@then('the unique ID should be "{expected_id}"')
def step_then_check_unique_id(context, expected_id):
    scenario_context = get_current_scenario_context(context)
    unique_id = scenario_context.get("unique_id")
    assert unique_id == expected_id


@given("a FastAPI app with CORS configuration")
def step_given_fastapi_app_with_cors(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    FastAPIUtils.setup_cors(app, test_config)

    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}

    scenario_context.store("app", app)


@then('the app should allow origins "{expected_origin}"')
def step_then_check_cors_origin(context, expected_origin):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", headers={"Origin": expected_origin})

    assert response.headers.get("access-control-allow-origin") == expected_origin


@then('the app should have expose headers "{expected_headers}"')
def step_then_check_expose_headers(context, expected_headers):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", headers={"Origin": "https://example.com"})

    assert response.headers.get("access-control-expose-headers") == expected_headers


@then("the app should have max age {expected_max_age}")
def step_then_check_max_age(context, expected_max_age):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.options(
        "/test",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-max-age") == expected_max_age


@when('I make a request with origin "{origin}"')
def step_when_request_with_origin(context, origin):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", headers={"Origin": origin})
    scenario_context.store("response", response)


@when('I make a {method} request with origin "{origin}"')
def step_when_request_with_method_and_origin(context, method, origin):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.request(method.upper(), "/test", headers={"Origin": origin})
    scenario_context.store("response", response)


@when('I send a request to test endpoint with origin "{origin}" and custom header "{header}"')
def step_when_request_with_origin_and_header(context, origin, header):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", headers={"Origin": origin, header: "test-value"})
    scenario_context.store("response", response)


@when('I send a POST request to test endpoint with origin "{origin}" and custom content-type "{content_type}"')
def step_when_post_with_content_type(context, origin, content_type):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.post(
        "/test",
        headers={"Origin": origin, "Content-Type": content_type},
        json={"test": "data"},
    )
    scenario_context.store("response", response)


@when('I make an OPTIONS preflight requesting method "{method}"')
def step_when_options_preflight_method(context, method):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.options(
        "/test",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": method,
        },
    )
    scenario_context.store("response", response)


@when('I make an OPTIONS preflight requesting header "{header}"')
def step_when_options_preflight_header(context, header):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.options(
        "/test",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": header,
        },
    )
    scenario_context.store("response", response)


@when('I make an OPTIONS preflight {preflight_type}')
def step_when_options_preflight_type(context, preflight_type):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    test_config = BaseConfig.global_config()
    allowed_origin = test_config.FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGINS[0]

    client = TestClient(app)

    if preflight_type == "without Origin header":
        response = client.options("/test", headers={"Access-Control-Request-Method": "GET"})
    elif preflight_type == "without Access-Control-Request-Method header":
        response = client.options("/test", headers={"Origin": allowed_origin})
    elif preflight_type == "with invalid Origin":
        response = client.options(
            "/test",
            headers={"Origin": "https://invalid.com", "Access-Control-Request-Method": "GET"},
        )
    else:
        response = client.options("/test")

    scenario_context.store("response", response)


@then("the response should NOT have access-control-allow-origin header")
def step_then_cors_origin_not_allowed(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    assert response.headers.get("access-control-allow-origin") is None, (
        f"Expected no CORS origin header, but got: {response.headers.get('access-control-allow-origin')}"
    )


@then("the response should NOT have access-control-allow-methods header")
def step_then_methods_not_allowed(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    test_config = BaseConfig.global_config()
    allowed_methods = test_config.FASTAPI.CORS_MIDDLEWARE_ALLOW_METHODS
    methods_header = response.headers.get("access-control-allow-methods", "")

    for method in ["PUT", "DELETE", "PATCH", "TRACE", "CONNECT"]:
        assert method not in methods_header, (
            f"Disallowed method {method} should not be in access-control-allow-methods: {methods_header}"
        )


@then("the response should NOT have access-control-allow-headers header")
def step_then_headers_not_allowed(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    headers_header = response.headers.get("access-control-allow-headers", "")

    for header in ["X-Custom-Token", "X-Api-Key", "X-Debug", "Cookie"]:
        assert header not in headers_header, (
            f"Disallowed header {header} should not be in access-control-allow-headers: {headers_header}"
        )


@then("the response should return status code 405")
def step_then_response_should_be_405(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    assert response.status_code == 405, (
        f"Expected 405 status code, but got: {response.status_code}"
    )


@then("the custom header should NOT be in access-control-expose-headers")
def step_then_custom_header_not_exposed(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    expose_headers = response.headers.get("access-control-expose-headers", "")

    for header in ["X-Custom-Token", "X-Api-Key", "X-Debug", "Cookie"]:
        assert header not in expose_headers, (
            f"Custom header {header} should not be in access-control-expose-headers: {expose_headers}"
        )


@when('an endpoint raises a "{exception_type}"')
def step_when_endpoint_raises_exception(context, exception_type):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    app.add_exception_handler(
        eval(exception_type),
        FastAPIExceptionHandler.custom_exception_handler,
    )

    @app.get("/test-exception")
    def raise_exception():
        raise eval(exception_type)()

    client = TestClient(app)
    response = client.get("/test-exception")
    scenario_context.store("response", response)


@then("the response should have status code 500")
def step_then_check_500_error(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    assert response.status_code == 500


@when("an endpoint raises a validation error")
def step_when_endpoint_raises_validation_error(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    app.add_exception_handler(ValidationError, FastAPIExceptionHandler.validation_exception_handler)

    class TestSchema(BaseModel):
        id: int

    @app.get("/test-validation")
    def validate_data(schema: TestSchema = Depends()):
        return {"message": "Valid"}

    client = TestClient(app)
    response = client.get("/test-validation", params={"id": "invalid"})
    scenario_context.store("response", response)


@then("the response should have status code 422")
def step_then_check_422_error(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    assert response.status_code == 422
