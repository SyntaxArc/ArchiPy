import time
import uuid
from unittest.mock import AsyncMock, patch

from behave import given, then, when
from fastapi import Depends
from httpx2 import ASGITransport, AsyncClient

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.configs.base_config import BaseConfig
from archipy.helpers.interceptors.fastapi.rate_limit.fastapi_rest_rate_limit_handler import (
    FastAPIRestRateLimitHandler,
)
from archipy.helpers.utils.app_utils import AppUtils
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.helpers.utils.rate_limit_utils import RateLimitUtils
from archipy.models.dtos.rate_limit_window_dto import RateLimitWindowDTO
from archipy.models.errors import InvalidArgumentError
from features.test_helpers import get_current_scenario_context

_DEFAULT_TRUSTED_PROXIES = ["127.0.0.1", "::1", "testclient"]
_DEFAULT_TRUSTED_PROXIES_WITH_HOPS = ["127.0.0.1", "::1", "testclient", "10.0.0.1", "10.0.0.2"]


def _authorization_header(token: str) -> dict[str, str]:
    """Build an Authorization header for a Bearer JWT."""
    return {"Authorization": f"Bearer {token}"}


def _build_rate_limited_app(
    calls_count: int,
    seconds: int,
    endpoint_path: str,
    *,
    trusted_proxy_ips: list[str] | None = None,
    identity_from_access_token: bool | None = None,
    additional_windows: list[RateLimitWindowDTO] | None = None,
):
    """Build a FastAPI app with a rate-limited GET endpoint."""
    test_config = BaseConfig.global_config()
    test_config.PROMETHEUS.IS_ENABLED = False
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    rate_limit_handler = FastAPIRestRateLimitHandler(
        calls_count=calls_count,
        seconds=seconds,
        trusted_proxy_ips=trusted_proxy_ips or [],
        identity_from_access_token=identity_from_access_token,
        additional_windows=additional_windows,
    )

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
    scenario_context.store("trusted_proxy_ips", [])
    scenario_context.store("identity_from_access_token", False)
    scenario_context.store("additional_windows", None)


@given(
    "a multi-window FastAPI endpoint with burst {burst_calls:d} calls per {burst_seconds:d} seconds "
    "and sustained {sustained_calls:d} calls per {sustained_seconds:d} seconds",
)
def step_given_multi_window_fastapi_endpoint(
    context,
    burst_calls,
    burst_seconds,
    sustained_calls,
    sustained_seconds,
):
    """Register burst and sustained FastAPI rate-limit windows for the scenario."""
    scenario_context = get_current_scenario_context(context)
    path_id = uuid.uuid4().hex
    endpoint_path = f"/rate-limit/multi/{path_id}"
    scenario_context.store("calls_count", burst_calls)
    scenario_context.store("seconds", burst_seconds)
    scenario_context.store(
        "additional_windows",
        [RateLimitWindowDTO(calls_count=sustained_calls, window_ms=sustained_seconds * 1000)],
    )
    scenario_context.store("endpoint_path", endpoint_path)
    scenario_context.store("trusted_proxy_ips", [])
    scenario_context.store("identity_from_access_token", False)


@given("a rate-limited FastAPI endpoint allowing {calls_count:d} calls per {seconds:d} seconds with trusted proxies")
def step_given_rate_limited_endpoint_with_trusted_proxies(context, calls_count, seconds):
    """Register rate-limit settings with trusted proxy peers enabled."""
    scenario_context = get_current_scenario_context(context)
    path_id = uuid.uuid4().hex
    endpoint_path = f"/rate-limit/{path_id}"
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("endpoint_path", endpoint_path)
    scenario_context.store("trusted_proxy_ips", _DEFAULT_TRUSTED_PROXIES)
    scenario_context.store("identity_from_access_token", False)


@given(
    "a rate-limited FastAPI endpoint allowing {calls_count:d} calls per {seconds:d} seconds "
    "with trusted proxies and internal hops",
)
def step_given_rate_limited_endpoint_with_trusted_proxies_and_hops(context, calls_count, seconds):
    """Register rate-limit settings with trusted proxy peers including internal hop addresses."""
    scenario_context = get_current_scenario_context(context)
    path_id = uuid.uuid4().hex
    endpoint_path = f"/rate-limit/{path_id}"
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("endpoint_path", endpoint_path)
    scenario_context.store("trusted_proxy_ips", _DEFAULT_TRUSTED_PROXIES_WITH_HOPS)
    scenario_context.store("identity_from_access_token", False)


