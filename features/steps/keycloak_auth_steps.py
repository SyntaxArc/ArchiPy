import asyncio
import time
import warnings
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import grpc
import grpc.aio
import httpx
from behave import given, step, then, when
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from features.test_helpers import get_current_scenario_context

from archipy.adapters.keycloak import auth as keycloak_auth
from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter
from archipy.adapters.keycloak.auth import AuthContextManager
from archipy.models.dtos.keycloak.token_dtos import KeycloakUserInfoDTO
from archipy.models.dtos.keycloak_dtos import AuthenticatedUserDTO
from archipy.models.errors import BaseError


class _Aborted(Exception):
    """Raised by the fake servicer contexts, like a real gRPC abort."""


class _FakeSyncServicerContext(grpc.ServicerContext):
    def __init__(self, metadata):
        self._metadata = metadata
        self.abort_code = None
        self.abort_message = None
        self.trailing = None

    def invocation_metadata(self):
        return self._metadata

    def set_trailing_metadata(self, trailing):
        self.trailing = trailing

    def abort(self, code, details):
        self.abort_code = code
        self.abort_message = details
        raise _Aborted


class _FakeAsyncServicerContext(grpc.aio.ServicerContext):
    def __init__(self, metadata):
        self._metadata = metadata
        self.abort_code = None
        self.abort_message = None
        self.trailing = None

    def invocation_metadata(self):
        return self._metadata

    def set_trailing_metadata(self, trailing):
        self.trailing = trailing

    async def abort(self, code, details, trailing_metadata=()):
        self.abort_code = code
        self.abort_message = details
        raise _Aborted


# The gRPC contexts are ABCs; the fakes only implement what the decorators touch.
_FakeSyncServicerContext.__abstractmethods__ = frozenset()
_FakeAsyncServicerContext.__abstractmethods__ = frozenset()


class _RealisticSyncServicerContext(_FakeSyncServicerContext):
    """Aborts like grpc's real sync context: record the status, then raise a bare ``Exception``."""

    def __init__(self, metadata):
        super().__init__(metadata)
        self.abort_calls = 0
        self._code = None

    def code(self):
        return self._code

    def abort(self, code, details):
        self.abort_calls += 1
        self._code = self.abort_code = code
        self.abort_message = details
        raise Exception  # noqa: TRY002 - this is what grpc does


class _RealisticAsyncServicerContext(_FakeAsyncServicerContext):
    """Aborts like grpc's real aio context: raise ``grpc.aio.AbortError`` once the status is recorded."""

    def __init__(self, metadata):
        super().__init__(metadata)
        self.abort_calls = 0

    async def abort(self, code, details, trailing_metadata=()):
        self.abort_calls += 1
        self.abort_code = code
        self.abort_message = details
        raise grpc.aio.AbortError("Locally aborted.")


_RealisticSyncServicerContext.__abstractmethods__ = frozenset()
_RealisticAsyncServicerContext.__abstractmethods__ = frozenset()


class _PlainContext:
    """Not a gRPC servicer context: only exposes metadata."""

    def __init__(self, metadata):
        self._metadata = metadata

    def invocation_metadata(self):
        return self._metadata


def _ctx(context):
    return get_current_scenario_context(context)


def _split(value):
    return [v for v in value.split(",") if v]


def _auth_kwargs(scenario_context):
    kwargs = scenario_context.get("auth_kwargs")
    if kwargs is None:
        kwargs = {}
        scenario_context.store("auth_kwargs", kwargs)
    return kwargs


def _path_params(scenario_context):
    params = scenario_context.get("path_params")
    if params is None:
        params = {}
        scenario_context.store("path_params", params)
    return params


def _request_attrs(scenario_context):
    attrs = scenario_context.get("request_attrs")
    if attrs is None:
        attrs = {}
        scenario_context.store("request_attrs", attrs)
    return attrs


def _handler_calls(scenario_context):
    calls = scenario_context.get("handler_calls")
    if calls is None:
        calls = []
        scenario_context.store("handler_calls", calls)
    return calls


def _real_sync_adapter(scenario_context):
    adapter = getattr(scenario_context, "adapter", None)
    assert adapter is not None, "a configured Keycloak adapter is required first"
    return adapter


