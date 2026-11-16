"""Immutable resource ownership identity."""

from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.dtos.keycloak.token_dtos import KeycloakOrganizationClaimDTO, KeycloakUserInfoDTO
from archipy.models.types.owner_type import OwnerType


class OwnerDTO(BaseDTO):
    """Resource owner; both UUID and type identify the ownership boundary."""

    owner_uuid: UUID = Field(description="UUID of the user or organization that owns the resource.")
    type: OwnerType = Field(description="Whether the resource owner is a user or an organization.")
    user: KeycloakUserInfoDTO | None = Field(
        default=None,
        description="Authenticated UserInfo claims for a user owner; absent for organization owners.",
    )
    organization: KeycloakOrganizationClaimDTO | None = Field(
        default=None,
        description="Selected organization claims for an organization owner; absent for user owners.",
    )

    @model_validator(mode="after")
    def validate_owner_claims(self) -> Self:
        """Require supplied claims to identify the matching owner kind and UUID."""
        if self.user is not None and (
            not self.is_user or self.user.user_uuid is None or UUID(self.user.user_uuid) != self.owner_uuid
        ):
            message = "User claims must match the user owner's UUID"
            raise ValueError(message)
        if self.organization is not None and (not self.is_organization or self.organization.id != self.owner_uuid):
            message = "Organization claims must match the organization owner's UUID"
            raise ValueError(message)
        return self

    @property
    def is_user(self) -> bool:
        """Return whether this owner is a user."""
        return self.type == OwnerType.USER

    @property
    def is_organization(self) -> bool:
        """Return whether this owner is an organization."""
        return self.type == OwnerType.ORGANIZATION
