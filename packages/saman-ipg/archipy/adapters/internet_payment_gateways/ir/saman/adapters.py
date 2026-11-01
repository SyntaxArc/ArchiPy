"""Saman IPG adapter implementations."""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import TYPE_CHECKING, Self
from urllib.parse import urlsplit

import httpx2

from archipy.adapters.internet_payment_gateways.ir.saman.ports import (
    AsyncSamanShaparakPaymentPort,
    SamanShaparakPaymentPort,
)
from archipy.configs.base_config import BaseConfig
from archipy.models.dtos.saman_ipg_dtos import (
    PaymentRequestDTO,
    PaymentResponseDTO,
    ReverseRequestDTO,
    ReverseResponseDTO,
    VerifyRequestDTO,
    VerifyResponseDTO,
)
from archipy.models.errors import BaseError, FailedPreconditionError
from archipy.models.errors.system_errors import InternalError, UnavailableError
from archipy.models.errors.validation_errors import InvalidArgumentError

if TYPE_CHECKING:
    from archipy.configs.config_template import SamanShaparakConfig

logger = logging.getLogger(__name__)


def _validated_ipg_url(url: str | None, status: object, allowed_hosts: list[str]) -> str | None:
    """Validate the dynamic payment page URL returned by the Neo-PG token service.

    Args:
        url: Value of the X-IPG-Url response header, if any.
        status: Status reported in the token reply; the URL is only required when it is 1 (success).
        allowed_hosts: Domains the URL host must belong to (the domain itself or a subdomain).

    Returns:
        str | None: The validated URL, or None when the reply carries no URL and is not a success.

    Raises:
        FailedPreconditionError: If a successful reply carries no X-IPG-Url header.
        InvalidArgumentError: If the URL is not https or its host is not in the allowed domains.
    """
    if not url:
        if status == 1:
            raise FailedPreconditionError()
        return None
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    allowed = any(host == domain.lower() or host.endswith(f".{domain.lower()}") for domain in allowed_hosts)
    if parts.scheme != "https" or not allowed:
        raise InvalidArgumentError(argument_name="X-IPG-Url")
    return url


