import inspect
import json
from unittest.mock import patch

import httpx2
from behave import given, then, when

from archipy.adapters.internet_payment_gateways.ir.saman import adapters as saman_adapters
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SamanShaparakConfig
from archipy.models.dtos.saman_ipg_dtos import PaymentRequestDTO, ReverseRequestDTO, VerifyRequestDTO
from features.test_helpers import get_current_scenario_context

GATEWAY = "https://gateway.test/saman"
KINDS = {
    "sync": (False, saman_adapters.SamanShaparakPaymentAdapter),
    "async": (True, saman_adapters.AsyncSamanShaparakPaymentAdapter),
    "sync Neo-PG": (False, saman_adapters.SamanNeoPgShaparakPaymentAdapter),
    "async Neo-PG": (True, saman_adapters.AsyncSamanNeoPgShaparakPaymentAdapter),
}


def _endpoint_of(url):
    lowered = str(url).lower()
    if "reverse" in lowered:
        return "reverse"
    if "verify" in lowered:
        return "verify"
    return "token"


class _StubHttpClient:
    """Recording stand-in for httpx2.Client / httpx2.AsyncClient (the third-party boundary)."""

    def __init__(self, state, is_async, proxy=None, **_):
        self.proxy = proxy
        self._state = state
        self._is_async = is_async
        state["clients"].append(self)
        if is_async:
            self.post = self._post_async
        else:
            self.post = self._post

    def _post(self, url, json=None, **_):
        endpoint = _endpoint_of(url)
        self._state["calls"].append({"endpoint": endpoint, "url": str(url), "json": json})
        outcome = self._state["script"].get(endpoint)
        if outcome is None:
            raise AssertionError(f"Unscripted Saman endpoint {endpoint}")
        if outcome["kind"] == "raise":
            raise outcome["exception"]
        request = httpx2.Request("POST", str(url))
        headers = self._state["headers"].get(endpoint, {})
        if outcome["json"] is not None:
            return httpx2.Response(outcome["status"], json=outcome["json"], headers=headers, request=request)
        return httpx2.Response(outcome["status"], content=outcome["raw"], headers=headers, request=request)

    async def _post_async(self, url, json=None, **kwargs):
        return self._post(url, json=json, **kwargs)


def _state(context):
    """Return per-scenario fake-gateway state, installing the client patches on first use."""
    scenario_context = get_current_scenario_context(context)
    state = scenario_context.get("saman_state")
    if state is not None:
        return state
    state = {"script": {}, "headers": {}, "calls": [], "clients": []}

    def sync_factory(**kwargs):
        return _StubHttpClient(state, False, **kwargs)

    def async_factory(**kwargs):
        return _StubHttpClient(state, True, **kwargs)

    sync_patch = patch.object(httpx2, "Client", sync_factory)
    async_patch = patch.object(httpx2, "AsyncClient", async_factory)
    sync_patch.start()
    async_patch.start()
    context.add_cleanup(sync_patch.stop)
    context.add_cleanup(async_patch.stop)
    scenario_context.store("saman_state", state)
    return state


def _make_config(terminal_id, proxies=None):
    return SamanShaparakConfig(
        TERMINAL_ID=terminal_id or None,
        PAYMENT_URL=f"{GATEWAY}/token",
        VERIFY_URL=f"{GATEWAY}/verify",
        REVERSE_URL=f"{GATEWAY}/reverse",
        PROXIES=proxies,
    )


def _try_create(context, kind, config):
    _state(context)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    adapter_class = KINDS[kind][1]
    try:
        scenario_context.store("adapter", adapter_class(config) if config is not None else adapter_class())
    except Exception as exception:
        scenario_context.store("error", exception)


async def _call(context, method_name, request):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    scenario_context.store("result", None)
    try:
        result = getattr(scenario_context.get("adapter"), method_name)(request)
        if inspect.isawaitable(result):
            result = await result
        scenario_context.store("result", result)
    except Exception as exception:
        scenario_context.store("error", exception)


