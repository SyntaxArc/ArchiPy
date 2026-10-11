Feature: Timeout Decorator
  As a developer
  I want long-running functions to be aborted after a deadline
  So that my application does not hang

  Scenario: Function finishing within the timeout returns its result
    Given a timeout-decorated function that sleeps 0.01 seconds with a 1 second limit
    When the timeout-decorated function is called
    Then the timeout-decorated function returns "done"
    And no timeout alarm remains pending

  Scenario: Function exceeding the timeout raises DeadlineExceededError
    Given a timeout-decorated function that sleeps 3.0 seconds with a 1 second limit
    When the timeout-decorated function is called
    Then the timeout-decorated function raises DeadlineExceededError
    And the timeout error names operation "slow_function"
    And the timeout error has code "DEADLINE_EXCEEDED"
    And the timeout-decorated function was interrupted before 2 seconds
    And no timeout alarm remains pending

  Scenario: Errors raised by the function propagate and clear the alarm
    Given a timeout-decorated function that raises ValueError with a 1 second limit
    When the timeout-decorated function is called
    Then the timeout-decorated function raises ValueError
    And no timeout alarm remains pending

  Scenario: Arguments are passed through and function metadata is preserved
    Given a timeout-decorated function that sleeps 0.0 seconds with a 1 second limit
    When the timeout-decorated function is called with arguments 5 and 6
    Then the timeout-decorated function returns "done:11"
    And the timeout-decorated function keeps its name "slow_function"
