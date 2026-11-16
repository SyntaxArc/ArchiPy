"""Immutable resource ownership identity."""

from uuid import UUID

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types.owner_type import OwnerType


class Owner(BaseDTO):
    """Resource owner; both UUID and type identify the ownership boundary."""

    uuid: UUID
    type: OwnerType
