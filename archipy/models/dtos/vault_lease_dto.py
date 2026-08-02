"""DTO for HashiCorp Vault dynamic secret leases."""

from typing import Any

from pydantic import Field

from archipy.models.dtos.base_dtos import BaseDTO


class VaultLeaseDTO(BaseDTO):
    """Represents a leased dynamic secret returned by Vault.

    Attributes:
        lease_id: Unique lease identifier used for renew/revoke operations.
        lease_duration: Lease TTL in seconds.
        renewable: Whether the lease can be renewed.
        data: Secret payload associated with the lease (e.g. username/password).
    """

    lease_id: str = Field(description="Unique lease identifier")
    lease_duration: int = Field(description="Lease TTL in seconds")
    renewable: bool = Field(description="Whether the lease can be renewed")
    data: dict[str, Any] = Field(default_factory=dict, description="Secret payload for the lease")