def _result(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("error") is None, f"Unexpected error: {scenario_context.get('error')!r}"
    return scenario_context.get("result")


def _parse_proxies(text):
    if text == "none":
        return None
    return dict(pair.split("=", 1) for pair in text.split(","))


@given('a {kind} Saman adapter with terminal "{terminal}"')
def step_given_adapter(context, kind, terminal):
    _try_create(context, kind, _make_config(terminal))
    assert get_current_scenario_context(context).get("error") is None


@given('a {kind} Saman adapter using proxies "{proxies}"')
def step_given_adapter_with_proxies(context, kind, proxies):
    _try_create(context, kind, _make_config("13579", _parse_proxies(proxies)))
    assert get_current_scenario_context(context).get("error") is None


@given('the global Saman terminal id is "{terminal}"')
def step_given_global_terminal(context, terminal):
    saman_config = BaseConfig.global_config().SAMAN_SHAPARAK
    original = saman_config.TERMINAL_ID
    saman_config.TERMINAL_ID = terminal
    context.add_cleanup(setattr, saman_config, "TERMINAL_ID", original)


@given('the Saman "{endpoint}" endpoint answers {status:d} with JSON:')
def step_given_answers_json(context, endpoint, status):
    _state(context)["script"][endpoint] = {
        "kind": "response",
        "status": status,
        "json": json.loads(context.text),
        "raw": None,
    }


@given('the Saman "{endpoint}" endpoint answers {status:d} with raw body "{body}"')
def step_given_answers_raw(context, endpoint, status, body):
    _state(context)["script"][endpoint] = {"kind": "response", "status": status, "json": None, "raw": body.encode()}


@given('the Saman "{endpoint}" endpoint sends header "{name}" with value "{value}"')
def step_given_header(context, endpoint, name, value):
    _state(context)["headers"].setdefault(endpoint, {})[name] = value


@given('the Saman "{endpoint}" endpoint fails with a {failure}')
def step_given_failure(context, endpoint, failure):
    exceptions = {"connection error": httpx2.ConnectError("refused"), "timeout": httpx2.ReadTimeout("slow")}
    _state(context)["script"][endpoint] = {"kind": "raise", "exception": exceptions[failure]}


@when("I create a {kind} Saman adapter with no terminal")
def step_when_create_without_terminal(context, kind):
    _try_create(context, kind, _make_config(""))


@when("I create a {kind} Saman adapter from global config")
def step_when_create_from_global(context, kind):
    _try_create(context, kind, None)
    assert get_current_scenario_context(context).get("error") is None


@when('I initiate a Saman payment of {amount:d} for reservation "{res_num}" redirecting to "{url}"')
async def step_when_initiate(context, amount, res_num, url):
    request = PaymentRequestDTO(amount=amount, res_num=res_num, redirect_url=url)
    await _call(context, "initiate_payment", request)


@when('I initiate a Saman payment of {amount:d} redirecting to "{url}" with options:')
async def step_when_initiate_with_options(context, amount, url):
    row = context.table.rows[0]
    request = PaymentRequestDTO(
        amount=amount,
        res_num=row["ResNum"],
        redirect_url=url,
        cell_number=row["CellNumber"],
        wage=int(row["Wage"]),
        token_expiry_in_min=int(row["TokenExpiryInMin"]),
        hashed_card_number=row["HashedCardNumber"],
    )
    await _call(context, "initiate_payment", request)


@when('I verify Saman reference "{reference}"')
async def step_when_verify(context, reference):
    await _call(context, "verify_payment", VerifyRequestDTO(reference_number=reference))


@when('I reverse Saman reference "{reference}"')
async def step_when_reverse(context, reference):
    await _call(context, "reverse_payment", ReverseRequestDTO(reference_number=reference))


@when("I build a Saman payment request with {field} {value}")
def step_when_build_request(context, field, value):
    kwargs = {"amount": 100, "res_num": "R1", "redirect_url": "https://a.example/r"}
    if field == "amount":
        kwargs["amount"] = int(value)
    elif field == "token_expiry":
        kwargs["token_expiry_in_min"] = int(value)
    elif field == "redirect_url":
        kwargs["redirect_url"] = value
    elif field == "res_num":
        kwargs["res_num"] = None
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    try:
        PaymentRequestDTO(**kwargs)
    except Exception as exception:
        scenario_context.store("error", exception)


@then('the Saman initiation response has status {status:d} and token "{token}"')
def step_then_initiation_token(context, status, token):
    result = _result(context)
    assert result.status == status
    assert result.token == token


@then("the Saman initiation response has status {status:d} and no token")
def step_then_initiation_no_token(context, status):
    result = _result(context)
    assert result.status == status
    assert result.token is None


@then("the Saman initiation response has no error")
def step_then_initiation_no_error(context):
    result = _result(context)
    assert result.error_code is None
    assert result.error_desc is None


@then('the Saman initiation response has error code "{code}" and description "{description}"')
def step_then_initiation_error(context, code, description):
    result = _result(context)
    assert result.error_code == code
    assert result.error_desc == description


@then('the Saman initiation response has IPG URL "{url}"')
def step_then_ipg_url(context, url):
    assert _result(context).ipg_url == url


@then("the Saman initiation response has no IPG URL")
def step_then_no_ipg_url(context):
    assert _result(context).ipg_url is None


def _single_call(context, endpoint):
    calls = [call for call in _state(context)["calls"] if call["endpoint"] == endpoint]
    assert len(calls) == 1, f"Expected one call to {endpoint}, got {len(calls)}"
    return calls[0]


@then('the Saman "{endpoint}" endpoint received JSON with:')
def step_then_received_json(context, endpoint):
    call = _single_call(context, endpoint)
    row = context.table.rows[0]
    for heading in context.table.headings:
        assert str(call["json"][heading]) == row[heading], (
            f"{heading}: expected {row[heading]!r}, got {call['json'].get(heading)!r}"
        )


@then('the Saman "{endpoint}" endpoint received no field "{field}"')
def step_then_received_no_field(context, endpoint, field):
    assert field not in _single_call(context, endpoint)["json"]


@then('the Saman verification succeeded with result code {code:d} and description "{description}"')
def step_then_verify_success(context, code, description):
    result = _result(context)
    assert result.success is True
    assert result.result_code == code
    assert result.result_description == description


@then('the Saman verification failed with result code {code:d} and description "{description}"')
def step_then_verify_failed(context, code, description):
    result = _result(context)
    assert result.success is False
    assert result.result_code == code
    assert result.result_description == description


@then('the Saman verification detail has rrn "{rrn}" and reference "{reference}"')
def step_then_verify_rrn(context, rrn, reference):
    result = _result(context)
    assert result.rrn == rrn
    assert result.reference_number == reference


@then('the Saman verification detail has masked pan "{masked}" and hashed pan "{hashed}"')
def step_then_verify_pan(context, masked, hashed):
    result = _result(context)
    assert result.masked_pan == masked
    assert result.hashed_pan == hashed


@then(
    'the Saman verification detail has original amount {original:d}, affective amount {affective:d} and trace "{trace}"',
)
def step_then_verify_amounts(context, original, affective, trace):
    result = _result(context)
    assert result.original_amount == original
    assert result.affective_amount == affective
    assert result.trace_no == trace


@then("the Saman verification detail is empty")
def step_then_verify_empty(context):
    result = _result(context)
    for field in (
        "rrn",
        "reference_number",
        "masked_pan",
        "hashed_pan",
        "original_amount",
        "affective_amount",
        "trace_no",
    ):
        assert getattr(result, field) is None, field


@then('the Saman reversal succeeded with result code {code:d} and description "{description}"')
def step_then_reverse_success(context, code, description):
    result = _result(context)
    assert result.success is True
    assert result.result_code == code
    assert result.result_description == description


@then('the Saman reversal failed with result code {code:d} and description "{description}"')
def step_then_reverse_failed(context, code, description):
    result = _result(context)
    assert result.success is False
    assert result.result_code == code
    assert result.result_description == description


@then('the Saman call fails with "{error_name}"')
def step_then_call_fails(context, error_name):
    error = get_current_scenario_context(context).get("error")
    assert error is not None, "Expected an error but the call succeeded"
    assert type(error).__name__ == error_name, f"Expected {error_name}, got {type(error).__name__}"


@then('the Saman failure carries resource type "{resource_type}"')
def step_then_resource_type(context, resource_type):
    error = get_current_scenario_context(context).get("error")
    assert error is not None, "Expected an error but the call succeeded"
    assert error.additional_data.get("resource_type") == resource_type


@then('the Saman HTTP client uses proxy "{expected}"')
def step_then_proxy(context, expected):
    clients = _state(context)["clients"]
    assert len(clients) == 1
    assert clients[0].proxy == (None if expected == "none" else expected)


@then("the Saman request is rejected as invalid")
def step_then_request_rejected(context):
    error = get_current_scenario_context(context).get("error")
    assert error is not None, "Expected the request to be rejected"
    assert type(error).__name__ in {"ValidationError", "InvalidArgumentError"}, type(error).__name__


@then("the Saman failure carries HTTP status {status:d}")
def step_then_failure_http_status(context, status):
    error = get_current_scenario_context(context).get("error")
    assert error.additional_data.get("status_code") == status
