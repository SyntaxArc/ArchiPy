---
title: Payment Gateways Adapter Tutorial
description: Practical examples for using the ArchiPy Parsian and Saman Shaparak payment gateway adapters.
---

# Payment Gateways Adapter Tutorial

This tutorial covers ArchiPy's integrations with Iranian Shaparak payment gateways, demonstrating complete payment flows
with proper error handling and Python 3.14 type hints.

## Supported Gateways

| Gateway              | Adapter Class                           | Protocol                       |
|----------------------|-----------------------------------------|--------------------------------|
| Parsian Shaparak     | `ParsianShaparakPaymentAdapter`         | SOAP/WSDL                      |
| Saman Shaparak       | `SamanShaparakPaymentAdapter`           | REST/JSON                      |
| Saman Neo-PG         | `SamanNeoPgShaparakPaymentAdapter`      | REST/JSON (dynamic URL)        |
| Async Saman Shaparak | `AsyncSamanShaparakPaymentAdapter`      | REST/JSON (async)              |
| Async Saman Neo-PG   | `AsyncSamanNeoPgShaparakPaymentAdapter` | REST/JSON (async, dynamic URL) |

## Installation

```bash
uv add "archipy[parsian-ipg]"  # Parsian gateway
uv add "archipy[saman-ipg]"    # Saman gateway
```

!!! tip
    Payment gateways are optional extras. Install only the gateway (s) you need.

---

## Parsian Shaparak

Parsian uses a SOAP-based protocol with WSDL service definitions.

### Configuration

```bash
PARSIAN_SHAPARAK__LOGIN_ACCOUNT=your_merchant_login_account
PARSIAN_SHAPARAK__PAYMENT_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?WSDL
PARSIAN_SHAPARAK__CONFIRM_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?WSDL
PARSIAN_SHAPARAK__REVERSAL_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Reverse/ReversalService.asmx?WSDL
```

Or via direct config:

```python
from archipy.configs.config_template import ParsianShaparakConfig

config = ParsianShaparakConfig(
    LOGIN_ACCOUNT="your_merchant_login_account",
)
```

!!! note "Logging"
    Debug logs name only the order id, the amount and the last four characters of a token. The login account and
    full tokens are never logged.

### Initializing the Adapter

```python
import logging

from archipy.adapters.internet_payment_gateways.ir.parsian import ParsianShaparakPaymentAdapter
from archipy.models.errors import InvalidArgumentError

logger = logging.getLogger(__name__)

try:
    payment_adapter = ParsianShaparakPaymentAdapter()
except InvalidArgumentError as e:
    logger.error(f"Failed to initialize payment adapter: {e}")
    raise
else:
    logger.info("Payment adapter initialized successfully")
```

### Initiating a Payment

```python
from archipy.adapters.internet_payment_gateways.ir.parsian import PaymentRequestDTO
from archipy.models.errors import UnavailableError, InvalidArgumentError

payment_request = PaymentRequestDTO(
    amount=10000,
    order_id=12345,
    callback_url="https://your-app.com/payment/callback",
)

try:
    payment_response = payment_adapter.initiate_payment(payment_request)
except UnavailableError as e:
    logger.error(f"Payment service unavailable: {e}")
    raise
except InvalidArgumentError as e:
    logger.error(f"Invalid payment request: {e}")
    raise
else:
    if payment_response.status == 0:
        payment_url = f"https://pec.shaparak.ir/NewIPG/?Token={payment_response.token}"
        logger.info(f"Payment initiated, token: {payment_response.token}")
    else:
        logger.error(f"Payment initiation failed: {payment_response.message}")
```

### Confirming a Payment

!!! warning
    A response does not mean the payment is confirmed. Check `confirm_response.status`: `0` is a confirmed payment.
    The callback `token` is user-controlled input: prefer `confirm_payment_with_amount` (below) with the order id and
    amount you stored when the payment was initiated, so the gateway checks them for you.

```python
from archipy.adapters.internet_payment_gateways.ir.parsian import ConfirmRequestDTO
from archipy.models.errors import UnavailableError, InternalError

token = 123456789
confirm_request = ConfirmRequestDTO(token=token)

try:
    confirm_response = payment_adapter.confirm_payment(confirm_request)
except UnavailableError as e:
    logger.error(f"Confirmation service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Confirmation failed: {e}")
    raise
else:
    if confirm_response.status == 0:
        logger.info(f"Payment confirmed, RRN: {confirm_response.rrn}, Card: {confirm_response.card_number_masked}")
    else:
        logger.warning(f"Confirmation failed: {confirm_response.status}")
```

