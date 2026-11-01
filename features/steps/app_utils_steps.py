import asyncio
import datetime
import json
import tempfile
import warnings
from pathlib import Path
from types import SimpleNamespace

import grpc
from behave import given, then, when
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi import Depends, FastAPI, WebSocket
from fastapi.routing import APIRoute
from pydantic import BaseModel, ValidationError
from starlette.testclient import TestClient

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import FastAPIConfig, RedisMode
from archipy.configs.sections.grpc import GrpcConfig
from archipy.helpers.utils.app_utils import (
    AppUtils,
    AsyncGrpcAPIUtils,
    FastAPIUtils,
    GrpcAPIUtils,
)
from archipy.helpers.errors.fastapi import handle_fastapi_exception
from archipy.helpers.errors.fastapi.handlers import validation_response
from archipy.models.errors import BaseError, ConfigurationError, InvalidArgumentError
from features.test_helpers import get_current_scenario_context
from features.test_servers import (
    create_test_async_grpc_servicer,
    create_test_grpc_servicer,
    test_service_pb2,
    test_service_pb2_grpc,
)


async def _validation_handler(_request, exception):
    return validation_response(exception)


def _middleware_names(app) -> list[str]:
    return [middleware.cls.__name__ for middleware in app.user_middleware]


def _add_test_endpoint(app: FastAPI) -> None:
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}


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


@when("I make an OPTIONS preflight {preflight_type}")
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


@then("the response should return status code {status_code:d}")
def step_then_response_status_code(context, status_code):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")

    assert response.status_code == status_code, f"Expected {status_code} status code, but got: {response.status_code}"


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
        handle_fastapi_exception,
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

    app.add_exception_handler(ValidationError, _validation_handler)

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


def _reset_optional_middleware_config(fastapi_config) -> None:
    fastapi_config.GZIP_MIDDLEWARE_IS_ENABLED = False
    fastapi_config.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = False
    fastapi_config.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS = []
    fastapi_config.HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED = False


@given("a FastAPI app with GZip middleware enabled")
def step_given_fastapi_app_with_gzip(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)
    test_config.FASTAPI.GZIP_MIDDLEWARE_IS_ENABLED = True

    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)

    @app.get("/large")
    def large_endpoint():
        return {"data": "x" * 1000}

    @app.get("/small")
    def small_endpoint():
        return {"ok": True}

    scenario_context.store("app", app)


@given('a FastAPI app with TrustedHost middleware enabled for "{host}"')
def step_given_fastapi_app_with_trusted_host(context, host):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)
    test_config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = True
    test_config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS = [host]

    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    _add_test_endpoint(app)
    scenario_context.store("app", app)


@given("a FastAPI app with TrustedHost enabled and no allowed hosts")
def step_given_fastapi_app_trusted_host_empty_hosts(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)
    test_config.FASTAPI.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = True

    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    scenario_context.store("app", app)


@given("a FastAPI app with HTTPS redirect middleware enabled")
def step_given_fastapi_app_with_https_redirect(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)
    test_config.FASTAPI.HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED = True

    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    _add_test_endpoint(app)
    scenario_context.store("app", app)


@given("a FastAPI app with HTTPS redirect middleware disabled")
def step_given_fastapi_app_without_https_redirect(context):
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)

    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    _add_test_endpoint(app)
    scenario_context.store("app", app)


