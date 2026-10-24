"""Base classes for Keycloak representation DTOs."""

import warnings
from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

_REMOVAL_VERSION = "6.0.0"


class DictCompatMixin(BaseModel):
    """Read-only dict-style access for DTOs that replaced plain ``dict`` return values.

    Every access emits a ``DeprecationWarning``. Keys are the camelCase Keycloak field names and
    fields that are unset (``None``) are absent, matching the dicts these DTOs replaced.
    """

    def _compat_dict(self, access: str) -> dict[str, Any]:
        warnings.warn(
            f"dict-style access ({access}) on {type(self).__name__} is deprecated and will be removed in "
            f"{_REMOVAL_VERSION}; use attribute access instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        return self.model_dump(by_alias=True, exclude_none=True)

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """Return the value stored under ``key``."""
        return self._compat_dict("[]")[key]

    def __contains__(self, key: object) -> bool:
        """Return whether ``key`` is a set field."""
        return key in self._compat_dict("in")

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        """Return the value stored under ``key`` or ``default``."""
        return self._compat_dict("get()").get(key, default)

    def keys(self) -> Any:  # noqa: ANN401
        """Return the set field names."""
        return self._compat_dict("keys()").keys()

    def values(self) -> Any:  # noqa: ANN401
        """Return the set field values."""
        return self._compat_dict("values()").values()

    def items(self) -> Any:  # noqa: ANN401
        """Return the set ``(name, value)`` pairs."""
        return self._compat_dict("items()").items()


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
        populate_by_name=True,
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


class KeycloakResponseDTO(DictCompatMixin, KeycloakBaseDTO):
    """Base for representations returned by Keycloak.

    Unknown fields (added by newer Keycloak versions) are kept in ``model_extra`` instead of failing validation.
    """

    model_config = ConfigDict(extra="allow")
