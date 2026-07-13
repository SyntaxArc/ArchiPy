@needs-redis
Feature: FastAPI REST rate limit handler
  As a developer
  I want rate limiting backed by Redis INCREX
  So that requests are bounded per client and time window

  Scenario: Requests within the limit succeed
    Given a rate-limited FastAPI endpoint allowing 3 calls per 60 seconds
    When 3 requests are made to the endpoint
    Then response 1 should have status 200
    And response 1 should include a "X-RateLimit-Limit" header
    And response 1 should include a "X-RateLimit-Remaining" header
    And response 2 should have status 200
    And response 3 should have status 200

  Scenario: Requests exceeding the limit are rejected with 429
    Given a rate-limited FastAPI endpoint allowing 3 calls per 60 seconds
    When 4 requests are made to the endpoint
    Then response 1 should have status 200
    And response 2 should have status 200
    And response 3 should have status 200
    And response 4 should have status 429
    And response 4 should include a "Retry-After" header
    And response 4 should include a "X-RateLimit-Limit" header
    And response 4 should include a "X-RateLimit-Remaining" header

  Scenario: Rate limit window resets after expiry
    Given a rate-limited FastAPI endpoint allowing 2 calls per 1 seconds
    When 2 requests are made to the endpoint
    Then response 1 should have status 200
    And response 2 should have status 200
    When 1 requests are made to the endpoint
    Then response 1 should have status 429
    When I wait 2 seconds for the rate limit window to expire
    And 1 requests are made to the endpoint
    Then response 1 should have status 200

  Scenario: Spoofed client IP headers are ignored without trusted proxies
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds
    When 1 requests are made to the endpoint with header "X-Real-IP" "8.8.8.8"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Real-IP" "1.1.1.1"
    Then response 1 should have status 429

  Scenario: Distinct clients are limited independently behind trusted proxies
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies
    When 1 requests are made to the endpoint with header "X-Real-IP" "8.8.8.8"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Real-IP" "1.1.1.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Real-IP" "8.8.8.8"
    Then response 1 should have status 429
    When 1 requests are made to the endpoint with header "X-Real-IP" "1.1.1.1"
    Then response 1 should have status 429

  Scenario: Multi-hop X-Forwarded-For chain resolves client behind trusted proxies
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies and internal hops
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "8.8.8.8, 10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "1.1.1.1, 10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "8.8.8.8, 10.0.0.1"
    Then response 1 should have status 429

  Scenario: Injected X-Forwarded-For entries before the real client are ignored
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies and internal hops
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "1.1.1.1, 8.8.8.8, 10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "9.9.9.9, 8.8.8.8, 10.0.0.1"
    Then response 1 should have status 429

  Scenario: X-Forwarded-For port suffixes are stripped behind trusted proxies
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies and internal hops
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "8.8.8.8:443, 10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Forwarded-For" "8.8.8.8:8443, 10.0.0.1"
    Then response 1 should have status 429

  Scenario: Multiple X-Forwarded-For header fields are combined
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies and internal hops
    When 1 requests are made to the endpoint with X-Forwarded-For fields "8.8.8.8" and "10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with X-Forwarded-For fields "1.1.1.1" and "10.0.0.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with X-Forwarded-For fields "8.8.8.8" and "10.0.0.1"
    Then response 1 should have status 429

  Scenario: X-Real-IP is ignored when X-Forwarded-For is present
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds with trusted proxies and internal hops
    When 1 requests are made to the endpoint with headers
      | header            | value                          |
      | X-Forwarded-For   | 8.8.8.8, 10.0.0.1              |
      | X-Real-IP         | 1.1.1.1                        |
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with headers
      | header            | value                          |
      | X-Forwarded-For   | 8.8.8.8, 10.0.0.1              |
      | X-Real-IP         | 9.9.9.9                        |
    Then response 1 should have status 429

  Scenario: Redis failures return 503 when fail closed
    Given a rate-limited FastAPI endpoint allowing 3 calls per 60 seconds
    When 1 request is made while Redis is unavailable
    Then response 1 should have status 503

  Scenario: Query params without identifier_fn is rejected at construction
    When a rate limit handler is created with query params but no identifier
    Then an InvalidArgumentError should be raised

  Scenario: Distinct JWT users are limited independently
    Given a JWT rate-limited FastAPI endpoint allowing 2 calls per 60 seconds
    And JWT access tokens for user A and user B
    When 2 requests are made to the endpoint with JWT token for user A
    Then response 1 should have status 200
    And response 2 should have status 200
    When 1 requests are made to the endpoint with JWT token for user A
    Then response 1 should have status 429
    When 1 requests are made to the endpoint with JWT token for user B
    Then response 1 should have status 200

  Scenario: Requests without JWT fall back to client IP bucket
    Given a JWT rate-limited FastAPI endpoint allowing 1 calls per 60 seconds
    When 1 requests are made to the endpoint
    Then response 1 should have status 200
    When 1 requests are made to the endpoint
    Then response 1 should have status 429

  Scenario: Invalid JWT access token falls back to client IP bucket
    Given a JWT rate-limited FastAPI endpoint allowing 1 calls per 60 seconds
    And a valid user UUID
    And an expired access token
    When 1 requests are made to the endpoint with the stored JWT token
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with the stored JWT token
    Then response 1 should have status 429

  Scenario: Multiple windows enforce burst before sustained limits
    Given a multi-window FastAPI endpoint with burst 2 calls per 1 seconds and sustained 3 calls per 60 seconds
    When 2 requests are made to the endpoint
    Then response 1 should have status 200
    And response 2 should have status 200
    When 1 requests are made to the endpoint
    Then response 1 should have status 429

  Scenario: Multi-window success headers reflect the most constrained window
    Given a multi-window FastAPI endpoint with burst 10 calls per 60 seconds and sustained 2 calls per 60 seconds
    When 1 requests are made to the endpoint
    Then response 1 should have status 200
    And response 1 header "X-RateLimit-Limit" should equal "2"
    And response 1 header "X-RateLimit-Remaining" should equal "1"

  Scenario: Invalid primary rate limit window construction is rejected
    When compute_rate_limit_window is called with calls_count 0 and seconds 60
    Then an InvalidArgumentError should be raised
