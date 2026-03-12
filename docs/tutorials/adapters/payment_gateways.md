---
title: Payment Gateways Adapter Tutorial
description: Practical examples for using the ArchiPy Parsian Shaparak payment gateway adapter.
---

# Payment Gateways Adapter Tutorial

This example demonstrates how to use the Parsian Shaparak payment gateway adapter to process online payments in Iran
with proper error handling and Python 3.14 type hints.

## Installation

```bash
uv add "archipy[parsian-ipg]"
```

!!! tip
The Parsian Shaparak payment gateway is an optional extra. Install it only when integrating with Iranian payment
services.

## Configuration

Configure the payment gateway adapter via environment variables or a `ParsianShaparakConfig` object.

### Environment Variables

```bash
PARSIAN_SHAPARAK__LOGIN_ACCOUNT=your_merchant_login_account
PARSIAN_SHAPARAK__PAYMENT_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?WSDL
PARSIAN_SHAPARAK__CONFIRM_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?WSDL
PARSIAN_SHAPARAK__REVERSAL_WSDL_URL=https://pec.shaparak.ir/NewIPGServices/Reverse/ReversalService.asmx?WSDL
```

### Direct Configuration

```python
from archipy.configs.config_template import ParsianShaparakConfig

config = ParsianShaparakConfig(
    LOGIN_ACCOUNT="your_merchant_login_account",
    # Override WSDL URLs only if using a staging/custom endpoint:
    # PAYMENT_WSDL_URL="https://custom.url/to/payment/wsdl",
    # CONFIRM_WSDL_URL="https://custom.url/to/confirm/wsdl",
    # REVERSAL_WSDL_URL="https://custom.url/to/reversal/wsdl",
)
```

## Basic Usage

### Initializing the Adapter

```python
import logging

from archipy.adapters.internet_payment_gateways.ir.parsian.adapters import (
    ConfirmRequestDTO,
    ConfirmWithAmountRequestDTO,
    ParsianShaparakPaymentAdapter,
    PaymentRequestDTO,
    ReverseRequestDTO,
)
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

# Initialize the payment adapter
try:
    payment_adapter = ParsianShaparakPaymentAdapter()
except ConfigurationError as e:
    logger.error(f"Failed to initialize payment adapter: {e}")
    raise
else:
    logger.info("Payment adapter initialized successfully")
```

### Processing Payments

#### Initiating a Payment

To start a payment transaction:

```python
import logging

from archipy.models.errors import UnavailableError, InvalidArgumentError

# Configure logging
logger = logging.getLogger(__name__)

# Create payment request
payment_request = PaymentRequestDTO(
    amount=10000,  # Amount in IRR (10,000 Rials)
    order_id=12345,  # Your unique order ID
    callback_url="https://your-app.com/payment/callback",  # URL to redirect after payment
    additional_data="Optional additional data",  # Optional
    originator="Optional originator info"  # Optional
)

# Send payment request
try:
    payment_response = payment_adapter.initiate_payment(payment_request)
except UnavailableError as e:
    logger.error(f"Payment service unavailable: {e}")
    raise
except InvalidArgumentError as e:
    logger.error(f"Invalid payment request: {e}")
    raise
else:
    # Check response
    if payment_response.status == 0:  # 0 means success in Parsian API
        # Redirect user to payment page
        payment_url = f"https://pec.shaparak.ir/NewIPG/?Token={payment_response.token}"
        logger.info(f"Payment initiated successfully, token: {payment_response.token}")
        # Use this URL to redirect the user to the payment gateway
    else:
        # Handle error
        logger.error(f"Payment initiation failed: {payment_response.message}")
```

#### Confirming a Payment

After the user completes the payment and returns to your callback URL, confirm the payment:

```python
import logging

from archipy.models.errors import UnavailableError, InternalError

# Configure logging
logger = logging.getLogger(__name__)

# Get the token from query parameters in your callback handler
token = 123456789  # This would come from the callback request

# Create confirm request
confirm_request = ConfirmRequestDTO(token=token)

# Confirm payment
try:
    confirm_response = payment_adapter.confirm_payment(confirm_request)
except UnavailableError as e:
    logger.error(f"Payment confirmation service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Payment confirmation failed: {e}")
    raise
else:
    if confirm_response.status == 0:  # 0 means success
        # Payment successful
        reference_number = confirm_response.rrn
        masked_card = confirm_response.card_number_masked

        logger.info(f"Payment confirmed! Reference: {reference_number}, Card: {masked_card}")
    else:
        # Handle failed confirmation
        logger.warning(f"Payment confirmation failed with status: {confirm_response.status}")
```

#### Confirming with Amount Verification

For enhanced security, you can confirm with amount verification:

