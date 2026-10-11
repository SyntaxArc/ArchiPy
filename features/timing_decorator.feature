Feature: Timing Decorator
  As a developer
  I want execution time of functions logged at DEBUG level
  So that I can spot slow code

  Scenario: Execution time is logged when root logging level is DEBUG
    Given a timing-decorated function that sleeps 0.02 seconds
    And the root logging level is DEBUG
    When the timing-decorated function is called
    Then the timing-decorated function returns "result"
    And one timing log message is recorded for "slow_work"
    And the timing log message reports at least 0.02 seconds

  Scenario: Nothing is logged when root logging level is not DEBUG
    Given a timing-decorated function that sleeps 0.0 seconds
    And the root logging level is WARNING
    When the timing-decorated function is called
    Then the timing-decorated function returns "result"
    And no timing log message is recorded

  Scenario: Arguments are passed through and function metadata is preserved
    Given a timing-decorated function that sleeps 0.0 seconds
    And the root logging level is DEBUG
    When the timing-decorated function is called with arguments 2 and 3
    Then the timing-decorated function returns "result:5"
    And the timing-decorated function keeps its name "slow_work"

  Scenario: Errors from the function propagate without a timing log
    Given a timing-decorated function that raises ValueError
    And the root logging level is DEBUG
    When the timing-decorated function is called
    Then the timing-decorated function raises ValueError
    And no timing log message is recorded
