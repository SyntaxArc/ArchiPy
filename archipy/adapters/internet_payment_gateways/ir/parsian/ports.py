from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.parsian_ipg_dtos import (
        ConfirmRequestDTO,
        ConfirmResponseDTO,
        ConfirmWithAmountRequestDTO,
        ConfirmWithAmountResponseDTO,
        PaymentRequestDTO,
        PaymentResponseDTO,
        ReverseRequestDTO,
        ReverseResponseDTO,
    )


class ParsianShaparakPaymentPort:
    """Port interface for Parsian Shaparak payment gateway.

    Defines the contract for Parsian IPG adapters implementing payment
    operations (token request, confirmation, and reversal).
    """

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError


class AsyncParsianShaparakPaymentPort:
    """Async port interface for Parsian Shaparak payment gateway.

    Defines the contract for async Parsian IPG adapters implementing payment
    operations (token request, confirmation, and reversal).
    """

    @abstractmethod
    async def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token (async).

        Args:
            request: Payment request data.

        Returns:
            PaymentResponseDTO: Response containing token, status, and message.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        raise NotImplementedError

    @abstractmethod
    async def confirm_payment(self, request: ConfirmRequestDTO) -> ConfirmResponseDTO:
        """Step 3: Confirm transaction (async).

        Args:
            request: Confirm request data.

        Returns:
            ConfirmResponseDTO: Response containing status, RRN, card number, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        raise NotImplementedError

    @abstractmethod
    async def confirm_payment_with_amount(self, request: ConfirmWithAmountRequestDTO) -> ConfirmWithAmountResponseDTO:
        """Confirm transaction with amount and order verification (async).

        Args:
            request: Confirm with amount request data.

        Returns:
            ConfirmWithAmountResponseDTO: Response containing status, RRN, card number, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        raise NotImplementedError

    @abstractmethod
    async def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction (async).

        Args:
            request: Reverse request data.

        Returns:
            ReverseResponseDTO: Response containing status, message, and token.

        Raises:
            UnavailableError: If a SOAP fault occurs during the request.
            InternalError: If an unexpected error occurs during the request.
        """
        raise NotImplementedError