### Confirming with Amount Verification

```python
from archipy.adapters.internet_payment_gateways.ir.parsian import ConfirmWithAmountRequestDTO
from archipy.models.errors import UnavailableError, InternalError, InvalidArgumentError

confirm_with_amount_request = ConfirmWithAmountRequestDTO(
    token=123456789,
    order_id=12345,
    amount=10000
)

try:
    confirm_response = payment_adapter.confirm_payment_with_amount(confirm_with_amount_request)
except InvalidArgumentError as e:
    logger.error(f"Invalid confirmation parameters: {e}")
    raise
except UnavailableError as e:
    logger.error(f"Confirmation service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Confirmation failed: {e}")
    raise
else:
    if confirm_response.status == 0:
        logger.info("Payment confirmed with amount verification!")
    else:
        logger.warning(f"Confirmation failed: {confirm_response.status}")
```

### Reversing a Payment

!!! note
    Check `reverse_response.status` after the call. `0` means the reversal succeeded.

```python
from archipy.adapters.internet_payment_gateways.ir.parsian import ReverseRequestDTO
from archipy.models.errors import UnavailableError, InternalError

reverse_request = ReverseRequestDTO(token=123456789)

try:
    reverse_response = payment_adapter.reverse_payment(reverse_request)
except UnavailableError as e:
    logger.error(f"Reversal service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Reversal failed: {e}")
    raise
else:
    if reverse_response.status == 0:
        logger.info("Payment reversal successful!")
    else:
        logger.error(f"Reversal failed: {reverse_response.message}")
```

---

## Saman Shaparak

Saman uses a REST/JSON protocol with four adapter variants:

- **`SamanShaparakPaymentAdapter`** — Classic SEP adapter, redirects to fixed payment URL
- **`SamanNeoPgShaparakPaymentAdapter`** — Neo-PG adapter, receives dynamic payment URL from response header
- **`AsyncSamanShaparakPaymentAdapter`** — Async version of classic SEP adapter
- **`AsyncSamanNeoPgShaparakPaymentAdapter`** — Async version of Neo-PG adapter

### Configuration

```bash
SAMAN_SHAPARAK__TERMINAL_ID=your_terminal_id
SAMAN_SHAPARAK__PAYMENT_URL=https://sep.shaparak.ir/onlinepg/onlinepg
SAMAN_SHAPARAK__VERIFY_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction
SAMAN_SHAPARAK__REVERSE_URL=https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTransaction
```

Or via direct config:

```python
from archipy.configs.config_template import SamanShaparakConfig

config = SamanShaparakConfig(
    TERMINAL_ID="your_terminal_id",
)
```

### Initializing the Adapter

```python
import logging

from archipy.adapters.internet_payment_gateways.ir.saman import (
    SamanShaparakPaymentAdapter,
    SamanNeoPgShaparakPaymentAdapter,
    AsyncSamanShaparakPaymentAdapter,
    AsyncSamanNeoPgShaparakPaymentAdapter,
)
from archipy.models.errors import InvalidArgumentError

logger = logging.getLogger(__name__)

try:
    payment_adapter = SamanShaparakPaymentAdapter()
    neo_adapter = SamanNeoPgShaparakPaymentAdapter()
    async_adapter = AsyncSamanShaparakPaymentAdapter()
    async_neo_adapter = AsyncSamanNeoPgShaparakPaymentAdapter()
except InvalidArgumentError as e:
    logger.error(f"Failed to initialize payment adapter: {e}")
    raise
else:
    logger.info("Payment adapter initialized successfully")
```

### Initiating a Payment

```python
from archipy.adapters.internet_payment_gateways.ir.saman import PaymentRequestDTO
from archipy.models.errors import UnavailableError, InternalError

payment_request = PaymentRequestDTO(
    amount=10000,
    res_num="order-12345",
    redirect_url="https://your-app.com/payment/callback",
    cell_number="09123456789",
)

try:
    payment_response = payment_adapter.initiate_payment(payment_request)
except UnavailableError as e:
    logger.error(f"Payment service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Unexpected error: {e}")
    raise
else:
    if payment_response.status == 1:
        logger.info(f"Payment initiated, token: {payment_response.token}")
    else:
        logger.error(f"Payment initiation failed: {payment_response.error_code} - {payment_response.error_desc}")
```

