import threading
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.datetime_utils import DatetimeUtils


@given('a naive datetime "{date_string}"')
def step_given_naive_datetime(context: Context, date_string) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = datetime.fromisoformat(date_string)
    scenario_context.store("datetime_obj", datetime_obj)


@when("the datetime is ensured to be timezone aware")
def step_when_timezone_ensured(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = scenario_context.get("datetime_obj")
    result_datetime = DatetimeUtils.ensure_timezone_aware(datetime_obj)
    scenario_context.store("result_datetime", result_datetime)


@then("the result should be in UTC timezone")
def step_then_result_should_be_utc(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    result_datetime = scenario_context.get("result_datetime")
    assert result_datetime.tzinfo == UTC


@given('a datetime "{date_string}"')
def step_given_datetime(context: Context, date_string) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = datetime.fromisoformat(date_string)
    scenario_context.store("datetime_obj", datetime_obj)


@when("the datetime is converted to a string")
def step_when_datetime_is_converted(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = scenario_context.get("datetime_obj")
    result_string = DatetimeUtils.get_string_datetime_from_datetime(datetime_obj)
    scenario_context.store("result_string", result_string)


@then('the resulting string should match the format "{format_string}"')
def step_then_string_should_match_format(context: Context, format_string) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = scenario_context.get("datetime_obj")
    result_string = scenario_context.get("result_string")
    expected_string = datetime_obj.strftime(format_string)
    assert result_string == expected_string


@given('a datetime string "{date_string}"')
def step_given_datetime_string(context: Context, date_string) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("date_string", date_string)


@when("the string is converted to a datetime object")
def step_when_string_to_datetime(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    date_string = scenario_context.get("date_string")
    result_datetime = DatetimeUtils.get_datetime_from_string_datetime(date_string)
    scenario_context.store("result_datetime", result_datetime)


@then("the resulting object should be a valid datetime")
def step_then_result_is_datetime(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    result_datetime = scenario_context.get("result_datetime")
    assert isinstance(result_datetime, datetime)


@when("the current UTC time is retrieved")
def step_when_get_current_utc(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    utc_now = DatetimeUtils.get_datetime_utc_now()
    scenario_context.store("utc_now", utc_now)


@then("it should be a valid datetime")
def step_then_utc_now_is_datetime(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    utc_now = scenario_context.get("utc_now")
    assert isinstance(utc_now, datetime)


@when("the current epoch time is retrieved")
def step_when_get_epoch_now(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    epoch_now = DatetimeUtils.get_epoch_time_now()
    scenario_context.store("epoch_now", epoch_now)


@then("it should be a valid integer timestamp")
def step_then_epoch_is_integer(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    epoch_now = scenario_context.get("epoch_now")
    assert isinstance(epoch_now, int)


@when("1 day is added")
def step_when_add_day(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = scenario_context.get("datetime_obj")
    result_datetime = DatetimeUtils.get_datetime_after_given_datetime_or_now(
        days=1,
        datetime_given=datetime_obj,
    )
    scenario_context.store("result_datetime", result_datetime)


@then('the resulting datetime should be "{expected_date}"')
def step_then_datetime_is_correct(context: Context, expected_date) -> None:
    scenario_context = get_current_scenario_context(context)
    result_datetime = scenario_context.get("result_datetime")
    expected_datetime = datetime.fromisoformat(expected_date)
    assert result_datetime == expected_datetime


@when("1 day is subtracted")
def step_when_subtract_day(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    datetime_obj = scenario_context.get("datetime_obj")
    result_datetime = DatetimeUtils.get_datetime_before_given_datetime_or_now(
        days=1,
        datetime_given=datetime_obj,
    )
    scenario_context.store("result_datetime", result_datetime)


@given('a Gregorian date "{date_str}"')
def step_given_gregorian_date(context: Context, date_str) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("date_str", date_str)
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        scenario_context.store("target_date", target_date)
    except ValueError:
        scenario_context.store("target_date", None)


@given("today's date in Gregorian calendar")
def step_given_todays_date(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    target_date = date.today()
    scenario_context.store("target_date", target_date)


@given('an invalid Gregorian date "{date_str}"')
def step_given_invalid_gregorian_date(context: Context, date_str) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("date_str", date_str)
    scenario_context.store("target_date", None)


@when("we check if the date is a holiday in Iran")
def step_when_check_holiday_in_iran(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    target_date = scenario_context.get("target_date")
    date_str = scenario_context.get("date_str")
    DatetimeUtils._holiday_cache.clear()

    def mock_call_holiday_api(jalali_date) -> dict:
        # Nowruz (1 Farvardin) is the only fixed holiday used by these scenarios.
        is_nowruz = jalali_date.month == 1 and jalali_date.day == 1
        events = (
            [
                {
                    "jalali_year": jalali_date.year,
                    "jalali_month": jalali_date.month,
                    "jalali_day": jalali_date.day,
                    "is_holiday": True,
                },
            ]
            if is_nowruz
            else []
        )
        return {"data": {"event_list": events}}

    try:
        if target_date is not None:
            with patch.object(DatetimeUtils, "_call_holiday_api", side_effect=mock_call_holiday_api):
                result = DatetimeUtils.is_holiday_in_iran(target_date)
            scenario_context.store("result", result)
            scenario_context.store("error", None)
        else:
            raise ValueError(f"Invalid date: {date_str}")
    except Exception as e:
        scenario_context.store("error", e)
        scenario_context.store("result", None)


@when("we check if the date is a holiday in Iran multiple times")
def step_when_check_holiday_multiple_times(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    target_date = scenario_context.get("target_date")

    def mock_call_holiday_api(jalali_date) -> dict:
        current_count = scenario_context.get("api_call_count", 0)
        scenario_context.store("api_call_count", current_count + 1)
        return {
            "data": {
                "event_list": [
                    {
                        "jalali_year": target_date.year,
                        "jalali_month": target_date.month,
                        "jalali_day": target_date.day,
                        "is_holiday": True,
                    },
                ],
            },
        }

    with patch.object(DatetimeUtils, "_call_holiday_api", side_effect=mock_call_holiday_api):
        scenario_context.store("api_call_count", 0)
        result_first = DatetimeUtils.is_holiday_in_iran(target_date)
        result_second = DatetimeUtils.is_holiday_in_iran(target_date)
        scenario_context.store("result_first", result_first)
        scenario_context.store("result_second", result_second)


@then("an error should be raised")
def step_then_error_should_be_raised(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("error")
    assert isinstance(error, Exception)


@then("the result should be cached, avoiding repeated API calls")
def step_then_result_should_be_cached(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    api_call_count = scenario_context.get("api_call_count")
    result_first = scenario_context.get("result_first")
    result_second = scenario_context.get("result_second")

    assert api_call_count == 1
    assert result_first == result_second


@given('a historical Gregorian date "{date_str}"')
def step_given_historical_gregorian_date(context: Context, date_str) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("date_str", date_str)
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    scenario_context.store("target_date", target_date)
    scenario_context.store("is_historical", True)


@given("a Gregorian date strictly after today")
def step_given_gregorian_date_strictly_after_today(context: Context) -> None:
    """Store a fixed test date that always receives standard CACHE_TTL.

    Holiday cache uses HISTORICAL_CACHE_TTL when target_date <= UTC today; standard TTL applies only
    for strictly future calendar dates. A frozen ISO string in Gherkin goes stale as wall time moves.
    """
    scenario_context = get_current_scenario_context(context)
    utc_today = DatetimeUtils.get_datetime_utc_now().date()
    target_date = utc_today + timedelta(days=1)
    scenario_context.store("date_str", target_date.strftime("%Y-%m-%d"))
    scenario_context.store("target_date", target_date)


@when("we check if the date is a holiday in Iran with cache verification")
def step_when_check_holiday_with_cache_verification(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    target_date = scenario_context.get("target_date")

    def mock_call_holiday_api(jalali_date) -> dict:
        return {
            "data": {
                "event_list": [
                    {
                        "jalali_year": jalali_date.year,
                        "jalali_month": jalali_date.month,
                        "jalali_day": jalali_date.day,
                        "is_holiday": True,
                    },
                ],
            },
        }

    with patch.object(DatetimeUtils, "_call_holiday_api", side_effect=mock_call_holiday_api):
        result = DatetimeUtils.is_holiday_in_iran(target_date)
        scenario_context.store("result", result)

        date_str = target_date.strftime("%Y-%m-%d")
        cache_entry = DatetimeUtils._holiday_cache.get(date_str)
        scenario_context.store("cache_entry", cache_entry)


@then("the result should be cached with historical TTL")
def step_then_cached_with_historical_ttl(context: Context) -> None:
    from datetime import timedelta

    scenario_context = get_current_scenario_context(context)
    cache_entry = scenario_context.get("cache_entry")
    test_config = BaseConfig.global_config()

    assert cache_entry is not None, "Cache entry should exist"
    assert test_config is not None, "Test config should be available"

    is_holiday, expiry_time = cache_entry
    current_time = DatetimeUtils.get_datetime_utc_now()

    expected_expiry_range_start = current_time + timedelta(seconds=test_config.DATETIME.HISTORICAL_CACHE_TTL - 5)
    expected_expiry_range_end = current_time + timedelta(seconds=test_config.DATETIME.HISTORICAL_CACHE_TTL + 5)

    assert (
        expected_expiry_range_start <= expiry_time <= expected_expiry_range_end
    ), f"Cache expiry time should be around {test_config.DATETIME.HISTORICAL_CACHE_TTL} seconds from now"


@then("the result should be cached with standard TTL")
def step_then_cached_with_standard_ttl(context: Context) -> None:
    from datetime import timedelta

    scenario_context = get_current_scenario_context(context)
    cache_entry = scenario_context.get("cache_entry")
    test_config = BaseConfig.global_config()

    assert cache_entry is not None, "Cache entry should exist"
    assert test_config is not None, "Test config should be available"

    is_holiday, expiry_time = cache_entry
    current_time = DatetimeUtils.get_datetime_utc_now()

    expected_expiry_range_start = current_time + timedelta(seconds=test_config.DATETIME.CACHE_TTL - 5)
    expected_expiry_range_end = current_time + timedelta(seconds=test_config.DATETIME.CACHE_TTL + 5)

    assert (
        expected_expiry_range_start <= expiry_time <= expected_expiry_range_end
    ), f"Cache expiry time should be around {test_config.DATETIME.CACHE_TTL} seconds from now"


@when('the string "{value}" is parsed with the format "{format_}"')
def step_when_parse_with_format(context: Context, value, format_) -> None:
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("parsed", DatetimeUtils.get_datetime_from_string_datetime(value, format_))


@then('the parsed datetime is "{expected}" in UTC')
def step_then_parsed_is_utc(context: Context, expected) -> None:
    parsed = get_current_scenario_context(context).get("parsed")
    assert parsed.astimezone(UTC).isoformat() == expected, parsed.isoformat()


@then("the parsed datetime keeps a UTC offset of {minutes:d} minutes")
def step_then_parsed_offset(context: Context, minutes) -> None:
    parsed = get_current_scenario_context(context).get("parsed")
    assert parsed.utcoffset() == timedelta(minutes=minutes), parsed.utcoffset()


@when('the date range from "{start}" to "{end}" is generated')
def step_when_daterange(context: Context, start, end) -> None:
    scenario_context = get_current_scenario_context(context)
    dates = DatetimeUtils.daterange(datetime.fromisoformat(start), datetime.fromisoformat(end))
    scenario_context.store("generated_dates", [d.isoformat() for d in dates])


@then('the generated dates are "{expected}"')
def step_then_generated_dates(context: Context, expected) -> None:
    dates = get_current_scenario_context(context).get("generated_dates")
    assert dates == ([] if expected == "none" else expected.split(",")), dates


def _restore_cache(context: Context) -> None:
    original = dict(DatetimeUtils._holiday_cache)
    original_max = DatetimeUtils._HOLIDAY_CACHE_MAX_SIZE

    def restore() -> None:
        DatetimeUtils._holiday_cache.clear()
        DatetimeUtils._holiday_cache.update(original)
        DatetimeUtils._HOLIDAY_CACHE_MAX_SIZE = original_max

    context.add_cleanup(restore)


@given("an expired holiday cache entry")
def step_given_expired_cache_entry(context: Context) -> None:
    _restore_cache(context)
    DatetimeUtils._holiday_cache.clear()
    DatetimeUtils._holiday_cache["2000-01-01"] = (True, DatetimeUtils.get_datetime_utc_now() - timedelta(days=1))


@when("{count:d} threads read the holiday cache at the same time")
def step_when_threads_read_cache(context: Context, count) -> None:
    scenario_context = get_current_scenario_context(context)
    barrier = threading.Barrier(count)
    errors: list[BaseException] = []

    def worker() -> None:
        barrier.wait()
        try:
            DatetimeUtils._check_cache("2000-01-01", DatetimeUtils.get_datetime_utc_now())
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    scenario_context.store("thread_errors", errors)


@then("no thread raised an error")
def step_then_no_thread_error(context: Context) -> None:
    errors = get_current_scenario_context(context).get("thread_errors")
    assert errors == [], errors


@given("the holiday cache is limited to {size:d} entries")
def step_given_cache_limit(context: Context, size) -> None:
    _restore_cache(context)
    DatetimeUtils._holiday_cache.clear()
    DatetimeUtils._HOLIDAY_CACHE_MAX_SIZE = size


@when("{count:d} holiday statuses are cached")
def step_when_statuses_cached(context: Context, count) -> None:
    now = DatetimeUtils.get_datetime_utc_now()
    for index in range(count):
        DatetimeUtils._store_in_cache(f"2030-01-{index + 1:02d}", False, now + timedelta(hours=1), now)
    get_current_scenario_context(context).store("last_cached_key", f"2030-01-{count:02d}")


@then("the holiday cache holds at most {size:d} entries")
def step_then_cache_size(context: Context, size) -> None:
    assert len(DatetimeUtils._holiday_cache) <= size, len(DatetimeUtils._holiday_cache)


@then("the most recently cached holiday is still present")
def step_then_latest_cached(context: Context) -> None:
    assert get_current_scenario_context(context).get("last_cached_key") in DatetimeUtils._holiday_cache


@when("we check the date while the API returns an invalid response")
def step_when_invalid_api_response(context: Context) -> None:
    scenario_context = get_current_scenario_context(context)
    target_date = scenario_context.get("target_date")
    _restore_cache(context)
    DatetimeUtils._holiday_cache.clear()
    with patch.object(DatetimeUtils, "_call_holiday_api", side_effect=ValueError("not json")):
        try:
            DatetimeUtils.is_holiday_in_iran(target_date)
            scenario_context.store("error", None)
        except Exception as e:
            scenario_context.store("error", e)
