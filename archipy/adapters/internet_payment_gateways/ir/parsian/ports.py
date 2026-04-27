from abc import abstractmethod

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
