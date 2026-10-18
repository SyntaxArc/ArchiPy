import asyncio
import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import grpc
from behave import given, then, when

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators import grpc_rate_limit
from archipy.helpers.interceptors.grpc.base.server_interceptor import (
    BaseAsyncGrpcServerInterceptor,
    BaseGrpcServerInterceptor,
    MethodName,
)
from archipy.helpers.interceptors.grpc.rate_limit import (
    AsyncGrpcServerRateLimitInterceptor,
    AsyncInMemoryRateLimitStore,
    GrpcServerRateLimitInterceptor,
    InMemoryRateLimitStore,
)
from archipy.helpers.utils.app_utils import AsyncGrpcAPIUtils, GrpcAPIUtils
from archipy.helpers.utils.jwt_utils import JWTUtils
from archipy.helpers.utils.rate_limit_utils import RateLimitUtils
from archipy.models.errors import InvalidArgumentError
from features.test_helpers import get_current_scenario_context

_SERVICE = "test.RateLimitService"
_UNREACHABLE_REDIS_TIMEOUT_SECONDS = 0.5

_INTERCEPTOR_MODES = frozenset({"sync", "async"})


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
    updates = {}
    identity = scenario_context.get("identity_from_access_token")
    if identity is not None:
        updates["IDENTITY_FROM_ACCESS_TOKEN"] = identity
    fail_closed = scenario_context.get("fail_closed")
    if fail_closed is not None:
        updates["FAIL_CLOSED"] = fail_closed
    return config.GRPC_RATE_LIMIT.model_copy(update=updates) if updates else config.GRPC_RATE_LIMIT


class _CustomBackendError(Exception):
    """Error of a caller-supplied store that means its backend is down."""


class _FailingRateLimitStore:
    """Counter store whose backend is always down, with the error the caller named as an unavailable backend."""

    def increx(self, name, **kwargs):
        raise _CustomBackendError

    def pttl(self, name):
        raise _CustomBackendError


class _AsyncFailingRateLimitStore:
    """The awaitable counterpart of ``_FailingRateLimitStore``."""

    async def increx(self, name, **kwargs):
        raise _CustomBackendError

    async def pttl(self, name):
        raise _CustomBackendError


def _create_interceptor_with_store(scenario_context, config: BaseConfig):
    """Build the interceptor straight from its constructor with a store the caller passes."""
    failing = scenario_context.get("custom_store") == "failing"
    memory_store = scenario_context.get("memory_counter_store")
    if memory_store is None:
        memory_store = AsyncInMemoryRateLimitStore() if _is_async_mode(scenario_context) else InMemoryRateLimitStore()
        scenario_context.store("memory_counter_store", memory_store)
    rate_limit_config = _rate_limit_config_for_scenario(scenario_context, config)
    if _is_async_mode(scenario_context):
        return AsyncGrpcServerRateLimitInterceptor(
            rate_limit_config=rate_limit_config,
            store=_AsyncFailingRateLimitStore() if failing else memory_store,
            store_errors=(_CustomBackendError,),
        )
    return GrpcServerRateLimitInterceptor(
        rate_limit_config=rate_limit_config,
        store=_FailingRateLimitStore() if failing else memory_store,
        store_errors=(_CustomBackendError,),
    )


def _create_interceptor(scenario_context):
    """Build the sync or async rate-limit interceptor via AppUtils setup helpers."""
    config = BaseConfig.global_config()
    if scenario_context.get("custom_store"):
        interceptor = _create_interceptor_with_store(scenario_context, config)
        return _finish_interceptor(scenario_context, interceptor)
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
    return _finish_interceptor(scenario_context, interceptors[0])


def _finish_interceptor(scenario_context, interceptor):
    """Apply the scenario's proxy and identifier settings to the interceptor and keep it in the scenario context."""
    if scenario_context.get("trusted_proxy_hosts"):
        interceptor._trusted_proxy_hosts = scenario_context.get("trusted_proxy_hosts")
    if scenario_context.get("failing_identifier"):
        interceptor._identifier_fn = _failing_identifier
    scenario_context.store("grpc_interceptor", interceptor)
    return interceptor


def _failing_identifier(_context, _method_name_model):
    """Custom identifier function that always fails."""
    raise RuntimeError("identity backend down")


