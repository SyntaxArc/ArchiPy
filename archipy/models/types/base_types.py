from enum import Enum
from typing import Self


class BaseType(Enum):
    """Base class for creating enumerated types with custom values.

    This class extends the `Enum` class to allow custom values for enum members.
    """

    def __new__(cls, *args: object, **_: object) -> Self:
        """Create a new instance of the enum member.

        Args:
            cls: The enum class.
            *args: Arguments passed to the enum member.
            **_: Unused keyword arguments.

        Returns:
            BaseType: A new instance of the enum member with the custom value.
        """
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj


class FilterOperationType(Enum):
    """Enumeration of filter operations for querying or filtering data.

    This enum defines the types of operations that can be used in filtering,
    such as equality checks, comparisons, and string matching.

    Attributes:
        EQUAL (str): Represents an equality check.
        NOT_EQUAL (str): Represents a non-equality check.
        LESS_THAN (str): Represents a less-than comparison.
        LESS_THAN_OR_EQUAL (str): Represents a less-than-or-equal comparison.
        GREATER_THAN (str): Represents a greater-than comparison.
        GREATER_THAN_OR_EQUAL (str): Represents a greater-than-or-equal comparison.
        IN_LIST (str): Represents a check for membership in a list.
        NOT_IN_LIST (str): Represents a check for non-membership in a list.
        LIKE (str): Represents a case-sensitive string pattern match.
        ILIKE (str): Represents a case-insensitive string pattern match.
        STARTS_WITH (str): Represents a check if a string starts with a given prefix.
        ENDS_WITH (str): Represents a check if a string ends with a given suffix.
        CONTAINS (str): Represents a check if a string contains a given substring.
        IS_NULL (str): Represents a check if a value is null.
        IS_NOT_NULL (str): Represents a check if a value is not null.
    """

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    LIKE = "like"
    ILIKE = "ilike"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    CONTAINS = "contains"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
