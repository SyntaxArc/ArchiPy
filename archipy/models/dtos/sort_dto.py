from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, Field

from archipy.models.types.sort_order_type import SortOrderType

# Generic types
T = TypeVar("T", bound=Enum)


class SortDTO[T](BaseModel):
    """Data Transfer Object for sorting parameters.

    This DTO encapsulates sorting information for database queries and API responses,
    providing a standard way to specify how results should be ordered.

    Attributes:
        column (T | str): The name or enum value of the column to sort by
        order (str): The sort direction - "ASC" for ascending, "DESC" for descending

    Examples:
        >>> from archipy.models.dtos.sort_dto import SortDTO
        >>> from archipy.models.types.sort_order_type import SortOrderType
        >>>
        >>> # Sort by name in ascending order
        >>> sort = SortDTO(column="name", order=SortOrderType.ASCENDING)
        >>>
        >>> # Sort by creation date in descending order (newest first)
        >>> sort = SortDTO(column="created_at", order="DESCENDING")
        >>>
        >>> # Using with a database query
        >>> def get_sorted_users(sort: SortDTO = SortDTO.default()):
        ...     query = select(User)
        ...     if sort.order == SortOrderType.ASCENDING:
        ...         query = query.order_by(getattr(User, sort.column).asc())
        ...     else:
        ...         query = query.order_by(getattr(User, sort.column).desc())
        ...     return db.execute(query).scalars().all()
        >>>
        >>> # Using with enum column types
        >>> from enum import Enum
        >>> class UserColumns(Enum):
        ...     ID = "id"
        ...     NAME = "name"
        ...     EMAIL = "email"
        ...     CREATED_AT = "created_at"
        >>>
        >>> # Create a sort configuration with enum
        >>> sort = SortDTO[UserColumns](column=UserColumns.NAME, order=SortOrderType.ASCENDING)
    """

    column: T | str = Field(default="created_at", description="Column name or enum to sort by")
    order: SortOrderType = Field(default=SortOrderType.DESCENDING, description="Sort order (ASCENDING or DESCENDING)")

    @classmethod
    def default(cls) -> SortDTO:
        """Create a default sort configuration.

        Returns a sort configuration that orders by created_at in descending order
        (newest first), which is a common default sorting behavior.

        Returns:
            SortDTO: A default sort configuration

        Examples:
            >>> default_sort = SortDTO.default()
            >>> print(f"Sort by {default_sort.column} {default_sort.order}")
            Sort by created_at DESCENDING
        """
        return cls(column="created_at", order=SortOrderType.DESCENDING)
