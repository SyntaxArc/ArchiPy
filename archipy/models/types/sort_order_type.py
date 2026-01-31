from enum import Enum


class SortOrderType(Enum):
    """Enumeration of sorting order types.

    This enum defines the types of sorting orders that can be applied to data,
    such as ascending or descending.

    Attributes:
        ASCENDING (str): Represents sorting in ascending order.
        DESCENDING (str): Represents sorting in descending order.
    """

    ASCENDING = "ASCENDING"
    DESCENDING = "DESCENDING"