@contextmanager
def _real_keycloak_adapters(scenario_context):
    """Point keycloak auth at adapters configured for the real Keycloak container client.

    The sync adapter is the scenario adapter created by the keycloak adapter steps. The async adapter is built
    fresh from the same configuration so it binds to the running event loop.
    """
    sync_adapter = _real_sync_adapter(scenario_context)
    # The remote cache is keyed by the identity of the adapter configuration, so every call of a scenario must see
    # the same configuration object.
    async_configs = scenario_context.get("async_configs")
    if async_configs is None:
        async_configs = sync_adapter.configs.model_copy()
        scenario_context.store("async_configs", async_configs)
    async_adapter = AsyncKeycloakAdapter(async_configs)
    with ExitStack() as stack:
        stack.enter_context(patch.object(keycloak_auth, "_shared_sync_adapter", lambda: sync_adapter))
        stack.enter_context(patch.object(keycloak_auth, "_shared_async_adapter", lambda: async_adapter))
        if scenario_context.get("claims_unreadable"):

            async def _no_claims_async(_token):
                return {}

            stack.enter_context(patch.object(sync_adapter, "get_token_info", lambda _token: {}))
            stack.enter_context(patch.object(async_adapter, "get_token_info", _no_claims_async))
        yield


@contextmanager
def _adapters_for_call(scenario_context):
    with _real_keycloak_adapters(scenario_context):
        yield


AUTH_REALM = "auth-realm"


@given("a keycloak auth realm with a client")
def step_keycloak_auth_realm_with_client(context):
    """Create the realm and client every keycloak auth scenario needs, talking to Keycloak directly."""
    step_keycloak_auth_realm_with_client_via(context, "direct")


@given("a keycloak auth realm with a client via {via}")
def step_keycloak_auth_realm_with_client_via(context, via):
    """Create the realm and client every keycloak auth scenario needs, directly or through Envoy."""
    context.execute_steps(
        f"""
        Given a configured sync Keycloak adapter via {via}
        And I create a realm named "{AUTH_REALM}" with display name "Auth Realm" using sync adapter
        And I create a client named "auth-client" in realm "{AUTH_REALM}" with service accounts and update adapter using sync adapter
        """,
    )
    keycloak_auth.clear_keycloak_remote_cache()
    context.add_cleanup(keycloak_auth.clear_keycloak_remote_cache)
    AuthContextManager.clear_auth_context()
    context.add_cleanup(AuthContextManager.clear_auth_context)


@given(
    'a keycloak auth realm with user "{username}" holding realm role "{role}" and an access token',
)
def step_keycloak_auth_realm_with_user_token(context, username, role):
    """Realm, client, a user with the realm role and a real access token for that user."""
    step_keycloak_auth_realm_with_user_token_via(context, username, role, "direct")


@given(
    'a keycloak auth realm with user "{username}" holding realm role "{role}" and an access token via {via}',
)
def step_keycloak_auth_realm_with_user_token_via(context, username, role, via):
    """Realm, client, a user with the realm role and a real access token, directly or through Envoy."""
    step_keycloak_auth_realm_with_client_via(context, via)
    context.execute_steps(
        f"""
        Given I create a user with username "{username}" and password "pass123" using sync adapter
        And I create a realm role named "{role}" with description "Reader" using sync adapter
        And I assign realm role "{role}" to user "{username}" using sync adapter
        And the keycloak auth access token of user "{username}" is obtained with password "pass123"
        """,
    )


@given("the keycloak auth adapter caches remote lookups for {seconds:g} seconds")
def step_keycloak_auth_cache_ttl(context, seconds):
    configs = _real_sync_adapter(_ctx(context)).configs
    # The adapter shares the global Keycloak configuration, so the previous value must come back after the scenario.
    previous = configs.REMOTE_CACHE_TTL_SECONDS
    configs.REMOTE_CACHE_TTL_SECONDS = seconds
    context.add_cleanup(lambda: setattr(configs, "REMOTE_CACHE_TTL_SECONDS", previous))


@given("the keycloak auth adapter cannot read the claims of issued tokens")
def step_keycloak_auth_claims_unreadable(context):
    _ctx(context).store("claims_unreadable", True)


