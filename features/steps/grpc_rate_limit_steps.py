import uuid
from unittest.mock import MagicMock, patch

import grpc
from behave import given, then, when

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import grpc_rate_limit_decorator
from archipy.helpers.interceptors.grpc.base.server_interceptor import MethodName
from archipy.helpers.utils.app_utils import AsyncGrpcAPIUtils, GrpcAPIUtils
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.helpers.utils.rate_limit_utils import RateLimitUtils
from archipy.models.errors import InvalidArgumentError
from features.test_helpers import get_current_scenario_context

_INTERCEPTOR_MODES = frozenset({"sync", "async"})


class _AbortCalled(Exception):
    """Raised when a mocked gRPC context abort is invoked."""


def _store_interceptor_mode(scenario_context, mode: str) -> None:
    """Persist the interceptor mode for the current scenario."""
    if mode not in _INTERCEPTOR_MODES:
        raise ValueError(f"Unsupported gRPC interceptor mode: {mode!r}")
    scenario_context.store("grpc_interceptor_mode", mode)


def _is_async_mode(scenario_context) -> bool:
    """Return whether the scenario uses the async gRPC rate-limit interceptor."""
    return scenario_context.get("grpc_interceptor_mode") == "async"


def _rate_limit_config_for_scenario(scenario_context, config: BaseConfig):
    """Return gRPC rate-limit config with scenario identity overrides applied."""
    identity = scenario_context.get("identity_from_access_token")
    if identity is None:
        return config.GRPC_RATE_LIMIT
    return config.GRPC_RATE_LIMIT.model_copy(update={"IDENTITY_FROM_ACCESS_TOKEN": identity})


def _create_interceptor(scenario_context):
    """Build the sync or async rate-limit interceptor via AppUtils setup helpers."""
    config = BaseConfig.global_config()
    original_rate_limit = config.GRPC_RATE_LIMIT
    config.GRPC_RATE_LIMIT = _rate_limit_config_for_scenario(scenario_context, config)
    interceptors: list[object] = []
    try:
        if _is_async_mode(scenario_context):
            AsyncGrpcAPIUtils.setup_rate_limit_interceptor(config, interceptors)
        else:
            GrpcAPIUtils.setup_rate_limit_interceptor(config, interceptors)
    finally:
        config.GRPC_RATE_LIMIT = original_rate_limit

    if len(interceptors) != 1:
        raise RuntimeError(
            "Expected exactly one gRPC rate-limit interceptor; set GRPC_RATE_LIMIT__IS_ENABLED=true",
        )
    return interceptors[0]


def _build_method_name(scenario_context) -> MethodName:
    """Build a unique method name model for the scenario."""
    method_suffix = scenario_context.get("method_suffix")
    return MethodName(
        full_name=f"test.RateLimitService/{method_suffix}",
        package="test",
        service="RateLimitService",
        method=method_suffix,
    )


def _build_sync_context(*, peer: str = "ipv4:127.0.0.1:12345", metadata: list[tuple[str, str]] | None = None) -> MagicMock:
    """Build a mocked sync gRPC servicer context."""
    context = MagicMock(spec=grpc.ServicerContext)
    context.peer.return_value = peer
    context.invocation_metadata.return_value = metadata or []

    def abort_side_effect(code: grpc.StatusCode, details: str) -> None:
        context.abort_code = code
        context.abort_details = details
        raise _AbortCalled()

    context.abort.side_effect = abort_side_effect
    return context


def _build_async_context(*, peer: str = "ipv4:127.0.0.1:12345", metadata: list[tuple[str, str]] | None = None) -> MagicMock:
    """Build a mocked async gRPC servicer context."""
    context = MagicMock(spec=grpc.aio.ServicerContext)
    context.peer.return_value = peer
    context.invocation_metadata.return_value = metadata or []

    async def abort_side_effect(code: grpc.StatusCode, details: str) -> None:
        context.abort_code = code
        context.abort_details = details
        raise _AbortCalled()

    context.abort = abort_side_effect
    return context


def _outcome_from_abort(context: MagicMock) -> str:
    """Map a mocked abort to a scenario outcome label."""
    if context.abort_code == grpc.StatusCode.UNAVAILABLE:
        return "unavailable"
    if context.abort_code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return "rate_limited"
    return "aborted"


def _decorate_handler(calls_count: int, seconds: int):
    """Return a decorated handler function for the configured window."""

    @grpc_rate_limit_decorator(calls_count=calls_count, seconds=seconds)
    def handler(_request, _context):
        return {"status": "ok"}

    return handler


