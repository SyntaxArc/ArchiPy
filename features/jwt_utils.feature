Feature: JWT Utilities

  Scenario: Generate an access token
    Given a valid user UUID
    When an access token is created
    Then a JWT token should be returned

  Scenario: Generate a refresh token
    Given a valid user UUID
    When a refresh token is created
    Then a JWT token should be returned

  Scenario: Decode a valid access token
    Given a valid user UUID
    And a valid access token
    When the token is decoded
    Then the decoded payload should be valid

  Scenario: Decode a valid refresh token
    Given a valid user UUID
    And a valid refresh token
    When the token is decoded
    Then the decoded payload should be valid

  Scenario: Expired token should not be valid
    Given a valid user UUID
    And an expired access token
    When the token is decoded
    Then a TokenExpiredError should be raised

  Scenario: Invalid token should not be accepted
    Given a valid user UUID
    And an invalid token
    When the token is decoded
    Then an InvalidTokenError should be raised

  Scenario Outline: Additional claims cannot redefine identity claims
    Given a valid user UUID
    When an access token is created with the additional claim "<claim>"
    Then a token claims error should be raised

    Examples:
      | claim         |
      | sub           |
      | type          |
      | token_version |
      | iss           |
      | aud           |
      | jti           |

  Scenario: Clock skew within the configured leeway is tolerated
    Given a valid user UUID
    And an access token that expired 5 seconds ago
    When the token is decoded with a leeway of 30 seconds
    Then the decoded payload should be valid

  Scenario: Clock skew beyond the configured leeway is rejected
    Given a valid user UUID
    And an access token that expired 60 seconds ago
    When the token is decoded with a leeway of 30 seconds
    Then a TokenExpiredError should be raised

  Scenario: The unsigned none algorithm is refused
    Given a valid user UUID
    When an access token is created with the signing algorithm "none"
    Then a token claims error should be raised

  Scenario: An empty required token type is still enforced
    Given a valid user UUID
    And a valid access token
    When the token is decoded requiring an empty token type
    Then an InvalidTokenError should be raised

  Scenario: A negative leeway is rejected by the configuration
    When an authentication configuration is built with a leeway of -1
    Then the configuration is rejected

  Scenario Outline: A signing key shorter than the HMAC algorithm requires is refused
    Given a valid user UUID
    When an access token is created with a <length> byte signing key and the algorithm "<algorithm>"
    Then a token claims error should be raised

    Examples:
      | length | algorithm |
      | 31     | HS256     |
      | 47     | HS384     |
      | 63     | HS512     |

  Scenario Outline: A signing key of the required HMAC length works
    Given a valid user UUID
    When an access token is created with a <length> byte signing key and the algorithm "<algorithm>"
    Then no token error is raised

    Examples:
      | length | algorithm |
      | 32     | HS256     |
      | 48     | HS384     |
      | 64     | HS512     |

  Scenario: A short signing key is also refused when decoding
    Given a valid user UUID
    And a valid access token
    When the token is decoded with a 8 byte signing key
    Then a token claims error should be raised

  Scenario Outline: A <kind> token is checked against the token type that is required
    Given a valid user UUID
    And a valid <kind> token
    When the token is verified as a <required> token
    Then the verification should <outcome>

    Examples: Token type checks
      | kind    | required | outcome |
      | access  | access   | succeed |
      | refresh | refresh  | succeed |
      | access  | refresh  | fail    |
      | refresh | access   | fail    |

  Scenario: A token issued under an older token version is refused
    Given a valid user UUID
    And a valid access token
    When the token is decoded after the configured token version changes
    Then an InvalidTokenError should be raised

  Scenario Outline: The user UUID is read from the subject claim of <case>
    When the user UUID is extracted from <case>
    Then the extraction should <outcome>

    Examples: Subject claims
      | case                | outcome |
      | a valid subject     | succeed |
      | a missing subject   | fail    |
      | a numeric subject   | fail    |
      | a malformed subject | fail    |

  Scenario: The token expiry is the expiry claim of the token
    Given a valid user UUID
    And a valid access token
    When the token expiry is read
    Then the expiry should match the expiry claim

  Scenario: The token expiry of an invalid token is refused
    Given an invalid token
    When the token expiry is read
    Then an InvalidTokenError should be raised

  Scenario Outline: A token is not created from <case>
    When a token is created from <case>
    Then a token claims error should be raised

    Examples: Invalid inputs
      | case              |
      | empty data        |
      | a zero expiry     |
      | a negative expiry |
