from types import SimpleNamespace
from unittest.mock import patch

import grpc
import grpc.aio
from behave import given, step, then, when
from fastapi.security import HTTPAuthorizationCredentials

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


class _PlainContext:
    """Not a gRPC servicer context: only exposes metadata."""

    def __init__(self, metadata):
        self._metadata = metadata

    def invocation_metadata(self):
        return self._metadata


class _StubKeycloak:
    """Scripted Keycloak adapter boundary (sync)."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.configs = SimpleNamespace(CLIENT_ID=CLIENT_ID)

    def validate_token(self, token):
        return token in self.tokens and self.tokens[token]["valid"]

    def get_token_info(self, token):
        return self.tokens.get(token, {}).get("token_info")

    def get_userinfo(self, token):
        return self.tokens.get(token, {}).get("userinfo")

    def check_permissions_batch(self, token, permissions):
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
    return scenario_context.get("auth_kwargs")


@given("a keycloak utils stub adapter is installed")
def step_keycloak_utils_install_stub(context):
    sc = _ctx(context)
    tokens = {}
    sc.store("tokens", tokens)
    sc.store("auth_kwargs", {})
    sc.store("path_params", {})
    sc.store("handler_calls", [])
    sync_stub = _StubKeycloak(tokens)
    async_stub = _AsyncStubKeycloak(tokens)
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


@given('the keycloak utils stub token "{token}" has client role "{role}"')
def step_keycloak_utils_client_role(context, token, role):
    userinfo = _ctx(context).get("tokens")[token]["userinfo"]
    userinfo["resource_access"] = {CLIENT_ID: {"roles": [role]}}


@given('the keycloak utils stub treats token "{token}" as invalid')
def step_keycloak_utils_invalid_token(context, token):
    _ctx(context).get("tokens")[token] = {"valid": False, "token_info": None, "userinfo": None}


@given('the keycloak utils stub has no token info for token "{token}"')
def step_keycloak_utils_no_token_info(context, token):
    _ctx(context).get("tokens")[token]["token_info"] = {}


@given('the keycloak utils stub has no userinfo for token "{token}"')
def step_keycloak_utils_no_userinfo(context, token):
    _ctx(context).get("tokens")[token]["userinfo"] = {}


@given('the keycloak utils stub grants permissions "{perms}" to token "{token}"')
def step_keycloak_utils_grant_permissions(context, perms, token):
    _ctx(context).get("tokens")[token]["granted"] = {tuple(p.split("#")) for p in _split(perms)}


@given('the keycloak utils stub token "{token}" carries actor chain "{chain}"')
def step_keycloak_utils_actor_chain(context, token, chain):
    act = None
    for entry in reversed(_split(chain)):
        kind, ident = entry.split(":")
        node = {"sub": ident} if kind == "user" else {"client_id": ident}
        if act:
            node["act"] = act
        act = node
    _ctx(context).get("tokens")[token]["token_info"]["act"] = act


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
    _ctx(context).get("path_params")[name] = value


@when('the keycloak utils {mode} fastapi dependency is called with token "{token}"')
async def step_keycloak_utils_call_dependency(context, mode, token):
    await _call_dependency(context, mode, HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


@when("the keycloak utils {mode} fastapi dependency is called without credentials")
async def step_keycloak_utils_call_dependency_anonymous(context, mode):
    await _call_dependency(context, mode, None)


async def _call_dependency(context, mode, credentials):
    sc = _ctx(context)
    request = SimpleNamespace(path_params=dict(sc.get("path_params")), state=SimpleNamespace())
    sc.store("request", request)
    kwargs = dict(_auth_kwargs(sc))
    try:
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


@then('the keycloak utils request state actor chain is "{chain}"')
def step_keycloak_utils_state_chain(context, chain):
    actors = _ctx(context).get("request").state.actor_chain
    assert ",".join(f"{a.type.value}:{a.id}" for a in actors) == chain


# gRPC


@given('the keycloak utils grpc auth reads the resource from request attribute "{attr}"')
def step_keycloak_utils_grpc_resource_attr(context, attr):
    _auth_kwargs(_ctx(context)).update(resource_attribute_name=attr)


@given("the keycloak utils grpc handler crashes with a runtime failure")
def step_keycloak_utils_grpc_crash(context):
    _ctx(context).store("handler_crash", True)


def _make_handler(sc):
    calls = sc.get("handler_calls")

    def handler(self, request, ctx):
        _record(calls)
        if sc.get("handler_crash"):
            raise RuntimeError("boom")
        return "handled"

    async def async_handler(self, request, ctx):
        return handler(self, request, ctx)

    return handler, async_handler


def _record(calls):
    auth = AuthContextManager.get_auth_context()
    calls.append(auth)


async def _invoke_grpc(context, mode, metadata, plain=False):
    sc = _ctx(context)
    handler, async_handler = _make_handler(sc)
    kwargs = dict(_auth_kwargs(sc))
    if plain:
        grpc_context = _PlainContext(metadata)
    elif mode == "sync":
        grpc_context = _FakeSyncServicerContext(metadata)
    else:
        grpc_context = _FakeAsyncServicerContext(metadata)
    sc.store("grpc_context", grpc_context)
    request = SimpleNamespace()
    try:
        if mode == "sync":
            wrapped = KeycloakUtils.grpc_auth(**kwargs)(handler)
            result = wrapped(object(), request, grpc_context)
        else:
            wrapped = KeycloakUtils.async_grpc_auth(**kwargs)(async_handler)
            result = await wrapped(object(), request, grpc_context)
        sc.store("handler_result", result)
    except BaseError as error:
        sc.store("error", error)
    except _Aborted:
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
    calls = sc.get("handler_calls")
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
    assert _ctx(context).get("handler_calls") == []


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
