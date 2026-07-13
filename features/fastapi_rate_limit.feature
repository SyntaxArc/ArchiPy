@needs-redis
Feature: FastAPI REST rate limit handler
  As a developer
  I want rate limiting backed by Redis INCREX
  So that requests are bounded per client and time window

  Scenario: Requests within the limit succeed
    Given a rate-limited FastAPI endpoint allowing 3 calls per 60 seconds
    When 3 requests are made to the endpoint
    Then response 1 should have status 200
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

  Scenario: Distinct clients are limited independently
    Given a rate-limited FastAPI endpoint allowing 1 calls per 60 seconds
    When 1 requests are made to the endpoint with header "X-Real-IP" "8.8.8.8"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Real-IP" "1.1.1.1"
    Then response 1 should have status 200
    When 1 requests are made to the endpoint with header "X-Real-IP" "8.8.8.8"
    Then response 1 should have status 429
    When 1 requests are made to the endpoint with header "X-Real-IP" "1.1.1.1"
    Then response 1 should have status 429
