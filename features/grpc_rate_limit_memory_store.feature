Feature: In-memory rate limit store
  As a developer
  I want a rate limit counter store that needs no Redis
  So that tests and single-process servers can enforce rate limits

  Scenario Outline: Calls beyond the window limit are rejected
    Given a <mode> in-memory rate limit store
    When the counter "user:1" is incremented 3 times with a limit of 2 per 60000 ms
    Then the increments should apply 1, 1 and 0
    And the counter "user:1" should have a time to live below 60001 ms

    Examples: Store modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A window expires and the counter starts over
    Given a <mode> in-memory rate limit store
    When the counter "user:2" is incremented 2 times with a limit of 1 per 50 ms
    And 120 ms pass
    And the counter "user:2" is incremented 1 times with a limit of 1 per 50 ms
    Then the last increment should apply 1

    Examples: Store modes
      | mode  |
      | sync  |
      | async |

  Scenario: A refund gives back one call and never goes below zero
    Given a sync in-memory rate limit store
    When the counter "user:3" is incremented 1 times with a limit of 2 per 60000 ms
    And the counter "user:3" is refunded 2 times
    Then the counter "user:3" should hold 0

  Scenario: An unknown counter does not exist
    Given a sync in-memory rate limit store
    Then the counter "missing" should have no time to live record