@when('the keycloak auth sessions of user "{username}" are cleared')
def step_keycloak_auth_clear_sessions(context, username):
    sc = _ctx(context)
    _real_sync_adapter(sc).clear_user_sessions(_user_id(sc, username))


@when("the keycloak adapter's own permission cache is cleared")
def step_keycloak_auth_clear_adapter_permission_cache(context):
    """Drop the adapter-level permission cache so only the keycloak auth TTL cache can serve a stale answer."""
    _real_sync_adapter(_ctx(context)).check_permissions_batch.clear_cache()


@when('the keycloak auth permission granting scope "{scope}" on resource "{resource}" of client "{client}" is deleted')
def step_keycloak_auth_delete_permission(context, scope, resource, client):
    sc = _ctx(context)
    adapter = _real_sync_adapter(sc)
    internal_id = sc.get(f"client_{client}")["internal_client_id"]
    permission_name = f"{resource}-{scope}-permission"
    permission_id = next(
        p["id"] for p in adapter.admin_adapter.get_client_authz_permissions(internal_id) if p["name"] == permission_name
    )
    adapter.delete_client_authz_policy(internal_id, permission_id)


@when("the keycloak auth cached lookups expire")
def step_keycloak_auth_cache_expires(context):
    with keycloak_auth._remote_cache_lock:
        for key, (_, value) in list(keycloak_auth._remote_cache.items()):
            keycloak_auth._remote_cache[key] = (0.0, value)


@given('the keycloak {surface} auth requires any of roles "{roles}"')
def step_keycloak_auth_any_roles(context, surface, roles):
    _auth_kwargs(_ctx(context)).update(required_roles=frozenset(_split(roles)), all_roles_required=False)


@given('the keycloak fastapi auth requires all roles "{roles}"')
def step_keycloak_auth_all_roles(context, roles):
    _auth_kwargs(_ctx(context)).update(required_roles=frozenset(_split(roles)), all_roles_required=True)


@given('the keycloak fastapi auth requires permissions "{perms}"')
def step_keycloak_auth_required_permissions(context, perms):
    pairs = tuple(tuple(p.split("#")) for p in _split(perms))
    _auth_kwargs(_ctx(context)).update(required_permissions=pairs)


@given('the keycloak fastapi auth guards resource type "{rtype}" by path parameter "{param}"')
def step_keycloak_auth_guard_resource(context, rtype, param):
    _auth_kwargs(_ctx(context)).update(resource_type=rtype, resource_type_param=param)


@given('the keycloak fastapi auth sets only its {argument} to "{value}"')
def step_keycloak_auth_guard_one_argument(context, argument, value):
    key = {"resource type": "resource_type", "path parameter": "resource_type_param"}[argument]
    _auth_kwargs(_ctx(context)).update({key: value})


@given('the keycloak fastapi auth treats roles "{roles}" as admin roles')
def step_keycloak_auth_admin_roles(context, roles):
    _auth_kwargs(_ctx(context)).update(admin_roles=frozenset(_split(roles)))


@given('the keycloak auth request path parameter "{name}" is "{value}"')
def step_keycloak_auth_path_param(context, name, value):
    _path_params(_ctx(context))[name] = value