class SamanShaparakPaymentAdapter(SamanShaparakPaymentPort):
    """Saman Shaparak (SEP) Classic Adapter - Full v3/.5 Protocol.

    Implements the SamanShaparakPaymentPort interface using httpx for HTTP operations.
    Provides methods for initiating payments, verifying transactions, and reversing payments.
    """

    def __init__(self, config: SamanShaparakConfig | None = None) -> None:
        """Initialize SamanShaparakPaymentAdapter.

        Args:
            config: Optional Saman Shaparak config; defaults to the global config.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not configured.
        """
        configs = config or BaseConfig.global_config().SAMAN_SHAPARAK

        if not configs.TERMINAL_ID:
            raise InvalidArgumentError(argument_name="TERMINAL_ID")

        self.terminal_id = configs.TERMINAL_ID
        self.payment_url = str(configs.PAYMENT_URL)
        self.verify_url = str(configs.VERIFY_URL)
        self.reverse_url = str(configs.REVERSE_URL)
        self.allowed_ipg_hosts = list(configs.ALLOWED_IPG_HOSTS)

        proxy = self._get_proxy(configs.PROXIES)
        self.client = httpx2.Client(proxy=proxy, timeout=configs.TIMEOUT)

        logger.info("SamanShaparakPaymentAdapter initialized with terminal %s", self.terminal_id)

    @staticmethod
    def _get_proxy(proxies: dict[str, str] | None) -> str | None:
        if proxies is None:
            return None
        return proxies.get("https") or proxies.get("http") or proxies.get("socks5") or proxies.get("socks5h")

    def close(self) -> None:
        """Close the underlying HTTP client and release its connections."""
        self.client.close()

    def __enter__(self) -> Self:
        """Enter the context manager.

        Returns:
            Self: This adapter.
        """
        return self

    def __exit__(self, *_: object) -> None:
        """Close the adapter when leaving the context manager."""
        self.close()

    def _get_terminal_number(self) -> int:
        """Convert the configured terminal ID to the numeric form required by verify/reverse.

        Returns:
            int: Numeric terminal number.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
        """
        try:
            return int(self.terminal_id)
        except ValueError as e:
            raise InvalidArgumentError(argument_name="TERMINAL_ID") from e

    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token.

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, etc.

        Raises:
            UnavailableError: If the payment service is unavailable or returns HTTP 5xx.
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

            logger.debug("Saman initiate payment payload: %s", payload)
            resp = self.client.post(self.payment_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Token Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Token Service") from e
            raise InternalError() from e
        except Exception as e:
            raise InternalError() from e

    def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (strongly recommended).

        Args:
            request: Verify request with reference number.

        Returns:
            VerifyResponseDTO: Response containing transaction details.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
            UnavailableError: If the verify service is unavailable or returns HTTP 5xx.
            InternalError: If an unexpected error occurs.
        """
        terminal_number = self._get_terminal_number()
        try:
            payload = {
                "RefNum": request.reference_number,
                "TerminalNumber": terminal_number,
            }

            resp = self.client.post(self.verify_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            transaction_detail = data.get("TransactionDetail") or {}
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
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Verify Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Verify Service") from e
            raise InternalError() from e
        except Exception as e:
            raise InternalError() from e

    def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction.

        Args:
            request: Reverse request with reference number.

        Returns:
            ReverseResponseDTO: Response containing reversal result.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
            UnavailableError: If the reverse service is unavailable or returns HTTP 5xx.
            InternalError: If an unexpected error occurs.
        """
        terminal_number = self._get_terminal_number()
        try:
            payload = {
                "RefNum": request.reference_number,
                "TerminalNumber": terminal_number,
            }
            resp = self.client.post(self.reverse_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ReverseResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Reverse Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Reverse Service") from e
            raise InternalError() from e
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
            UnavailableError: If the payment service is unavailable or returns HTTP 5xx.
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

            ipg_url = _validated_ipg_url(resp.headers.get("X-IPG-Url"), data.get("status"), self.allowed_ipg_hosts)

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
                ipg_url=ipg_url,
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
            raise InternalError() from e
        except BaseError:
            raise
        except Exception as e:
            raise InternalError() from e


class AsyncSamanShaparakPaymentAdapter(AsyncSamanShaparakPaymentPort):
    """Async Saman Shaparak (SEP) Classic Adapter - Full v3/.5 Protocol.

    Async implementation of SamanShaparakPaymentPort using httpx2.AsyncClient.
    Provides async methods for initiating payments, verifying transactions,
    and reversing payments.
    """

    def __init__(self, config: SamanShaparakConfig | None = None) -> None:
        """Initialize AsyncSamanShaparakPaymentAdapter.

        Args:
            config: Optional Saman Shaparak config; defaults to the global config.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not configured.
        """
        configs = config or BaseConfig.global_config().SAMAN_SHAPARAK

        if not configs.TERMINAL_ID:
            raise InvalidArgumentError(argument_name="TERMINAL_ID")

        self.terminal_id = configs.TERMINAL_ID
        self.payment_url = str(configs.PAYMENT_URL)
        self.verify_url = str(configs.VERIFY_URL)
        self.reverse_url = str(configs.REVERSE_URL)
        self.allowed_ipg_hosts = list(configs.ALLOWED_IPG_HOSTS)

        proxy = self._get_proxy(configs.PROXIES)
        self.client = httpx2.AsyncClient(proxy=proxy, timeout=configs.TIMEOUT)

        logger.info(
            "AsyncSamanShaparakPaymentAdapter initialized with terminal %s",
            self.terminal_id,
        )

    @staticmethod
    def _get_proxy(proxies: dict[str, str] | None) -> str | None:
        if proxies is None:
            return None
        return proxies.get("https") or proxies.get("http") or proxies.get("socks5") or proxies.get("socks5h")

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release its connections."""
        await self.client.aclose()

    async def __aenter__(self) -> Self:
        """Enter the async context manager.

        Returns:
            Self: This adapter.
        """
        return self

    async def __aexit__(self, *_: object) -> None:
        """Close the adapter when leaving the async context manager."""
        await self.aclose()

    def _get_terminal_number(self) -> int:
        """Convert the configured terminal ID to the numeric form required by verify/reverse.

        Returns:
            int: Numeric terminal number.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
        """
        try:
            return int(self.terminal_id)
        except ValueError as e:
            raise InvalidArgumentError(argument_name="TERMINAL_ID") from e

    async def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token (async).

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, etc.

        Raises:
            UnavailableError: If the payment service is unavailable or returns HTTP 5xx.
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

            logger.debug("Saman async initiate payment payload: %s", payload)
            resp = await self.client.post(self.payment_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Token Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Token Service") from e
            raise InternalError() from e
        except Exception as e:
            raise InternalError() from e

    async def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (async, strongly recommended).

        Args:
            request: Verify request with reference number.

        Returns:
            VerifyResponseDTO: Response containing transaction details.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
            UnavailableError: If the verify service is unavailable or returns HTTP 5xx.
            InternalError: If an unexpected error occurs.
        """
        terminal_number = self._get_terminal_number()
        try:
            payload = {
                "RefNum": request.reference_number,
                "TerminalNumber": terminal_number,
            }

            resp = await self.client.post(self.verify_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            transaction_detail = data.get("TransactionDetail") or {}
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
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Verify Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Verify Service") from e
            raise InternalError() from e
        except Exception as e:
            raise InternalError() from e

    async def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction (async).

        Args:
            request: Reverse request with reference number.

        Returns:
            ReverseResponseDTO: Response containing reversal result.

        Raises:
            InvalidArgumentError: If TERMINAL_ID is not numeric.
            UnavailableError: If the reverse service is unavailable or returns HTTP 5xx.
            InternalError: If an unexpected error occurs.
        """
        terminal_number = self._get_terminal_number()
        try:
            payload = {
                "RefNum": request.reference_number,
                "TerminalNumber": terminal_number,
            }
            resp = await self.client.post(self.reverse_url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            return ReverseResponseDTO(
                success=data.get("Success", False),
                result_code=data.get("ResultCode", -1),
                result_description=data.get("ResultDescription", "Unknown"),
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Reverse Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Reverse Service") from e
            raise InternalError() from e
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
            UnavailableError: If the payment service is unavailable or returns HTTP 5xx.
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

            ipg_url = _validated_ipg_url(resp.headers.get("X-IPG-Url"), data.get("status"), self.allowed_ipg_hosts)

            return PaymentResponseDTO(
                status=data.get("status"),
                token=data.get("token"),
                error_code=data.get("errorCode"),
                error_desc=data.get("errorDesc"),
                ipg_url=ipg_url,
            )
        except httpx2.RequestError as e:
            raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
        except httpx2.HTTPStatusError as e:
            if e.response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
                raise UnavailableError(resource_type="Saman Neo-PG Token Service") from e
            raise InternalError() from e
        except BaseError:
            raise
        except Exception as e:
            raise InternalError() from e
