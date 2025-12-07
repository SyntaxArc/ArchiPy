Feature: Base Utilities

  Scenario Outline: Sanitize Iranian phone and landline numbers
    Given an input phone number "<input_number>"
    When the phone number is sanitized
    Then the sanitized output should be "<expected_output>"

    Examples:
      | input_number | expected_output |
      | +989123456789 | 09123456789 |
      | 00989123456789 | 09123456789 |
      | 912-345-6789 | 09123456789 |
      | 021-12345678 | 02112345678 |

  Scenario: Validate a correct Iranian mobile number
    Given a valid mobile phone number "09123456789"
    When the phone number is validated
    Then the validation should succeed

  Scenario: Validate an invalid Iranian mobile number
    Given an invalid mobile phone number "08123456789"
    When the phone number validation is attempted
    Then an error message "شماره تلفن همراه ایران نامعتبر است: ۰۸۱۲۳۴۵۶۷۸۹" should be raised

  Scenario: Validate a correct Iranian landline number
    Given a valid landline phone number "02112345678"
    When the landline number is validated
    Then the validation should succeed

  Scenario: Validate an incorrect Iranian landline number
    Given an invalid landline phone number "04123"
    When the landline number validation is attempted
    Then an error message "شماره تلفن ثابت ایران نامعتبر است: ۰۴۱۲۳" should be raised

  Scenario: Validate a correct Iranian national code
    Given a valid national code "1234567891"
    When the national code is validated
    Then the validation should succeed

  Scenario: Validate an incorrect Iranian national code
    Given an invalid national code "1234567890"
    When the national code validation is attempted
    Then an error message "فرمت کد ملی وارد شده اشتباه است: ۱۲۳۴۵۶۷۸۹۰" should be raised
