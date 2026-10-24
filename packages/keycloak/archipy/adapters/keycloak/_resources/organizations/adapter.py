"""Keycloak adapter mixins for organization operations."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from archipy.adapters.keycloak._base import (
    AsyncKeycloakMixinBase,
    SyncKeycloakMixinBase,
    segment,
    to_dto,
    to_dto_list,
    to_mutation_result,
    to_request_payload,
)
from archipy.helpers.utils.string_utils import StringUtils
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


def _organization_payload(
    name: str,
    alias: str,
    kwargs: dict[str, Any],
    config: KeycloakOrganizationRequestDTO | None = None,
) -> dict[str, Any]:
    """Build organization create payload with snake_case kwargs mapped to camelCase."""
    payload: dict[str, Any] = {**(config.to_payload() if config is not None else {}), "name": name, "alias": alias}
    for key, value in kwargs.items():
        if key in {"name", "alias"}:
            continue
        payload[StringUtils.snake_to_camel_case(key)] = value
    return payload


def _organization_update_payload(
    kwargs: dict[str, Any],
    config: KeycloakOrganizationRequestDTO | None = None,
) -> dict[str, Any]:
    """Build organization update payload with snake_case kwargs mapped to camelCase."""
    return {
        **(config.to_payload() if config is not None else {}),
        **{StringUtils.snake_to_camel_case(key): value for key, value in kwargs.items()},
    }


class KeycloakOrganizationsMixin(SyncKeycloakMixinBase):
    """Sync Keycloak mixin for organization operations."""

    def get_organizations(self, query: dict[str, Any] | None = None) -> list[KeycloakOrganizationDTO]:
        """Fetch all organizations, optionally filtered by query parameters.

        Args:
            query: Optional filter query parameters.

        Returns:
            List of organization representations.
        """
        return to_dto_list(
            KeycloakOrganizationDTO,
            self._call_keycloak(
                "get_organizations",
                lambda: self.admin_adapter.get_organizations(query=query),
            ),
        )

    def get_organization(self, organization_id: str) -> KeycloakOrganizationDTO:
        """Get representation of the organization by ID.

        Args:
            organization_id: Organization identifier.

        Returns:
            Organization representation.
        """
        return to_dto(
            KeycloakOrganizationDTO,
            self._call_keycloak(
                "get_organization",
                lambda: self.admin_adapter.get_organization(organization_id),
            ),
        )

    def create_organization(
        self,
        name: str,
        alias: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Create a new organization. Name and alias must be unique.

        Args:
            name: Organization name.
            alias: Organization alias.
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: Additional organization attributes (snake_case mapped to camelCase).

        Returns:
            Created organization ID, or None.
        """
        payload = _organization_payload(name, alias, kwargs, config)
        return self._call_keycloak(
            "create_organization",
            lambda: self.admin_adapter.create_organization(payload=payload),
        )

    def update_organization(
        self,
        organization_id: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakUpdateResultDTO:
        """Update an existing organization.

        Args:
            organization_id: Organization identifier.
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: Organization attributes to update (snake_case mapped to camelCase).

        Returns:
            Update response payload.
        """
        payload = _organization_update_payload(kwargs, config)
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._call_keycloak(
                "update_organization",
                lambda: self.admin_adapter.update_organization(organization_id=organization_id, payload=payload),
            ),
        )

    def delete_organization(self, organization_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "delete_organization",
                lambda: self.admin_adapter.delete_organization(organization_id=organization_id),
            ),
        )

    def get_organization_idps(self, organization_id: str) -> list[KeycloakIdentityProviderDTO]:
        """Get identity providers linked to an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            List of identity provider representations.
        """
        return to_dto_list(
            KeycloakIdentityProviderDTO,
            self._call_keycloak(
                "get_organization_idps",
                lambda: self.admin_adapter.get_organization_idps(organization_id=organization_id),
            ),
        )

    def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationDTO]:
        """Get organizations by user id.

        Args:
            user_id: User identifier.

        Returns:
            Organizations the user belongs to.
        """
        return to_dto_list(
            KeycloakOrganizationDTO,
            self._call_keycloak(
                "get_user_organizations",
                lambda: self.admin_adapter.get_user_organizations(user_id=user_id),
            ),
        )

    def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationMemberDTO]:
        """Get members by organization id, optionally filtered by query parameters.

        Args:
            organization_id: Organization identifier.
            query: Optional filter query parameters.

        Returns:
            Member representations.
        """
        return to_dto_list(
            KeycloakOrganizationMemberDTO,
            self._call_keycloak(
                "get_organization_members",
                lambda: self.admin_adapter.get_organization_members(organization_id=organization_id, query=query),
            ),
        )

    def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Member count.
        """
        return self._call_keycloak(
            "get_organization_members_count",
            lambda: self.admin_adapter.get_organization_members_count(organization_id=organization_id),
        )

    def organization_user_add(self, user_id: str, organization_id: str) -> KeycloakAssignResultDTO:
        """Add a user to an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Raw response bytes.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._call_keycloak(
                "organization_user_add",
                lambda: self.admin_adapter.organization_user_add(user_id=user_id, organization_id=organization_id),
            ),
        )

    def organization_user_remove(self, user_id: str, organization_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Removal response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._call_keycloak(
                "organization_user_remove",
                lambda: self.admin_adapter.organization_user_remove(user_id=user_id, organization_id=organization_id),
            ),
        )

    def organization_idp_add(self, organization_id: str, idp_alias: str) -> KeycloakAssignResultDTO:
        """Link an identity provider to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            self._admin_request(
                "organization_idp_add",
                "post",
                f"/organizations/{segment(organization_id)}/identity-providers",
                body=idp_alias,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def organization_idp_remove(self, organization_id: str, idp_alias: str) -> KeycloakDeleteResultDTO:
        """Unlink an identity provider from an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "organization_idp_remove",
                "delete",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organization_idp(self, organization_id: str, idp_alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider linked to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The identity provider.
        """
        return to_dto(
            KeycloakIdentityProviderDTO,
            self._admin_request(
                "get_organization_idp",
                "get",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_organization_idp(
        self,
        organization_id: str,
        idp_alias: str,
        link: KeycloakOrganizationIdentityProviderLinkRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update how an identity provider is linked to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.
            link: Link settings, such as auto membership.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_organization_idp",
                "put",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                body=to_request_payload(link),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organizations_count(self, query: dict[str, Any] | None = None) -> int:
        """Count the organizations matching the query.

        Args:
            query: Optional filters: ``search``, ``q``, ``exact`` and ``identityProvider``.

        Returns:
            The number of organizations.
        """
        return self._admin_request(
            "get_organizations_count",
            "get",
            "/organizations/count",
            params=query,
            expected=(HTTPStatus.OK,),
        )

    def get_organization_member(self, organization_id: str, member_id: str) -> KeycloakOrganizationMemberDTO:
        """Get one member of an organization.

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.

        Returns:
            The member.
        """
        return to_dto(
            KeycloakOrganizationMemberDTO,
            self._admin_request(
                "get_organization_member",
                "get",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def update_organization_member_membership_type(
        self,
        organization_id: str,
        member_id: str,
        membership_type: str,
    ) -> KeycloakUpdateResultDTO:
        """Set a member's membership type (``MANAGED`` or ``UNMANAGED``).

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.
            membership_type: ``MANAGED`` or ``UNMANAGED``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "update_organization_member_membership_type",
                "put",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}/membership-type",
                body=membership_type,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def get_organization_invitations(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationInvitationDTO]:
        """List the invitations of an organization.

        Args:
            organization_id: Organization identifier.
            query: Optional filters: ``search``, ``email``, ``status``, ``first`` and ``max``.

        Returns:
            The invitations.
        """
        return to_dto_list(
            KeycloakOrganizationInvitationDTO,
            self._admin_request(
                "get_organization_invitations",
                "get",
                f"/organizations/{segment(organization_id)}/invitations",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    def get_organization_invitation(
        self,
        organization_id: str,
        invitation_id: str,
    ) -> KeycloakOrganizationInvitationDTO:
        """Get one invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The invitation.
        """
        return to_dto(
            KeycloakOrganizationInvitationDTO,
            self._admin_request(
                "get_organization_invitation",
                "get",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    def delete_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakDeleteResultDTO:
        """Delete an invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            self._admin_request(
                "delete_organization_invitation",
                "delete",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    def resend_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakUpdateResultDTO:
        """Resend an invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            self._admin_request(
                "resend_organization_invitation",
                "post",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}/resend",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )


class AsyncKeycloakOrganizationsMixin(AsyncKeycloakMixinBase):
    """Async Keycloak mixin for organization operations."""

    async def get_organizations(self, query: dict[str, Any] | None = None) -> list[KeycloakOrganizationDTO]:
        """Fetch all organizations, optionally filtered by query parameters.

        Args:
            query: Optional filter query parameters.

        Returns:
            List of organization representations.
        """
        return to_dto_list(
            KeycloakOrganizationDTO,
            await self._async_call_keycloak(
                "get_organizations",
                lambda: self.admin_adapter.a_get_organizations(query=query),
            ),
        )

    async def get_organization(self, organization_id: str) -> KeycloakOrganizationDTO:
        """Get representation of the organization by ID.

        Args:
            organization_id: Organization identifier.

        Returns:
            Organization representation.
        """
        return to_dto(
            KeycloakOrganizationDTO,
            await self._async_call_keycloak(
                "get_organization",
                lambda: self.admin_adapter.a_get_organization(organization_id=organization_id),
            ),
        )

    async def create_organization(
        self,
        name: str,
        alias: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> str | None:
        """Create a new organization. Name and alias must be unique.

        Args:
            name: Organization name.
            alias: Organization alias.
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: Additional organization attributes (snake_case mapped to camelCase).

        Returns:
            Created organization ID, or None.
        """
        payload = _organization_payload(name, alias, kwargs, config)
        return await self._async_call_keycloak(
            "create_organization",
            lambda: self.admin_adapter.a_create_organization(payload=payload),
        )

    async def update_organization(
        self,
        organization_id: str,
        config: KeycloakOrganizationRequestDTO | None = None,
        **kwargs: Any,
    ) -> KeycloakUpdateResultDTO:
        """Update an existing organization.

        Args:
            organization_id: Organization identifier.
            config: Optional request DTO; keyword arguments override its values.
            **kwargs: Organization attributes to update (snake_case mapped to camelCase).

        Returns:
            Update response payload.
        """
        payload = _organization_update_payload(kwargs, config)
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_call_keycloak(
                "update_organization",
                lambda: self.admin_adapter.a_update_organization(organization_id=organization_id, payload=payload),
            ),
        )

    async def delete_organization(self, organization_id: str) -> KeycloakDeleteResultDTO:
        """Delete an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Deletion response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "delete_organization",
                lambda: self.admin_adapter.a_delete_organization(organization_id=organization_id),
            ),
        )

    async def get_organization_idps(self, organization_id: str) -> list[KeycloakIdentityProviderDTO]:
        """Get identity providers linked to an organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            List of identity provider representations.
        """
        return to_dto_list(
            KeycloakIdentityProviderDTO,
            await self._async_call_keycloak(
                "get_organization_idps",
                lambda: self.admin_adapter.a_get_organization_idps(organization_id=organization_id),
            ),
        )

    async def get_user_organizations(self, user_id: str) -> list[KeycloakOrganizationDTO]:
        """Get organizations by user id.

        Args:
            user_id: User identifier.

        Returns:
            Organizations the user belongs to.
        """
        return to_dto_list(
            KeycloakOrganizationDTO,
            await self._async_call_keycloak(
                "get_user_organizations",
                lambda: self.admin_adapter.a_get_user_organizations(user_id=user_id),
            ),
        )

    async def get_organization_members(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationMemberDTO]:
        """Get members by organization id, optionally filtered by query parameters.

        Args:
            organization_id: Organization identifier.
            query: Optional filter query parameters.

        Returns:
            Member representations.
        """
        return to_dto_list(
            KeycloakOrganizationMemberDTO,
            await self._async_call_keycloak(
                "get_organization_members",
                lambda: self.admin_adapter.a_get_organization_members(organization_id=organization_id, query=query),
            ),
        )

    async def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization.

        Args:
            organization_id: Organization identifier.

        Returns:
            Member count.
        """
        return await self._async_call_keycloak(
            "get_organization_members_count",
            lambda: self.admin_adapter.a_get_organization_members_count(organization_id=organization_id),
        )

    async def organization_user_add(self, user_id: str, organization_id: str) -> KeycloakAssignResultDTO:
        """Add a user to an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Raw response bytes.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_call_keycloak(
                "organization_user_add",
                lambda: self.admin_adapter.a_organization_user_add(user_id=user_id, organization_id=organization_id),
            ),
        )

    async def organization_user_remove(self, user_id: str, organization_id: str) -> KeycloakDeleteResultDTO:
        """Remove a user from an organization.

        Args:
            user_id: User identifier.
            organization_id: Organization identifier.

        Returns:
            Removal response payload.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_call_keycloak(
                "organization_user_remove",
                lambda: self.admin_adapter.a_organization_user_remove(user_id=user_id, organization_id=organization_id),
            ),
        )

    async def organization_idp_add(self, organization_id: str, idp_alias: str) -> KeycloakAssignResultDTO:
        """Link an identity provider to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The assign result.
        """
        return to_mutation_result(
            KeycloakAssignResultDTO,
            await self._async_admin_request(
                "organization_idp_add",
                "post",
                f"/organizations/{segment(organization_id)}/identity-providers",
                body=idp_alias,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def organization_idp_remove(self, organization_id: str, idp_alias: str) -> KeycloakDeleteResultDTO:
        """Unlink an identity provider from an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "organization_idp_remove",
                "delete",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organization_idp(self, organization_id: str, idp_alias: str) -> KeycloakIdentityProviderDTO:
        """Get an identity provider linked to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.

        Returns:
            The identity provider.
        """
        return to_dto(
            KeycloakIdentityProviderDTO,
            await self._async_admin_request(
                "get_organization_idp",
                "get",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_organization_idp(
        self,
        organization_id: str,
        idp_alias: str,
        link: KeycloakOrganizationIdentityProviderLinkRequestDTO | dict[str, Any],
    ) -> KeycloakUpdateResultDTO:
        """Update how an identity provider is linked to an organization.

        Args:
            organization_id: Organization identifier.
            idp_alias: Alias of the identity provider.
            link: Link settings, such as auto membership.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_organization_idp",
                "put",
                f"/organizations/{segment(organization_id)}/identity-providers/{segment(idp_alias)}",
                body=to_request_payload(link),
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organizations_count(self, query: dict[str, Any] | None = None) -> int:
        """Count the organizations matching the query.

        Args:
            query: Optional filters: ``search``, ``q``, ``exact`` and ``identityProvider``.

        Returns:
            The number of organizations.
        """
        return await self._async_admin_request(
            "get_organizations_count",
            "get",
            "/organizations/count",
            params=query,
            expected=(HTTPStatus.OK,),
        )

    async def get_organization_member(self, organization_id: str, member_id: str) -> KeycloakOrganizationMemberDTO:
        """Get one member of an organization.

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.

        Returns:
            The member.
        """
        return to_dto(
            KeycloakOrganizationMemberDTO,
            await self._async_admin_request(
                "get_organization_member",
                "get",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def update_organization_member_membership_type(
        self,
        organization_id: str,
        member_id: str,
        membership_type: str,
    ) -> KeycloakUpdateResultDTO:
        """Set a member's membership type (``MANAGED`` or ``UNMANAGED``).

        Args:
            organization_id: Organization identifier.
            member_id: User identifier.
            membership_type: ``MANAGED`` or ``UNMANAGED``.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "update_organization_member_membership_type",
                "put",
                f"/organizations/{segment(organization_id)}/members/{segment(member_id)}/membership-type",
                body=membership_type,
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def get_organization_invitations(
        self,
        organization_id: str,
        query: dict[str, Any] | None = None,
    ) -> list[KeycloakOrganizationInvitationDTO]:
        """List the invitations of an organization.

        Args:
            organization_id: Organization identifier.
            query: Optional filters: ``search``, ``email``, ``status``, ``first`` and ``max``.

        Returns:
            The invitations.
        """
        return to_dto_list(
            KeycloakOrganizationInvitationDTO,
            await self._async_admin_request(
                "get_organization_invitations",
                "get",
                f"/organizations/{segment(organization_id)}/invitations",
                params=query,
                expected=(HTTPStatus.OK,),
            ),
        )

    async def get_organization_invitation(
        self,
        organization_id: str,
        invitation_id: str,
    ) -> KeycloakOrganizationInvitationDTO:
        """Get one invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The invitation.
        """
        return to_dto(
            KeycloakOrganizationInvitationDTO,
            await self._async_admin_request(
                "get_organization_invitation",
                "get",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}",
                expected=(HTTPStatus.OK,),
            ),
        )

    async def delete_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakDeleteResultDTO:
        """Delete an invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The delete result.
        """
        return to_mutation_result(
            KeycloakDeleteResultDTO,
            await self._async_admin_request(
                "delete_organization_invitation",
                "delete",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )

    async def resend_organization_invitation(self, organization_id: str, invitation_id: str) -> KeycloakUpdateResultDTO:
        """Resend an invitation of an organization.

        Args:
            organization_id: Organization identifier.
            invitation_id: Invitation identifier.

        Returns:
            The update result.
        """
        return to_mutation_result(
            KeycloakUpdateResultDTO,
            await self._async_admin_request(
                "resend_organization_invitation",
                "post",
                f"/organizations/{segment(organization_id)}/invitations/{segment(invitation_id)}/resend",
                expected=(HTTPStatus.NO_CONTENT,),
            ),
        )