def _build_method_name(scenario_context) -> MethodName:
    """Build a unique method name model for the scenario."""
    method_suffix = scenario_context.get("method_suffix")
    return MethodName(
        full_name=f"test.RateLimitService/{method_suffix}",
        package="test",
        service="RateLimitService",
        method=method_suffix,
    )


class _PassthroughSyncInterceptor(BaseGrpcServerInterceptor):
    """Sync interceptor that only forwards the call; it sits after the rate limiter."""

    def intercept(self, method, request, context, method_name_model):
        return method(request, context)


class _PassthroughAsyncInterceptor(BaseAsyncGrpcServerInterceptor):
    """Async interceptor that only forwards the call; it sits after the rate limiter."""

    async def intercept(self, method, request, context, method_name_model):
        return await method(request, context)


def _outcome_for_code(code: grpc.StatusCode | None) -> str:
    """Map the status code a real client saw to a scenario outcome label."""
    if code is None:
        return "allowed"
    if code == grpc.StatusCode.UNAVAILABLE:
        return "unavailable"
    if code == grpc.StatusCode.RESOURCE_EXHAUSTED:
        return "rate_limited"
    return "aborted"


def _build_handler(scenario_context, *, decorated: bool = True, runs: list[int] | None = None, returns_value=True):
    """Return a unary handler, decorated with the scenario's rate-limit windows unless ``decorated`` is False.

    The handler is a coroutine function in async mode, as the async server requires.
    """
    payload = b"ok" if returns_value else None

    if _is_async_mode(scenario_context):

        async def handler(_request, _context):
            if runs is not None:
                runs.append(1)
            return payload

    else:

        def handler(_request, _context):
            if runs is not None:
                runs.append(1)
            return payload

    if not decorated:
        return handler
    if scenario_context.get("multi_window"):
        handler = grpc_rate_limit(
            calls_count=scenario_context.get("burst_calls"),
            seconds=scenario_context.get("burst_seconds"),
        )(handler)
        return grpc_rate_limit(
            calls_count=scenario_context.get("sustained_calls"),
            seconds=scenario_context.get("sustained_seconds"),
        )(handler)
    return grpc_rate_limit(calls_count=scenario_context.get("calls_count"), seconds=scenario_context.get("seconds"))(
        handler,
    )


def _closed_local_port() -> int:
    """Return a loopback port nothing listens on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _make_redis_unreachable(scenario_context, interceptor) -> None:
    """Point the interceptor at a real Redis client whose server port is closed, so every call fails to connect."""
    redis_config = BaseConfig.global_config().REDIS.model_copy(
        update={
            "MASTER_HOST": "127.0.0.1",
            "PORT": _closed_local_port(),
            "SOCKET_CONNECT_TIMEOUT": _UNREACHABLE_REDIS_TIMEOUT_SECONDS,
            "SOCKET_TIMEOUT": _UNREACHABLE_REDIS_TIMEOUT_SECONDS,
        },
    )
    adapter_class = AsyncRedisAdapter if _is_async_mode(scenario_context) else RedisAdapter
    interceptor._store = adapter_class(redis_config=redis_config)


async def _call_real_server(
    scenario_context,
    interceptor,
    handler,
    count: int,
    *,
    metadata: list[tuple[str, str]] | None = None,
    follow_with_passthrough: bool = False,
) -> list[str]:
    """Serve ``handler`` behind the rate limiter on a real in-process gRPC server and call it ``count`` times.

    Returns the outcome label of each call as seen by a real client.
    """
    method = scenario_context.get("method_suffix")
    path = f"/{_SERVICE}/{method}"
    rpc_handler = grpc.unary_unary_rpc_method_handler(handler, response_serializer=lambda response: response or b"")
    generic_handler = grpc.method_handlers_generic_handler(_SERVICE, {method: rpc_handler})
    outcomes: list[str] = []

    if _is_async_mode(scenario_context):
        interceptors = [interceptor, *([_PassthroughAsyncInterceptor()] if follow_with_passthrough else [])]
        server = grpc.aio.server(interceptors=interceptors)
        server.add_generic_rpc_handlers((generic_handler,))
        port = server.add_insecure_port("127.0.0.1:0")
        await server.start()
        try:
            async with grpc.aio.insecure_channel(f"127.0.0.1:{port}") as channel:
                for _ in range(count):
                    try:
                        await channel.unary_unary(path)(b"", metadata=metadata)
                        outcomes.append(_outcome_for_code(None))
                    except grpc.aio.AioRpcError as error:
                        outcomes.append(_outcome_for_code(error.code()))
        finally:
            await server.stop(None)
    else:
        interceptors = [interceptor, *([_PassthroughSyncInterceptor()] if follow_with_passthrough else [])]
        server = grpc.server(ThreadPoolExecutor(max_workers=2), interceptors=interceptors)
        server.add_generic_rpc_handlers((generic_handler,))
        port = server.add_insecure_port("127.0.0.1:0")
        server.start()
        try:
            with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
                for _ in range(count):
                    try:
                        channel.unary_unary(path)(b"", metadata=metadata)
                        outcomes.append(_outcome_for_code(None))
                    except grpc.RpcError as error:
                        outcomes.append(_outcome_for_code(error.code()))
        finally:
            server.stop(None).wait()
    return outcomes


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


@given("the interceptor counts in the {store} counter store")
def step_given_interceptor_counter_store(context, store):
    """Count in Redis through the default adapter, or in memory through a store passed to the constructor."""
    assert store in {"redis", "memory"}, store
    if store == "memory":
        get_current_scenario_context(context).store("custom_store", "memory")


@given("the interceptor is built with a caller store whose backend is down")
def step_given_interceptor_with_failing_store(context):
    """Build the interceptor with a store that raises an error the caller named as an unavailable backend."""
    get_current_scenario_context(context).store("custom_store", "failing")


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
    """Invoke decorated RPCs through the rate-limit interceptor on a real gRPC server."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(scenario_context, interceptor, _build_handler(scenario_context), count)
    scenario_context.store("grpc_outcomes", outcomes)


