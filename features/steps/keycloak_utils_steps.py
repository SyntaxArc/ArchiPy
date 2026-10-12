import time
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import grpc
import grpc.aio
from behave import given, step, then, when
from fastapi.security import HTTPAuthorizationCredentials

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter
from archipy.helpers.utils import keycloak_utils
from archipy.helpers.utils.keycloak_utils import AuthContextManager, KeycloakUtils
from archipy.models.dtos.keycloak_dtos import AuthenticatedUserDTO
from archipy.models.errors import BaseError
from features.test_helpers import get_current_scenario_context

CLIENT_ID = "archipy-client"


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


class _StubKeycloak:
    """Scripted Keycloak adapter boundary (sync)."""

    def __init__(self, tokens, calls=None):
        self.tokens = tokens
        self.calls = calls if calls is not None else {}
        self.configs = SimpleNamespace(CLIENT_ID=CLIENT_ID)

    def validate_token(self, token):
        return token in self.tokens and self.tokens[token]["valid"]

    def get_token_info(self, token):
        return self.tokens.get(token, {}).get("token_info")

    def get_userinfo(self, token):
        self.calls["userinfo"] = self.calls.get("userinfo", 0) + 1
        return self.tokens.get(token, {}).get("userinfo")

    def check_permissions_batch(self, token, permissions):
        self.calls["permissions"] = self.calls.get("permissions", 0) + 1
        granted = self.tokens.get(token, {}).get("granted", set())
        return {p for p in permissions if p in granted}


class _AsyncStubKeycloak(_StubKeycloak):
    async def validate_token(self, token):
        return super().validate_token(token)

    async def get_token_info(self, token):
        return super().get_token_info(token)

    async def get_userinfo(self, token):
        return super().get_userinfo(token)

    async def check_permissions_batch(self, token, permissions):
        return super().check_permissions_batch(token, permissions)


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
    """Point KeycloakUtils at adapters configured for the real Keycloak container client.

    The sync adapter is the scenario adapter created by the keycloak adapter steps. The async adapter is built
    fresh from the same configuration so it binds to the running event loop.
    """
    sync_adapter = _real_sync_adapter(scenario_context)
    async_adapter = AsyncKeycloakAdapter(sync_adapter.configs.model_copy())
    with (
        patch.object(keycloak_utils, "_shared_sync_adapter", lambda: sync_adapter),
        patch.object(keycloak_utils, "_shared_async_adapter", lambda: async_adapter),
    ):
        yield


@contextmanager
def _adapters_for_call(scenario_context):
    if scenario_context.get("stub_installed"):
        yield
    else:
        with _real_keycloak_adapters(scenario_context):
            yield


@given("a keycloak utils stub adapter is installed")
def step_keycloak_utils_install_stub(context):
    sc = _ctx(context)
    tokens = {}
    sc.store("tokens", tokens)
    sc.store("stub_installed", True)
    calls = {}
    sync_stub = _StubKeycloak(tokens, calls)
    async_stub = _AsyncStubKeycloak(tokens, calls)
    sc.store("stubs", (sync_stub, async_stub))
    sc.store("stub_calls", calls)
    keycloak_utils.clear_keycloak_remote_cache()
    context.add_cleanup(keycloak_utils.clear_keycloak_remote_cache)
    for name, stub in (("_shared_sync_adapter", sync_stub), ("_shared_async_adapter", async_stub)):
        patcher = patch.object(keycloak_utils, name, lambda stub=stub: stub)
        patcher.start()
        context.add_cleanup(patcher.stop)
    AuthContextManager.clear_auth_context()
    context.add_cleanup(AuthContextManager.clear_auth_context)


@given('the keycloak utils stub accepts token "{token}" for user "{sub}" with realm roles "{roles}"')
def step_keycloak_utils_accept_token(context, token, sub, roles):
    _ctx(context).get("tokens")[token] = {
        "valid": True,
        "token_info": {"sub": sub},
        "userinfo": {
            "sub": sub,
            "preferred_username": f"{sub}-name",
            "email": f"{sub}@example.com",
            "realm_access": {"roles": _split(roles)},
        },
        "granted": set(),
    }


