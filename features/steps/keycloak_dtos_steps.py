import datetime
import warnings
from pathlib import Path
from tempfile import mkdtemp

from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from pydantic import ValidationError

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter
from archipy.configs.sections.keycloak import KeycloakConfig

from archipy.adapters.keycloak._base import to_mutation_result, to_request_payload, with_created_id

from archipy.models.dtos.keycloak.common_dtos import KeycloakMutationResultDTO
from archipy.models.dtos.keycloak import authz_dtos, common_dtos, client_scope_dtos, component_dtos, group_dtos, role_dtos, user_dtos
from archipy.models.dtos.keycloak import organization_dtos, token_dtos, uma_dtos

_MODULES = (
    common_dtos,
    authz_dtos,
    client_scope_dtos,
    component_dtos,
    group_dtos,
    organization_dtos,
    role_dtos,
    token_dtos,
    uma_dtos,
    user_dtos,
)


def _dto_class(name):
    for module in _MODULES:
        if hasattr(module, name):
            return getattr(module, name)
    raise AssertionError(f"unknown Keycloak DTO {name}")


@given('a Keycloak {dto} response with an unknown field "{field}"')
def step_response_with_unknown_field(context, dto, field):
    sc = get_current_scenario_context(context)
    sc.store("response", _dto_class(dto).model_validate({field: "value"}))


@then('the {dto} response keeps "{field}" in its extra fields')
def step_response_keeps_extra(context, dto, field):
    response = get_current_scenario_context(context).get("response")
    assert response.model_extra == {field: "value"}, response.model_extra


@when('a Keycloak {dto} is built with an unknown field "{field}"')
def step_build_with_unknown_field(context, dto, field):
    sc = get_current_scenario_context(context)
    try:
        _dto_class(dto).model_validate({field: "value"})
    except ValidationError as e:
        sc.store("validation_error", e)
    else:
        sc.store("validation_error", None)


@then("building the {dto} fails with a validation error")
def step_build_fails(context, dto):
    assert get_current_scenario_context(context).get("validation_error") is not None


@given('a Keycloak request DTO {dto} with {attribute} set to "{value}"')
def step_request_with_attribute(context, dto, attribute, value):
    sc = get_current_scenario_context(context)
    sc.store("request", _dto_class(dto)(**{attribute: value}))


@then('its payload has "{wire_name}" set to "{value}"')
def step_payload_has(context, wire_name, value):
    payload = get_current_scenario_context(context).get("request").to_payload()
    assert payload == {wire_name: value}, payload


@given('a Keycloak KeycloakRoleDTO response with name "{name}"')
def step_role_response(context, name):
    get_current_scenario_context(context).store("response", role_dtos.KeycloakRoleDTO(name=name))


@when("the response is read with {access}")
def step_read_response(context, access):
    sc = get_current_scenario_context(context)
    response = sc.get("response")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = response["name"] if access == "brackets" else response.get("name")
    sc.store("value", value)
    sc.store("warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then("a dict-style access deprecation warning is raised")
def step_dict_warning(context):
    caught = get_current_scenario_context(context).get("warnings")
    assert len(caught) == 1 and "dict-style access" in str(caught[0].message), caught


@then('the value read is "{value}"')
def step_value_read(context, value):
    assert get_current_scenario_context(context).get("value") == value


@given("a Keycloak KeycloakTokenClaimsDTO response without claims")
def step_empty_claims(context):
    get_current_scenario_context(context).store("response", token_dtos.KeycloakTokenClaimsDTO())


@then("the response is falsy")
def step_response_falsy(context):
    assert not get_current_scenario_context(context).get("response")


@when("a {kind} payload is converted for the Keycloak adapter")
def step_convert_payload(context, kind):
    sc = get_current_scenario_context(context)
    value = group_dtos.KeycloakGroupRequestDTO(name="ops") if kind == "DTO" else {"name": "ops"}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sc.store("adapter_payload", to_request_payload(value))
    sc.store("warnings", [w for w in caught if issubclass(w.category, DeprecationWarning)])


@then('the adapter payload is {{"name": "ops"}}')
def step_adapter_payload(context):
    assert get_current_scenario_context(context).get("adapter_payload") == {"name": "ops"}


@then("the dict deprecation warning is {state}")
def step_dict_deprecation_state(context, state):
    caught = get_current_scenario_context(context).get("warnings")
    assert bool(caught) == (state == "raised"), caught


_MUTATION_BODIES = {
    "an empty dict": {},
    "empty bytes": b"",
    "a skip-exists dict": {"msg": "Already exists"},
    "JSON bytes with a field": b'{"futureField": 1}',
    "non-JSON bytes": b"<html>created</html>",
}


@when("the Keycloak mutation body {body} is converted")
def step_convert_mutation_body(context, body):
    get_current_scenario_context(context).store("mutation_result", to_mutation_result(KeycloakMutationResultDTO, _MUTATION_BODIES[body]))


@then("the mutation result message is {message}")
def step_mutation_message(context, message):
    result = get_current_scenario_context(context).get("mutation_result")
    assert result.msg == (None if message == "none" else message), result


@then("the mutation result extra fields are {extra}")
def step_mutation_extra(context, extra):
    result = get_current_scenario_context(context).get("mutation_result")
    expected = {} if extra == "none" else {extra: 1}
    assert (result.model_extra or {}) == expected, result.model_extra


@when("the Keycloak mutation body {body} is converted to {result_dto}")
def step_convert_mutation_body_to(context, body, result_dto):
    get_current_scenario_context(context).store(
        "mutation_result",
        to_mutation_result(_dto_class(result_dto), _MUTATION_BODIES[body]),
    )


@then("the result is a {result_dto} and a KeycloakMutationResultDTO")
def step_result_is_subclass(context, result_dto):
    result = get_current_scenario_context(context).get("mutation_result")
    assert type(result) is _dto_class(result_dto)
    assert isinstance(result, KeycloakMutationResultDTO)


@given("a Keycloak create result with message {message}")
def step_create_result_with_message(context, message):
    msg = None if message == "none" else message
    get_current_scenario_context(context).store("create_result", common_dtos.KeycloakCreateResultDTO(msg=msg))


@when('the id of the created resource is looked up as "{created_id}"')
def step_lookup_created_id(context, created_id):
    sc = get_current_scenario_context(context)
    calls = []

    def lookup():
        calls.append(1)
        return created_id

    sc.store("create_result", with_created_id(sc.get("create_result"), lookup))
    sc.store("lookup_calls", len(calls))


@then("the create result id is {expected}")
def step_create_result_id(context, expected):
    result = get_current_scenario_context(context).get("create_result")
    assert result.id == (None if expected == "none" else expected), result


@then("the lookup ran {ran}")
def step_lookup_ran(context, ran):
    assert (get_current_scenario_context(context).get("lookup_calls") == 1) == (ran == "yes")


@when(
    'I validate a Keycloak request DTO {dto} from a payload keyed by {key_style} with "{key}" set to "{value}"',
)
def step_validate_request_payload(context, dto, key_style, key, value):
    get_current_scenario_context(context).store("validated_dto", _dto_class(dto).model_validate({key: value}))


@then('the validated DTO has {attribute} equal to "{value}"')
def step_validated_dto_attribute(context, attribute, value):
    validated = get_current_scenario_context(context).get("validated_dto")
    assert getattr(validated, attribute) == value, validated


def _write_self_signed_pair(directory):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "keycloak-test")])
    now = datetime.datetime.now(datetime.UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_file = Path(directory) / "client.pem"
    key_file = Path(directory) / "client.key"
    cert_file.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )
    return str(cert_file), str(key_file)


