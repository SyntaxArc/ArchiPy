"""Keycloak user profile representation DTOs (generated from the Keycloak admin OpenAPI spec)."""

from pydantic import JsonValue

from archipy.models.dtos.keycloak.base import KeycloakRequestDTO, KeycloakResponseDTO


class KeycloakUserProfileConfigDTO(KeycloakResponseDTO):
    """Keycloak ``UPConfig`` as returned by the admin API."""

    attributes: list[KeycloakUserProfileAttributeDTO] | None = None
    groups: list[KeycloakUserProfileGroupDTO] | None = None
    unmanaged_attribute_policy: str | None = None


class KeycloakUserProfileConfigRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UPConfig`` payload sent to the admin API."""

    attributes: list[KeycloakUserProfileAttributeRequestDTO] | None = None
    groups: list[KeycloakUserProfileGroupRequestDTO] | None = None
    unmanaged_attribute_policy: str | None = None


class KeycloakUserProfileAttributeDTO(KeycloakResponseDTO):
    """Keycloak ``UPAttribute`` as returned by the admin API."""

    name: str | None = None
    display_name: str | None = None
    validations: dict[str, dict[str, JsonValue]] | None = None
    annotations: dict[str, JsonValue] | None = None
    required: KeycloakUserProfileAttributeRequiredDTO | None = None
    permissions: KeycloakUserProfileAttributePermissionsDTO | None = None
    selector: dict[str, JsonValue] | None = None
    group: str | None = None
    multivalued: bool | None = None
    default_value: str | None = None


class KeycloakUserProfileAttributeRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UPAttribute`` payload sent to the admin API."""

    name: str | None = None
    display_name: str | None = None
    validations: dict[str, dict[str, JsonValue]] | None = None
    annotations: dict[str, JsonValue] | None = None
    required: KeycloakUserProfileAttributeRequiredRequestDTO | None = None
    permissions: KeycloakUserProfileAttributePermissionsRequestDTO | None = None
    selector: dict[str, JsonValue] | None = None
    group: str | None = None
    multivalued: bool | None = None
    default_value: str | None = None


class KeycloakUserProfileGroupDTO(KeycloakResponseDTO):
    """Keycloak ``UPGroup`` as returned by the admin API."""

    name: str | None = None
    display_header: str | None = None
    display_description: str | None = None
    annotations: dict[str, JsonValue] | None = None


class KeycloakUserProfileGroupRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UPGroup`` payload sent to the admin API."""

    name: str | None = None
    display_header: str | None = None
    display_description: str | None = None
    annotations: dict[str, JsonValue] | None = None


class KeycloakUserProfileAttributeRequiredDTO(KeycloakResponseDTO):
    """Keycloak ``UPAttributeRequired`` as returned by the admin API."""

    roles: list[str] | None = None
    scopes: list[str] | None = None


class KeycloakUserProfileAttributeRequiredRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UPAttributeRequired`` payload sent to the admin API."""

    roles: list[str] | None = None
    scopes: list[str] | None = None


class KeycloakUserProfileAttributePermissionsDTO(KeycloakResponseDTO):
    """Keycloak ``UPAttributePermissions`` as returned by the admin API."""

    view: list[str] | None = None
    edit: list[str] | None = None


class KeycloakUserProfileAttributePermissionsRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UPAttributePermissions`` payload sent to the admin API."""

    view: list[str] | None = None
    edit: list[str] | None = None


class KeycloakUserProfileMetadataDTO(KeycloakResponseDTO):
    """Keycloak ``UserProfileMetadata`` as returned by the admin API."""

    attributes: list[dict[str, JsonValue]] | None = None
    groups: list[dict[str, JsonValue]] | None = None


class KeycloakUserProfileMetadataRequestDTO(KeycloakRequestDTO):
    """Keycloak ``UserProfileMetadata`` payload sent to the admin API."""

    attributes: list[dict[str, JsonValue]] | None = None
    groups: list[dict[str, JsonValue]] | None = None