@given('the keycloak utils stub has no token info for token "{token}"')
def step_keycloak_utils_no_token_info(context, token):
    _ctx(context).get("tokens")[token]["token_info"] = {}


@given('the keycloak utils stub has no userinfo for token "{token}"')
def step_keycloak_utils_no_userinfo(context, token):
    _ctx(context).get("tokens")[token]["userinfo"] = {}


@given("the keycloak utils stub caches remote lookups for {seconds:g} seconds")
def step_keycloak_utils_stub_cache_ttl(context, seconds):
    for stub in _ctx(context).get("stubs"):
        stub.configs.REMOTE_CACHE_TTL_SECONDS = seconds


@given('the keycloak utils stub grants permission "{perm}" to token "{token}"')
def step_keycloak_utils_stub_grants(context, perm, token):
    _ctx(context).get("tokens")[token]["granted"].add(tuple(perm.split("#")))


@when('the keycloak utils stub revokes userinfo for token "{token}"')
def step_keycloak_utils_stub_revokes_userinfo(context, token):
    _ctx(context).get("tokens")[token]["userinfo"] = {}


@when('the keycloak utils stub revokes permission "{perm}" from token "{token}"')
def step_keycloak_utils_stub_revokes_permission(context, perm, token):
    _ctx(context).get("tokens")[token]["granted"].discard(tuple(perm.split("#")))


@when("the keycloak utils cached lookups expire")
def step_keycloak_utils_cache_expires(context):
    with keycloak_utils._remote_cache_lock:
        for key, (_, value) in list(keycloak_utils._remote_cache.items()):
            keycloak_utils._remote_cache[key] = (0.0, value)


@then('the keycloak utils stub served {count:d} "{kind}" lookups')
def step_keycloak_utils_lookup_count(context, count, kind):
    actual = _ctx(context).get("stub_calls").get(kind, 0)
    assert actual == count, f"Expected {count} {kind} lookups, got {actual}"


@given('the keycloak utils {surface} auth requires any of roles "{roles}"')
def step_keycloak_utils_any_roles(context, surface, roles):
    _auth_kwargs(_ctx(context)).update(required_roles=frozenset(_split(roles)), all_roles_required=False)


@given('the keycloak utils fastapi auth requires all roles "{roles}"')
def step_keycloak_utils_all_roles(context, roles):
    _auth_kwargs(_ctx(context)).update(required_roles=frozenset(_split(roles)), all_roles_required=True)


@given('the keycloak utils fastapi auth requires permissions "{perms}"')
def step_keycloak_utils_required_permissions(context, perms):
    pairs = tuple(tuple(p.split("#")) for p in _split(perms))
    _auth_kwargs(_ctx(context)).update(required_permissions=pairs)


@given('the keycloak utils fastapi auth guards resource type "{rtype}" by path parameter "{param}"')
def step_keycloak_utils_guard_resource(context, rtype, param):
    _auth_kwargs(_ctx(context)).update(resource_type=rtype, resource_type_param=param)


@given('the keycloak utils fastapi auth treats roles "{roles}" as admin roles')
def step_keycloak_utils_admin_roles(context, roles):
    _auth_kwargs(_ctx(context)).update(admin_roles=frozenset(_split(roles)))


@given('the keycloak utils request path parameter "{name}" is "{value}"')
def step_keycloak_utils_path_param(context, name, value):
    _path_params(_ctx(context))[name] = value