@given(
    "a Keycloak config with a CA bundle, a client certificate and key, a 2.5 second timeout, 4 retries, a pool of 7, "
    "a proxy and a custom header",
)
def step_connection_options_config(context):
    cert_file, key_file = _write_self_signed_pair(mkdtemp())
    config = KeycloakConfig(
        SERVER_URL="https://keycloak.invalid",
        CLIENT_ID="client",
        VERIFY_SSL=cert_file,
        TIMEOUT=2.5,
        CLIENT_CERT_FILE=cert_file,
        CLIENT_KEY_FILE=key_file,
        MAX_RETRIES=4,
        POOL_MAXSIZE=7,
        PROXIES={"https://": "http://proxy.invalid:3128"},
        CUSTOM_HEADERS={"X-Tenant": "acme"},
    )
    sc = get_current_scenario_context(context)
    sc.store("keycloak_config", config)
    sc.store("keycloak_cert_pair", (cert_file, key_file))


@when("the {client} adapter builds its OpenID and UMA clients")
def step_build_clients(context, client):
    sc = get_current_scenario_context(context)
    config = sc.get("keycloak_config")
    adapter_class = AsyncKeycloakAdapter if client == "async" else KeycloakAdapter
    openid = adapter_class._get_openid_client(config)
    uma = adapter_class._get_uma_client(config)
    sc.store("keycloak_connections", [openid.connection, uma.connection])


@then(
    "every client connection uses the CA bundle, the client certificate pair, the timeout, the retries, the pool, "
    "the proxy and the header",
)
def step_connections_use_options(context):
    sc = get_current_scenario_context(context)
    cert_file, key_file = sc.get("keycloak_cert_pair")
    connections = sc.get("keycloak_connections")
    assert len(connections) == 2
    assert connections[0].proxies == {"https://": "http://proxy.invalid:3128"}
    for connection in connections:
        assert connection.verify == cert_file
        assert connection.cert == (cert_file, key_file)
        assert connection.timeout == 2.5
        assert connection.max_retries == 4
        assert connection.pool_maxsize == 7
        assert connection.headers["X-Tenant"] == "acme"
        adapter = connection._s.adapters["https://"]
        assert adapter.max_retries.total == 4
        assert connection._s.proxies["https"] == "http://proxy.invalid:3128"


@when("a Keycloak config is built with a client key file but no client certificate")
def step_config_key_without_cert(context):
    sc = get_current_scenario_context(context)
    try:
        KeycloakConfig(CLIENT_KEY_FILE="/etc/ssl/client.key")
    except ValidationError as e:
        sc.store("validation_error", e)
    else:
        sc.store("validation_error", None)


@when('a Keycloak config is built with VERIFY_SSL "{value}"')
def step_config_verify_ssl(context, value):
    get_current_scenario_context(context).store("keycloak_config", KeycloakConfig(VERIFY_SSL=value))


@then('the Keycloak config VERIFY_SSL is "{parsed}"')
def step_config_verify_ssl_is(context, parsed):
    assert str(get_current_scenario_context(context).get("keycloak_config").VERIFY_SSL) == parsed
