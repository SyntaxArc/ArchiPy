import logging

import httpx

from archipy.adapters.internet_payment_gateways.ir.saman.ports import (
    AsyncSamanShaparakPaymentPort,
    PaymentRequestDTO,
    PaymentResponseDTO,
    ReverseRequestDTO,
    ReverseResponseDTO,
    SamanShaparakPaymentPort,
    VerifyRequestDTO,
    VerifyResponseDTO,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SamanShaparakConfig
from archipy.models.errors.system_errors import InternalError, UnavailableError

logger = logging.getLogger(__name__)


class SamanShaparakPaymentAdapter(SamanShaparakPaymentPort):
    """Saman Shaparak (SEP) Classic Adapter - Full v3/.5 Protocol.

    Implements the SamanShaparakPaymentPort interface using httpx for HTTP operations.
    Provides methods for initiating payments, verifying transactions, and reversing payments.
    """

    def __init__(self, config: SamanShaparakConfig | None = None) -> None:
        configs = BaseConfig.global_config().SAMAN_SHAPARAK if config is None else config

        if not configs.TERMINAL_ID:
            raise ValueError("TERMINAL_ID must be provided in SamanShaparakConfig")

        self.terminal_id = configs.TERMINAL_ID
        self.payment_url = str(configs.PAYMENT_URL)
        self.verify_url = str(configs.VERIFY_URL)
        self.reverse_url = str(configs.REVERSE_URL)

        proxy = self._get_proxy(configs.PROXIES)
        self.client = httpx.Client(proxy=proxy, timeout=30)

        logger.info(f"SamanShaparakPaymentAdapter initialized with terminal {self.terminal_id}")

    @staticmethod
    def _get_proxy(proxies: dict[str, str] | None) -> str | None:
        if proxies is None:
            return None
        return proxies.get("https") or proxies.get("http")

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token.

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, etc.

        Raises:
            UnavailableError: If the payment service is unavailable.
            InternalError: If an unexpected error occurs.
        """
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
            resp = self.client.post(self.payment_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
            )
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Token Service") from e
        except Exception as e:
            raise InternalError() from e

    def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (strongly recommended).

        Args:
            request: Verify request with reference number.

        Returns:
            VerifyResponseDTO: Response containing transaction details.

        Raises:
            UnavailableError: If the verify service is unavailable.
            InternalError: If an unexpected error occurs.
        """
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}

            resp = self.client.post(self.verify_url, json=payload)
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
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Verify Service") from e
        except Exception as e:
            raise InternalError() from e

    def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction.

        Args:
            request: Reverse request with reference number.

        Returns:
            ReverseResponseDTO: Response containing reversal result.

        Raises:
            UnavailableError: If the reverse service is unavailable.
            InternalError: If an unexpected error occurs.
        """
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}
            resp = self.client.post(self.reverse_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ReverseResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
            )
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Reverse Service") from e
        except Exception as e:
            raise InternalError() from e


class SamanNeoPgShaparakPaymentAdapter(SamanShaparakPaymentAdapter):
    """Saman Neo-PG (New Generation) Adapter - Uses dynamic X-IPG-Url.

    Extends SamanShaparakPaymentAdapter to capture the dynamic payment page URL
    from the X-IPG-Url header in the token response.
    """

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Override to capture dynamic neo-pg URL from header.

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, and IPG URL.

        Raises:
            UnavailableError: If the payment service is unavailable.
            InternalError: If an unexpected error occurs.
        """
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

            resp = self.client.post(self.payment_url, json=payload)
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
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
        except Exception as e:
            raise InternalError() from e


class AsyncSamanShaparakPaymentAdapter(AsyncSamanShaparakPaymentPort):
    """Async Saman Shaparak (SEP) Classic Adapter - Full v3/.5 Protocol.

    Async implementation of SamanShaparakPaymentPort using httpx.AsyncClient.
    Provides async methods for initiating payments, verifying transactions,
    and reversing payments.
    """

    def __init__(self, config: SamanShaparakConfig | None = None) -> None:
        configs = BaseConfig.global_config().SAMAN_SHAPARAK if config is None else config

        if not configs.TERMINAL_ID:
            raise ValueError("TERMINAL_ID must be provided in SamanShaparakConfig")

        self.terminal_id = configs.TERMINAL_ID
        self.payment_url = str(configs.PAYMENT_URL)
        self.verify_url = str(configs.VERIFY_URL)
        self.reverse_url = str(configs.REVERSE_URL)

        proxy = self._get_proxy(configs.PROXIES)
        self.client = httpx.AsyncClient(proxy=proxy, timeout=30)

        logger.info(f"AsyncSamanShaparakPaymentAdapter initialized with terminal {self.terminal_id}")

    @staticmethod
    def _get_proxy(proxies: dict[str, str] | None) -> str | None:
        if proxies is None:
            return None
        return proxies.get("https") or proxies.get("http")

    async def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token (async).

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, etc.

        Raises:
            UnavailableError: If the payment service is unavailable.
            InternalError: If an unexpected error occurs.
        """
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

            logger.debug(f"Saman async initiate payment payload: {payload}")
            resp = await self.client.post(self.payment_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
            )
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Token Service") from e
        except Exception as e:
            raise InternalError() from e

    async def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (async, strongly recommended).

        Args:
            request: Verify request with reference number.

        Returns:
            VerifyResponseDTO: Response containing transaction details.

        Raises:
            UnavailableError: If the verify service is unavailable.
            InternalError: If an unexpected error occurs.
        """
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}

            resp = await self.client.post(self.verify_url, json=payload)
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
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Verify Service") from e
        except Exception as e:
            raise InternalError() from e

    async def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction (async).

        Args:
            request: Reverse request with reference number.

        Returns:
            ReverseResponseDTO: Response containing reversal result.

        Raises:
            UnavailableError: If the reverse service is unavailable.
            InternalError: If an unexpected error occurs.
        """
        try:
            payload = {"RefNum": request.reference_number, "TerminalNumber": int(self.terminal_id)}
            resp = await self.client.post(self.reverse_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ReverseResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
            )
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Reverse Service") from e
        except Exception as e:
            raise InternalError() from e


class AsyncSamanNeoPgShaparakPaymentAdapter(AsyncSamanShaparakPaymentAdapter):
    """Async Saman Neo-PG (New Generation) Adapter - Uses dynamic X-IPG-Url.

    Async implementation extending AsyncSamanShaparakPaymentAdapter to capture
    the dynamic payment page URL from the X-IPG-Url header in the token response.
    """

    async def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Override to capture dynamic neo-pg URL from header (async).

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, and IPG URL.

        Raises:
            UnavailableError: If the payment service is unavailable.
            InternalError: If an unexpected error occurs.
        """
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

            resp = await self.client.post(self.payment_url, json=payload)
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
        except httpx.RequestError as e:
            raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
        except Exception as e:
            raise InternalError() from e
