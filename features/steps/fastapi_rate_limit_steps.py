import time
import uuid

from behave import given, then, when
from fastapi import Depends
from httpx2 import ASGITransport, AsyncClient

from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler import (
    FastAPIRestRateLimitHandler,
)
from archipy.helpers.utils.app_utils import AppUtils
from features.test_helpers import get_current_scenario_context


def _build_rate_limited_app(calls_count: int, seconds: int, endpoint_path: str):
    """Build a FastAPI app with a rate-limited GET endpoint."""
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = False
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    rate_limit_handler = FastAPIRestRateLimitHandler(calls_count=calls_count, seconds=seconds)

    @app.get(endpoint_path, dependencies=[Depends(rate_limit_handler)])
    def rate_limited_endpoint():
        return {"status": "ok"}

    return app


@given("a rate-limited FastAPI endpoint allowing {calls_count:d} calls per {seconds:d} seconds")
def step_given_rate_limited_endpoint(context, calls_count, seconds):
    """Register rate-limit settings and a unique endpoint path for the scenario."""
    scenario_context = get_current_scenario_context(context)
    path_id = uuid.uuid4().hex
    endpoint_path = f"/rate-limit/{path_id}"
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("endpoint_path", endpoint_path)


async def _make_requests(context, count, headers=None):
    """Issue sequential GET requests to the rate-limited endpoint."""
    scenario_context = get_current_scenario_context(context)
    calls_count = scenario_context.get("calls_count")
    seconds = scenario_context.get("seconds")
    endpoint_path = scenario_context.get("endpoint_path")
    app = _build_rate_limited_app(calls_count, seconds, endpoint_path)
    responses = []
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for _ in range(count):
            response = await client.get(endpoint_path, headers=headers or {})
            responses.append(response)
    scenario_context.store("responses", responses)


@when("{count:d} requests are made to the endpoint")
async def step_when_requests_made(context, count):
    """Make multiple requests without custom headers."""
    await _make_requests(context, count)


@when('{count:d} requests are made to the endpoint with header "{header_name}" "{header_value}"')
async def step_when_requests_made_with_header(context, count, header_name, header_value):
    """Make multiple requests with a single custom header."""
    await _make_requests(context, count, headers={header_name: header_value})


@when("I wait {seconds:d} seconds for the rate limit window to expire")
def step_when_wait_for_window(context, seconds):
    """Wait for the rate limit window to expire."""
    time.sleep(seconds)


@then("response {index:d} should have status {status_code:d}")
def step_then_response_status(context, index, status_code):
    """Assert the HTTP status code of a stored response (1-based index)."""
    scenario_context = get_current_scenario_context(context)
    responses = scenario_context.get("responses")
    assert responses is not None, "No responses stored in scenario context"
    response = responses[index - 1]
    assert response.status_code == status_code, (
        f"Expected response {index} status {status_code}, got {response.status_code}"
    )


@then('response {index:d} should include a "{header_name}" header')
def step_then_response_has_header(context, index, header_name):
    """Assert a response includes the given header."""
    scenario_context = get_current_scenario_context(context)
    responses = scenario_context.get("responses")
    assert responses is not None, "No responses stored in scenario context"
    response = responses[index - 1]
    assert header_name in response.headers, (
        f"Expected response {index} to include header {header_name!r}, got {dict(response.headers)}"
    )
