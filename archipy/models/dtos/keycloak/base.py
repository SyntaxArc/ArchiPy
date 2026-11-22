"""Base classes for Keycloak representation DTOs."""

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class KeycloakBaseDTO(BaseModel):
    """Standalone base for Keycloak admin API representations.

    Not derived from ``BaseDTO``: that base silently drops unknown fields (``extra="ignore"``), which would hide
    typos in requests and discard fields added by newer Keycloak versions. Subclass
    :class:`KeycloakRequestDTO` or :class:`KeycloakResponseDTO` instead of this class directly.

    Fields use snake_case in Python and camelCase on the wire. Every Keycloak representation field is optional
    in the REST API spec, so DTO fields default to ``None``.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        validate_default=True,
        from_attributes=True,
        frozen=True,
        str_strip_whitespace=True,
    )

    def to_payload(self) -> dict[str, Any]:
        """Serialize to the camelCase JSON payload python-keycloak expects, omitting unset fields."""
        return self.model_dump(by_alias=True, exclude_none=True, mode="json")


class KeycloakRequestDTO(KeycloakBaseDTO):
    """Base for payloads sent to Keycloak. Unknown fields are rejected, as the server does."""

    model_config = ConfigDict(extra="forbid")


class KeycloakResponseDTO(KeycloakBaseDTO):
    """Base for representations returned by Keycloak.

    Unknown fields (added by newer Keycloak versions) are kept in ``model_extra`` instead of failing validation.
    """

    model_config = ConfigDict(extra="allow")
