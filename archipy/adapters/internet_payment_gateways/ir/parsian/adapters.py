import logging

import requests
import zeep
from pydantic import Field, HttpUrl
from zeep.exceptions import Fault
from zeep.transports import Transport

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ParsianShaparakConfig
from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import InternalError, UnavailableError

# Configure logging
logger = logging.getLogger(__name__)


# DTOs for ParsianShaparakPaymentAdapter
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


class ParsianShaparakPaymentAdapter:
    """Adapter for interacting with Parsian Shaparak payment gateway services.

    Provides methods for initiating payments, confirming transactions, and reversing
    payments through the Parsian Shaparak payment gateway SOAP services. Supports
    proxy configuration for environments where direct connections are not possible.
    """

    def __init__(self, config: ParsianShaparakConfig | None = None) -> None:
        """Initialize the adapter with Parsian Shaparak configuration.

        Args:
            config (ParsianShaparakConfig | None): Configuration for Parsian Shaparak services.
                If None, uses global config. Includes optional proxy configuration via
                the PROXIES field.

        Raises:
            ValueError: If LOGIN_ACCOUNT is not a valid string.
        """
        configs = BaseConfig.global_config().PARSIAN_SHAPARAK if config is None else config
        if not configs.LOGIN_ACCOUNT or not isinstance(configs.LOGIN_ACCOUNT, str):
            raise ValueError("LOGIN_ACCOUNT must be a non-empty string")

        self.login_account = configs.LOGIN_ACCOUNT
        transport = None
        if configs.PROXIES:
            session = requests.Session()
            session.proxies = configs.PROXIES
            transport = Transport(session=session)

        # Initialize SOAP clients
        self.sale_client = zeep.Client(wsdl=configs.PAYMENT_WSDL_URL, transport=transport)
        self.confirm_client = zeep.Client(wsdl=configs.CONFIRM_WSDL_URL, transport=transport)
        self.reversal_client = zeep.Client(wsdl=configs.REVERSAL_WSDL_URL, transport=transport)

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Initiate a payment request.

        Args:
            request (PaymentRequestDTO): Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, and message.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        try:
            request_data = {
                "LoginAccount": self.login_account,
                "Amount": request.amount,
                "OrderId": request.order_id,
                "CallBackUrl": str(request.callback_url),
                "AdditionalData": request.additional_data,
                "Originator": request.originator,
            }

            logger.debug(f"Initiating payment: {request_data}")
            response = self.sale_client.service.SalePaymentRequest(requestData=request_data)
            result = PaymentResponseDTO(
                token=response.Token,
                status=response.Status,
                message=response.Message,
            )
            logger.debug(f"Payment response: {result}")
        except Fault as exception:
            raise UnavailableError(resource_type="Parsian Shaparak Sale Service") from exception
        except Exception as exception:
            raise InternalError() from exception
        else:
            return result

    def confirm_payment(self, request: ConfirmRequestDTO) -> ConfirmResponseDTO:
        """Confirm a payment transaction.

        Args:
            request (ConfirmRequestDTO): Confirm request data.

        Returns:
            ConfirmResponseDTO: Response containing status, RRN, card number, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        try:
            request_data = {"LoginAccount": self.login_account, "Token": request.token}

            logger.debug(f"Confirming payment: {request_data}")
            response = self.confirm_client.service.ConfirmPayment(requestData=request_data)
            result = ConfirmResponseDTO(
                status=response.Status,
                rrn=response.RRN,
                card_number_masked=response.CardNumberMasked,
                token=response.Token,
            )
            logger.debug(f"Confirm response: {result}")
        except Fault as exception:
            raise UnavailableError(resource_type="Parsian Shaparak Confirm Service") from exception
        except Exception as exception:
            raise InternalError() from exception
        else:
            return result

    def confirm_payment_with_amount(self, request: ConfirmWithAmountRequestDTO) -> ConfirmWithAmountResponseDTO:
        """Confirm a payment transaction with amount and order verification.

        Args:
            request (ConfirmWithAmountRequestDTO): Confirm with amount request data.

        Returns:
            ConfirmWithAmountResponseDTO: Response containing status, RRN, card number, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        try:
            request_data = {
                "LoginAccount": self.login_account,
                "Token": request.token,
                "OrderId": request.order_id,
                "Amount": request.amount,
            }

            logger.debug(f"Confirming payment with amount: {request_data}")
            response = self.confirm_client.service.ConfirmPaymentWithAmount(requestData=request_data)
            result = ConfirmWithAmountResponseDTO(
                status=response.Status,
                rrn=response.RRN,
                card_number_masked=response.CardNumberMasked,
                token=response.Token,
            )
            logger.debug(f"Confirm with amount response: {result}")
        except Fault as exception:
            raise UnavailableError(resource_type="Parsian Shaparak Confirm Service") from exception
        except Exception as exception:
            raise InternalError() from exception
        else:
            return result

    def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Request a reversal of a confirmed transaction.

        Args:
            request (ReverseRequestDTO): Reverse request data.

        Returns:
            ReverseResponseDTO: Response containing status, message, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        try:
            request_data = {"LoginAccount": self.login_account, "Token": request.token}

            logger.debug(f"Reversing payment: {request_data}")
            response = self.reversal_client.service.ReversalRequest(requestData=request_data)
            result = ReverseResponseDTO(
                status=response.Status,
                message=response.Message,
                token=response.Token,
            )
            logger.debug(f"Reversal response: {result}")
        except Fault as exception:
            raise UnavailableError(resource_type="Parsian Shaparak Reversal Service") from exception
        except Exception as exception:
            raise InternalError() from exception
        else:
            return result
