Feature: Retry Decorator
  As a developer
  I want failing functions to be retried automatically
  So that transient failures do not break my workflow

  Scenario: Function succeeding on first call is not retried
    Given a retry config with max_retries 3 and delay 0.0
    And a retry-decorated function that raises ValueError on the first 0 calls
    When the retry-decorated function is called
    Then the retry-decorated function returns "ok"
    And the retry-decorated function was invoked 1 times

  Scenario: Function recovers after transient failures
    Given a retry config with max_retries 3 and delay 0.0
    And a retry-decorated function that raises ValueError on the first 2 calls
    When the retry-decorated function is called
    Then the retry-decorated function returns "ok"
    And the retry-decorated function was invoked 3 times

  Scenario: Retries are exhausted and ResourceExhaustedError is raised
    Given a retry config with max_retries 3 and delay 0.0
    And a retry resource type "external-api"
    And a retry-decorated function that raises ValueError on the first 10 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises ResourceExhaustedError
    And the retry-decorated function was invoked 3 times
    And the retry error carries resource type "external-api"

  Scenario: Zero max_retries never calls the function
    Given a retry config with max_retries 0 and delay 0.0
    And a retry-decorated function that raises ValueError on the first 0 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises ResourceExhaustedError
    And the retry-decorated function was invoked 0 times

  Scenario: Delay is applied between attempts but not after the last one
    Given a retry config with max_retries 3 and delay 0.05
    And a retry-decorated function that raises ValueError on the first 10 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises ResourceExhaustedError
    And the retry elapsed time is at least 0.1 seconds
    And the retry elapsed time is below 0.15 seconds

  Scenario: Only errors listed in retry_on are retried
    Given a retry config with max_retries 3 and delay 0.0
    And a retry config retrying only on ValueError
    And a retry-decorated function that raises ValueError on the first 2 calls
    When the retry-decorated function is called
    Then the retry-decorated function returns "ok"
    And the retry-decorated function was invoked 3 times

  Scenario: Errors not listed in retry_on propagate immediately
    Given a retry config with max_retries 3 and delay 0.0
    And a retry config retrying only on ValueError
    And a retry-decorated function that raises KeyError on the first 10 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises built-in error KeyError
    And the retry-decorated function was invoked 1 times

  Scenario: Ignored errors propagate immediately
    Given a retry config with max_retries 3 and delay 0.0
    And a retry config ignoring ValueError
    And a retry-decorated function that raises ValueError on the first 10 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises built-in error ValueError
    And the retry-decorated function was invoked 1 times

  Scenario: Ignore takes precedence over retry_on
    Given a retry config with max_retries 3 and delay 0.0
    And a retry config retrying only on ValueError
    And a retry config ignoring ValueError
    And a retry-decorated function that raises ValueError on the first 10 calls
    When the retry-decorated function is called
    Then the retry-decorated function raises built-in error ValueError
    And the retry-decorated function was invoked 1 times

  Scenario: Arguments are passed through and function metadata is preserved
    Given a retry config with max_retries 2 and delay 0.0
    And a retry-decorated function that raises ValueError on the first 1 calls
    When the retry-decorated function is called with arguments 3 and 4
    Then the retry-decorated function returns "ok:7"
    And the retry-decorated function keeps its name "flaky_function"