def _decorate_handler_multi(burst_calls: int, burst_seconds: int, sustained_calls: int, sustained_seconds: int):
    """Return a handler with stacked burst and sustained decorators."""

    @grpc_rate_limit_decorator(calls_count=sustained_calls, seconds=sustained_seconds)
    @grpc_rate_limit_decorator(calls_count=burst_calls, seconds=burst_seconds)
    def handler(_request, _context):
        return {"status": "ok"}

    return handler


def _undecorated_handler(_request, _context):
    return {"status": "ok"}


def _invoke_rpc_sync(
    interceptor,
    handler,
    method_name_model: MethodName,
    *,
    metadata: list[tuple[str, str]] | None = None,
) -> str:
    """Invoke the sync interceptor once and return the outcome label."""
    context = _build_sync_context(metadata=metadata)
    try:
        result = interceptor.intercept(handler, {}, context, method_name_model)
    except _AbortCalled:
        return _outcome_from_abort(context)
    assert result == {"status": "ok"}
    return "allowed"


async def _invoke_rpc_async(
    interceptor,
    handler,
    method_name_model: MethodName,
    *,
    metadata: list[tuple[str, str]] | None = None,
) -> str:
    """Invoke the async interceptor once and return the outcome label."""
    context = _build_async_context(metadata=metadata)
    try:
        result = await interceptor.intercept(handler, {}, context, method_name_model)
    except _AbortCalled:
        return _outcome_from_abort(context)
    assert result == {"status": "ok"}
    return "allowed"


async def _invoke_rpcs(
    scenario_context,
    interceptor,
    handler,
    method_name_model: MethodName,
    count: int,
    *,
    metadata: list[tuple[str, str]] | None = None,
) -> list[str]:
    """Invoke decorated RPCs through the configured interceptor mode."""
    outcomes = []
    if _is_async_mode(scenario_context):
        for _ in range(count):
            outcomes.append(await _invoke_rpc_async(interceptor, handler, method_name_model, metadata=metadata))
    else:
        for _ in range(count):
            outcomes.append(_invoke_rpc_sync(interceptor, handler, method_name_model, metadata=metadata))
    return outcomes


def _resolve_handler(scenario_context):
    """Return the decorated handler configured for the scenario."""
    if scenario_context.get("multi_window"):
        return _decorate_handler_multi(
            scenario_context.get("burst_calls"),
            scenario_context.get("burst_seconds"),
            scenario_context.get("sustained_calls"),
            scenario_context.get("sustained_seconds"),
        )
    return _decorate_handler(scenario_context.get("calls_count"), scenario_context.get("seconds"))


@given("a {mode} gRPC JWT rate limit interceptor allowing {calls_count:d} calls per {seconds:d} seconds")
def step_given_jwt_grpc_rate_limit_interceptor(context, mode, calls_count, seconds):
    """Register JWT identity gRPC rate-limit settings."""
    scenario_context = get_current_scenario_context(context)
    _store_interceptor_mode(scenario_context, mode)
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("method_suffix", f"Call{uuid.uuid4().hex}")
    scenario_context.store("identity_from_access_token", True)
    scenario_context.store("multi_window", False)


@given("a {mode} gRPC rate limit interceptor allowing {calls_count:d} calls per {seconds:d} seconds")
def step_given_grpc_rate_limit_interceptor(context, mode, calls_count, seconds):
    """Register gRPC rate-limit settings for the scenario."""
    scenario_context = get_current_scenario_context(context)
    _store_interceptor_mode(scenario_context, mode)
    scenario_context.store("calls_count", calls_count)
    scenario_context.store("seconds", seconds)
    scenario_context.store("method_suffix", f"Call{uuid.uuid4().hex}")
    scenario_context.store("identity_from_access_token", False)
    scenario_context.store("multi_window", False)


@given(
    "a {mode} gRPC rate limit interceptor with burst {burst_calls:d} calls per {burst_seconds:d} seconds "
    "and sustained {sustained_calls:d} calls per {sustained_seconds:d} seconds",
)
def step_given_grpc_multi_window_interceptor(
    context,
    mode,
    burst_calls,
    burst_seconds,
    sustained_calls,
    sustained_seconds,
):
    """Register stacked burst and sustained gRPC rate-limit windows."""
    scenario_context = get_current_scenario_context(context)
    _store_interceptor_mode(scenario_context, mode)
    scenario_context.store("burst_calls", burst_calls)
    scenario_context.store("burst_seconds", burst_seconds)
    scenario_context.store("sustained_calls", sustained_calls)
    scenario_context.store("sustained_seconds", sustained_seconds)
    scenario_context.store("method_suffix", f"Call{uuid.uuid4().hex}")
    scenario_context.store("identity_from_access_token", False)
    scenario_context.store("multi_window", True)