async def _make_requests(
    context,
    count,
    headers=None,
    header_list=None,
    *,
    identity_from_access_token: bool | None = None,
):
    """Issue sequential GET requests to the rate-limited endpoint."""
    scenario_context = get_current_scenario_context(context)
    calls_count = scenario_context.get("calls_count")
    seconds = scenario_context.get("seconds")
    endpoint_path = scenario_context.get("endpoint_path")
    trusted_proxy_ips = scenario_context.get("trusted_proxy_ips")
    resolved_identity_from_access_token = (
        identity_from_access_token
        if identity_from_access_token is not None
        else scenario_context.get("identity_from_access_token")
    )
    additional_windows = scenario_context.get("additional_windows")
    app = _build_rate_limited_app(
        calls_count,
        seconds,
        endpoint_path,
        trusted_proxy_ips=trusted_proxy_ips,
        identity_from_access_token=resolved_identity_from_access_token,
        additional_windows=additional_windows,
    )
    responses = []
    request_headers = header_list or headers or {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        for _ in range(count):
            response = await client.get(endpoint_path, headers=request_headers)
            responses.append(response)
    scenario_context.store("responses", responses)


@given("a JWT rate-limited FastAPI endpoint allowing {calls_count:d} calls per {seconds:d} seconds")
def step_given_jwt_rate_limited_endpoint(context, calls_count, seconds):
    """Register JWT identity rate-limit settings and a unique endpoint path."""
    scenario_context = get_current_scenario_context(context)
    path_id = uuid.uuid4().hex
    endpoint_path = f"/rate-limit/jwt/{path_id}"
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("endpoint_path", endpoint_path)
    scenario_context.store("trusted_proxy_ips", [])
    scenario_context.store("identity_from_access_token", True)


@given("JWT access tokens for user A and user B")
def step_given_jwt_tokens_for_two_users(context):
    """Create distinct access tokens for two users."""
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    scenario_context.store("jwt_token_user_a", JWTUtils.create_access_token(user_a, auth_config=test_config.AUTH))
    scenario_context.store("jwt_token_user_b", JWTUtils.create_access_token(user_b, auth_config=test_config.AUTH))


@when("{count:d} requests are made to the endpoint")
async def step_when_requests_made(context, count):
    """Make multiple requests without custom headers."""
    await _make_requests(context, count)


@when('{count:d} requests are made to the endpoint with JWT token for user {user_label}')
async def step_when_requests_made_with_jwt_user(context, count, user_label):
    """Make multiple requests with a stored JWT token for the given user label."""
    scenario_context = get_current_scenario_context(context)
    token_key = f"jwt_token_user_{user_label.lower()}"
    token = scenario_context.get(token_key)
    await _make_requests(context, count, headers=_authorization_header(token))


@when("{count:d} requests are made to the endpoint with the stored JWT token")
async def step_when_requests_made_with_stored_jwt_token(context, count):
    """Make multiple requests with the scenario's stored JWT token."""
    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get("token")
    await _make_requests(context, count, headers=_authorization_header(token))


@when('{count:d} requests are made to the endpoint with header "{header_name}" "{header_value}"')
async def step_when_requests_made_with_header(context, count, header_name, header_value):
    """Make multiple requests with a single custom header."""
    await _make_requests(context, count, headers={header_name: header_value})


@when(
    '{count:d} requests are made to the endpoint with X-Forwarded-For fields "{first_value}" and "{second_value}"',
)
async def step_when_requests_made_with_xff_fields(context, count, first_value, second_value):
    """Make multiple requests with repeated X-Forwarded-For header fields."""
    header_list = [("X-Forwarded-For", first_value), ("X-Forwarded-For", second_value)]
    await _make_requests(context, count, header_list=header_list)


@when("{count:d} requests are made to the endpoint with headers")
async def step_when_requests_made_with_headers_table(context, count):
    """Make multiple requests with headers from a Gherkin table."""
    header_list = [(row["header"], row["value"]) for row in context.table]
    await _make_requests(context, count, header_list=header_list)


@when("I wait {seconds:d} seconds for the rate limit window to expire")
def step_when_wait_for_window(context, seconds):
    """Wait for the rate limit window to expire."""
    time.sleep(seconds)


@when("1 request is made while Redis is unavailable")
async def step_when_request_while_redis_unavailable(context):
    """Make a request while Redis increx raises a connection error."""
    scenario_context = get_current_scenario_context(context)
    calls_count = scenario_context.get("calls_count")
    seconds = scenario_context.get("seconds")
    endpoint_path = scenario_context.get("endpoint_path")
    app = _build_rate_limited_app(
        calls_count,
        seconds,
        endpoint_path,
        trusted_proxy_ips=[],
        identity_from_access_token=False,
    )
    with patch.object(AsyncRedisAdapter, "increx", new_callable=AsyncMock, side_effect=ConnectionError("down")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.get(endpoint_path)
    scenario_context.store("responses", [response])


@when("a rate limit handler is created with query params but no identifier")
def step_when_invalid_handler_created(context):
    """Attempt to construct a handler with unsafe query_params configuration."""
    scenario_context = get_current_scenario_context(context)
    try:
        FastAPIRestRateLimitHandler(
            calls_count=1,
            seconds=60,
            query_params={"user_id"},
            identity_from_access_token=False,
        )
        scenario_context.store("invalid_handler_error", None)
    except InvalidArgumentError as exc:
        scenario_context.store("invalid_handler_error", exc)


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


@then('response {index:d} header "{header_name}" should equal "{expected_value}"')
def step_then_response_header_equals(context, index, header_name, expected_value):
    """Assert a response header has the expected value."""
    scenario_context = get_current_scenario_context(context)
    responses = scenario_context.get("responses")
    assert responses is not None, "No responses stored in scenario context"
    response = responses[index - 1]
    actual_value = response.headers.get(header_name)
    assert actual_value == expected_value, (
        f"Expected response {index} header {header_name!r} to equal {expected_value!r}, got {actual_value!r}"
    )


@then("an InvalidArgumentError should be raised")
def step_then_invalid_argument_error(context):
    """Assert handler construction failed with InvalidArgumentError."""
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("invalid_handler_error")
    assert isinstance(error, InvalidArgumentError), (
        f"Expected InvalidArgumentError, got {error!r}"
    )
