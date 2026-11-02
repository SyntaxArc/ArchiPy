import inspect
import logging
from types import SimpleNamespace
from unittest.mock import patch

import httpx2
import requests
import zeep
from behave import given, then, when
from zeep.exceptions import Fault
from zeep.exceptions import TransportError as ZeepTransportError

from archipy.adapters.internet_payment_gateways.ir.parsian import adapters as parsian_adapters
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ParsianShaparakConfig
from archipy.models.dtos.parsian_ipg_dtos import (
    ConfirmRequestDTO,
    ConfirmWithAmountRequestDTO,
    PaymentRequestDTO,
    ReverseRequestDTO,
)
from features.test_helpers import get_current_scenario_context

WSDL_BASE = "https://gateway.test/parsian"
SERVICES = {"sale": "PAYMENT_WSDL_URL", "confirm": "CONFIRM_WSDL_URL", "reversal": "REVERSAL_WSDL_URL"}


def _convert(value):
    """Table cell to python value: empty is None, integers are ints."""
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return value


class _StubService:
    """Recording stand-in for the SOAP `service` proxy (sync or async)."""

    def __init__(self, wsdl, transport, state):
        self._wsdl = wsdl
        self._transport = transport
        self._state = state

    def __getattr__(self, operation):
        def respond(**kwargs):
            self._state["calls"].append(
                {"wsdl": self._wsdl, "operation": operation, "requestData": kwargs.get("requestData")},
            )
            outcome = self._state["script"].get(operation)
            if outcome is None:
                raise AssertionError(f"Unscripted Parsian operation {operation}")
            kind, payload = outcome
            if kind == "raise":
                raise payload
            return payload

        if self._state["is_async"]:

            async def respond_async(**kwargs):
                return respond(**kwargs)

            return respond_async
        return respond


class _StubClient:
    """Recording stand-in for zeep.Client / zeep.AsyncClient (the third-party boundary)."""

    def __init__(self, state, wsdl=None, transport=None):
        self.wsdl = wsdl
        self.transport = transport
        state["clients"].append(self)
        self.service = _StubService(wsdl, transport, state)


def _state(context):
    """Return per-scenario fake-gateway state, installing the client patches on first use."""
    scenario_context = get_current_scenario_context(context)
    state = scenario_context.get("parsian_state")
    if state is not None:
        return state
    state = {"script": {}, "calls": [], "clients": [], "is_async": False}

    def client_factory(wsdl=None, transport=None, **_):
        return _StubClient(state, wsdl=wsdl, transport=transport)

    sync_patch = patch.object(zeep, "Client", client_factory)
    async_patch = patch.object(parsian_adapters, "AsyncClient", client_factory)
    sync_patch.start()
    async_patch.start()
    context.add_cleanup(sync_patch.stop)
    context.add_cleanup(async_patch.stop)
    scenario_context.store("parsian_state", state)
    return state


def _make_config(login_account, proxies=None):
    return ParsianShaparakConfig(
        LOGIN_ACCOUNT=login_account or None,
        PAYMENT_WSDL_URL=f"{WSDL_BASE}/sale?wsdl",
        CONFIRM_WSDL_URL=f"{WSDL_BASE}/confirm?wsdl",
        REVERSAL_WSDL_URL=f"{WSDL_BASE}/reversal?wsdl",
        PROXIES=proxies,
    )


def _build_adapter(context, kind, config):
    state = _state(context)
    state["is_async"] = kind == "async"
    adapter_class = (
        parsian_adapters.AsyncParsianShaparakPaymentAdapter
        if kind == "async"
        else parsian_adapters.ParsianShaparakPaymentAdapter
    )
    return adapter_class(config) if config is not None else adapter_class()


def _try_create(context, kind, config):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("kind", kind)
    scenario_context.store("error", None)
    try:
        scenario_context.store("adapter", _build_adapter(context, kind, config))
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


@given('a {kind:w} Parsian adapter with login account "{account}"')
def step_given_parsian_adapter(context, kind, account):
    _try_create(context, kind, _make_config(account))
    assert get_current_scenario_context(context).get("error") is None


@given('a {kind:w} Parsian adapter using proxy "{proxy}"')
def step_given_parsian_adapter_with_proxy(context, kind, proxy):
    proxies = {"https": proxy, "http": proxy} if proxy != "none" else None
    _try_create(context, kind, _make_config("merchant-1", proxies))
    assert get_current_scenario_context(context).get("error") is None


@given('the global Parsian login account is "{account}"')
def step_given_global_login_account(context, account):
    parsian_config = BaseConfig.global_config().PARSIAN_SHAPARAK
    original = parsian_config.LOGIN_ACCOUNT
    parsian_config.LOGIN_ACCOUNT = account
    context.add_cleanup(setattr, parsian_config, "LOGIN_ACCOUNT", original)


