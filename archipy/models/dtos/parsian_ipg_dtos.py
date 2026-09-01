"""DTOs for Parsian IPG operations."""

from pydantic import Field, HttpUrl

from archipy.models.dtos.base_dtos import BaseDTO


class PaymentRequestDTO(BaseDTO):
    """DTO for initiating a payment request."""

    amount: int = Field(..., gt=0, description="Transaction amount in IRR")
    order_id: int = Field(..., gt=0, description="Unique order identifier")
    callback_url: HttpUrl = Field(..., description="URL to redirect after payment")
    additional_data: str | None = Field(None, description="Additional transaction data")
    originator: str | None = Field(None, description="Transaction originator")


class PaymentResponseDTO(BaseDTO):
    """DTO for payment response."""

    token: int | None = Field(None, description="Transaction token")
    status: int | None = Field(None, description="Transaction status code")
    message: str | None = Field(None, description="Status message or error description")


class ConfirmRequestDTO(BaseDTO):
    """DTO for confirming a payment."""

    token: int = Field(..., gt=0, description="Transaction token")


class ConfirmResponseDTO(BaseDTO):
    """DTO for confirm payment response."""

    status: int | None = Field(None, description="Transaction status code")
    rrn: int | None = Field(None, description="Retrieval Reference Number")
    card_number_masked: str | None = Field(None, description="Masked card number")
    token: int | None = Field(None, description="Transaction token")


class ConfirmWithAmountRequestDTO(BaseDTO):
    """DTO for confirming a payment with amount and order verification."""

    token: int = Field(..., gt=0, description="Transaction token")
    order_id: int = Field(..., gt=0, description="Unique order identifier")
    amount: int = Field(..., gt=0, description="Transaction amount in IRR")


class ConfirmWithAmountResponseDTO(BaseDTO):
    """DTO for confirm payment with amount response."""

    status: int | None = Field(None, description="Transaction status code")
    rrn: int | None = Field(None, description="Retrieval Reference Number")
    card_number_masked: str | None = Field(None, description="Masked card number")
    token: int | None = Field(None, description="Transaction token")


class ReverseRequestDTO(BaseDTO):
    """DTO for reversing a payment."""

    token: int = Field(..., gt=0, description="Transaction token")


class ReverseResponseDTO(BaseDTO):
    """DTO for reverse payment response."""

    status: int | None = Field(None, description="Transaction status code")
    message: str | None = Field(None, description="Status message or error description")
    token: int | None = Field(None, description="Transaction token")
