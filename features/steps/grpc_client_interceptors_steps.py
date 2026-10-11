import grpc
from behave import given, then, when

from archipy.helpers.interceptors.grpc.base.client_interceptor import (
    AsyncClientCallDetails,
    BaseAsyncGrpcClientInterceptor,
    BaseGrpcClientInterceptor,
    ClientCallDetails,
)
from features.test_helpers import get_current_scenario_context

_METHOD = "/pkg.Svc/Call"
_ORIG_METADATA = (("x-orig", "keep"),)
_SENTINEL = object()
_STREAM_KINDS = {"unary_stream", "stream_stream"}
_CLIENT_STREAM_KINDS = {"stream_unary", "stream_stream"}


def _parse_metadata(text):
    key, _, value = text.partition("=")
    return ((key, value),)


class _SyncInterceptor(BaseGrpcClientInterceptor):
    def __init__(self, extra=None):
        self.extra = extra

    def intercept(self, method, request_or_iterator, call_details):
        if self.extra is not None:
            metadata = list(call_details.metadata or []) + [self.extra]
            call_details = ClientCallDetails(
                call_details.method,
                call_details.timeout,
                metadata,
                call_details.credentials,
                call_details.wait_for_ready,
                call_details.compression,
            )
            return method(request_or_iterator, call_details)
        return super().intercept(method, request_or_iterator, call_details)


class _AsyncInterceptor(BaseAsyncGrpcClientInterceptor):
    def __init__(self, extra=None):
        self.extra = extra

    async def intercept(self, method, request_or_iterator, call_details):
        if self.extra is not None:
            metadata = list(call_details.metadata or []) + [self.extra]
            call_details = AsyncClientCallDetails(
                call_details.method,
                call_details.timeout,
                metadata,
                call_details.credentials,
                call_details.wait_for_ready,
            )
            return await method(request_or_iterator, call_details)
        return await super().intercept(method, request_or_iterator, call_details)


def _sync_details():
    return ClientCallDetails(_METHOD, 5.0, _ORIG_METADATA, None, None, None)


def _async_details():
    return AsyncClientCallDetails(_METHOD, 5.0, _ORIG_METADATA, None, None)


def _request_for(kind, text):
    if kind in _CLIENT_STREAM_KINDS:
        return iter(text.split(","))
    return text


def _make_sync_continuation(scenario_context, fail):
    def continuation(details, request):
        scenario_context.store("client_seen_details", details)
        scenario_context.store("client_seen_request", request)
        if fail:
            raise RuntimeError("continuation failed")
        return _SENTINEL

    return continuation


def _make_stream_continuation(scenario_context, is_async):
    def sync_stream(request):
        yield from request if hasattr(request, "__next__") else request.split(",")

    async def async_stream(request):
        for item in request if hasattr(request, "__next__") else request.split(","):
            yield item

    def sync_cont(details, request):
        scenario_context.store("client_seen_details", details)
        scenario_context.store("client_seen_request", request)
        return sync_stream(request)

    async def async_cont(details, request):
        scenario_context.store("client_seen_details", details)
        scenario_context.store("client_seen_request", request)
        return async_stream(request)

    return async_cont if is_async else sync_cont


# ---- call details -------------------------------------------------------------


@when('sync client call details are built for method "{method}" with timeout {timeout:f} and metadata "{meta}"')
def step_client_sync_details(context, method, timeout, meta):
    details = ClientCallDetails(method, timeout, _parse_metadata(meta), None, True, grpc.Compression.Gzip)
    get_current_scenario_context(context).store("client_details", details)


@when('async client call details are built for method "{method}" with timeout {timeout:f} and metadata "{meta}"')
def step_client_async_details(context, method, timeout, meta):
    details = AsyncClientCallDetails(method, timeout, _parse_metadata(meta), None, False)
    get_current_scenario_context(context).store("client_details", details)


@then('the client call details report method "{method}" and timeout {timeout:f} and metadata "{meta}"')
def step_client_details_fields(context, method, timeout, meta):
    details = get_current_scenario_context(context).get("client_details")
    assert details.method == method
    assert details.timeout == timeout
    assert tuple(details.metadata) == _parse_metadata(meta)


@then("the client call details are a gRPC client call details instance")
def step_client_details_sync_instance(context):
    details = get_current_scenario_context(context).get("client_details")
    assert isinstance(details, grpc.ClientCallDetails)
    assert details.compression == grpc.Compression.Gzip
    assert details.wait_for_ready is True


@then("the client call details are an async gRPC client call details instance")
def step_client_details_async_instance(context):
    details = get_current_scenario_context(context).get("client_details")
    assert isinstance(details, grpc.aio.ClientCallDetails)
    assert details.wait_for_ready is False


@then("the base sync client interceptor cannot be instantiated")
def step_client_base_sync_abstract(context):
    try:
        BaseGrpcClientInterceptor()
    except TypeError:
        return
    raise AssertionError("BaseGrpcClientInterceptor should be abstract")


@then("the base async client interceptor cannot be instantiated")
def step_client_base_async_abstract(context):
    try:
        BaseAsyncGrpcClientInterceptor()
    except TypeError:
        return
    raise AssertionError("BaseAsyncGrpcClientInterceptor should be abstract")


# ---- sync interceptor ---------------------------------------------------------


@given("a sync pass-through client interceptor")
def step_client_sync_passthrough(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _SyncInterceptor())
    scenario_context.store("client_fail", False)


@given("a sync pass-through client interceptor with a failing continuation")
def step_client_sync_failing(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _SyncInterceptor())
    scenario_context.store("client_fail", True)


