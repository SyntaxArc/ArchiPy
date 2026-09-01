"""DTOs for Saman IPG operations."""

from typing import Self

from pydantic import Field, HttpUrl, model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import FailedPreconditionError


class PaymentRequestDTO(BaseDTO):
    """Request for getting payment token."""

    amount: int = Field(..., gt=0, description="مبلغ به ریال")
    res_num: str = Field(..., description="شماره سفارش یکتا (ResNum)")
    redirect_url: HttpUrl = Field(..., description="آدرس صفحه بازگشت")
    cell_number: str | None = Field(None, description="شماره موبایل خریدار")
    wage: int | None = Field(None, description="مبلغ کارمزد")
    token_expiry_in_min: int = Field(20, ge=20, le=3600, description="مدت اعتبار توکن به دقیقه")
    hashed_card_number: str | None = Field(None, description="شماره کارت هش شده")


class PaymentResponseDTO(BaseDTO):
    """Response from token request."""

    status: int
    token: str | None = None
    error_code: str | None = None
    error_desc: str | None = None
    ipg_url: str | None = Field(None, description="Dynamic payment page URL from X-IPG-Url header (Neo-PG only)")

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        """Validate TLS-related settings to ensure compatibility."""
        if (self.status == 1 and self.token is None) or (self.status == -1 and self.error_code is None):
            raise FailedPreconditionError()
        return self


class VerifyRequestDTO(BaseDTO):
    """Request for verifying a payment."""

    reference_number: str = Field(..., description="رسید دیجیتالی (RefNum)")


class VerifyResponseDTO(BaseDTO):
    """Response from payment verification."""

    success: bool
    result_code: int
    result_description: str
    rrn: str | None = None
    reference_number: str | None = None
    masked_pan: str | None = None
    hashed_pan: str | None = None
    original_amount: int | None = None
    affective_amount: int | None = None
    trace_no: str | None = None


class ReverseRequestDTO(BaseDTO):
    """Request for reversing a payment."""

    reference_number: str = Field(...)


class ReverseResponseDTO(BaseDTO):
    """Response from payment reversal."""

    success: bool
    result_code: int
    result_description: str
