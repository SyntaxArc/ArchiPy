from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import ClassVar, Protocol, Self, TypeVar

from pydantic import field_validator, model_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import InvalidArgumentError, OutOfRangeError
from archipy.models.types.time_interval_unit_type import TimeIntervalUnitType


# Generic types
class Comparable(Protocol):
    """Protocol for types that support comparison operators."""

    def __gt__(self, other: object) -> bool:
        """Greater than comparison operator."""
        ...


R = TypeVar("R", bound=Comparable)  # Type for range values (Decimal, int, date, etc.)


class BaseRangeDTO[R](BaseDTO):
    """Base Data Transfer Object for range queries.

    Encapsulates a range of values with from_ and to fields.
    Provides validation to ensure range integrity.
    """

    from_: R | None = None
    to: R | None = None

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        """Validate that from_ is less than or equal to to when both are provided.

        Returns:
            Self: The validated model instance.

        Raises:
            OutOfRangeError: If from_ is greater than to.
        """
        if self.from_ is not None and self.to is not None:
            # Use comparison with proper type handling
            # The protocol ensures both values support comparison
            try:
                if self.from_ > self.to:  # type: ignore[operator]
                    raise OutOfRangeError(field_name="from_")
            except TypeError:
                # If comparison fails, skip validation (shouldn't happen with proper types)
                pass
        return self


class DecimalRangeDTO(BaseRangeDTO[Decimal]):
    """Data Transfer Object for decimal range queries."""

    from_: Decimal | None = None
    to: Decimal | None = None

    @field_validator("from_", "to", mode="before")
    @classmethod
    def convert_to_decimal(cls, value: Decimal | str | None) -> Decimal | None:
        """Convert input values to Decimal type.

        Args:
            value: The value to convert (None, string, or Decimal).

        Returns:
            Decimal | None: The converted Decimal value or None.

        Raises:
            InvalidArgumentError: If the value cannot be converted to Decimal.
        """
        if value is None:
            return None
        try:
            return Decimal(value)
        except (TypeError, ValueError) as e:
            raise InvalidArgumentError(argument_name="value") from e


class IntegerRangeDTO(BaseRangeDTO[int]):
    """Data Transfer Object for integer range queries."""

    from_: int | None = None
    to: int | None = None


class DateRangeDTO(BaseRangeDTO[date]):
    """Data Transfer Object for date range queries."""

    from_: date | None = None
    to: date | None = None


class DatetimeRangeDTO(BaseRangeDTO[datetime]):
    """Data Transfer Object for datetime range queries."""

    from_: datetime | None = None
    to: datetime | None = None


class DatetimeIntervalRangeDTO(BaseRangeDTO[datetime]):
    """Data Transfer Object for datetime range queries with interval.

    Rejects requests if the number of intervals exceeds MAX_ITEMS or if interval-specific
    range size or 'to' age constraints are violated.
    """

    from_: datetime
    to: datetime
    interval: TimeIntervalUnitType

    # Maximum number of intervals allowed
    MAX_ITEMS: ClassVar[int] = 100

    # Range size limits for each interval
    RANGE_SIZE_LIMITS: ClassVar[dict[TimeIntervalUnitType, timedelta]] = {
        TimeIntervalUnitType.SECONDS: timedelta(days=2),
        TimeIntervalUnitType.MINUTES: timedelta(days=7),
        TimeIntervalUnitType.HOURS: timedelta(days=30),
        TimeIntervalUnitType.DAYS: timedelta(days=365),
        TimeIntervalUnitType.WEEKS: timedelta(days=365 * 2),
        TimeIntervalUnitType.MONTHS: timedelta(days=365 * 5),  # No limit for MONTHS, set high
        TimeIntervalUnitType.YEAR: timedelta(days=365 * 10),  # No limit for YEAR, set high
    }

    # 'to' age limits for each interval
    TO_AGE_LIMITS: ClassVar[dict[TimeIntervalUnitType, timedelta]] = {
        TimeIntervalUnitType.SECONDS: timedelta(days=2),
        TimeIntervalUnitType.MINUTES: timedelta(days=7),
        TimeIntervalUnitType.HOURS: timedelta(days=30),
        TimeIntervalUnitType.DAYS: timedelta(days=365 * 5),
        TimeIntervalUnitType.WEEKS: timedelta(days=365 * 10),
        TimeIntervalUnitType.MONTHS: timedelta(days=365 * 20),  # No limit for MONTHS, set high
        TimeIntervalUnitType.YEAR: timedelta(days=365 * 50),  # No limit for YEAR, set high
    }

    # Mapping of intervals to timedelta for step size
    INTERVAL_TO_TIMEDELTA: ClassVar[dict[TimeIntervalUnitType, timedelta]] = {
        TimeIntervalUnitType.SECONDS: timedelta(seconds=1),
        TimeIntervalUnitType.MINUTES: timedelta(minutes=1),
        TimeIntervalUnitType.HOURS: timedelta(hours=1),
        TimeIntervalUnitType.DAYS: timedelta(days=1),
        TimeIntervalUnitType.WEEKS: timedelta(weeks=1),
        TimeIntervalUnitType.MONTHS: timedelta(days=30),  # Approximate
        TimeIntervalUnitType.YEAR: timedelta(days=365),  # Approximate
    }

    @model_validator(mode="after")
    def validate_interval_constraints(self) -> Self:
        """Validate interval based on range size, 'to' field age, and max intervals.

        - Each interval has specific range size and 'to' age limits.
        - Rejects if the number of intervals exceeds MAX_ITEMS.

        Returns:
            Self: The validated model instance.

        Raises:
            OutOfRangeError: If interval constraints are violated or number of intervals > MAX_ITEMS.
        """
        if self.from_ is not None and self.to is not None:
            # Validate range size limit for the selected interval
            range_size = self.to - self.from_
            max_range_size = self.RANGE_SIZE_LIMITS.get(self.interval)
            if max_range_size and range_size > max_range_size:
                raise OutOfRangeError(field_name="range_size")

            # Validate 'to' age limit
            current_time = datetime.now()
            max_to_age = self.TO_AGE_LIMITS.get(self.interval)
            if max_to_age:
                age_threshold = current_time - max_to_age
                if self.to < age_threshold:
                    raise OutOfRangeError(field_name="to")

            # Calculate number of intervals
            step = self.INTERVAL_TO_TIMEDELTA[self.interval]
            range_duration = self.to - self.from_
            num_intervals = int(range_duration.total_seconds() / step.total_seconds()) + 1

            # Reject if number of intervals exceeds MAX_ITEMS
            if num_intervals > self.MAX_ITEMS:
                raise OutOfRangeError(field_name="interval_count")

        return self
