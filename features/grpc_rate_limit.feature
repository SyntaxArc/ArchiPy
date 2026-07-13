@needs-redis
Feature: gRPC server rate limit interceptor
  As a developer
  I want decorator-declared gRPC rate limits backed by Redis INCREX
  So that RPCs are bounded per client and time window

  Scenario Outline: RPCs within the limit succeed
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    When 3 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: RPCs exceeding the limit are rejected
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    When 4 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed
    And gRPC outcome 4 should be rate_limited

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Undecorated RPCs are not rate limited
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    When 3 undecorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Stacked decorators enforce burst and sustained windows
    Given a <mode> gRPC rate limit interceptor with burst 2 calls per 1 seconds and sustained 3 calls per 60 seconds
    When 2 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    When 1 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be rate_limited

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Distinct JWT users are limited independently over gRPC
    Given a <mode> gRPC JWT rate limit interceptor allowing 2 calls per 60 seconds
    And JWT access tokens for gRPC user A and user B
    When 2 decorated gRPC RPCs are invoked with JWT token for user A
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    When 1 decorated gRPC RPCs are invoked with JWT token for user A
    Then gRPC outcome 1 should be rate_limited
    When 1 decorated gRPC RPCs are invoked with JWT token for user B
    Then gRPC outcome 1 should be allowed

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Redis failures abort when fail closed
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    When 1 decorated gRPC RPC is invoked while Redis is unavailable
    Then gRPC outcome 1 should be unavailable

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario: Invalid rate limit window construction is rejected
    When compute_rate_limit_window is called with calls_count 0 and seconds 60
    Then an InvalidArgumentError should be raised
