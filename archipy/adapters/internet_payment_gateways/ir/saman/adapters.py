import logging
from typing import Self

import requests
from pydantic import Field, HttpUrl, model_validator

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SamanShaparakConfig
from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import FailedPreconditionError
from archipy.models.errors.system_errors import InternalError, UnavailableError

logger = logging.getLogger(__name__)


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
    # For Neo-PG only
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


class SamanShaparakPaymentAdapter:
    """Saman Shaparak (SEP) Classic Adapter - Full v3/.5 Protocol."""

    def __init__(self, config: SamanShaparakConfig | None = None) -> None:
        configs = BaseConfig.global_config().SAMAN_SHAPARAK if config is None else config

        if not configs.TERMINAL_ID:
            raise ValueError("TERMINAL_ID must be provided in SamanShaparakConfig")

        self.terminal_id = configs.TERMINAL_ID
        self.payment_url = str(configs.PAYMENT_URL)
        self.verify_url = str(configs.VERIFY_URL)
        self.reverse_url = str(configs.REVERSE_URL)

        self.session = requests.Session()
        if configs.PROXIES:
            self.session.proxies.update(configs.PROXIES)

        logger.info(f"SamanShaparakPaymentAdapter initialized with terminal {self.terminal_id}")

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token."""
        try:
            payload = {
                "action": "token",
                "TerminalId": self.terminal_id,
                "Amount": request.amount,
                "ResNum": request.res_num,
                "RedirectUrl": str(request.redirect_url),
                "CellNumber": request.cell_number,
                "Wage": request.wage,
                "TokenExpiryInMin": request.token_expiry_in_min,
                "HashedCardNumber": request.hashed_card_number,
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            logger.debug(f"Saman initiate payment payload: {payload}")
            resp = self.session.post(self.payment_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
            )
        except requests.RequestException as e:
            raise UnavailableError(resource_type="Saman Token Service") from e
        except Exception as e:
            raise InternalError() from e

    def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (strongly recommended)."""
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}

            resp = self.session.post(self.verify_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            transaction_detail = data.get("TransactionDetail", {})
            return VerifyResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
                rrn=transaction_detail.get("RRN"),
                reference_number=transaction_detail.get("RefNum"),
                masked_pan=transaction_detail.get("MaskedPan"),
                hashed_pan=transaction_detail.get("HashedPan"),
                original_amount=transaction_detail.get("OrginalAmount"),
                affective_amount=transaction_detail.get("AffectiveAmount"),
                trace_no=transaction_detail.get("StraceNo"),
            )
        except requests.RequestException as e:
            raise UnavailableError(resource_type="Saman Verify Service") from e
        except Exception as e:
            raise InternalError() from e

    def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction."""
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}
            resp = self.session.post(self.reverse_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            return ReverseResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
            )
        except requests.RequestException as e:
            raise UnavailableError(resource_type="Saman Reverse Service") from e
        except Exception as e:
            raise InternalError() from e


class SamanNeoPgShaparakPaymentAdapter(SamanShaparakPaymentAdapter):
    """Saman Neo-PG (New Generation) Adapter - Uses dynamic X-IPG-Url."""

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Override to capture dynamic neo-pg URL from header."""
        try:
            payload = {
                "action": "token",
                "TerminalId": self.terminal_id,
                "Amount": request.amount,
                "ResNum": request.res_num,
                "RedirectUrl": str(request.redirect_url),
                "CellNumber": request.cell_number,
                "Wage": request.wage,
                "TokenExpiryInMin": request.token_expiry_in_min,
                "HashedCardNumber": request.hashed_card_number,
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            resp = self.session.post(self.payment_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            ipg_url = resp.headers.get("X-IPG-Url")

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
                ipg_url=ipg_url,
            )
        except requests.RequestException as e:
            raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
        except Exception as e:
            raise InternalError() from e
