import logging

import requests
import zeep
from zeep.exceptions import Fault
from zeep.transports import Transport

from archipy.adapters.internet_payment_gateways.ir.parsian.ports import (
    ConfirmRequestDTO,
    ConfirmResponseDTO,
    ConfirmWithAmountRequestDTO,
    ConfirmWithAmountResponseDTO,
    ParsianShaparakPaymentPort,
    PaymentRequestDTO,
    PaymentResponseDTO,
    ReverseRequestDTO,
    ReverseResponseDTO,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ParsianShaparakConfig
from archipy.models.errors import InternalError, UnavailableError

logger = logging.getLogger(__name__)


class ParsianShaparakPaymentAdapter(ParsianShaparakPaymentPort):
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

        self.sale_client = zeep.Client(wsdl=configs.PAYMENT_WSDL_URL, transport=transport)
        self.confirm_client = zeep.Client(wsdl=configs.CONFIRM_WSDL_URL, transport=transport)
        self.reversal_client = zeep.Client(wsdl=configs.REVERSAL_WSDL_URL, transport=transport)

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token.

        Args:
            request: Payment request data.

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
        """Step 3: Confirm transaction.

        Args:
            request: Confirm request data.

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
        """Confirm transaction with amount and order verification.

        Args:
            request: Confirm with amount request data.

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
        """Reverse a transaction.

        Args:
            request: Reverse request data.

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
