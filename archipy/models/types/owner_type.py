"""Resource owner types."""

from enum import StrEnum


class OwnerType(StrEnum):
    """Kind of subject that owns a resource."""

    USER = "USER"
    ORGANIZATION = "ORGANIZATION"
