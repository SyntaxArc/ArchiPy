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
    app = FastAPI()
    FastAPIUtils.setup_cors(app, test_config)
    scenario_context.store("app", app)


@when("CORS middleware is setup")
def step_when_cors_is_setup(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    middleware_stack = {middleware.cls.__name__ for middleware in app.user_middleware}
    scenario_context.store("middleware_stack", middleware_stack)


@then('the app should allow origins "{expected_origin}"')
def step_then_check_cors_origin(context, expected_origin):
    scenario_context = get_current_scenario_context(context)
    middleware_stack = scenario_context.get("middleware_stack")
    test_config = BaseConfig.global_config()
    assert "CORSMiddleware" in middleware_stack
    assert expected_origin in test_config.FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGINS


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
