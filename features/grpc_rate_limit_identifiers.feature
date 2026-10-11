@unit
Feature: gRPC rate-limit identity helpers

  Scenario: Tuple metadata is normalized to a string dict
    Given identifier metadata with tuple entries:
      | key        | value |
      | x-trace-id | abc   |
      | x-tenant   | acme  |
    When identifier metadata is normalized
    Then the normalized identifier metadata has 2 entries
    And the normalized identifier metadata maps "x-trace-id" to "abc"
    And the normalized identifier metadata maps "x-tenant" to "acme"

  Scenario: Longer tuples use the first two items and list pairs are ignored
    Given identifier metadata with list-style pair "x-a" and "1"
    And identifier metadata with a three-item tuple "x-b", "2" and "extra"
    When identifier metadata is normalized
    Then the normalized identifier metadata has 1 entries
    And the normalized identifier metadata maps "x-b" to "2"

  Scenario: Attribute-style metadata entries are normalized
    Given identifier metadata with attribute entries:
      | key      | value |
      | x-source | grpc  |
    When identifier metadata is normalized
    Then the normalized identifier metadata maps "x-source" to "grpc"

  Scenario: Bytes values are decoded and invalid bytes are dropped
    Given identifier metadata with bytes value "caf" followed by invalid byte under key "x-bin"
    When identifier metadata is normalized
    Then the normalized identifier metadata maps "x-bin" to "caf"

  Scenario: Non-string values are converted to strings
    Given identifier metadata with integer value 42 under key "x-count"
    When identifier metadata is normalized
    Then the normalized identifier metadata maps "x-count" to "42"

  Scenario: Malformed entries are skipped
    Given identifier metadata with tuple entries:
      | key  | value |
      | x-ok | yes   |
    And identifier metadata with a one-item tuple "lonely"
    And identifier metadata with a bare string entry "not-a-pair"
    When identifier metadata is normalized
    Then the normalized identifier metadata has 1 entries
    And the normalized identifier metadata maps "x-ok" to "yes"

  Scenario: Empty metadata yields an empty dict
    Given identifier metadata that is empty
    When identifier metadata is normalized
    Then the normalized identifier metadata has 0 entries

  Scenario: Later duplicate keys win
    Given identifier metadata with tuple entries:
      | key | value |
      | x-k | first |
      | x-k | last  |
    When identifier metadata is normalized
    Then the normalized identifier metadata maps "x-k" to "last"

  Scenario Outline: Bearer token is extracted from the authorization header
    Given identifier metadata with header "<header>" and value "<value>"
    When the bearer token is extracted from identifier metadata
    Then the extracted identifier bearer token is "<token>"

    Examples:
      | header        | value            | token   |
      | authorization | Bearer abc.def   | abc.def |
      | Authorization | Bearer abc.def   | abc.def |
      | authorization | bearer abc.def   | abc.def |
      | authorization | BEARER abc.def   | abc.def |
      | authorization | Bearer   abc.def | abc.def |

  Scenario Outline: Bearer extraction yields nothing for unusable headers
    Given identifier metadata with header "<header>" and value "<value>"
    When the bearer token is extracted from identifier metadata
    Then no identifier bearer token is extracted

    Examples:
      | header        | value      |
      | authorization | Basic abc  |
      | authorization | Bearer     |
      | authorization | abcdef     |
      | x-other       | Bearer abc |

  Scenario: Bearer extraction yields nothing without metadata
    Given identifier metadata that is empty
    When the bearer token is extracted from identifier metadata
    Then no identifier bearer token is extracted

  Scenario: Bearer token is extracted from bytes metadata values
    Given identifier metadata with bytes header "authorization" and value "Bearer xyz"
    When the bearer token is extracted from identifier metadata
    Then the extracted identifier bearer token is "xyz"

  Scenario: Subject is resolved from a valid access token
    Given identifier metadata with a valid access token for a new user
    When the subject is resolved from identifier metadata
    Then the resolved identifier subject is the user UUID

  Scenario: Subject is not resolved from a refresh token
    Given identifier metadata with a refresh token for a new user
    When the subject is resolved from identifier metadata
    Then no identifier subject is resolved

  Scenario: Subject is not resolved from an expired access token
    Given identifier metadata with an expired access token for a new user
    When the subject is resolved from identifier metadata
    Then no identifier subject is resolved

  Scenario: Subject is not resolved from a token signed with another key
    Given identifier metadata with an access token signed with another key
    When the subject is resolved from identifier metadata
    Then no identifier subject is resolved

  Scenario: Subject is not resolved from a malformed token
    Given identifier metadata with header "authorization" and value "Bearer not-a-jwt"
    When the subject is resolved from identifier metadata
    Then no identifier subject is resolved

  Scenario: Subject is not resolved without an authorization header
    Given identifier metadata that is empty
    When the subject is resolved from identifier metadata
    Then no identifier subject is resolved

  Scenario: Explicit auth configuration overrides the global one
    Given identifier metadata with an access token signed with another key
    When the subject is resolved from identifier metadata using that other key configuration
    Then the resolved identifier subject is the user UUID