```python
import logging

from archipy.models.errors import UnavailableError, InternalError, InvalidArgumentError

# Configure logging
logger = logging.getLogger(__name__)

# Create confirm with amount request
confirm_with_amount_request = ConfirmWithAmountRequestDTO(
    token=123456789,
    order_id=12345,
    amount=10000
)

# Confirm payment with amount verification
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
    if confirm_response.status == 0:  # 0 means success
        # Payment successful with amount verification
        logger.info("Payment confirmed with amount verification!")
    else:
        # Handle failed confirmation
        logger.warning(f"Payment confirmation failed with status: {confirm_response.status}")
```

#### Reversing a Payment

If needed, you can reverse (refund) a successful payment:

```python
import logging

from archipy.models.errors import UnavailableError, InternalError

# Configure logging
logger = logging.getLogger(__name__)

# Create reverse request
reverse_request = ReverseRequestDTO(token=123456789)

# Request payment reversal
try:
    reverse_response = payment_adapter.reverse_payment(reverse_request)
except UnavailableError as e:
    logger.error(f"Reversal service unavailable: {e}")
    raise
except InternalError as e:
    logger.error(f"Reversal failed: {e}")
    raise
else:
    if reverse_response.status == 0:  # 0 means success
        # Reversal successful
        logger.info("Payment reversal successful!")
    else:
        # Handle failed reversal
        logger.error(f"Payment reversal failed: {reverse_response.message}")
```

## Error Handling

The adapter uses ArchiPy's error system to provide consistent error handling:

```python
import logging

from archipy.models.errors import UnavailableError, InternalError

# Configure logging
logger = logging.getLogger(__name__)

try:
    payment_response = payment_adapter.initiate_payment(payment_request)
except UnavailableError as e:
    # Handle service unavailable error
    logger.error(f"Payment service unavailable: {e}")
    raise
except InternalError as e:
    # Handle unexpected error
    logger.error(f"Unexpected error: {e}")
    raise
else:
    logger.info(f"Payment initiated with token: {payment_response.token}")
```

## Complete Example

Here's a complete example integrating the payment flow into a FastAPI application:

```python
import logging

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from archipy.adapters.internet_payment_gateways.ir.parsian.adapters import (
    ConfirmRequestDTO,
    ParsianShaparakPaymentAdapter,
    PaymentRequestDTO,
)
from archipy.models.errors import InternalError, InvalidArgumentError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)

app = FastAPI()
payment_adapter = ParsianShaparakPaymentAdapter()


# Create order model
class OrderCreate(BaseModel):
    amount: int
    order_id: int
    description: str | None = None


# Payment routes
@app.post("/payments/create")
async def create_payment(order: OrderCreate) -> dict[str, int | str]:
    """Create a payment request.

    Args:
        order: Order creation data

    Returns:
        Payment token and URL

    Raises:
        HTTPException: If payment initiation fails
    """
    try:
        payment_request = PaymentRequestDTO(
            amount=order.amount,
            order_id=order.order_id,
            callback_url="https://your-app.com/payments/callback",
            additional_data=order.description
        )

        response = payment_adapter.initiate_payment(payment_request)
    except InvalidArgumentError as e:
        logger.error(f"Invalid payment parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment parameters"
        ) from e
    except UnavailableError as e:
        logger.error(f"Payment service unavailable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment service unavailable"
        ) from e
    except InternalError as e:
        logger.error(f"Internal error during payment initiation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        ) from e
    else:
        if response.status != 0:
            logger.warning(f"Payment initiation failed: {response.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment initiation failed: {response.message}"
            )

        logger.info(f"Payment created for order {order.order_id}, token: {response.token}")
        # Return payment URL or token
        return {
            "token": response.token,
            "payment_url": f"https://pec.shaparak.ir/NewIPG/?Token={response.token}"
        }


@app.get("/payments/callback")
async def payment_callback(token: int, request: Request) -> dict[str, str]:  # noqa: ARG001
    """Handle payment callback from gateway.

    Args:
        token: Payment token from gateway
        request: FastAPI request object

    Returns:
        Payment status information
    """
    try:
        confirm_request = ConfirmRequestDTO(token=token)
        confirm_response = payment_adapter.confirm_payment(confirm_request)
    except UnavailableError as e:
        logger.error(f"Confirmation service unavailable: {e}")
        return {
            "status": "error",
            "message": "Payment service unavailable"
        }
    except InternalError as e:
        logger.error(f"Confirmation failed: {e}")
        return {
            "status": "error",
            "message": "Payment verification failed"
        }
    else:
        if confirm_response.status == 0:
            # Payment successful - update your database
            logger.info(f"Payment confirmed, RRN: {confirm_response.rrn}")
            return {
                "status": "success",
                "reference_number": confirm_response.rrn,
                "card": confirm_response.card_number_masked
            }
        else:
            logger.warning(f"Payment verification failed with status: {confirm_response.status}")
            return {
                "status": "failed",
                "message": "Payment verification failed"
            }
```

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Payment gateway configuration setup
- [BDD Testing](../testing_strategy.md) — Testing payment operations
- [API Reference](../../api_reference/adapters/payment_gateways.md) — Full payment gateway API documentation
