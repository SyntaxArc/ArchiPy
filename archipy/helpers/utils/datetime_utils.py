import time
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from typing import Any, ClassVar

import jdatetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from archipy.configs.base_config import BaseConfig
from archipy.models.errors import UnknownError


class DatetimeUtils:
    """A utility class for handling date and time operations, including conversions, caching, and API integrations.

    This class provides methods for working with both Gregorian and Jalali (Persian) calendars, as well as
    utility functions for timezone-aware datetime objects, date ranges, and string formatting.
    """

    """A class-level cache for storing holiday statuses to avoid redundant API calls."""
    _holiday_cache: ClassVar[dict[str, tuple[bool, datetime]]] = {}

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
        # Convert to Jalali date first
        jalali_date = cls.convert_to_jalali(target_date)
        date_str = target_date.strftime("%Y-%m-%d")
        current_time = cls.get_datetime_utc_now()

        # Check cache first
        is_cached, is_holiday = cls._check_cache(date_str, current_time)
        if is_cached:
            return is_holiday

        # Fetch holiday status and cache it
        return cls._fetch_and_cache_holiday_status(jalali_date, date_str, current_time)

    @classmethod
    def _check_cache(cls, date_str: str, current_time: datetime) -> tuple[bool, bool]:
        """Checks the cache for holiday status to avoid redundant API calls.

        Args:
            date_str (str): The date string to check in the cache.
            current_time (datetime): The current time to compare against cache expiration.

        Returns:
            tuple[bool, bool]: A tuple where the first element indicates if the cache was hit,
                               and the second element is the cached holiday status.
        """
        cached_data = cls._holiday_cache.get(date_str)
        if cached_data:
            is_holiday, expiry_time = cached_data
            if current_time < expiry_time:
                return True, is_holiday

            # Remove expired cache entry
            del cls._holiday_cache[date_str]

        return False, False

    @classmethod
    def _fetch_and_cache_holiday_status(
        cls,
        jalali_date: jdatetime.date,
        date_str: str,
        current_time: datetime,
    ) -> bool:
        """Fetches holiday status from the API and caches the result.

        This method calls an external API to determine if the given Jalali date is a holiday.
        If the API call is successful, the result is cached with an expiration time to avoid
        redundant API calls. If the API call fails, an `UnknownError` is raised.

        Args:
            jalali_date (jdatetime.date): The Jalali date to check for holiday status.
            date_str (str): The date string to use as a cache key.
            current_time (datetime): The current time to set cache expiration.

        Returns:
            bool: True if the date is a holiday, False otherwise.

        Raises:
            UnknownError: If the API request fails due to a network issue or other request-related errors.
        """
        try:
            config: Any = BaseConfig.global_config()
            response = cls._call_holiday_api(jalali_date)
            is_holiday = cls._parse_holiday_response(response, jalali_date)

            # Determine cache TTL based on whether the date is historical
            target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC).date()
            is_historical = target_date <= current_time.date()
            cache_ttl = config.DATETIME.HISTORICAL_CACHE_TTL if is_historical else config.DATETIME.CACHE_TTL

            # Cache the result with appropriate expiration
            expiry_time = current_time + timedelta(seconds=cache_ttl)
            cls._holiday_cache[date_str] = (is_holiday, expiry_time)
        except requests.RequestException as exception:
            raise UnknownError from exception

        return is_holiday

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
    def daterange(cls, start_date: datetime, end_date: datetime) -> Generator[date, None, None]:
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