### Neo-PG: Capturing Dynamic Payment URL

!!! note
    The Neo-PG adapter reads the payment URL from the `X-IPG-Url` response header. When the header is missing,
    `ipg_url` is empty, so check it before you redirect the customer.

```python
try:
    payment_response = neo_adapter.initiate_payment(payment_request)
except UnavailableError as e:
    logger.error(f"Neo-PG service unavailable: {e}")
    raise
else:
    if payment_response.status == 1:
        ipg_url = payment_response.ipg_url
        if ipg_url:
            logger.info(f"Payment initiated, redirect to: {ipg_url}")
        else:
            logger.warning("Neo-PG response missing X-IPG-Url header")
    else:
        logger.error(f"Payment initiation failed: {payment_response.error_code}")
```

### Verifying a Payment

```python
from archipy.adapters.internet_payment_gateways.ir.saman import VerifyRequestDTO
from archipy.models.errors import UnavailableError, InternalError

verify_request = VerifyRequestDTO(reference_number="reference-number-from-callback")

try:
    verify_response = payment_adapter.verify_payment(verify_request)
except UnavailableError as e:
    logger.error(f"Verify service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Verify failed: {e}")
    raise
else:
    if verify_response.success:
        logger.info(
            f"Payment verified! RRN: {verify_response.rrn}, "
            f"Card: {verify_response.masked_pan}, Amount: {verify_response.original_amount}"
        )
    else:
        logger.warning(f"Verification failed: {verify_response.result_code} - {verify_response.result_description}")
```

### Reversing a Payment

```python
from archipy.adapters.internet_payment_gateways.ir.saman import ReverseRequestDTO
from archipy.models.errors import UnavailableError, InternalError

reverse_request = ReverseRequestDTO(reference_number="reference-number")

try:
    reverse_response = payment_adapter.reverse_payment(reverse_request)
except UnavailableError as e:
    logger.error(f"Reversal service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Reversal failed: {e}")
    raise
else:
    if reverse_response.success:
        logger.info("Payment reversal successful!")
    else:
        logger.error(f"Reversal failed: {reverse_response.result_code} - {reverse_response.result_description}")
```

---

## Complete FastAPI Example

The callback query parameters come from the user's browser, so never trust them alone. Store the order id and amount
when the payment is initiated, confirm against the stored values and fulfil the order only once. The example keeps
orders in a dict for brevity; use a database in production. It uses the async adapters because the handlers are
`async def` (sync adapters would block the event loop).

