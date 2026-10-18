@needs-redis
Feature: gRPC server rate limit interceptor
  As a developer
  I want decorator-declared gRPC rate limits backed by Redis INCREX
  So that RPCs are bounded per client and time window

  Scenario Outline: RPCs within the limit succeed
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    When 3 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: RPCs exceeding the limit are rejected
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    When 4 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be allowed
    And gRPC outcome 4 should be rate_limited

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

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
    And the interceptor counts in the <store> counter store
    When 2 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    When 1 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be rate_limited

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: Distinct JWT users are limited independently over gRPC
    Given a <mode> gRPC JWT rate limit interceptor allowing 2 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    And JWT access tokens for gRPC user A and user B
    When 2 decorated gRPC RPCs are invoked with JWT token for user A
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    When 1 decorated gRPC RPCs are invoked with JWT token for user A
    Then gRPC outcome 1 should be rate_limited
    When 1 decorated gRPC RPCs are invoked with JWT token for user B
    Then gRPC outcome 1 should be allowed

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: Redis failures abort when fail closed
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    When 1 decorated gRPC RPC is invoked while Redis is unavailable
    Then gRPC outcome 1 should be unavailable

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: An error type the caller names for its store follows the fail-closed setting
    Given a <mode> gRPC rate limit interceptor allowing 3 calls per 60 seconds
    And the interceptor is built with a caller store whose backend is down
    When 1 decorated gRPC RPC is invoked
    Then gRPC outcome 1 should be unavailable

    Examples: Interceptor modes
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A call rejected by a later window gives its earlier window quota back
    Given a <mode> gRPC rate limit interceptor with burst 3 calls per 60 seconds and sustained 2 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    When 4 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be rate_limited
    And gRPC outcome 4 should be rate_limited
    And the gRPC burst window counter should be 2

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

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
    And the interceptor counts in the <store> counter store
    And the gRPC rate limiter trusts proxy "127.0.0.1"
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be allowed
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be rate_limited
    When 1 decorated gRPC RPCs are invoked with forwarded client 198.51.100.9
    Then gRPC outcome 1 should be allowed

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: Callers behind an untrusted proxy share the proxy bucket
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7
    Then gRPC outcome 1 should be allowed
    When 1 decorated gRPC RPCs are invoked with forwarded client 198.51.100.9
    Then gRPC outcome 1 should be rate_limited

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: Callers behind a chain of trusted proxies are limited by the first untrusted hop
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    And the gRPC rate limiter trusts proxy "127.0.0.1"
    And the gRPC rate limiter trusts proxy "10.0.0.2"
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7, 10.0.0.2
    Then gRPC outcome 1 should be allowed
    When 1 decorated gRPC RPCs are invoked with forwarded client 203.0.113.7, 10.0.0.2
    Then gRPC outcome 1 should be rate_limited
    When 1 decorated gRPC RPCs are invoked with forwarded client 198.51.100.9, 10.0.0.2
    Then gRPC outcome 1 should be allowed

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario Outline: A trusted proxy that sends no forwarded header is limited as one caller
    Given a <mode> gRPC rate limit interceptor allowing 1 calls per 60 seconds
    And the interceptor counts in the <store> counter store
    And the gRPC rate limiter trusts proxy "127.0.0.1"
    When 2 decorated gRPC RPCs are invoked
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be rate_limited

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario: A missing peer is reported as unknown
    When the gRPC peer is missing
    Then the parsed gRPC peer should be "unknown"

  Scenario Outline: A peer address is reduced to its host
    When the gRPC peer "<peer>" is parsed
    Then the parsed gRPC peer should be "<host>"

    Examples: Peer formats
      | peer                    | host              |
      | ipv4:203.0.113.7:50051  | 203.0.113.7       |
      | ipv4:203.0.113.7        | 203.0.113.7       |
      | ipv6:[2001:db8::1]:5005 | 2001:db8::1       |
      | unix:/tmp/grpc.sock     | /tmp/grpc.sock    |
      | unknown-transport       | unknown-transport |

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
    And the interceptor counts in the <store> counter store
    When 3 RPCs are invoked on a real server where another interceptor follows the rate limiter
    Then gRPC outcome 1 should be allowed
    And gRPC outcome 2 should be allowed
    And gRPC outcome 3 should be rate_limited

    Examples: Interceptor modes and counter stores
      | mode  | store  |
      | sync  | redis  |
      | sync  | memory |
      | async | redis  |
      | async | memory |

  Scenario: Invalid rate limit window construction is rejected
    When compute_rate_limit_window is called with calls_count 0 and seconds 60
    Then an InvalidArgumentError should be raised

  Scenario: A negative rate limit window component is rejected
    When compute_rate_limit_window is called with calls_count 1 and seconds 100 and minutes -1
    Then an InvalidArgumentError should be raised

  Scenario Outline: Calls beyond the window limit are rejected
    Given a <mode> in-memory rate limit store
    When the counter "<name>" is incremented <calls> times with a limit of <limit> per <window> ms
    Then the last increment should apply <last_applied>
    And the counter "<name>" should have a time to live below <ttl_limit> ms

    Examples: Sync store
      | mode | name   | calls | limit | window | last_applied | ttl_limit |
      | sync | user:1 | 3     | 2     | 60000  | 0            | 60001     |
      | sync | user:2 | 2     | 2     | 60000  | 1            | 60001     |
      | sync | user:3 | 1     | 1     | 1000   | 1            | 1001      |

    Examples: Async store
      | mode  | name   | calls | limit | window | last_applied | ttl_limit |
      | async | user:4 | 3     | 2     | 60000  | 0            | 60001     |
      | async | user:5 | 2     | 2     | 60000  | 1            | 60001     |
      | async | user:6 | 1     | 1     | 1000   | 1            | 1001      |

  Scenario Outline: A window expires and the counter starts over
    Given a <mode> in-memory rate limit store
    When the counter "<name>" is incremented 2 times with a limit of 1 per <window> ms
    And <wait> ms pass
    And the counter "<name>" is incremented 1 times with a limit of 1 per <window> ms
    Then the last increment should apply 1

    Examples: Store modes
      | mode  | name   | window | wait |
      | sync  | user:7 | 50     | 120  |
      | async | user:8 | 50     | 120  |

  Scenario Outline: A refund gives back calls and never goes below zero
    Given a <mode> in-memory rate limit store
    When the counter "<name>" is incremented <calls> times with a limit of 2 per 60000 ms
    And the counter "<name>" is refunded <refunds> times
    Then the counter "<name>" should hold <remaining>

    Examples: Store modes
      | mode  | name    | calls | refunds | remaining |
      | sync  | user:9  | 1     | 2       | 0         |
      | sync  | user:10 | 2     | 1       | 1         |
      | async | user:11 | 1     | 2       | 0         |
      | async | user:12 | 2     | 1       | 1         |

  Scenario Outline: A refund of a counter that does not exist creates nothing
    Given a <mode> in-memory rate limit store
    When the counter "<name>" is refunded 1 times
    Then the counter "<name>" should have no time to live record

    Examples: Store modes
      | mode  | name     |
      | sync  | refund:1 |
      | async | refund:2 |

  Scenario Outline: An unknown counter does not exist
    Given a <mode> in-memory rate limit store
    Then the counter "<name>" should have no time to live record

    Examples: Store modes
      | mode  | name      |
      | sync  | missing:1 |
      | async | missing:2 |