@when("I request the large payload endpoint with gzip accepted")
def step_when_request_large_payload_with_gzip(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/large", headers={"Accept-Encoding": "gzip"})
    scenario_context.store("response", response)


@when("I request the small payload endpoint with gzip accepted")
def step_when_request_small_payload_with_gzip(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/small", headers={"Accept-Encoding": "gzip"})
    scenario_context.store("response", response)


@when("I request the test endpoint")
def step_when_request_test_endpoint(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test")
    scenario_context.store("response", response)


@when('I request the test endpoint with host "{host}"')
def step_when_request_test_endpoint_with_host(context, host):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", headers={"Host": host})
    scenario_context.store("response", response)


@when("I request the test endpoint without following redirects")
def step_when_request_test_endpoint_no_redirect(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")

    client = TestClient(app)
    response = client.get("/test", follow_redirects=False)
    scenario_context.store("response", response)


@then("the app should not have GZip middleware")
def step_then_app_no_gzip_middleware(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    assert "GZipMiddleware" not in _middleware_names(app), "GZip middleware was added"


@then("the app should not have TrustedHost middleware")
def step_then_app_no_trusted_host_middleware(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    assert "TrustedHostMiddleware" not in _middleware_names(app), "TrustedHost middleware was added"


@then("the app should not have HTTPS redirect middleware")
def step_then_app_no_https_redirect_middleware(context):
    scenario_context = get_current_scenario_context(context)
    app = scenario_context.get("app")
    assert "HTTPSRedirectMiddleware" not in _middleware_names(app), "HTTPS redirect middleware was added"


@then("the response should have content-encoding gzip")
def step_then_response_has_gzip_encoding(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    assert response.headers.get("content-encoding") == "gzip", (
        f"Expected content-encoding gzip, but got: {response.headers.get('content-encoding')}"
    )


@then("the response should not have content-encoding gzip")
def step_then_response_no_gzip_encoding(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    assert response.headers.get("content-encoding") != "gzip", (
        f"Expected no gzip encoding, but got: {response.headers.get('content-encoding')}"
    )


@then("the response location should use https scheme")
def step_then_response_location_https(context):
    scenario_context = get_current_scenario_context(context)
    response = scenario_context.get("response")
    location = response.headers.get("location", "")
    assert location.startswith("https://"), f"Expected https location, but got: {location}"


class _RecordingSyncInterceptor(grpc.ServerInterceptor):
    """Real sync server interceptor that records the name of every call that passes through it."""

    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self._calls = calls

    def intercept_service(self, continuation, handler_call_details):
        self._calls.append(self.name)
        return continuation(handler_call_details)


class _RecordingAsyncInterceptor(grpc.aio.ServerInterceptor):
    """Real aio server interceptor that records the name of every call that passes through it."""

    def __init__(self, name: str, calls: list[str]) -> None:
        self.name = name
        self._calls = calls

    async def intercept_service(self, continuation, handler_call_details):
        self._calls.append(self.name)
        return await continuation(handler_call_details)


@given('custom {kind} gRPC interceptors "{names}"')
def step_given_custom_grpc_interceptors(context, kind, names):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("custom_interceptor_kind", kind)
    scenario_context.store("custom_interceptor_names", names.split(","))


def _call_sync_grpc_app(config, custom) -> None:
    server = AppUtils.create_grpc_app(config, customized_interceptors=custom)
    test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_grpc_servicer(), server)
    port = server.add_insecure_port("localhost:0")
    server.start()
    try:
        with grpc.insecure_channel(f"localhost:{port}") as channel:
            response = test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                test_service_pb2.TestRequest(data="hi"),
                timeout=5,
            )
        assert response.result == "success", response
    finally:
        server.stop(None).wait(5)


async def _call_async_grpc_app(config, custom) -> None:
    server = AppUtils.create_async_grpc_app(config, customized_interceptors=custom)
    test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_async_grpc_servicer(), server)
    port = server.add_insecure_port("localhost:0")
    await server.start()
    try:
        async with grpc.aio.insecure_channel(f"localhost:{port}") as channel:
            response = await test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                test_service_pb2.TestRequest(data="hi"),
                timeout=5,
            )
        assert response.result == "success", response
    finally:
        await server.stop(None)


@when("a {mode} gRPC app is created with the custom interceptors")
def step_when_grpc_app_created(context, mode):
    scenario_context = get_current_scenario_context(context)
    config = BaseConfig.global_config()
    calls: list[str] = []
    interceptor_class = _RecordingSyncInterceptor if mode == "sync" else _RecordingAsyncInterceptor
    interceptors = [interceptor_class(name, calls) for name in scenario_context.get("custom_interceptor_names")]
    container = {"list": list, "tuple": tuple, "set": set}[scenario_context.get("custom_interceptor_kind")]
    custom = container(interceptors)

    # A real server on a free port serves a real call, so the interceptors that ran are the ones the app applied.
    if mode == "sync":
        _call_sync_grpc_app(config, custom)
    else:
        asyncio.run(_call_async_grpc_app(config, custom))
    scenario_context.store("called_interceptors", calls)


@then('the gRPC app should run the custom interceptors in the order "{names}"')
def step_then_grpc_app_interceptor_order(context, names):
    calls = get_current_scenario_context(context).get("called_interceptors")
    assert calls == names.split(","), f"Got {calls}"


@then("the gRPC app should run all the custom interceptors")
def step_then_grpc_app_all_interceptors(context):
    scenario_context = get_current_scenario_context(context)
    calls = scenario_context.get("called_interceptors")
    assert sorted(calls) == sorted(scenario_context.get("custom_interceptor_names")), f"Got {calls}"


def _write_self_signed_certificate(directory: Path) -> tuple[Path, Path]:
    """Write a self-signed CA certificate valid for localhost and its key; return both paths."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path = directory / "cert.pem"
    key_path = directory / "key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    return cert_path, key_path


def _config_with_grpc(grpc_config: GrpcConfig) -> BaseConfig:
    return BaseConfig.global_config().model_copy(update={"GRPC": grpc_config})


def _tls_grpc_config(directory: Path, *, mtls: bool, client_cert: bool) -> BaseConfig:
    cert_path, key_path = _write_self_signed_certificate(directory)
    return _config_with_grpc(
        GrpcConfig(
            TLS_ENABLED=True,
            TLS_CERT_FILE=str(cert_path),
            TLS_KEY_FILE=str(key_path),
            TLS_CA_FILE=str(cert_path) if mtls else None,
            TLS_REQUIRE_CLIENT_AUTH=mtls,
            STUB_TLS_ENABLED=True,
            STUB_TLS_CA_FILE=str(cert_path),
            STUB_TLS_CERT_FILE=str(cert_path) if client_cert else None,
            STUB_TLS_KEY_FILE=str(key_path) if client_cert else None,
        ),
    )


def _call_tls_sync(config) -> str:
    server = AppUtils.create_grpc_app(config)
    test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_grpc_servicer(), server)
    port = AppUtils.add_grpc_port(server, config, "localhost:0")
    server.start()
    try:
        with AppUtils.create_grpc_channel(config, f"localhost:{port}") as channel:
            response = test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                test_service_pb2.TestRequest(data="hi"),
                timeout=5,
            )
        return response.result
    except grpc.RpcError:
        return "rejected"
    finally:
        server.stop(None).wait(5)


async def _call_tls_async(config) -> str:
    server = AppUtils.create_async_grpc_app(config)
    test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_async_grpc_servicer(), server)
    port = AppUtils.add_grpc_port(server, config, "localhost:0")
    await server.start()
    try:
        async with AppUtils.create_grpc_channel(config, f"localhost:{port}", aio=True) as channel:
            response = await test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                test_service_pb2.TestRequest(data="hi"),
                timeout=5,
            )
        return response.result
    except grpc.RpcError:
        return "rejected"
    finally:
        await server.stop(None)


@when("a {mode} gRPC server with TLS is called by a TLS channel with mutual TLS {mtls} and a client certificate {client}")
def step_when_grpc_tls_call(context, mode, mtls, client):
    scenario_context = get_current_scenario_context(context)
    directory = tempfile.TemporaryDirectory()
    context.add_cleanup(directory.cleanup)
    config = _tls_grpc_config(Path(directory.name), mtls=mtls == "required", client_cert=client == "presented")
    if mode == "sync":
        result = _call_tls_sync(config)
    else:
        result = asyncio.run(_call_tls_async(config))
    scenario_context.store("tls_result", result)


@then("the TLS call should be {outcome}")
def step_then_grpc_tls_outcome(context, outcome):
    result = get_current_scenario_context(context).get("tls_result")
    expected = "success" if outcome == "served" else "rejected"
    assert result == expected, f"Got {result}"


@when("a {mode} gRPC server without TLS is called by a plaintext channel")
def step_when_grpc_plaintext_call(context, mode):
    scenario_context = get_current_scenario_context(context)
    config = _config_with_grpc(GrpcConfig())
    if mode == "sync":
        server = AppUtils.create_grpc_app(config)
        test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_grpc_servicer(), server)
        port = AppUtils.add_grpc_port(server, config, "localhost:0")
        server.start()
        try:
            with AppUtils.create_grpc_channel(config, f"localhost:{port}") as channel:
                response = test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                    test_service_pb2.TestRequest(data="hi"),
                    timeout=5,
                )
        finally:
            server.stop(None).wait(5)
        result = response.result
    else:

        async def call() -> str:
            server = AppUtils.create_async_grpc_app(config)
            test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_async_grpc_servicer(), server)
            port = AppUtils.add_grpc_port(server, config, "localhost:0")
            await server.start()
            try:
                async with AppUtils.create_grpc_channel(config, f"localhost:{port}", aio=True) as channel:
                    response = await test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                        test_service_pb2.TestRequest(data="hi"),
                        timeout=5,
                    )
                return response.result
            finally:
                await server.stop(None)

        result = asyncio.run(call())
    scenario_context.store("tls_result", result)


@when("a gRPC config is built with {settings}")
def step_when_grpc_config_built(context, settings):
    scenario_context = get_current_scenario_context(context)
    keys = settings.split(",")
    values: dict[str, bool | str] = {key: True for key in keys if key in {"TLS_ENABLED", "TLS_REQUIRE_CLIENT_AUTH"}}
    values.update({key: "/nonexistent/x.pem" for key in keys if key.endswith("_FILE")})
    try:
        GrpcConfig(**values)
        scenario_context.store("grpc_config_error", None)
    except InvalidArgumentError as exception:
        scenario_context.store("grpc_config_error", str(exception))


@then("the gRPC config should be {outcome}")
def step_then_grpc_config_outcome(context, outcome):
    error = get_current_scenario_context(context).get("grpc_config_error")
    if outcome == "accepted":
        assert error is None, error
    else:
        assert error is not None, "Expected a validation error"


@given("gRPC rate limiting is enabled with fail closed set to {fail_closed} and a Redis client that cannot be created")
def step_given_rate_limit_enabled_failing_redis(context, fail_closed):
    scenario_context = get_current_scenario_context(context)
    rate_limit = BaseConfig.global_config().GRPC_RATE_LIMIT.model_copy(
        update={"IS_ENABLED": True, "FAIL_CLOSED": fail_closed == "true"},
    )
    scenario_context.store("rate_limit_config", SimpleNamespace(GRPC_RATE_LIMIT=rate_limit))

    # A sentinel-mode Redis config without a service name makes the real RedisAdapter refuse to build its clients.
    global_config = BaseConfig.global_config()
    original_redis = global_config.REDIS
    global_config.REDIS = original_redis.model_copy(update={"MODE": RedisMode.SENTINEL, "SENTINEL_SERVICE_NAME": None})

    def restore_redis() -> None:
        global_config.REDIS = original_redis

    context.add_cleanup(restore_redis)


@when("the {mode} gRPC rate limit interceptor is set up")
def step_when_rate_limit_interceptor_set_up(context, mode):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("rate_limit_config")
    setup = (
        GrpcAPIUtils.setup_rate_limit_interceptor if mode == "sync" else AsyncGrpcAPIUtils.setup_rate_limit_interceptor
    )
    interceptors: list = []
    error = None
    try:
        setup(config, interceptors)
    except InvalidArgumentError as exc:
        error = exc
    scenario_context.store("setup_error", error)
    scenario_context.store("setup_interceptors", interceptors)


@then("the gRPC rate limit setup should raise the initialization error")
def step_then_rate_limit_setup_raises(context):
    error = get_current_scenario_context(context).get("setup_error")
    assert isinstance(error, InvalidArgumentError), f"Got {error!r}"


@then("the gRPC rate limit setup should continue without the interceptor")
def step_then_rate_limit_setup_continues(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("setup_error") is None
    assert scenario_context.get("setup_interceptors") == []


def _add_echo_websocket(app: FastAPI) -> None:
    @app.websocket("/ws")
    async def echo(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("connected")
        await websocket.close()


def _store_websocket_app(context, configure) -> None:
    scenario_context = get_current_scenario_context(context)
    test_config = BaseConfig.global_config()
    _reset_optional_middleware_config(test_config.FASTAPI)
    configure(test_config.FASTAPI)
    app = AppUtils.create_fastapi_app(test_config, configure_exception_handlers=False)
    _add_echo_websocket(app)
    scenario_context.store("app", app)


@given('a FastAPI app with TrustedHost middleware enabled for "{host}" and an echo WebSocket')
def step_given_trusted_host_websocket_app(context, host):
    def configure(fastapi_config):
        fastapi_config.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED = True
        fastapi_config.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS = [host]

    _store_websocket_app(context, configure)


@given("a FastAPI app with HTTPS redirect middleware {state} and an echo WebSocket")
def step_given_https_redirect_websocket_app(context, state):
    _store_websocket_app(
        context,
        lambda fastapi_config: setattr(fastapi_config, "HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED", state == "enabled"),
    )


@when('a WebSocket client connects with the host "{host}"')
def step_when_websocket_connects_with_host(context, host):
    scenario_context = get_current_scenario_context(context)
    client = TestClient(get_current_scenario_context(context).get("app"))
    try:
        with client.websocket_connect("/ws", headers={"host": host}) as websocket:
            scenario_context.store("ws_message", websocket.receive_text())
        scenario_context.store("ws_handshake", "accepted")
    except Exception:  # noqa: BLE001 - a refused handshake raises WebSocketDisconnect or a denial response
        scenario_context.store("ws_handshake", "refused")


@then("the WebSocket handshake should be {outcome}")
def step_then_websocket_handshake_outcome(context, outcome):
    assert get_current_scenario_context(context).get("ws_handshake") == outcome


@given("a configuration built from:")
def step_given_config_built_from(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("built_config", BaseConfig(**json.loads(context.text)))


@when("the uvicorn arguments are built")
def step_when_uvicorn_arguments_built(context):
    scenario_context = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        arguments = AppUtils.uvicorn_config(scenario_context.get("built_config"))
    scenario_context.store("uvicorn_arguments", arguments)
    scenario_context.store("caught_warnings", [str(item.message) for item in caught if item.category is DeprecationWarning])


@then('the uvicorn argument "{name}" is {value}')
def step_then_uvicorn_argument(context, name, value):
    arguments = get_current_scenario_context(context).get("uvicorn_arguments")
    assert arguments[name] == json.loads(value), arguments


@then('the uvicorn arguments leave out "{name}"')
def step_then_uvicorn_arguments_leave_out(context, name):
    arguments = get_current_scenario_context(context).get("uvicorn_arguments")
    assert name not in arguments, arguments


@then("no deprecation warning is raised")
def step_then_no_deprecation_warning(context):
    assert get_current_scenario_context(context).get("caught_warnings") == []


@then('a deprecation warning mentions "{text}"')
def step_then_deprecation_warning_mentions(context, text):
    messages = get_current_scenario_context(context).get("caught_warnings")
    assert any(text in message for message in messages), messages


@then('building a configuration from the following fails with "{reason}":')
def step_then_config_build_fails(context, reason):
    try:
        BaseConfig(**json.loads(context.text))
    except ConfigurationError as error:
        assert error.additional_data["reason"] == reason, error.additional_data
    else:
        raise AssertionError("the config was accepted")


@when("the FASTAPI section is built with a deprecated uvicorn field")
def step_when_fastapi_section_built(context):
    scenario_context = get_current_scenario_context(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        FastAPIConfig(TIMEOUT_KEEP_ALIVE=9)
    scenario_context.store("caught_warnings", [str(item.message) for item in caught if item.category is DeprecationWarning])


@when('the {section} field "{name}" is read')
def step_when_config_field_read(context, section, name):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("built_config")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        getattr(getattr(config, section), name)
    scenario_context.store(
        "caught_warnings",
        [str(item.message) for item in caught if item.category is DeprecationWarning],
    )


@when('the UVICORN field "{name}" is read and the FASTAPI section is dumped')
def step_when_uvicorn_field_read_and_fastapi_dumped(context, name):
    scenario_context = get_current_scenario_context(context)
    config = scenario_context.get("built_config")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        getattr(config.UVICORN, name)
        config.FASTAPI.model_dump()
        repr(config.FASTAPI)
    scenario_context.store(
        "caught_warnings",
        [str(item.message) for item in caught if item.category is DeprecationWarning],
    )


@then('the JSON schema of the FASTAPI section marks "{name}" as deprecated')
def step_then_fastapi_schema_deprecated(context, name):
    schema = FastAPIConfig.model_json_schema()
    assert schema["properties"][name].get("deprecated") is True, schema["properties"][name]


def _compression_grpc_config(compression: str) -> BaseConfig:
    return _config_with_grpc(
        GrpcConfig(
            SERVER_COMPRESSION=compression,
            STUB_COMPRESSION=compression,
            SHUTDOWN_GRACE_SECONDS=2,
            SERVER_OPTIONS_CONFIG_LIST=[("grpc.primary_user_agent", "archipy-server"), ("grpc.max_metadata_size", 16384)],
            STUB_OPTIONS_CONFIG_LIST=[("grpc.primary_user_agent", "archipy-stub"), ("grpc.max_metadata_size", 16384)],
        ),
    )


def _probe_stopped_channel(config, port: int) -> str:
    try:
        with AppUtils.create_grpc_channel(config, f"localhost:{port}") as channel:
            test_service_pb2_grpc.TestServiceStub(channel).TestMethod(test_service_pb2.TestRequest(data="hi"), timeout=2)
    except grpc.RpcError:
        return "rejected"
    return "served"


@when(
    "a {mode} gRPC server with {compression} compression and a string option is called by a channel with the same "
    "settings",
)
def step_when_grpc_compression_call(context, mode, compression):
    scenario_context = get_current_scenario_context(context)
    config = _compression_grpc_config(compression)
    assert config.GRPC.SHUTDOWN_GRACE_SECONDS == 2
    if mode == "sync":
        server = AppUtils.create_grpc_app(config)
        test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_grpc_servicer(), server)
        port = AppUtils.add_grpc_port(server, config, "localhost:0")
        server.start()
        try:
            with AppUtils.create_grpc_channel(config, f"localhost:{port}") as channel:
                result = test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                    test_service_pb2.TestRequest(data="hi"),
                    timeout=5,
                ).result
        finally:
            AppUtils.stop_grpc_app(server, config).wait(5)
    else:

        async def call() -> tuple[str, int]:
            server = AppUtils.create_async_grpc_app(config)
            test_service_pb2_grpc.add_TestServiceServicer_to_server(create_test_async_grpc_servicer(), server)
            port = AppUtils.add_grpc_port(server, config, "localhost:0")
            await server.start()
            try:
                async with AppUtils.create_grpc_channel(config, f"localhost:{port}", aio=True) as channel:
                    response = await test_service_pb2_grpc.TestServiceStub(channel).TestMethod(
                        test_service_pb2.TestRequest(data="hi"),
                        timeout=5,
                    )
                return response.result, port
            finally:
                await AppUtils.stop_grpc_app(server, config)

        result, port = asyncio.run(call())
    scenario_context.store("tls_result", result)
    scenario_context.store("stopped_probe", _probe_stopped_channel(config, port))


@then("a call to the stopped gRPC server should be rejected")
def step_then_stopped_grpc_call_rejected(context):
    assert get_current_scenario_context(context).get("stopped_probe") == "rejected"


@when("the gRPC config field {field} is set to {value}")
def step_when_grpc_config_field_set(context, field, value):
    scenario_context = get_current_scenario_context(context)
    try:
        GrpcConfig(**{field: value})
        scenario_context.store("grpc_field_error", None)
    except ValidationError as exception:
        scenario_context.store("grpc_field_error", str(exception))


@then("the gRPC field setting should be {outcome}")
def step_then_grpc_field_outcome(context, outcome):
    error = get_current_scenario_context(context).get("grpc_field_error")
    if outcome == "accepted":
        assert error is None, error
    else:
        assert error is not None, "Expected a validation error"
