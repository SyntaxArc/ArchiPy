from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from archipy.models.dtos.saman_ipg_dtos import (
        PaymentRequestDTO,
        PaymentResponseDTO,
        ReverseRequestDTO,
        ReverseResponseDTO,
        VerifyRequestDTO,
        VerifyResponseDTO,
    )


class SamanShaparakPaymentPort:
    """Port interface for Saman Shaparak payment gateway.

    Defines the contract for Saman IPG adapters implementing payment
    operations (token request, verification, and reversal).
    """

    @abstractmethod
    def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token."""
        raise NotImplementedError

    @abstractmethod
    def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction."""
        raise NotImplementedError

    @abstractmethod
    def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction."""
        raise NotImplementedError


class AsyncSamanShaparakPaymentPort:
    """Async port interface for Saman Shaparak payment gateway.

    Defines the contract for async Saman IPG adapters implementing payment
    operations (token request, verification, and reversal).
    """

    @abstractmethod
    async def initiate_payment(self, request: PaymentRequestDTO) -> PaymentResponseDTO:
        """Step 1: Request payment token (async)."""
        raise NotImplementedError

    @abstractmethod
    async def verify_payment(self, request: VerifyRequestDTO) -> VerifyResponseDTO:
        """Step 3: Verify transaction (async)."""
        raise NotImplementedError

    @abstractmethod
    async def reverse_payment(self, request: ReverseRequestDTO) -> ReverseResponseDTO:
        """Reverse a transaction (async)."""
        raise NotImplementedError