@when('the keycloak utils {mode} fastapi dependency is called with token "{token}"')
async def step_keycloak_utils_call_dependency(context, mode, token):
    await _call_dependency(context, mode, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


@when("the keycloak utils {mode} fastapi dependency is called without credentials")
async def step_keycloak_utils_call_dependency_anonymous(context, mode):
    await _call_dependency(context, mode, None)


async def _call_dependency(context, mode, credentials):
    sc = _ctx(context)
    request = SimpleNamespace(path_params=dict(_path_params(sc)), state=SimpleNamespace())
    sc.store("request", request)
    kwargs = dict(_auth_kwargs(sc))
    try:
        with _adapters_for_call(sc):
            if mode == "sync":
                dependency = KeycloakUtils.fastapi_auth(**kwargs)
                result = dependency(request, credentials, KeycloakUtils._get_keycloak_adapter())
            else:
                dependency = KeycloakUtils.async_fastapi_auth(**kwargs)
                result = await dependency(request, credentials, KeycloakUtils._get_async_keycloak_adapter())
        sc.store("result", result)
    except BaseError as error:
        sc.store("error", error)


@then('the keycloak utils call fails with error code "{code}"')
def step_keycloak_utils_error_code(context, code):
    sc = _ctx(context)
    error = sc.get("error")
    assert error is not None, "expected an error but the call succeeded"
    assert error.code == code, f"expected {code}, got {error.code}"


@then('the keycloak utils error lists required roles "{roles}"')
def step_keycloak_utils_error_roles(context, roles):
    error = _ctx(context).get("error")
    assert sorted(error.additional_data["required_roles"]) == sorted(_split(roles))


@then('the keycloak utils error lists missing permission "{perm}"')
def step_keycloak_utils_error_missing_permission(context, perm):
    error = _ctx(context).get("error")
    assert error.additional_data["missing_permissions"] == [perm]


@then('the keycloak utils dependency returns user info with subject "{sub}"')
def step_keycloak_utils_result_subject(context, sub):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    assert sc.get("result")["sub"] == sub
    assert sc.get("request").state.user_info["sub"] == sub


@then('the keycloak utils request state has user roles "{roles}"')
def step_keycloak_utils_state_roles(context, roles):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    assert sorted(sc.get("request").state.user_roles) == sorted(_split(roles))


@then("the keycloak utils request state has an empty actor chain")
def step_keycloak_utils_state_empty_chain(context):
    assert _ctx(context).get("request").state.actor_chain == []


# gRPC


@given('the keycloak utils grpc auth reads the resource from request attribute "{attr}"')
def step_keycloak_utils_grpc_resource_attr(context, attr):
    _auth_kwargs(_ctx(context)).update(resource_attribute_name=attr)


@given("the keycloak utils grpc handler is a response stream")
def step_keycloak_utils_grpc_stream(context):
    _ctx(context).store("handler_stream", True)


@given("the keycloak utils grpc handler aborts the servicer context itself")
def step_keycloak_utils_grpc_handler_aborts(context):
    _ctx(context).store("handler_aborts", True)


@then('the keycloak utils servicer context was aborted exactly once with status "{status}"')
def step_keycloak_utils_aborted_once(context, status):
    sc = _ctx(context)
    assert sc.get("aborted"), f"context not aborted, error={sc.get('error')!r}"
    grpc_context = sc.get("grpc_context")
    assert grpc_context.abort_calls == 1, f"expected one abort, got {grpc_context.abort_calls}"
    assert grpc_context.abort_code == getattr(grpc.StatusCode, status)


@then('the keycloak utils error should not expose "{text}"')
def step_keycloak_utils_error_hides(context, text):
    error = _ctx(context).get("error")
    assert error is not None, "expected an error but the call succeeded"
    exposed = f"{error.additional_data} {error.get_message()}"
    assert text not in exposed, f"the error exposed {text!r}: {exposed}"


@given("the keycloak utils grpc handler crashes with a runtime failure")
def step_keycloak_utils_grpc_crash(context):
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
                wrapped = KeycloakUtils.grpc_auth(**kwargs)(handler)
                result = wrapped(object(), request, grpc_context)
                if streaming:
                    result = ",".join(result)
            else:
                wrapped = KeycloakUtils.async_grpc_auth(**kwargs)(async_handler)
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


@when('the keycloak utils {mode} grpc handler is invoked with bearer token "{token}"')
async def step_keycloak_utils_grpc_bearer(context, mode, token):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {token}"),))


@when('the keycloak utils {mode} grpc handler is invoked with bearer token "{token}" on a plain context')
async def step_keycloak_utils_grpc_bearer_plain(context, mode, token):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {token}"),), plain=True)


@when('the keycloak utils {mode} grpc handler is invoked with metadata key "{key}" value "{value}"')
async def step_keycloak_utils_grpc_metadata(context, mode, key, value):
    await _invoke_grpc(context, mode, ((key, value),))


@when('the keycloak utils {mode} grpc handler is invoked with duplicate bearer tokens "{first}" and "{second}"')
async def step_keycloak_utils_grpc_duplicate_tokens(context, mode, first, second):
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {first}"), ("authorization", f"Bearer {second}")))


@when("the keycloak utils {mode} grpc handler is invoked without metadata")
async def step_keycloak_utils_grpc_no_metadata(context, mode):
    await _invoke_grpc(context, mode, ())


@when("the keycloak utils {mode} grpc handler is invoked without metadata on a plain context")
async def step_keycloak_utils_grpc_no_metadata_plain(context, mode):
    await _invoke_grpc(context, mode, (), plain=True)


@then('the keycloak utils grpc handler ran with user "{sub}" and roles "{roles}"')
def step_keycloak_utils_grpc_ran(context, sub, roles):
    sc = _ctx(context)
    assert sc.get("error") is None and not sc.get("aborted"), f"call failed: {sc.get('error')!r}"
    calls = _handler_calls(sc)
    assert len(calls) == 1
    auth = calls[0]
    assert isinstance(auth, AuthenticatedUserDTO)
    assert auth.user_id == sub
    assert sorted(auth.roles) == sorted(_split(roles))


@then('the keycloak utils grpc handler returned "{value}"')
def step_keycloak_utils_grpc_returned(context, value):
    assert _ctx(context).get("handler_result") == value


@then("the keycloak utils grpc handler did not run")
def step_keycloak_utils_grpc_not_run(context):
    assert _handler_calls(_ctx(context)) == []


@then('the keycloak utils servicer context was aborted with status "{status}"')
def step_keycloak_utils_aborted(context, status):
    sc = _ctx(context)
    assert sc.get("aborted"), f"context not aborted, error={sc.get('error')!r}"
    assert sc.get("grpc_context").abort_code == getattr(grpc.StatusCode, status)


# AuthContextManager


@given("no keycloak utils auth context is set")
def step_keycloak_utils_no_context(context):
    AuthContextManager.clear_auth_context()
    context.add_cleanup(AuthContextManager.clear_auth_context)


@step('the keycloak utils auth context is set for user "{sub}"')
def step_keycloak_utils_set_context(context, sub):
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


@when("the keycloak utils auth context is cleared by the manager")
def step_keycloak_utils_clear_context(context):
    AuthContextManager.clear_auth_context()


@then('the keycloak utils auth context belongs to user "{sub}"')
def step_keycloak_utils_context_user(context, sub):
    auth = AuthContextManager.get_auth_context()
    assert auth is not None and auth.user_id == sub


@then("the keycloak utils auth context is cleared")
def step_keycloak_utils_context_cleared(context):
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

    KeycloakUtils reads roles from UserInfo, but stock Keycloak only puts ``realm_access`` and ``resource_access``
    in the access token. The ``roles`` client scope mappers must have "Add to userinfo" enabled.
    """
    admin = adapter.admin_adapter
    roles_scope = next(scope for scope in admin.get_client_scopes() if scope["name"] == "roles")
    for mapper in admin.get_client_scope(roles_scope["id"]).get("protocolMappers", []):
        if mapper["protocolMapper"] in ("oidc-usermodel-realm-role-mapper", "oidc-usermodel-client-role-mapper"):
            mapper["config"]["userinfo.token.claim"] = "true"
            admin.update_mapper_in_client_scope(roles_scope["id"], mapper["id"], mapper)


@given('the keycloak utils access token of user "{username}" is obtained with password "{password}"')
def step_keycloak_utils_obtain_token(context, username, password):
    sc = _ctx(context)
    _expose_roles_in_userinfo(_real_sync_adapter(sc))
    token_response = _real_sync_adapter(sc).get_token(username, password)
    assert token_response and token_response.get("access_token"), "Keycloak issued no access token"
    tokens = sc.get("access_tokens") or {}
    tokens[username] = token_response["access_token"]
    sc.store("access_tokens", tokens)


@given('the keycloak utils realm "{realm}" has an access token lifespan of {seconds:d} seconds')
def step_keycloak_utils_token_lifespan(context, realm, seconds):
    adapter = _real_sync_adapter(_ctx(context))
    realm_representation = dict(adapter.get_realm(realm))
    realm_representation["accessTokenLifespan"] = seconds
    adapter.update_realm(realm, **realm_representation)


@when("the keycloak utils access token lifespan has elapsed")
def step_keycloak_utils_wait_expiry(context):
    # Fixed delay (not a polling loop): the token's exp claim is the only observable.
    time.sleep(3)


@given(
    'the keycloak utils client "{client}" guards resource "{resource}" with scopes "{scopes}" '
    'and grants scope "{scope}" to realm role "{role}"',
)
def step_keycloak_utils_uma_setup(context, client, resource, scopes, scope, role):
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


@given('the keycloak utils request path parameter "{name}" is the id of user "{username}"')
def step_keycloak_utils_path_param_user(context, name, username):
    sc = _ctx(context)
    _path_params(sc)[name] = _user_id(sc, username)


@given('the keycloak utils grpc request attribute "{name}" is the id of user "{username}"')
def step_keycloak_utils_request_attr_user(context, name, username):
    sc = _ctx(context)
    _request_attrs(sc)[name] = _user_id(sc, username)


@when('the keycloak utils {mode} fastapi dependency is called with the access token of user "{username}"')
async def step_keycloak_utils_call_with_user_token(context, mode, username):
    sc = _ctx(context)
    token = _access_token(sc, username)
    await _call_dependency(context, mode, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


@when('the keycloak utils {mode} grpc handler is invoked with the bearer access token of user "{username}"')
async def step_keycloak_utils_grpc_user_bearer(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {_access_token(sc, username)}"),))


@when('the keycloak utils {mode} grpc handler is invoked with the raw access token of user "{username}"')
async def step_keycloak_utils_grpc_user_raw(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", _access_token(sc, username)),))


@then('the keycloak utils dependency returns the user info of user "{username}"')
def step_keycloak_utils_result_user(context, username):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    info = sc.get("result")
    assert info["sub"] == _user_id(sc, username)
    assert info["preferred_username"] == username
    assert info["email"] == f"{username}@test.com"
    assert sc.get("request").state.user_info == info
    assert sc.get("request").state.token_info["sub"] == info["sub"]


@then('the keycloak utils request state user roles include "{roles}"')
def step_keycloak_utils_state_roles_include(context, roles):
    sc = _ctx(context)
    assert sc.get("error") is None, f"unexpected error {sc.get('error')!r}"
    missing = set(_split(roles)) - set(sc.get("request").state.user_roles)
    assert not missing, f"missing roles {missing}; got {sc.get('request').state.user_roles}"


@then('the keycloak utils grpc handler ran as user "{username}" with roles including "{roles}"')
def step_keycloak_utils_grpc_ran_as(context, username, roles):
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
    'the keycloak utils {mode} grpc handler is invoked with the bearer access token of user "{username}" on a plain context',
)
async def step_keycloak_utils_grpc_user_bearer_plain(context, mode, username):
    sc = _ctx(context)
    await _invoke_grpc(context, mode, (("authorization", f"Bearer {_access_token(sc, username)}"),), plain=True)
