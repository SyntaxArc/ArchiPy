Feature: TOTPUtils functionality

  Scenario: Generate TOTP with valid secret
    Given a valid secret "12345678901234567890"
    When a TOTP is generated
    Then a TOTP code is returned
    And an expiration time is provided

  Scenario: Verify TOTP with valid code
    Given a valid secret "12345678901234567890"
    And a TOTP code is generated
    When the TOTP code is verified
    Then the verification should succeed

  Scenario: Verify TOTP with invalid code
    Given a valid secret "12345678901234567890"
    And an invalid TOTP code "000000"
    When the invalid TOTP code is verified
    Then the verification should fail

  Scenario: Generate secret key
    When a secret key is generated
    Then a secret key is returned

  Scenario: Reject a code shorter than the configured length
    Given a valid secret "12345678901234567890"
    When the TOTP code "5" is checked
    Then the code check reports not valid

  Scenario: Reject a code longer than the configured length
    Given a valid secret "12345678901234567890"
    When the TOTP code "00000000" is checked
    Then the code check reports not valid

  Scenario: Reject a code written with non-ASCII digits
    Given a valid secret "12345678901234567890"
    When the TOTP code "٣٣٣٣٣٣" is checked
    Then the code check raises InvalidTokenError

  Scenario Outline: RFC 6238 vector is produced for raw and base32 secrets
    Given a valid secret "<secret>"
    And the current epoch time is 59
    When a TOTP is generated
    Then the TOTP code is "287082"
    And the TOTP code verifies

    Examples:
      | secret                           |
      | 12345678901234567890             |
      | GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ |

  Scenario: A secret produced by the generator round-trips
    When a secret key is generated
    And a TOTP is generated from the generated secret key
    Then the TOTP code verifies

  Scenario: A replay guard accepts a code the first time it is used
    Given a valid secret "12345678901234567890"
    And a TOTP code is generated
    And a replay guard that remembers used time steps
    When the TOTP code is verified with the replay guard
    Then the verification should succeed
    And the replay guard was asked about 1 time step

  Scenario: A replay guard rejects a code that was already used
    Given a valid secret "12345678901234567890"
    And a TOTP code is generated
    And a replay guard that remembers used time steps
    When the TOTP code is verified with the replay guard
    And the TOTP code is verified with the replay guard
    Then the verification should fail
    And the replay guard was asked about 2 time steps

  Scenario: A replay guard is not consulted for an invalid code
    Given a valid secret "12345678901234567890"
    And an invalid TOTP code "000000"
    And a replay guard that remembers used time steps
    When the invalid TOTP code is verified with the replay guard
    Then the verification should fail
    And the replay guard was asked about 0 time steps

  Scenario: The reported expiry never outlives the verification window
    Given a valid secret "12345678901234567890"
    When a TOTP is generated
    Then the expiration is no later than the verification window allows

  Scenario: Generating a secret key without a configured master key raises InvalidArgumentError
    When a secret key is generated without a TOTP master key
    Then the secret key generation raises InvalidArgumentError