@when('the keycloak auth fastapi dependency is called with token "{token}"')
async def step_keycloak_auth_call_dependency(context, token):
    await _call_dependency(context, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


@when("the keycloak auth fastapi dependency is called without credentials")
async def step_keycloak_auth_call_dependency_anonymous(context):
    await _call_dependency(context, None)


async def _call_dependency(context, credentials):
    sc = _ctx(context)
    request = SimpleNamespace(path_params=dict(_path_params(sc)), state=SimpleNamespace())
    sc.store("request", request)
    kwargs = dict(_auth_kwargs(sc))
    try:
        with _adapters_for_call(sc):
            dependency = keycloak_auth.fastapi_auth(**kwargs)
            generator = dependency(request, credentials, keycloak_auth._get_async_keycloak_adapter())
            try:
                result = await anext(generator)
                sc.store("auth_context_during", AuthContextManager.get_auth_context())
            finally:
                await generator.aclose()
        sc.store("result", result)
    except BaseError as error:
        sc.store("error", error)
    sc.store("auth_context_after", AuthContextManager.get_auth_context())


@then('the keycloak auth context holds user "{username}" while the dependency is active')
def step_keycloak_auth_context_during(context, username):
    auth_context = _ctx(context).get("auth_context_during")
    assert auth_context is not None, "the auth context was not set"
    assert auth_context.username == username, f"expected {username}, got {auth_context.username}"


@then('reading "{field}" from the request state warns and names "{replacement}"')
def step_keycloak_auth_state_read_warns(context, field, replacement):
    state = _ctx(context).get("request").state
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        list(getattr(state, field))
    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecations, "reading the request state did not warn"
    message = str(deprecations[0].message)
    assert f"request.state.{field}" in message and replacement in message, message
    assert deprecations[0].filename.endswith("keycloak_auth_steps.py"), deprecations[0].filename


@then("the value the keycloak auth dependency returned does not warn when it is read")
def step_keycloak_auth_returned_value_silent(context):
    result = _ctx(context).get("result")
    assert isinstance(result, KeycloakUserInfoDTO)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result.to_dict()
    assert not [w for w in caught if issubclass(w.category, DeprecationWarning)]


@then("the request state keeps the same content as the auth context")
def step_keycloak_auth_state_matches_context(context):
    sc = _ctx(context)
    state = sc.get("request").state
    during = sc.get("auth_context_during")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert dict(state.user_info) == during.raw_user_info.to_dict()
        assert set(state.user_roles) == set(during.roles)
        assert list(state.actor_chain) == list(during.actor_chain)
        assert dict(state.token_info) == during.token_info.to_dict()
    assert during.token_info.sub == during.user_id


@then("the keycloak auth context is cleared after the dependency ends")
def step_keycloak_auth_context_after(context):
    assert _ctx(context).get("auth_context_after") is None


@then('the keycloak auth call fails with error code "{code}"')
def step_keycloak_auth_error_code(context, code):
    sc = _ctx(context)
    error = sc.get("error")
    assert error is not None, "expected an error but the call succeeded"
    assert error.code == code, f"expected {code}, got {error.code}"


@then('the keycloak auth error lists required roles "{roles}"')
def step_keycloak_auth_error_roles(context, roles):
    error = _ctx(context).get("error")
    assert sorted(error.additional_data["required_roles"]) == sorted(_split(roles))


@then('the keycloak auth error lists missing permission "{perm}"')
def step_keycloak_auth_error_missing_permission(context, perm):
    error = _ctx(context).get("error")
    assert error.additional_data["missing_permissions"] == [perm]


@then("the keycloak auth request state has an empty actor chain")
def step_keycloak_auth_state_empty_chain(context):
    assert _ctx(context).get("request").state.actor_chain == []


# gRPC


@given('the keycloak grpc auth reads the resource from request attribute "{attr}"')
def step_keycloak_auth_grpc_resource_attr(context, attr):
    _auth_kwargs(_ctx(context)).update(resource_attribute_name=attr)


@given("the keycloak auth grpc handler is a response stream")
def step_keycloak_auth_grpc_stream(context):
    _ctx(context).store("handler_stream", True)


@given("the keycloak auth grpc handler aborts the servicer context itself")
def step_keycloak_auth_grpc_handler_aborts(context):
    _ctx(context).store("handler_aborts", True)


@then('the keycloak auth servicer context was aborted exactly once with status "{status}"')
def step_keycloak_auth_aborted_once(context, status):
    sc = _ctx(context)
    assert sc.get("aborted"), f"context not aborted, error={sc.get('error')!r}"
    grpc_context = sc.get("grpc_context")
    assert grpc_context.abort_calls == 1, f"expected one abort, got {grpc_context.abort_calls}"
    assert grpc_context.abort_code == getattr(grpc.StatusCode, status)


@then('the keycloak auth error should not expose "{text}"')
def step_keycloak_auth_error_hides(context, text):
    error = _ctx(context).get("error")
    assert error is not None, "expected an error but the call succeeded"
    exposed = f"{error.additional_data} {error.get_message()}"
    assert text not in exposed, f"the error exposed {text!r}: {exposed}"


@given("the keycloak auth grpc handler crashes with a runtime failure")
def step_keycloak_auth_grpc_crash(context):
    _ctx(context).store("handler_crash", True)


def _make_handler(sc):
    calls = _handler_calls(sc)

    def handler(self, request, ctx):
        _record(calls)
        if sc.get("handler_crash"):
            raise RuntimeError("boom")
        if sc.get("handler_aborts"):
            ctx.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "slow down")
        return "handled"

    async def async_handler(self, request, ctx):
        _record(calls)
        if sc.get("handler_crash"):
            raise RuntimeError("boom")
        if sc.get("handler_aborts"):
            await ctx.abort(grpc.StatusCode.RESOURCE_EXHAUSTED, "slow down")
        return "handled"

    def stream_handler(self, request, ctx):
        _record(calls)
        yield "a"
        yield "b"

    async def async_stream_handler(self, request, ctx):
        _record(calls)
        yield "a"
        yield "b"

    if sc.get("handler_stream"):
        return stream_handler, async_stream_handler
    return handler, async_handler