@given("JWT access tokens for gRPC user A and user B")
def step_given_grpc_jwt_tokens_for_two_users(context):
    """Create distinct JWT access tokens for two gRPC users."""
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    scenario_context.store(
        "grpc_jwt_token_user_a",
        JWTUtils.create_access_token(user_a, auth_config=test_config.AUTH),
    )
    scenario_context.store(
        "grpc_jwt_token_user_b",
        JWTUtils.create_access_token(user_b, auth_config=test_config.AUTH),
    )


@when("{count:d} decorated gRPC RPCs are invoked")
async def step_when_decorated_grpc_rpcs_invoked(context, count):
    """Invoke decorated RPCs through the rate-limit interceptor."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    method_name_model = _build_method_name(scenario_context)
    handler = _resolve_handler(scenario_context)
    outcomes = await _invoke_rpcs(scenario_context, interceptor, handler, method_name_model, count)
    scenario_context.store("grpc_outcomes", outcomes)


@when('{count:d} decorated gRPC RPCs are invoked with JWT token for user {user_label}')
async def step_when_decorated_grpc_rpcs_with_jwt_user(context, count, user_label):
    """Invoke decorated RPCs with a JWT metadata token for the given user."""
    scenario_context = get_current_scenario_context(context)
    token_key = f"grpc_jwt_token_user_{user_label.lower()}"
    token = scenario_context.get(token_key)
    interceptor = _create_interceptor(scenario_context)
    method_name_model = _build_method_name(scenario_context)
    handler = _decorate_handler(scenario_context.get("calls_count"), scenario_context.get("seconds"))
    metadata = [("authorization", f"Bearer {token}")]

    outcomes = await _invoke_rpcs(
        scenario_context,
        interceptor,
        handler,
        method_name_model,
        count,
        metadata=metadata,
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("{count:d} undecorated gRPC RPCs are invoked")
async def step_when_undecorated_grpc_rpcs_invoked(context, count):
    """Invoke undecorated RPCs through the rate-limit interceptor."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    method_name_model = _build_method_name(scenario_context)
    outcomes = await _invoke_rpcs(
        scenario_context,
        interceptor,
        _undecorated_handler,
        method_name_model,
        count,
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("1 decorated gRPC RPC is invoked while Redis is unavailable")
async def step_when_grpc_rpc_while_redis_unavailable(context):
    """Invoke one RPC while Redis increx raises a connection error."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    method_name_model = _build_method_name(scenario_context)
    handler = _decorate_handler(scenario_context.get("calls_count"), scenario_context.get("seconds"))

    if _is_async_mode(scenario_context):
        with patch.object(AsyncRedisAdapter, "increx", side_effect=ConnectionError("down")):
            outcomes = await _invoke_rpcs(scenario_context, interceptor, handler, method_name_model, 1)
    else:
        with patch.object(RedisAdapter, "increx", side_effect=ConnectionError("down")):
            outcomes = await _invoke_rpcs(scenario_context, interceptor, handler, method_name_model, 1)
    scenario_context.store("grpc_outcomes", outcomes)


@when("compute_rate_limit_window is called with calls_count {calls_count:d} and seconds {seconds:d}")
def step_when_compute_rate_limit_window_invalid(context, calls_count, seconds):
    """Attempt to build an invalid rate-limit window."""
    scenario_context = get_current_scenario_context(context)
    try:
        RateLimitUtils.compute_rate_limit_window(calls_count=calls_count, seconds=seconds)
        scenario_context.store("invalid_handler_error", None)
    except InvalidArgumentError as exc:
        scenario_context.store("invalid_handler_error", exc)


@then("gRPC outcome {index:d} should be {outcome}")
def step_then_grpc_outcome(context, index, outcome):
    """Assert the outcome of a stored gRPC invocation."""
    scenario_context = get_current_scenario_context(context)
    outcomes = scenario_context.get("grpc_outcomes")
    assert outcomes is not None, "No gRPC outcomes stored in scenario context"
    actual = outcomes[index - 1]
    assert actual == outcome, f"Expected gRPC outcome {index} to be {outcome!r}, got {actual!r}"
