Feature: Datetime Utilities

  Scenario: Ensure a timezone-aware datetime
    Given a naive datetime "2024-06-01T10:00:00"
    When the datetime is ensured to be timezone aware
    Then the result should be in UTC timezone

  Scenario: Convert datetime to string format
    Given a datetime "2024-06-01T10:00:00"
    When the datetime is converted to a string
    Then the resulting string should match the format "%Y-%m-%dT%H:%M:%S.%f"

  Scenario: Convert string to datetime
    Given a datetime string "2024-06-01T10:00:00"
    When the string is converted to a datetime object
    Then the resulting object should be a valid datetime

  Scenario: Get current UTC time
    When the current UTC time is retrieved
    Then it should be a valid datetime

  Scenario: Get current epoch time
    When the current epoch time is retrieved
    Then it should be a valid integer timestamp

  Scenario: Add time to a datetime
    Given a datetime "2024-06-01T10:00:00"
    When 1 day is added
    Then the resulting datetime should be "2024-06-02T10:00:00"

  Scenario: Subtract time from a datetime
    Given a datetime "2024-06-01T10:00:00"
    When 1 day is subtracted
    Then the resulting datetime should be "2024-05-31T10:00:00"

  Scenario: Check if a Gregorian date is a holiday in Iran (Non-holiday date)
    #    Assume this date is not a holiday in Iran
    Given a Gregorian date "2025-02-19"
    When we check if the date is a holiday in Iran
    Then the result should be False

  Scenario: Check if a Gregorian date is a holiday in Iran (Holiday date)
    #    Nowruz, a holiday in Iran
    Given a Gregorian date "2025-03-21"
    When we check if the date is a holiday in Iran
    Then the result should be True

  Scenario: Check holiday status for today's date
    Given today's date in Gregorian calendar
    When we check if the date is a holiday in Iran
    Then the result should be either True or False

  Scenario: Handle invalid Gregorian date input
    Given an invalid Gregorian date "2025-02-30"
    When we check if the date is a holiday in Iran
    Then an error should be raised

  Scenario: Ensure caching mechanism works for holiday checks
    #    Nowruz, a holiday in Iran
    Given a Gregorian date "2025-03-27"
    When we check if the date is a holiday in Iran multiple times
    Then the result should be cached, avoiding repeated API calls

  Scenario: Check if a date in the past is correctly identified as a holiday
    #    Nowruz in a past year
    Given a Gregorian date "2021-03-21"
    When we check if the date is a holiday in Iran
    Then the result should be True

  Scenario: Verify historical dates use longer cache TTL
    #    Test that historical dates get cached with HISTORICAL_CACHE_TTL
    Given a historical Gregorian date "2020-03-21"
    When we check if the date is a holiday in Iran with cache verification
    Then the result should be cached with historical TTL

  Scenario: Verify current dates use standard cache TTL
    #    Test that strictly future calendar dates get standard CACHE_TTL (today/past use historical TTL).
    Given a Gregorian date strictly after today
    When we check if the date is a holiday in Iran with cache verification
    Then the result should be cached with standard TTL

  Scenario: A UTC offset parsed from a format is kept
    When the string "2024-01-01 10:00 +0330" is parsed with the format "%Y-%m-%d %H:%M %z"
    Then the parsed datetime is "2024-01-01T06:30:00+00:00" in UTC
    And the parsed datetime keeps a UTC offset of 210 minutes

  Scenario: A string without an offset is read as UTC
    When the string "2024-01-01 10:00" is parsed with the format "%Y-%m-%d %H:%M"
    Then the parsed datetime is "2024-01-01T10:00:00+00:00" in UTC

  Scenario Outline: A date range counts calendar dates
    When the date range from "<start>" to "<end>" is generated
    Then the generated dates are "<dates>"

    Examples:
      | start               | end                 | dates                 |
      | 2024-01-01T23:00:00 | 2024-01-02T01:00:00 | 2024-01-01            |
      | 2024-01-01T10:00:00 | 2024-01-03T09:00:00 | 2024-01-01,2024-01-02 |
      | 2024-01-01T00:00:00 | 2024-01-03T00:00:00 | 2024-01-01,2024-01-02 |
      | 2024-01-01T10:00:00 | 2024-01-01T12:00:00 | none                  |

  Scenario: A date range accepts a mix of naive and aware datetimes
    When the date range from "2024-01-01T00:00:00" to "2024-01-03T00:00:00+00:00" is generated
    Then the generated dates are "2024-01-01,2024-01-02"

  Scenario: Concurrent reads of an expired holiday cache entry do not fail
    Given an expired holiday cache entry
    When 8 threads read the holiday cache at the same time
    Then no thread raised an error

  Scenario: The holiday cache stays within its size limit
    Given the holiday cache is limited to 3 entries
    When 10 holiday statuses are cached
    Then the holiday cache holds at most 3 entries
    And the most recently cached holiday is still present

  Scenario: A holiday API response that is not valid JSON raises an error
    Given a Gregorian date "2031-05-05"
    When we check the date while the API returns an invalid response
    Then an error should be raised