def _record(calls):
    auth = AuthContextManager.get_auth_context()
    calls.append(auth)


async def _invoke_grpc(context, mode, metadata, plain=False):
    sc = _ctx(context)
    handler, async_handler = _make_handler(sc)
    kwargs = dict(_auth_kwargs(sc))
    realistic = bool(sc.get("handler_aborts"))
    if plain:
        grpc_context = _PlainContext(metadata)
    elif mode == "sync":
        grpc_context = (_RealisticSyncServicerContext if realistic else _FakeSyncServicerContext)(metadata)
    else:
        grpc_context = (_RealisticAsyncServicerContext if realistic else _FakeAsyncServicerContext)(metadata)
    sc.store("grpc_context", grpc_context)
    request = SimpleNamespace(**_request_attrs(sc))
    streaming = bool(sc.get("handler_stream"))
    try:
        with _adapters_for_call(sc):
            if mode == "sync":
                wrapped = keycloak_auth.grpc_auth(**kwargs)(handler)
                result = wrapped(object(), request, grpc_context)
                if streaming:
                    result = ",".join(result)
            else:
                wrapped = keycloak_auth.grpc_auth(**kwargs)(async_handler)
                if streaming:
                    result = ",".join([item async for item in wrapped(object(), request, grpc_context)])
                else:
                    result = await wrapped(object(), request, grpc_context)
        sc.store("handler_result", result)
    except BaseError as error:
        sc.store("error", error)
    except _Aborted:
        sc.store("aborted", True)
    except Exception as error:
        if not (realistic and (type(error) is Exception or isinstance(error, grpc.aio.AbortError))):
            raise
        sc.store("aborted", True)


@when('the keycloak auth {mode} grpc handler is invoked with bearer token "{token}"')
async def step_keycloak_auth_grpc_bearer(context, mode, token):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {token}"),))


@when('the keycloak auth {mode} grpc handler is invoked with bearer token "{token}" on a plain context')
async def step_keycloak_auth_grpc_bearer_plain(context, mode, token):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {token}"),), plain=True)


@when('the keycloak auth {mode} grpc handler is invoked with metadata key "{key}" value "{value}"')
async def step_keycloak_auth_grpc_metadata(context, mode, key, value):
    await _invoke_grpc(context, mode, ((key, value),))


@when('the keycloak auth {mode} grpc handler is invoked with duplicate bearer tokens "{first}" and "{second}"')
async def step_keycloak_auth_grpc_duplicate_tokens(context, mode, first, second):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {first}"), ("authorization", f"Bearer {second}")))


@when("the keycloak auth {mode} grpc handler is invoked without metadata")
async def step_keycloak_auth_grpc_no_metadata(context, mode):
    await _invoke_grpc(context, mode, ())


@when("the keycloak auth {mode} grpc handler is invoked without metadata on a plain context")
async def step_keycloak_auth_grpc_no_metadata_plain(context, mode):
    await _invoke_grpc(context, mode, (), plain=True)


@then('the keycloak auth grpc handler returned "{value}"')
def step_keycloak_auth_grpc_returned(context, value):
    assert _ctx(context).get("handler_result") == value


@then("the keycloak auth grpc handler did not run")
def step_keycloak_auth_grpc_not_run(context):
    assert _handler_calls(_ctx(context)) == []


