import time
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import jdatetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from archipy.configs.base_config import BaseConfig
from archipy.helpers.decorators.cache import ttl_cache_decorator
from archipy.models.errors import UnknownError

_HOLIDAY_CACHE_MAXSIZE = 2048


def _iran_holiday_historical_cache_ttl_seconds() -> int:
    """Return DATETIME.HISTORICAL_CACHE_TTL from the global config (evaluated at decorate time)."""
    return BaseConfig.global_config().DATETIME.HISTORICAL_CACHE_TTL


def _iran_holiday_standard_cache_ttl_seconds() -> int:
    """Return DATETIME.CACHE_TTL from the global config (evaluated at decorate time)."""
    return BaseConfig.global_config().DATETIME.CACHE_TTL


class DatetimeUtils:
    """A utility class for handling date and time operations, including conversions, caching, and API integrations.

    This class provides methods for working with both Gregorian and Jalali (Persian) calendars, as well as
    utility functions for timezone-aware datetime objects, date ranges, and string formatting.
    """

    @staticmethod
    def convert_to_jalali(target_date: date) -> jdatetime.date:
        """Converts a Gregorian date to a Jalali (Persian) date.

        Args:
            target_date (date): The Gregorian date to convert.

        Returns:
            jdatetime.date: The corresponding Jalali date.
        """
        return jdatetime.date.fromgregorian(date=target_date)

    @classmethod
    def is_holiday_in_iran(cls, target_date: date) -> bool:
        """Determines if the target date is a holiday in Iran.

        This method leverages caching and an external API to check if the given date is a holiday.

        Args:
            target_date (date): The date to check for holiday status.

        Returns:
            bool: True if the date is a holiday, False otherwise.
        """
        date_str = target_date.strftime("%Y-%m-%d")
        utc_today = cls.get_datetime_utc_now().date()
        is_historical = target_date <= utc_today
        if is_historical:
            return cls._fetch_holiday_in_iran_historical(date_str)
        return cls._fetch_holiday_in_iran_standard(date_str)

    @staticmethod
    @ttl_cache_decorator(
        ttl_seconds=_iran_holiday_historical_cache_ttl_seconds,
        maxsize=_HOLIDAY_CACHE_MAXSIZE,
    )
    def _fetch_holiday_in_iran_historical(date_str: str) -> bool:
        """Resolve holiday flag for a date on or before UTC today; cached with historical TTL."""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        jalali_date = DatetimeUtils.convert_to_jalali(target_date)
        try:
            response = DatetimeUtils._call_holiday_api(jalali_date)
        except requests.RequestException as exception:
            raise UnknownError from exception
        return DatetimeUtils._parse_holiday_response(response, jalali_date)

    @staticmethod
    @ttl_cache_decorator(
        ttl_seconds=_iran_holiday_standard_cache_ttl_seconds,
        maxsize=_HOLIDAY_CACHE_MAXSIZE,
    )
    def _fetch_holiday_in_iran_standard(date_str: str) -> bool:
        """Resolve holiday flag for a strictly future calendar date; cached with standard TTL."""
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        jalali_date = DatetimeUtils.convert_to_jalali(target_date)
        try:
            response = DatetimeUtils._call_holiday_api(jalali_date)
        except requests.RequestException as exception:
            raise UnknownError from exception
        return DatetimeUtils._parse_holiday_response(response, jalali_date)

    @staticmethod
    def _call_holiday_api(jalali_date: jdatetime.date) -> dict[str, Any]:
        """Calls the Time.ir API to fetch holiday data for the given Jalali date.

        Args:
            jalali_date (jdatetime.date): The Jalali date to fetch data for.

        Returns:
            Dict[str, Any]: The JSON response from the API.

        Raises:
            requests.RequestException: If the API request fails.
        """
        config: Any = BaseConfig.global_config()
        retry_strategy = Retry(
            total=config.DATETIME.MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)

        url = DatetimeUtils._build_api_url(jalali_date)
        headers = {"x-api-key": config.DATETIME.TIME_IR_API_KEY}
        response = session.get(url, headers=headers, timeout=config.DATETIME.REQUEST_TIMEOUT)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    @staticmethod
    def _build_api_url(jalali_date: jdatetime.date) -> str:
        """Builds the API URL with Jalali date parameters.

        Args:
            jalali_date (jdatetime.date): The Jalali date to include in the URL.

        Returns:
            str: The constructed API URL.
        """
        config: Any = BaseConfig.global_config()
        base_url = config.DATETIME.TIME_IR_API_ENDPOINT
        return f"{base_url}?year={jalali_date.year}&month={jalali_date.month}&day={jalali_date.day}"

    @staticmethod
    def _parse_holiday_response(response_data: dict[str, Any], jalali_date: jdatetime.date) -> bool:
        """Parses the API response to extract and return the holiday status.

        Args:
            response_data (Dict[str, Any]): The JSON response from the API.
            jalali_date (jdatetime.date): The Jalali date to check.

        Returns:
            bool: True if the date is a holiday, False otherwise.
        """
        event_list = response_data.get("data", {}).get("event_list", [])
        for event_info in event_list:
            if (
                event_info.get("jalali_year") == jalali_date.year
                and event_info.get("jalali_month") == jalali_date.month
                and event_info.get("jalali_day") == jalali_date.day
            ):
                is_holiday = event_info.get("is_holiday", False)
                return bool(is_holiday)
        return False

    @classmethod
    def ensure_timezone_aware(cls, dt: datetime) -> datetime:
        """Ensures a datetime object is timezone-aware, converting it to UTC if necessary.

        Args:
            dt (datetime): The datetime object to make timezone-aware.

        Returns:
            datetime: The timezone-aware datetime object.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    @classmethod
    def daterange(cls, start_date: datetime, end_date: datetime) -> Generator[date]:
        """Generates a range of dates from start_date to end_date, exclusive of end_date.

        Args:
            start_date (datetime): The start date of the range.
            end_date (datetime): The end date of the range.

        Yields:
            date: Each date in the range.
        """
        for n in range((end_date - start_date).days):
            yield (start_date + timedelta(n)).date()

    @classmethod
    def get_string_datetime_from_datetime(cls, dt: datetime, format_: str | None = None) -> str:
        """Converts a datetime object to a formatted string. Default format is ISO 8601.

        Args:
            dt (datetime): The datetime object to format.
            format_ (str | None): The format string. If None, uses ISO 8601.

        Returns:
            str: The formatted datetime string.
        """
        format_ = format_ or "%Y-%m-%dT%H:%M:%S.%f"
        return dt.strftime(format_)

    @classmethod
    def standardize_string_datetime(cls, date_string: str) -> str:
        """Standardizes a datetime string to the default format.

        Args:
            date_string (str): The datetime string to standardize.

        Returns:
            str: The standardized datetime string.
        """
        datetime_ = cls.get_datetime_from_string_datetime(date_string)
        return cls.get_string_datetime_from_datetime(datetime_)

    @classmethod
    def get_datetime_from_string_datetime(cls, date_string: str, format_: str | None = None) -> datetime:
        """Parses a string to a datetime object using the given format, or ISO 8601 by default.

        Args:
            date_string (str): The datetime string to parse.
            format_ (str | None): The format string. If None, uses ISO 8601.

        Returns:
            datetime: The parsed datetime object with UTC timezone.
        """
        # Parse using a single expression and immediately make timezone-aware for both cases
        dt = (
            datetime.fromisoformat(date_string)
            if format_ is None
            else datetime.strptime(date_string, format_).replace(tzinfo=UTC)
        )

        # Handle the fromisoformat case which might already have timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return dt

    @classmethod
    def get_string_datetime_now(cls) -> str:
        """Gets the current datetime as a formatted string. Default format is ISO 8601.

        Returns:
            str: The formatted datetime string.
        """
        return cls.get_string_datetime_from_datetime(cls.get_datetime_now())

    @classmethod
    def get_datetime_now(cls) -> datetime:
        """Gets the current local datetime.

        Returns:
            datetime: The current local datetime.
        """
        return datetime.now()

    @classmethod
    def get_datetime_utc_now(cls) -> datetime:
        """Gets the current UTC datetime.

        Returns:
            datetime: The current UTC datetime.
        """
        return datetime.now(UTC)

    @classmethod
    def get_epoch_time_now(cls) -> int:
        """Gets the current time in seconds since the epoch.

        Returns:
            int: The current epoch time.
        """
        return int(time.time())

    @classmethod
    def get_datetime_before_given_datetime_or_now(
        cls,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        datetime_given: datetime | None = None,
    ) -> datetime:
        """Subtracts time from a given datetime or the current datetime if not specified.

        Args:
            weeks (int): The number of weeks to subtract.
            days (int): The number of days to subtract.
            hours (int): The number of hours to subtract.
            minutes (int): The number of minutes to subtract.
            seconds (int): The number of seconds to subtract.
            datetime_given (datetime | None): The datetime to subtract from. If None, uses the current datetime.

        Returns:
            datetime: The resulting datetime after subtraction.
        """
        datetime_given = datetime_given or cls.get_datetime_now()
        return datetime_given - timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)

    @classmethod
    def get_datetime_after_given_datetime_or_now(
        cls,
        weeks: int = 0,
        days: int = 0,
        hours: int = 0,
        minutes: int = 0,
        seconds: int = 0,
        datetime_given: datetime | None = None,
    ) -> datetime:
        """Adds time to a given datetime or the current datetime if not specified.

        Args:
            weeks (int): The number of weeks to add.
            days (int): The number of days to add.
            hours (int): The number of hours to add.
            minutes (int): The number of minutes to add.
            seconds (int): The number of seconds to add.
            datetime_given (datetime | None): The datetime to add to. If None, uses the current datetime.

        Returns:
            datetime: The resulting datetime after addition.
        """
        datetime_given = datetime_given or cls.get_datetime_now()
        return datetime_given + timedelta(weeks=weeks, days=days, hours=hours, minutes=minutes, seconds=seconds)
