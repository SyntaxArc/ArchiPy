Feature: Password Utilities

  Scenario: Hash a password successfully
    Given a password "SecureP@ss123"
    When the password is hashed
    Then a hashed password should be returned

  Scenario: Verify a correct password
    Given a password "SecureP@ss123"
    And the password is hashed
    When the password is verified
    Then the verification should succeed

  Scenario: Verify an incorrect password
    Given a password "SecureP@ss123"
    And the password is hashed
    When a different password "WrongPass123" is verified
    Then the verification should fail

  Scenario: Validate a strong password
    Given a password "StrongP@ssword1!"
    When the password is validated
    Then the password validation should succeed

  Scenario: Fail validation on a weak password
    Given a password "weak"
    When the password is validated
    Then the password validation should fail

  Scenario: Generate a secure password
    When a secure password is generated
    Then the generated password should meet security requirements

  Scenario: Prevent reusing an old password
    Given a password history containing "OldP@ssword1"
    When a user attempts to reuse "OldP@ssword1" as a new password
    Then the password validation should fail with an error message

  Scenario: Hashes record their own algorithm and iteration count
    Given a password "SecureP@ss123"
    When the password is hashed
    Then the stored hash uses the "pbkdf2_sha256" scheme with the configured iteration count

  Scenario: A hash still verifies after the iteration setting changes
    Given a password "SecureP@ss123"
    And the password is hashed
    When the password is verified with the iteration setting changed to 1000
    Then the verification should succeed

  Scenario: A legacy hash written without a scheme prefix still verifies
    Given a password "SecureP@ss123"
    And the password is hashed in the legacy format with the configured iteration count
    When the password is verified
    Then the verification should succeed

  Scenario: A legacy hash written with the former default iteration count still verifies
    Given a password "SecureP@ss123"
    And the password is hashed in the legacy format with 100000 iterations
    When the password is verified
    Then the verification should succeed

  Scenario: A legacy hash does not verify a different password
    Given a password "SecureP@ss123"
    And the password is hashed in the legacy format with the configured iteration count
    When a different password "WrongPass123" is verified
    Then the verification should fail

  Scenario Outline: Malformed stored hashes are rejected without raising
    Given a password "SecureP@ss123"
    And a stored hash "<stored>"
    When the password is verified
    Then the verification should fail

    Examples:
      | stored                              |
      | pbkdf2_sha256$abc$AAAA$AAAA         |
      | pbkdf2_sha256$0$AAAA$AAAA           |
      | pbkdf2_sha256$1000$AAAA             |
      | pbkdf2_sha256$1000$not base64!$AAAA |
      | not-a-hash                          |

  Scenario: A history size of zero disables the history check
    Given a password history containing "OldP@ssword1"
    And the password history size is 0
    When a user attempts to reuse "OldP@ssword1" as a new password
    Then the password validation should succeed

  Scenario: A negative password history size is rejected by the configuration
    When an authentication configuration is built with a password history size of -1
    Then the configuration is rejected