@then('the keycloak auth servicer context was aborted with status "{status}"')
def step_keycloak_auth_aborted(context, status):
    sc = _ctx(context)
    assert sc.get("aborted"), f"context not aborted, error={sc.get('error')!r}"
    assert sc.get("grpc_context").abort_code == getattr(grpc.StatusCode, status)


# AuthContextManager


@given("no keycloak auth context is set")
def step_keycloak_auth_no_context(context):
    AuthContextManager.clear_auth_context()
    context.add_cleanup(AuthContextManager.clear_auth_context)


@step('the keycloak auth context is set for user "{sub}"')
def step_keycloak_auth_set_context(context, sub):
    AuthContextManager.set_auth_context(
        AuthenticatedUserDTO(
            user_id=sub,
            username=f"{sub}-name",
            email=f"{sub}@example.com",
            roles=["reader"],
            token="secret-token",
            raw_user_info={"sub": sub},
        ),
    )
    context.add_cleanup(AuthContextManager.clear_auth_context)


@when('the keycloak auth context of user "{sub}" is set and then cleared with its token')
def step_keycloak_auth_nested_context(context, sub):
    token = AuthContextManager.set_auth_context(
        AuthenticatedUserDTO(user_id=sub, username=sub, email="", roles=[], token="t", raw_user_info={"sub": sub}),
    )
    assert AuthContextManager.get_auth_context().user_id == sub
    AuthContextManager.clear_auth_context(token)


@when("the keycloak auth context is cleared by the manager")
def step_keycloak_auth_clear_context(context):
    AuthContextManager.clear_auth_context()


@then('the keycloak auth context belongs to user "{sub}"')
def step_keycloak_auth_context_user(context, sub):
    auth = AuthContextManager.get_auth_context()
    assert auth is not None and auth.user_id == sub


@then("the keycloak auth context is cleared")
def step_keycloak_auth_context_cleared(context):
    assert AuthContextManager.get_auth_context() is None


# Real Keycloak container flows


def _user_id(sc, username):
    user_id = sc.get(f"user_id_{username}")
    assert user_id, f"user {username} was not created"
    return user_id


def _access_token(sc, username):
    token = (sc.get("access_tokens") or {}).get(username)
    assert token, f"no access token obtained for user {username}"
    return token


def _expose_roles_in_userinfo(adapter):
    """Add realm and client role claims to the UserInfo response of the current realm.

    keycloak auth reads roles from UserInfo, but stock Keycloak only puts ``realm_access`` and ``resource_access``
    in the access token. The ``roles`` client scope mappers must have "Add to userinfo" enabled.
    """
    admin = adapter.admin_adapter
    roles_scope = next(scope for scope in admin.get_client_scopes() if scope["name"] == "roles")
    for mapper in admin.get_client_scope(roles_scope["id"]).get("protocolMappers", []):
        if mapper["protocolMapper"] in ("oidc-usermodel-realm-role-mapper", "oidc-usermodel-client-role-mapper"):
            mapper["config"]["userinfo.token.claim"] = "true"
            admin.update_mapper_in_client_scope(roles_scope["id"], mapper["id"], mapper)


@given('the keycloak auth access token of user "{username}" is obtained with password "{password}"')
def step_keycloak_auth_obtain_token(context, username, password):
    sc = _ctx(context)
    _expose_roles_in_userinfo(_real_sync_adapter(sc))
    token_response = _real_sync_adapter(sc).get_token(username, password)
    assert token_response and token_response.access_token, "Keycloak issued no access token"
    tokens = sc.get("access_tokens") or {}
    tokens[username] = token_response.access_token
    sc.store("access_tokens", tokens)


@given('the keycloak auth realm "{realm}" has an access token lifespan of {seconds:d} seconds')
def step_keycloak_auth_token_lifespan(context, realm, seconds):
    adapter = _real_sync_adapter(_ctx(context))
    realm_representation = dict(adapter.get_realm(realm))
    realm_representation["accessTokenLifespan"] = seconds
    adapter.update_realm(realm, **realm_representation)


@when("the keycloak auth access token lifespan has elapsed")
def step_keycloak_auth_wait_expiry(context):
    # Fixed delay (not a polling loop): the token's exp claim is the only observable.
    time.sleep(3)


