"""Keycloak port mixins for organization operations."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

from archipy.models.dtos.keycloak.identity_provider_dtos import (
    KeycloakIdentityProviderDTO,
)

if TYPE_CHECKING:
    from archipy.models.dtos.keycloak.common_dtos import (
        KeycloakAssignResultDTO,
        KeycloakDeleteResultDTO,
        KeycloakUpdateResultDTO,
    )
    from archipy.models.dtos.keycloak.identity_provider_dtos import (
        KeycloakIdentityProviderDTO,
        KeycloakOrganizationIdentityProviderLinkRequestDTO,
    )
    from archipy.models.dtos.keycloak.organization_dtos import (
        KeycloakOrganizationDTO,
        KeycloakOrganizationInvitationDTO,
        KeycloakOrganizationMemberDTO,
        KeycloakOrganizationRequestDTO,
    )


class KeycloakOrganizationsPort:
    """Sync Keycloak port interface for organization operations."""

    @abstractmethod
    def get_organizations(self, query: dict[str, Any] | None = None) -> list[KeycloakOrganizationDTO]:
        """Fetch all organizations. Returns list of OrganizationRepresentation, filtered by query."""
        raise NotImplementedError

    @abstractmethod
    def get_organization(self, organization_id: str) -> KeycloakOrganizationDTO:
        """Get representation of the organization by ID."""
        raise NotImplementedError

    @abstractmethod
    def create_organization(
        self,
        name: str,
        alias: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        raise NotImplementedError

    @abstractmethod
    def update_organization(
        self,
        organization_id: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakUpdateResultDTO:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization(self, organization_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_idps(self, organization_id: str) -> list[KeycloakIdentityProviderDTO]:
        """Get IDPs by organization id."""
        raise NotImplementedError

    @abstractmethod
    def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationDTO]:
        """Get organizations by user id. Returns list of organizations the user is member of."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationMemberDTO]:
        """Get members by organization id, optionally filtered by query parameters."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        raise NotImplementedError

    @abstractmethod
    def organization_user_add(self, user_id: str, organization_id: str) -> KeycloakAssignResultDTO:
        """Add a user to an organization."""
        raise NotImplementedError

    @abstractmethod
    def organization_user_remove(self, user_id: str, organization_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization."""
        raise NotImplementedError

    @abstractmethod
    def organization_idp_add(self, organization_id: str, idp_alias: str) -> KeycloakAssignResultDTO:
        """Link an identity provider to an organization."""
        raise NotImplementedError

    @abstractmethod
    def organization_idp_remove(self, organization_id: str, idp_alias: str) -> KeycloakDeleteResultDTO:
        """Unlink an identity provider from an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_idp(self, organization_id: str, idp_alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider linked to an organization."""
        raise NotImplementedError

    @abstractmethod
    def update_organization_idp(
        self,
        organization_id: str,
        idp_alias: str,
        link: KeycloakOrganizationIdentityProviderLinkRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update how an identity provider is linked to an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organizations_count(self, query: dict[str, Any] | None = None) -> int:
        """Count the organizations matching the query."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_member(self, organization_id: str, member_id: str) -> KeycloakOrganizationMemberDTO:
        """Get one member of an organization."""
        raise NotImplementedError

    @abstractmethod
    def update_organization_member_membership_type(
        self,
        organization_id: str,
        member_id: str,
        membership_type: str,
    ) -> KeycloakUpdateResultDTO:
        """Set a member's membership type (``MANAGED`` or ``UNMANAGED``)."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_invitations(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationInvitationDTO]:
        """List the invitations of an organization."""
        raise NotImplementedError

    @abstractmethod
    def get_organization_invitation(
        self,
        organization_id: str,
        invitation_id: str,
    ) -> KeycloakOrganizationInvitationDTO:
        """Get one invitation of an organization."""
        raise NotImplementedError

    @abstractmethod
    def delete_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakDeleteResultDTO:
        """Delete an invitation of an organization."""
        raise NotImplementedError

    @abstractmethod
    def resend_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakUpdateResultDTO:
        """Resend an invitation of an organization."""
        raise NotImplementedError


class AsyncKeycloakOrganizationsPort:
    """Async Keycloak port interface for organization operations."""

    @abstractmethod
    async def get_organizations(self, query: dict[str, Any] | None = None) -> list[KeycloakOrganizationDTO]:
        """Fetch all organizations. Returns list of OrganizationRepresentation, filtered by query."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization(self, organization_id: str) -> KeycloakOrganizationDTO:
        """Get representation of the organization by ID."""
        raise NotImplementedError

    @abstractmethod
    async def create_organization(
        self,
        name: str,
        alias: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        raise NotImplementedError

    @abstractmethod
    async def update_organization(
        self,
        organization_id: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakUpdateResultDTO:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization(self, organization_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_idps(self, organization_id: str) -> list[KeycloakIdentityProviderDTO]:
        """Get IDPs by organization id."""
        raise NotImplementedError

    @abstractmethod
    async def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationDTO]:
        """Get organizations by user id. Returns list of organizations the user is member of."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationMemberDTO]:
        """Get members by organization id, optionally filtered by query parameters."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        raise NotImplementedError

    @abstractmethod
    async def organization_user_add(self, user_id: str, organization_id: str) -> KeycloakAssignResultDTO:
        """Add a user to an organization."""
        raise NotImplementedError

    @abstractmethod
    async def organization_user_remove(self, user_id: str, organization_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization."""
        raise NotImplementedError

    @abstractmethod
    async def organization_idp_add(self, organization_id: str, idp_alias: str) -> KeycloakAssignResultDTO:
        """Link an identity provider to an organization."""
        raise NotImplementedError

    @abstractmethod
    async def organization_idp_remove(self, organization_id: str, idp_alias: str) -> KeycloakDeleteResultDTO:
        """Unlink an identity provider from an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_idp(self, organization_id: str, idp_alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider linked to an organization."""
        raise NotImplementedError

    @abstractmethod
    async def update_organization_idp(
        self,
        organization_id: str,
        idp_alias: str,
        link: KeycloakOrganizationIdentityProviderLinkRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update how an identity provider is linked to an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organizations_count(self, query: dict[str, Any] | None = None) -> int:
        """Count the organizations matching the query."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_member(self, organization_id: str, member_id: str) -> KeycloakOrganizationMemberDTO:
        """Get one member of an organization."""
        raise NotImplementedError

    @abstractmethod
    async def update_organization_member_membership_type(
        self,
        organization_id: str,
        member_id: str,
        membership_type: str,
    ) -> KeycloakUpdateResultDTO:
        """Set a member's membership type (``MANAGED`` or ``UNMANAGED``)."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_invitations(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationInvitationDTO]:
        """List the invitations of an organization."""
        raise NotImplementedError

    @abstractmethod
    async def get_organization_invitation(
        self,
        organization_id: str,
        invitation_id: str,
    ) -> KeycloakOrganizationInvitationDTO:
        """Get one invitation of an organization."""
        raise NotImplementedError

    @abstractmethod
    async def delete_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakDeleteResultDTO:
        """Delete an invitation of an organization."""
        raise NotImplementedError

    @abstractmethod
    async def resend_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakUpdateResultDTO:
        """Resend an invitation of an organization."""
        raise NotImplementedError
