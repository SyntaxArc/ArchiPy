"""Payment gateway configuration."""

from pydantic import BaseModel, Field, HttpUrl


class ParsianShaparakConfig(BaseModel):
    """Configuration settings for Parsian Shaparak payment gateway integration.

    Controls connection parameters and authentication for the Parsian Shaparak
    payment gateway services.
    """

    LOGIN_ACCOUNT: str | None = Field(default=None, description="Merchant login account for authentication")
    PAYMENT_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Sale/SaleService.asmx?WSDL",
        description="WSDL URL for the payment service",
    )
    CONFIRM_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Confirm/ConfirmService.asmx?WSDL",
        description="WSDL URL for the confirm service",
    )
    REVERSAL_WSDL_URL: str = Field(
        default="https://pec.shaparak.ir/NewIPGServices/Reverse/ReversalService.asmx?WSDL",
        description="WSDL URL for the reversal service",
    )
    PROXIES: dict[str, str] | None = Field(
        default=None,
        description="Optional HTTP/HTTPS proxy configuration dictionary",
    )
    TIMEOUT: float = Field(
        default=30,
        gt=0,
        description="Seconds to wait for a SOAP operation response and to download each WSDL",
    )


class SamanShaparakConfig(BaseModel):
    """Configuration for Saman Shaparak (SEP) Payment Gateway."""

    TERMINAL_ID: str | None = Field(default=None, description="Merchant terminal id for authentication")
    PAYMENT_URL: HttpUrl = Field(
        default=HttpUrl("https://sep.shaparak.ir/onlinepg/onlinepg"),
        description="Token request endpoint",
    )
    VERIFY_URL: HttpUrl = Field(
        default=HttpUrl("https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction"),
        description="Verify endpoint",
    )
    REVERSE_URL: HttpUrl = Field(
        default=HttpUrl("https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/ReverseTransaction"),
        description="Reverse endpoint",
    )
    PROXIES: dict[str, str] | None = Field(default=None, description="Proxy settings")
    TIMEOUT: float = Field(default=30, gt=0, description="Seconds to wait for a gateway response")
    ALLOWED_IPG_HOSTS: list[str] = Field(
        default_factory=lambda: ["shaparak.ir"],
        description="Domains (and their subdomains) the Neo-PG X-IPG-Url redirect host must belong to",
    )