@given(
    'the keycloak auth client "{client}" guards resource "{resource}" with scopes "{scopes}" '
    'and grants scope "{scope}" to realm role "{role}"',
)
def step_keycloak_auth_uma_setup(context, client, resource, scopes, scope, role):
    sc = _ctx(context)
    adapter = _real_sync_adapter(sc)
    internal_id = sc.get(f"client_{client}")["internal_client_id"]
    admin = adapter.admin_adapter

    admin_client = admin.get_client(internal_id)
    if not admin_client.get("authorizationServicesEnabled"):
        admin_client["authorizationServicesEnabled"] = True
        admin.update_client(internal_id, admin_client)

    resource_type = f"urn:{client}:resources:{resource}"
    adapter.create_client_authz_resource(
        internal_id,
        {"name": resource, "type": resource_type, "scopes": [{"name": name} for name in _split(scopes)]},
        skip_exists=True,
    )
    resource_id = next(r["_id"] for r in admin.get_client_authz_resources(internal_id) if r["name"] == resource)
    scope_id = next(s["id"] for s in admin.get_client_authz_scopes(internal_id) if s["name"] == scope)
    role_id = admin.get_realm_role(role)["id"]

    policy_name = f"{resource}-{role}-policy"
    adapter.create_client_authz_role_based_policy(
        internal_id,
        {
            "name": policy_name,
            "type": "role",
            "logic": "POSITIVE",
            "decisionStrategy": "UNANIMOUS",
            "roles": [{"id": role_id}],
        },
        skip_exists=True,
    )
    policy_id = next(p["id"] for p in admin.get_client_authz_policies(internal_id) if p["name"] == policy_name)
    permission_name = f"{resource}-{scope}-permission"
    if not any(p["name"] == permission_name for p in admin.get_client_authz_permissions(internal_id)):
        adapter.create_client_authz_scope_permission(
            {
                "name": permission_name,
                "type": "scope",
                "logic": "POSITIVE",
                "decisionStrategy": "UNANIMOUS",
                "resources": [resource_id],
                "scopes": [scope_id],
                "policies": [policy_id],
            },
            internal_id,
        )


@given('the keycloak auth request path parameter "{name}" is the id of user "{username}"')
def step_keycloak_auth_path_param_user(context, name, username):
    sc = _ctx(context)
    _path_params(sc)[name] = _user_id(sc, username)


@given('the keycloak auth grpc request attribute "{name}" is the id of user "{username}"')
def step_keycloak_auth_request_attr_user(context, name, username):
    sc = _ctx(context)
    _request_attrs(sc)[name] = _user_id(sc, username)


