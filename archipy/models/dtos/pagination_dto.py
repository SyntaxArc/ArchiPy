"""DTOs for pagination inputs and outputs."""

from enum import Enum
from typing import ClassVar, Self, TypeVar

from pydantic import Field, model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import OutOfRangeError

# Generic types
T = TypeVar("T", bound=Enum)


class PaginationDTO(BaseDTO):
    """Data Transfer Object for pagination parameters.

    This DTO encapsulates pagination information for database queries and API responses,
    providing a standard way to specify which subset of results to retrieve.

    Attributes:
        page (int): The current page number (1-based indexing)
        page_size (int): Number of items per page
        offset (int): Calculated offset for database queries based on page and page_size

    Examples:
        >>> from archipy.models.dtos.pagination_dto import PaginationDTO
        >>>
        >>> # Default pagination (page 1, 10 items per page)
        >>> pagination = PaginationDTO()
        >>>
        >>> # Custom pagination
        >>> pagination = PaginationDTO(page=2, page_size=25)
        >>> print(pagination.offset)  # Access offset as a property
        25
        >>>
        >>> # Using with a database query
        >>> def get_users(pagination: PaginationDTO):
        ...     query = select(User).offset(pagination.offset).limit(pagination.page_size)
        ...     return db.execute(query).scalars().all()
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=10, ge=1, le=100, description="Number of items per page")

    MAX_ITEMS: ClassVar = 10000

    @model_validator(mode="after")
    def validate_pagination(self) -> Self:
        """Validate pagination limits to prevent excessive resource usage.

        Ensures that the requested number of items (page * page_size) doesn't exceed
        the maximum allowed limit.

        Returns:
            The validated model instance if valid.

        Raises:
            OutOfRangeError: If the total requested items exceeds MAX_ITEMS.
        """
        total_items = self.page * self.page_size
        if total_items > self.MAX_ITEMS:
            raise OutOfRangeError(field_name="pagination")
        return self

    @property
    def offset(self) -> int:
        """Calculate the offset for database queries.

        This property calculates how many records to skip based on the
        current page and page size.

        Returns:
            int: The number of records to skip

        Examples:
            >>> pagination = PaginationDTO(page=3, page_size=20)
            >>> pagination.offset
            40  # Skip the first 40 records (2 pages of 20 items)
        """
        return (self.page - 1) * self.page_size
