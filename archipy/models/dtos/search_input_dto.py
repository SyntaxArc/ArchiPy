"""DTOs for generic search inputs."""

from enum import Enum
from typing import TypeVar

from pydantic import BaseModel

from archipy.models.dtos.pagination_dto import PaginationDTO
from archipy.models.dtos.sort_dto import SortDTO

# Generic types
T = TypeVar("T", bound=Enum)


class SearchInputDTO[T](BaseModel):
    """Data Transfer Object for search inputs with pagination and sorting.

    This DTO encapsulates search parameters for database queries and API responses,
    providing a standard way to handle pagination and sorting.

    Type Parameters:
        T: The type for sort column (usually an Enum with column names).
    """

    pagination: PaginationDTO | None = None
    sort_info: SortDTO[T] | None = None