@when("{count:d} decorated gRPC RPCs are invoked with JWT token for user {user_label}")
async def step_when_decorated_grpc_rpcs_with_jwt_user(context, count, user_label):
    """Invoke decorated RPCs with a JWT metadata token for the given user."""
    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get(f"grpc_jwt_token_user_{user_label.lower()}")
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(
        scenario_context,
        interceptor,
        _build_handler(scenario_context),
        count,
        metadata=[("authorization", f"Bearer {token}")],
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("{count:d} undecorated gRPC RPCs are invoked")
async def step_when_undecorated_grpc_rpcs_invoked(context, count):
    """Invoke undecorated RPCs through the rate-limit interceptor."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(
        scenario_context,
        interceptor,
        _build_handler(scenario_context, decorated=False),
        count,
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("1 decorated gRPC RPC is invoked")
async def step_when_one_decorated_grpc_rpc(context):
    """Invoke one decorated RPC through the interceptor as built for the scenario."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(scenario_context, interceptor, _build_handler(scenario_context), 1)
    scenario_context.store("grpc_outcomes", outcomes)


@when("1 decorated gRPC RPC is invoked while Redis is unavailable")
async def step_when_grpc_rpc_while_redis_unavailable(context):
    """Invoke one RPC while the interceptor's Redis server port is closed."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    _make_redis_unreachable(scenario_context, interceptor)
    outcomes = await _call_real_server(scenario_context, interceptor, _build_handler(scenario_context), 1)
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


@when(
    "compute_rate_limit_window is called with calls_count {calls_count:d} and seconds {seconds:d} and minutes {minutes:d}",
)
def step_when_compute_rate_limit_window_negative(context, calls_count, seconds, minutes):
    """Attempt to build a window with a negative component."""
    scenario_context = get_current_scenario_context(context)
    try:
        RateLimitUtils.compute_rate_limit_window(calls_count=calls_count, seconds=seconds, minutes=minutes)
        scenario_context.store("invalid_handler_error", None)
    except InvalidArgumentError as exc:
        scenario_context.store("invalid_handler_error", exc)


@then("an InvalidArgumentError should be raised")
def step_then_invalid_argument_error_raised(context):
    """Assert InvalidArgumentError was raised for invalid window construction."""
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("invalid_handler_error")
    assert isinstance(error, InvalidArgumentError), f"Expected InvalidArgumentError, got {error!r}"


@then("gRPC outcome {index:d} should be {outcome}")
def step_then_grpc_outcome(context, index, outcome):
    """Assert the outcome of a stored gRPC invocation."""
    scenario_context = get_current_scenario_context(context)
    outcomes = scenario_context.get("grpc_outcomes")
    assert outcomes is not None, "No gRPC outcomes stored in scenario context"
    actual = outcomes[index - 1]
    assert actual == outcome, f"Expected gRPC outcome {index} to be {outcome!r}, got {actual!r}"


@given("the gRPC rate limiter fails open")
def step_given_grpc_rate_limiter_fails_open(context):
    """Let calls through when the rate-limit backend or identity resolution fails."""
    get_current_scenario_context(context).store("fail_closed", False)


@given("the gRPC rate limit identifier function fails")
def step_given_grpc_identifier_fails(context):
    """Install a custom identifier function that always raises."""
    get_current_scenario_context(context).store("failing_identifier", True)


@given('the gRPC rate limiter trusts proxy "{host}"')
def step_given_grpc_trusted_proxy(context, host):
    """Trust ``x-forwarded-for`` from the given proxy host."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("trusted_proxy_hosts", (scenario_context.get("trusted_proxy_hosts") or frozenset()) | {host})


@when("{count:d} decorated gRPC RPCs are invoked with forwarded client {client}")
async def step_when_decorated_grpc_rpcs_with_forwarded_client(context, count, client):
    """Invoke decorated RPCs from the loopback peer, which forwards for ``client`` via ``x-forwarded-for``."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(
        scenario_context,
        interceptor,
        _build_handler(scenario_context),
        count,
        metadata=[("x-forwarded-for", client)],
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("1 decorated gRPC RPC whose handler returns nothing is invoked while Redis is unavailable")
async def step_when_grpc_none_handler_while_redis_unavailable(context):
    """Invoke a handler that returns ``None`` while Redis is down and the limiter is fail open."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    _make_redis_unreachable(scenario_context, interceptor)
    runs: list[int] = []
    scenario_context.store("grpc_handler_runs", runs)
    outcomes = await _call_real_server(
        scenario_context,
        interceptor,
        _build_handler(scenario_context, runs=runs, returns_value=False),
        1,
    )
    scenario_context.store("grpc_outcomes", outcomes)


@when("{count:d} RPCs are invoked on a real server where another interceptor follows the rate limiter")
async def step_when_grpc_real_server_with_following_interceptor(context, count):
    """Call a rate-limited handler on a server where another interceptor follows the rate limiter."""
    scenario_context = get_current_scenario_context(context)
    interceptor = _create_interceptor(scenario_context)
    outcomes = await _call_real_server(
        scenario_context,
        interceptor,
        _build_handler(scenario_context),
        count,
        follow_with_passthrough=True,
    )
    scenario_context.store("grpc_outcomes", outcomes)


@then("the gRPC handler should have run {expected:d} time")
def step_then_grpc_handler_run_count(context, expected):
    """Assert how many times the handler body ran."""
    runs = get_current_scenario_context(context).get("grpc_handler_runs")
    assert len(runs) == expected, f"Expected the handler to run {expected} time(s), it ran {len(runs)}"


@then("the gRPC burst window counter should be {expected:d}")
def step_then_grpc_burst_counter(context, expected):
    """Assert the counter of the burst window (first declared window) for the default caller."""
    scenario_context = get_current_scenario_context(context)
    interceptor = scenario_context.get("grpc_interceptor")
    window = RateLimitUtils.compute_rate_limit_window(
        calls_count=scenario_context.get("burst_calls"),
        seconds=scenario_context.get("burst_seconds"),
    )
    key = interceptor._build_rate_limit_key("127.0.0.1", _build_method_name(scenario_context), window)
    store = interceptor._store
    if isinstance(store, InMemoryRateLimitStore):
        stored = store.increx(key, byint=0)[0]
    elif isinstance(store, AsyncInMemoryRateLimitStore):
        stored = asyncio.run(store.increx(key, byint=0))[0]
    else:
        stored = RedisAdapter().get(key)
    assert int(stored) == expected, f"Expected burst counter {expected}, found {stored!r}"


@when("the access token identity of gRPC user {user_label} is resolved from metadata")
def step_when_access_token_identity_resolved(context, user_label):
    """Resolve the identity of a user's access token the way the rate-limit interceptor does."""
    from archipy.helpers.interceptors.grpc.rate_limit.identifiers import resolve_jwt_access_token_sub_from_metadata

    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get(f"grpc_jwt_token_user_{user_label.lower()}")
    scenario_context.store(
        "grpc_resolved_identity",
        resolve_jwt_access_token_sub_from_metadata([("authorization", f"Bearer {token}")]),
    )


@then("the resolved gRPC identity is the subject of user {user_label}")
def step_then_resolved_identity_is_subject(context, user_label):
    scenario_context = get_current_scenario_context(context)
    token = scenario_context.get(f"grpc_jwt_token_user_{user_label.lower()}")
    expected = JWTUtils.decode_token(token, auth_config=BaseConfig.global_config().AUTH)["sub"]
    assert scenario_context.get("grpc_resolved_identity") == str(expected)


@then("no gRPC identity is resolved")
def step_then_no_identity_resolved(context):
    assert get_current_scenario_context(context).get("grpc_resolved_identity") is None


@when("the global config is replaced with one that uses a different JWT signing key")
def step_when_global_config_replaced(context):
    from pydantic import SecretStr

    original = BaseConfig.global_config()
    replacement = original.model_copy(deep=True)
    replacement.AUTH.SECRET_KEY = SecretStr("a-different-signing-key-that-is-long-enough-0123456789")
    BaseConfig.set_global(replacement)
    context.add_cleanup(lambda: BaseConfig.set_global(original))


@when("the auth config for gRPC identity resolution is resolved twice")
def step_when_auth_config_resolved_twice(context):
    from archipy.helpers.interceptors.grpc.rate_limit import identifiers

    get_current_scenario_context(context).store(
        "grpc_auth_configs",
        (identifiers._resolve_auth_config(), identifiers._resolve_auth_config()),
    )


@then("both resolutions return the same auth config object")
def step_then_same_auth_config(context):
    first, second = get_current_scenario_context(context).get("grpc_auth_configs")
    assert first is second
    assert first is BaseConfig.global_config().AUTH


def _call(scenario_context, method: str, *args, **kwargs):
    store = scenario_context.get("memory_store")
    if scenario_context.get("memory_store_mode") == "async":
        return asyncio.run(getattr(store, method)(*args, **kwargs))
    return getattr(store, method)(*args, **kwargs)


@given("a {mode} in-memory rate limit store")
def step_given_memory_store(context, mode):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("memory_store_mode", mode)
    scenario_context.store(
        "memory_store", AsyncInMemoryRateLimitStore() if mode == "async" else InMemoryRateLimitStore()
    )


@when('the counter "{name}" is incremented {times:d} times with a limit of {limit:d} per {window:d} ms')
def step_when_increment(context, name, times, limit, window):
    scenario_context = get_current_scenario_context(context)
    results = [
        _call(scenario_context, "increx", name, byint=1, ubound=limit, saturate=True, px=window, enx=True)
        for _ in range(times)
    ]
    scenario_context.store("memory_store_results", results)


@when("{milliseconds:d} ms pass")
def step_when_ms_pass(context, milliseconds):
    time.sleep(milliseconds / 1000)


@when('the counter "{name}" is refunded {times:d} times')
def step_when_refund(context, name, times):
    scenario_context = get_current_scenario_context(context)
    for _ in range(times):
        _call(scenario_context, "increx", name, byint=-1, lbound=0, saturate=True)


@then("the last increment should apply {applied:d}")
def step_then_last_applied(context, applied):
    results = get_current_scenario_context(context).get("memory_store_results")
    assert results[-1][1] == applied, results


@then('the counter "{name}" should have a time to live below {limit:d} ms')
def step_then_ttl_below(context, name, limit):
    ttl = _call(get_current_scenario_context(context), "pttl", name)
    assert 0 < ttl < limit, ttl


@then('the counter "{name}" should hold {value:d}')
def step_then_holds(context, name, value):
    result = _call(get_current_scenario_context(context), "increx", name, byint=0)
    assert result[0] == value, result


@then('the counter "{name}" should have no time to live record')
def step_then_no_ttl(context, name):
    assert _call(get_current_scenario_context(context), "pttl", name) == -2


@when('the gRPC peer "{peer}" is parsed')
def step_when_grpc_peer_parsed(context, peer):
    """Parse a ``ServicerContext.peer()`` string."""
    get_current_scenario_context(context).store("parsed_peer", GrpcServerRateLimitInterceptor._parse_peer(peer))


@when("the gRPC peer is missing")
def step_when_grpc_peer_missing(context):
    """Parse a missing ``ServicerContext.peer()``."""
    get_current_scenario_context(context).store("parsed_peer", GrpcServerRateLimitInterceptor._parse_peer(None))


@then('the parsed gRPC peer should be "{host}"')
def step_then_grpc_peer_parsed(context, host):
    parsed = get_current_scenario_context(context).get("parsed_peer")
    assert parsed == host, f"Expected {host!r}, got {parsed!r}"