```python
import logging

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from archipy.adapters.internet_payment_gateways.ir.parsian import (
    AsyncParsianShaparakPaymentAdapter,
    ConfirmWithAmountRequestDTO,
    PaymentRequestDTO,
)
from archipy.adapters.internet_payment_gateways.ir.saman import (
    AsyncSamanShaparakPaymentAdapter,
    PaymentRequestDTO as SamanPaymentRequestDTO,
    VerifyRequestDTO,
)
from archipy.models.errors import InternalError, InvalidArgumentError, UnavailableError

logger = logging.getLogger(__name__)

app = FastAPI()

parsian_adapter = AsyncParsianShaparakPaymentAdapter()
saman_adapter = AsyncSamanShaparakPaymentAdapter()

# Stand-in for a database: token (Parsian) or reservation number (Saman) -> stored order.
parsian_orders: dict[int, dict[str, int | bool]] = {}
saman_orders: dict[str, dict[str, int | bool]] = {}


class OrderCreate(BaseModel):
    amount: int
    order_id: int
    description: str | None = None


@app.post("/payments/parsian/create")
async def create_parsian_payment(order: OrderCreate) -> dict[str, int | str]:
    try:
        payment_request = PaymentRequestDTO(
            amount=order.amount,
            order_id=order.order_id,
            callback_url="https://your-app.com/payments/parsian/callback",
        )
        response = await parsian_adapter.initiate_payment(payment_request)
    except (InvalidArgumentError, UnavailableError, InternalError) as e:
        logger.error(f"Payment initiation failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")
    else:
        if response.status != 0 or response.token is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Payment failed: {response.message}")
        parsian_orders[response.token] = {"order_id": order.order_id, "amount": order.amount, "fulfilled": False}
        return {
            "token": response.token,
            "payment_url": f"https://pec.shaparak.ir/NewIPG/?Token={response.token}",
        }


@app.get("/payments/parsian/callback")
async def parsian_callback(token: int) -> dict[str, str]:
    stored = parsian_orders.get(token)
    if stored is None or stored["fulfilled"]:
        return {"status": "failed", "message": "Unknown or already processed payment"}
    try:
        confirm_response = await parsian_adapter.confirm_payment_with_amount(
            ConfirmWithAmountRequestDTO(token=token, order_id=stored["order_id"], amount=stored["amount"]),
        )
    except (InvalidArgumentError, UnavailableError, InternalError) as e:
        # The outcome is unknown after a timeout: check the transaction state before retrying.
        logger.error(f"Confirmation failed: {e}")
        return {"status": "error", "message": "Payment verification failed"}
    else:
        if confirm_response.status == 0:
            stored["fulfilled"] = True
            logger.info(f"Parsian payment confirmed, RRN: {confirm_response.rrn}")
            return {"status": "success", "reference_number": str(confirm_response.rrn)}
        return {"status": "failed", "message": "Payment verification failed"}


@app.post("/payments/saman/create")
async def create_saman_payment(order: OrderCreate) -> dict[str, int | str]:
    res_num = f"order-{order.order_id}"
    try:
        payment_request = SamanPaymentRequestDTO(
            amount=order.amount,
            res_num=res_num,
            redirect_url="https://your-app.com/payments/saman/callback",
        )
        response = await saman_adapter.initiate_payment(payment_request)
    except (InvalidArgumentError, UnavailableError, InternalError) as e:
        logger.error(f"Payment initiation failed: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Payment service unavailable")
    else:
        if response.status != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {response.error_desc}",
            )
        saman_orders[res_num] = {"order_id": order.order_id, "amount": order.amount, "fulfilled": False}
        return {"token": response.token, "payment_url": f"https://sep.shaparak.ir/onlinepg?token={response.token}"}


@app.get("/payments/saman/callback")
async def saman_callback(res_num: str, ref_num: str) -> dict[str, str]:
    stored = saman_orders.get(res_num)
    if stored is None or stored["fulfilled"]:
        return {"status": "failed", "message": "Unknown or already processed payment"}
    try:
        verify_response = await saman_adapter.verify_payment(VerifyRequestDTO(reference_number=ref_num))
    except (InvalidArgumentError, UnavailableError, InternalError) as e:
        logger.error(f"Verification failed: {e}")
        return {"status": "error", "message": "Payment verification failed"}
    else:
        if not verify_response.success:
            return {"status": "failed", "message": f"Verification failed: {verify_response.result_description}"}
        # Compare what the gateway verified with what we stored before fulfilling.
        if verify_response.reference_number != ref_num or verify_response.original_amount != stored["amount"]:
            logger.error("Saman verification does not match the stored order")
            return {"status": "failed", "message": "Payment does not match the order"}
        stored["fulfilled"] = True
        logger.info(f"Saman payment verified, RRN: {verify_response.rrn}")
        return {"status": "success", "reference_number": str(verify_response.rrn)}
```

## Error Handling

All adapters use ArchiPy's consistent error hierarchy:

!!! tip
    `InvalidArgumentError` raised by an adapter constructor means a required setting (`LOGIN_ACCOUNT` for Parsian,
    `TERMINAL_ID` for Saman) is missing. Fix the configuration instead of retrying.

| Error Type                | Trigger                                        |
|---------------------------|------------------------------------------------|
| `UnavailableError`        | SOAP fault, network failure, HTTP 5xx          |
| `InternalError`           | Any other failure, including unreadable or malformed gateway replies |
| `FailedPreconditionError` | Token reply inconsistent with its status (Saman) |
| `InvalidArgumentError`    | Invalid request parameters or missing `LOGIN_ACCOUNT` / `TERMINAL_ID` |

## Common Settings

Both configs accept `PROXIES` (a dict such as `{"https": "http://proxy:3128"}`; the async adapters use the first of
`https`, `http`, `socks5`, `socks5h`) and `TIMEOUT` (seconds). Set them with environment variables such as
`PARSIAN_SHAPARAK__PROXIES` and `SAMAN_SHAPARAK__TIMEOUT`.

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns
- [Configuration Management](../config_management.md) — Gateway configuration setup
- [BDD Testing](../testing_strategy.md) — Testing payment operations
- BDD feature files — [`parsian_ipg_adapter.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/parsian_ipg_adapter.feature), [`saman_ipg_adapter.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/saman_ipg_adapter.feature)
- [API Reference](../../api_reference/adapters/payment_gateways.md) — Full payment gateway API documentation