@given("Parsian debug logging is captured")
def step_given_log_capture(context):
    records = []

    class _Collector(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Collector(level=logging.DEBUG)
    adapter_logger = logging.getLogger(parsian_adapters.__name__)
    original_level = adapter_logger.level
    adapter_logger.setLevel(logging.DEBUG)
    adapter_logger.addHandler(handler)
    context.add_cleanup(adapter_logger.removeHandler, handler)
    context.add_cleanup(adapter_logger.setLevel, original_level)
    get_current_scenario_context(context).store("parsian_logs", records)


@given('the Parsian gateway answers "{operation}" with:')
def step_given_gateway_answers(context, operation):
    row = context.table.rows[0]
    fields = {heading: _convert(row[heading]) for heading in context.table.headings}
    _state(context)["script"][operation] = ("return", SimpleNamespace(**fields))


@given('the Parsian gateway raises a SOAP fault on "{operation}"')
def step_given_gateway_fault(context, operation):
    _state(context)["script"][operation] = ("raise", Fault("gateway is down"))


TRANSPORT_FAILURES = {
    "connection error": lambda: ConnectionError("connection reset"),
    "requests timeout": lambda: requests.exceptions.ReadTimeout("read timed out"),
    "requests connection error": lambda: requests.exceptions.ConnectionError("refused"),
    "httpx timeout": lambda: httpx2.ReadTimeout("read timed out"),
    "httpx connect error": lambda: httpx2.ConnectError("refused"),
    "zeep transport error": lambda: ZeepTransportError("HTTP 502"),
    "unexpected bug": lambda: KeyError("unexpected"),
}


@given('the Parsian gateway fails with {failure} on "{operation}"')
def step_given_gateway_transport_failure(context, failure, operation):
    _state(context)["script"][operation] = ("raise", TRANSPORT_FAILURES[failure]())


@when("I create a {kind:w} Parsian adapter with no login account")
def step_when_create_adapter(context, kind):
    _try_create(context, kind, _make_config(""))


@when("I create a {kind} Parsian adapter from global config")
def step_when_create_adapter_from_global(context, kind):
    _try_create(context, kind, None)
    assert get_current_scenario_context(context).get("error") is None


@when('I initiate a Parsian payment of {amount:d} for order {order_id:d} with callback "{callback}"')
async def step_when_initiate_payment(context, amount, order_id, callback):
    request = PaymentRequestDTO(amount=amount, order_id=order_id, callback_url=callback)
    await _call(context, "initiate_payment", request)


@when('I call Parsian "{operation}"')
async def step_when_call_operation(context, operation):
    requests_by_operation = {
        "SalePaymentRequest": (
            "initiate_payment",
            PaymentRequestDTO(amount=50000, order_id=1001, callback_url="https://shop.example.com/back"),
        ),
        "ConfirmPayment": ("confirm_payment", ConfirmRequestDTO(token=987654)),
        "ConfirmPaymentWithAmount": (
            "confirm_payment_with_amount",
            ConfirmWithAmountRequestDTO(token=987654, order_id=1001, amount=50000),
        ),
        "ReversalRequest": ("reverse_payment", ReverseRequestDTO(token=987654)),
    }
    method_name, request = requests_by_operation[operation]
    await _call(context, method_name, request)


@when("I confirm Parsian token {token:d}")
async def step_when_confirm(context, token):
    await _call(context, "confirm_payment", ConfirmRequestDTO(token=token))


@when("I confirm Parsian token {token:d} for order {order_id:d} and amount {amount:d}")
async def step_when_confirm_with_amount(context, token, order_id, amount):
    request = ConfirmWithAmountRequestDTO(token=token, order_id=order_id, amount=amount)
    await _call(context, "confirm_payment_with_amount", request)


@when("I reverse Parsian token {token:d}")
async def step_when_reverse(context, token):
    await _call(context, "reverse_payment", ReverseRequestDTO(token=token))


@when("I build a Parsian {request} with {field} {value:d}")
def step_when_build_request(context, request, field, value):
    valid = {
        "payment request": (PaymentRequestDTO, {"amount": 100, "order_id": 1, "callback_url": "https://a.example/cb"}),
        "confirm request": (ConfirmRequestDTO, {"token": 1}),
        "reverse request": (ReverseRequestDTO, {"token": 1}),
        "amount confirm": (ConfirmWithAmountRequestDTO, {"token": 1, "order_id": 1, "amount": 100}),
    }
    dto_class, kwargs = valid[request]
    kwargs[field] = value
    _try_build(context, dto_class, kwargs)


@when('I build a Parsian payment request whose callback is "{callback}"')
def step_when_build_request_with_callback(context, callback):
    _try_build(context, PaymentRequestDTO, {"amount": 100, "order_id": 1, "callback_url": callback})


def _try_build(context, dto_class, kwargs):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("error", None)
    try:
        dto_class(**kwargs)
    except Exception as exception:
        scenario_context.store("error", exception)


def _result(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("error") is None, f"Unexpected error: {scenario_context.get('error')!r}"
    return scenario_context.get("result")


@then("the Parsian initiation response has token {token:d} and status {status:d}")
def step_then_initiation_token(context, token, status):
    result = _result(context)
    assert result.token == token
    assert result.status == status


@then("the Parsian initiation response has no token and status {status:d}")
def step_then_initiation_no_token(context, status):
    result = _result(context)
    assert result.token is None
    assert result.status == status


@then('the Parsian initiation response has message "{message}"')
def step_then_initiation_message(context, message):
    assert _result(context).message == message


@then("the Parsian confirmation response has status {status:d} and rrn {rrn:d}")
def step_then_confirmation_status_rrn(context, status, rrn):
    result = _result(context)
    assert result.status == status
    assert result.rrn == rrn


@then("the Parsian confirmation response has status {status:d} and no rrn")
def step_then_confirmation_no_rrn(context, status):
    result = _result(context)
    assert result.status == status
    assert result.rrn is None
    assert result.card_number_masked is None


@then('the Parsian confirmation response has card "{card}" and token {token:d}')
def step_then_confirmation_card(context, card, token):
    result = _result(context)
    assert result.card_number_masked == card
    assert result.token == token


@then("the Parsian amount confirmation response has status {status:d} and rrn {rrn:d}")
def step_then_amount_confirmation(context, status, rrn):
    result = _result(context)
    assert result.status == status
    assert result.rrn == rrn


@then('the Parsian reversal response has status {status:d} and message "{message}"')
def step_then_reversal(context, status, message):
    result = _result(context)
    assert result.status == status
    assert result.message == message


@then('the Parsian gateway received "{operation}" on the "{service}" service with:')
def step_then_gateway_received(context, operation, service):
    state = _state(context)
    matching = [call for call in state["calls"] if call["operation"] == operation]
    assert len(matching) == 1, f"Expected one {operation} call, got {len(matching)}"
    call = matching[0]
    assert service in call["wsdl"].lower(), f"{operation} went to {call['wsdl']}"
    row = context.table.rows[0]
    for heading in context.table.headings:
        assert str(call["requestData"][heading]) == row[heading], (
            f"{heading}: expected {row[heading]!r}, got {call['requestData'][heading]!r}"
        )


@then('the Parsian call fails with "{error_name}"')
def step_then_call_fails(context, error_name):
    error = get_current_scenario_context(context).get("error")
    assert error is not None, "Expected an error but the call succeeded"
    assert type(error).__name__ == error_name, f"Expected {error_name}, got {type(error).__name__}"


@then('the Parsian failure carries resource type "{resource_type}"')
def step_then_failure_resource_type(context, resource_type):
    error = get_current_scenario_context(context).get("error")
    assert error.additional_data.get("resource_type") == resource_type


@then("the Parsian failure was caused by a SOAP fault")
def step_then_failure_cause(context):
    error = get_current_scenario_context(context).get("error")
    assert isinstance(error.__cause__, Fault)


@then("the Parsian request is rejected as invalid")
def step_then_request_rejected(context):
    error = get_current_scenario_context(context).get("error")
    assert error is not None, "Expected the request to be rejected"
    assert type(error).__name__ in {"ValidationError", "InvalidArgumentError"}, type(error).__name__


@then("the Parsian SOAP transport times operations out after {seconds:d} seconds and {proxy_use} the proxy")
def step_then_transport(context, seconds, proxy_use):
    clients = _state(context)["clients"]
    assert len(clients) == 3
    for client in clients:
        transport = client.transport
        assert transport is not None
        if _state(context)["is_async"]:
            assert transport.client.timeout.read == seconds, transport.client.timeout
            proxied = bool(transport.wsdl_client._mounts)  # the WSDL loader must get the proxy too
        else:
            assert transport.operation_timeout == seconds, transport.operation_timeout
            proxied = bool(transport.session.proxies)
        assert proxied == (proxy_use == "uses"), f"proxy_use={proxy_use}, proxied={proxied}"


@then('the Parsian debug logs contain neither "{secret}" nor "{token}" but do name order {order_id:d}')
def step_then_logs_redacted(context, secret, token, order_id):
    logs = get_current_scenario_context(context).get("parsian_logs")
    assert logs, "No debug logs were captured"
    joined = "\n".join(logs)
    assert secret not in joined, "login account leaked into the logs"
    assert token not in joined, "full token leaked into the logs"
    assert f"order_id={order_id}" in joined
