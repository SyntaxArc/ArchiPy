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

  Scenario Outline: A call rejected by a later window gives its earlier window quota back
    Given a <mode> gRPC rate limit interceptor with burst 3 calls per 60 seconds and sustained 2 calls per 60 seconds
    When 4 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be rate_limited
    And gRPC outcome 4 should be rate_limited
    And the gRPC burst window counter should be 2

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario: Access token identity resolution follows a replaced global config
    Given JWT access tokens for gRPC user A and user B
    When the access token identity of gRPC user A is resolved from metadata
    Then the resolved gRPC identity is the subject of user A
    When the global config is replaced with one that uses a different JWT signing key
    And the access token identity of gRPC user A is resolved from metadata
    Then no gRPC identity is resolved

  Scenario: The auth config for identity resolution is resolved once per global config
    When the auth config for gRPC identity resolution is resolved twice
    Then both resolutions return the same auth config object

  Scenario Outline: Failing identity resolution does not pool callers when fail open
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the gRPC rate limiter fails open
    And the gRPC rate limit identifier function fails
    When 3 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Failing identity resolution aborts when fail closed
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the gRPC rate limit identifier function fails
    When 1 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be unavailable

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Callers behind a trusted proxy are limited independently
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the gRPC rate limiter trusts proxy "127.0.0.1"
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be allowed
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be rate_limited
    When 1 decorated gRPC RPCs are invoked with forwarded client 198.51.100.9
    Then gRPC outcome 1 should be allowed

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Callers behind an untrusted proxy share the proxy bucket
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be allowed
    When 1 decorated gRPC RPCs are invoked with forwarded client 198.51.100.9
    Then gRPC outcome 1 should be rate_limited

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A fail-open limiter runs a handler that returns nothing exactly once
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    And the gRPC rate limiter fails open
    When 1 decorated gRPC RPC whose handler returns nothing is invoked while Redis is unavailable
    Then the gRPC handler should have run 1 time

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: Rate limits still apply when another interceptor follows the rate limiter
    Given a <mode> gRPC rate limit interceptor allowing 2 calls per 60 seconds
    When 3 RPCs are invoked on a real server where another interceptor follows the rate limiter
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be rate_limited

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario: Invalid rate limit window construction is rejected
    When compute_rate_limit_window is called with calls_count 0 and seconds 60
    Then an InvalidArgumentError should be raised

  Scenario: A negative rate limit window component is rejected
    When compute_rate_limit_window is called with calls_count 1 and seconds 100 and minutes -1
    Then an InvalidArgumentError should be raised