@given('a sync metadata-adding client interceptor adding "{key}" with "{value}"')
def step_client_sync_adding(context, key, value):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _SyncInterceptor((key, value)))
    scenario_context.store("client_fail", False)


def _run_sync(context, kind, text, *, stream_cont):
    scenario_context = get_current_scenario_context(context)
    interceptor = scenario_context.get("client_interceptor")
    if stream_cont:
        continuation = _make_stream_continuation(scenario_context, is_async=False)
    else:
        continuation = _make_sync_continuation(scenario_context, scenario_context.get("client_fail"))
    request = _request_for(kind, text)
    result = getattr(interceptor, f"intercept_{kind}")(continuation, _sync_details(), request)
    scenario_context.store("client_result", result)
    scenario_context.store("client_request_text", text)


@when('a sync "{kind}" call with request "{text}" is intercepted')
def step_client_sync_call(context, kind, text):
    _run_sync(context, kind, text, stream_cont=text == "a,b,c")


@when('a sync "{kind}" call with request "{text}" is intercepted expecting failure')
def step_client_sync_call_failure(context, kind, text):
    scenario_context = get_current_scenario_context(context)
    try:
        _run_sync(context, kind, text, stream_cont=False)
    except RuntimeError as exc:
        scenario_context.store("client_error", str(exc))


def _seen_request_text(scenario_context):
    seen = scenario_context.get("client_seen_request")
    if hasattr(seen, "__next__"):
        return ",".join(seen)
    return seen


@then('the sync continuation received request "{text}" with method "{method}"')
def step_client_sync_seen(context, text, method):
    scenario_context = get_current_scenario_context(context)
    assert _seen_request_text(scenario_context) == text
    assert scenario_context.get("client_seen_details").method == method


@then("the sync continuation received no extra client metadata")
def step_client_sync_no_extra(context):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert tuple(details.metadata) == _ORIG_METADATA


@then('the sync continuation received client metadata "{key}" with "{value}"')
def step_client_sync_has_meta(context, key, value):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert (key, value) in list(details.metadata), details.metadata


@then('the sync continuation kept the original client metadata "{key}" with "{value}"')
def step_client_sync_kept_meta(context, key, value):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert (key, value) in list(details.metadata), details.metadata


@then("the intercepted sync call returned the continuation result")
def step_client_sync_result(context):
    assert get_current_scenario_context(context).get("client_result") is _SENTINEL


@then('the intercepted sync streaming response yields "{text}"')
def step_client_sync_stream_yields(context, text):
    result = get_current_scenario_context(context).get("client_result")
    assert ",".join(result) == text


@then('the intercepted sync call raised "{message}"')
def step_client_sync_raised(context, message):
    assert get_current_scenario_context(context).get("client_error") == message


# ---- async interceptor --------------------------------------------------------


@given("an async pass-through client interceptor")
def step_client_async_passthrough(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _AsyncInterceptor())
    scenario_context.store("client_fail", False)


@given("an async pass-through client interceptor with a failing continuation")
def step_client_async_failing(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _AsyncInterceptor())
    scenario_context.store("client_fail", True)


@given('an async metadata-adding client interceptor adding "{key}" with "{value}"')
def step_client_async_adding(context, key, value):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("client_interceptor", _AsyncInterceptor((key, value)))
    scenario_context.store("client_fail", False)


def _make_async_continuation(scenario_context, fail):
    async def continuation(details, request):
        scenario_context.store("client_seen_details", details)
        scenario_context.store("client_seen_request", request)
        if fail:
            raise RuntimeError("continuation failed")
        return _SENTINEL

    return continuation


async def _run_async(context, kind, text):
    scenario_context = get_current_scenario_context(context)
    interceptor = scenario_context.get("client_interceptor")
    continuation = _make_async_continuation(scenario_context, scenario_context.get("client_fail"))
    request = _request_for(kind, text)
    result = await getattr(interceptor, f"intercept_{kind}")(continuation, _async_details(), request)
    scenario_context.store("client_result", result)


@when('an async "{kind}" call with request "{text}" is intercepted')
async def step_client_async_call(context, kind, text):
    await _run_async(context, kind, text)


@when('an async "{kind}" call with request "{text}" is intercepted expecting failure')
async def step_client_async_call_failure(context, kind, text):
    scenario_context = get_current_scenario_context(context)
    try:
        await _run_async(context, kind, text)
    except RuntimeError as exc:
        scenario_context.store("client_error", str(exc))


@then('the async continuation received request "{text}" with method "{method}"')
def step_client_async_seen(context, text, method):
    scenario_context = get_current_scenario_context(context)
    assert _seen_request_text(scenario_context) == text
    assert scenario_context.get("client_seen_details").method == method


@then("the async continuation received no extra client metadata")
def step_client_async_no_extra(context):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert tuple(details.metadata) == _ORIG_METADATA


@then('the async continuation received client metadata "{key}" with "{value}"')
def step_client_async_has_meta(context, key, value):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert (key, value) in list(details.metadata), details.metadata


@then('the async continuation kept the original client metadata "{key}" with "{value}"')
def step_client_async_kept_meta(context, key, value):
    details = get_current_scenario_context(context).get("client_seen_details")
    assert (key, value) in list(details.metadata), details.metadata


@then("the intercepted async call returned the continuation result")
def step_client_async_result(context):
    assert get_current_scenario_context(context).get("client_result") is _SENTINEL


@then('the intercepted async call raised "{message}"')
def step_client_async_raised(context, message):
    assert get_current_scenario_context(context).get("client_error") == message