@when('the keycloak auth fastapi dependency is called with the access token of user "{username}"')
async def step_keycloak_auth_call_with_user_token(context, username):
    sc = _ctx(context)
    token = _access_token(sc, username)
    await _call_dependency(context, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


@when('the keycloak auth {mode} grpc handler is invoked with the bearer access token of user "{username}"')
async def step_keycloak_auth_grpc_user_bearer(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {_access_token(sc, username)}"),))


@when('the keycloak auth {mode} grpc handler is invoked with the raw access token of user "{username}"')
async def step_keycloak_auth_grpc_user_raw(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", _access_token(sc, username)),))


@then('the keycloak auth dependency returns the user info of user "{username}"')
def step_keycloak_auth_result_user(context, username):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    info = sc.get("result")
    assert info.sub == _user_id(sc, username)
    assert info.preferred_username == username
    assert info.email == f"{username}@test.com"
    assert sc.get("request").state.user_info == info.to_dict()
    assert sc.get("request").state.token_info["sub"] == info.sub


@then('the keycloak auth request state user roles include "{roles}"')
def step_keycloak_auth_state_roles_include(context, roles):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    missing = set(_split(roles)) - set(sc.get("request").state.user_roles)
    assert not missing, f"missing roles {missing}; got {sc.get('request').state.user_roles}"


@then('the keycloak auth grpc handler ran as user "{username}" with roles including "{roles}"')
def step_keycloak_auth_grpc_ran_as(context, username, roles):
    sc = _ctx(context)
    assert sc.get("error") is None and not sc.get("aborted"), f"call failed: {sc.get('error')!r}"
    calls = _handler_calls(sc)
    assert len(calls) == 1, f"handler ran {len(calls)} times"
    auth = calls[0]
    assert isinstance(auth, AuthenticatedUserDTO)
    assert auth.user_id == _user_id(sc, username), (auth.user_id, _user_id(sc, username))
    assert auth.username == username, auth.username
    assert auth.token.get_secret_value() == _access_token(sc, username), "token differs"
    assert not set(_split(roles)) - set(auth.roles), auth.roles


@when(
    'the keycloak auth {mode} grpc handler is invoked with the bearer access token of user "{username}" on a plain context',
)
async def step_keycloak_auth_grpc_user_bearer_plain(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {_access_token(sc, username)}"),), plain=True)


@when(
    'the keycloak auth {mode} grpc handler is invoked with the access token of user "{username}" under authorization scheme "{scheme}"',
)
async def step_keycloak_auth_grpc_scheme(context, mode, username, scheme):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", f"{scheme} {_access_token(sc, username)}"),))


@when(
    'the keycloak auth {mode} grpc handler is invoked with a conflicting bearer token "{other}" next to the access token of user "{username}"',
)
async def step_keycloak_auth_grpc_conflicting(context, mode, other, username):
    sc = _ctx(context)
    metadata = (("authorization", f"Bearer {_access_token(sc, username)}"), ("authorization", f"Bearer {other}"))
    await _invoke_grpc(context, mode, metadata)


# A real FastAPI app: the auth context must reach async and sync endpoints, background tasks and streamed bodies


def _caller_name():
    auth_context = AuthContextManager.get_auth_context()
    return auth_context.username if auth_context is not None else None


@given("a FastAPI app whose routes are guarded by the keycloak fastapi auth")
def step_keycloak_auth_fastapi_app(context):
    sc = _ctx(context)
    guard = keycloak_auth.fastapi_auth(**_auth_kwargs(sc))
    app = FastAPI()
    background_seen = []
    sc.store("background_seen", background_seen)

    @app.get("/async")
    async def async_route(user: dict = Depends(guard)):  # noqa: B008
        return {"username": _caller_name()}

    @app.get("/sync")
    def sync_route(user: dict = Depends(guard)):  # noqa: B008
        return {"username": _caller_name()}

    @app.get("/background")
    async def background_route(tasks: BackgroundTasks, user: dict = Depends(guard)):  # noqa: B008
        tasks.add_task(lambda: background_seen.append(_caller_name()))
        return {"username": _caller_name()}

    @app.get("/stream")
    async def stream_route(user: dict = Depends(guard)):  # noqa: B008
        async def body():
            yield f"{_caller_name()}|"
            await asyncio.sleep(0)
            yield f"{_caller_name()}"

        return StreamingResponse(body())

    @app.get("/open")
    async def open_route():
        return {"username": _caller_name()}

    sc.store("fastapi_app", app)


@when('the guarded app is requested at "{path}" with the access token of user "{username}"')
async def step_keycloak_auth_request_with_token(context, path, username):
    await _request_app(context, path, {"Authorization": f"Bearer {_access_token(_ctx(context), username)}"})


@when('the guarded app is requested at "{path}" without credentials')
async def step_keycloak_auth_request_anonymous(context, path):
    await _request_app(context, path, {})


async def _request_app(context, path, headers):
    sc = _ctx(context)
    transport = httpx.ASGITransport(app=sc.get("fastapi_app"))
    with _adapters_for_call(sc):
        async with httpx.AsyncClient(transport=transport, base_url="http://guarded") as client:
            sc.store("app_response", await client.get(path, headers=headers))


@then('the app response reports the caller "{username}" every time it reads the auth context')
def step_keycloak_auth_response_caller(context, username):
    response = _ctx(context).get("app_response")
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    reported = response.text.count(username)
    assert reported >= 1, response.text
    assert "null" not in response.text and "None" not in response.text, response.text


@then('the background task saw the caller "{username}"')
def step_keycloak_auth_background_caller(context, username):
    assert _ctx(context).get("background_seen") == [username]


@then("the app response reports no caller")
def step_keycloak_auth_response_no_caller(context):
    response = _ctx(context).get("app_response")
    assert response.status_code == 200, f"{response.status_code}: {response.text}"
    assert response.json() == {"username": None}
