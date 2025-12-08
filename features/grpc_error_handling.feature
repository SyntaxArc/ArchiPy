Feature: gRPC Error Handling

  Background:
    Given a gRPC test server

  Scenario Outline: Sync gRPC handles custom BaseError exceptions
    When a sync gRPC method raises "<error_type>" error
    Then the gRPC call should fail with status code <grpc_status>
    And the error message should contain "<expected_message>"
    And the gRPC error code should be "<error_code>"

    Examples:
      | error_type           | grpc_status | error_code       | expected_message               |
      | NotFoundError        | 5           | NOT_FOUND        | Requested resource not found   |
      | InvalidArgumentError | 3           | INVALID_ARGUMENT | Invalid argument provided      |
      | UnauthenticatedError | 16          | UNAUTHENTICATED  | not authorized                 |
      | InternalError        | 13          | INTERNAL_ERROR   | Internal system error occurred |

  @async
  Scenario Outline: Async gRPC handles custom BaseError exceptions
    When an async gRPC method raises "<error_type>" error
    Then the gRPC call should fail with status code <grpc_status>
    And the error message should contain "<expected_message>"
    And the gRPC error code should be "<error_code>"

    Examples:
      | error_type           | grpc_status | error_code       | expected_message               |
      | NotFoundError        | 5           | NOT_FOUND        | Requested resource not found   |
      | InvalidArgumentError | 3           | INVALID_ARGUMENT | Invalid argument provided      |
      | UnauthenticatedError | 16          | UNAUTHENTICATED  | not authorized                 |
      | InternalError        | 13          | INTERNAL_ERROR   | Internal system error occurred |

  Scenario: Sync gRPC handles validation errors
    When a sync gRPC method receives invalid request
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "INVALID_ARGUMENT"
    And the error should contain validation error details

  @async
  Scenario: Async gRPC handles validation errors
    When an async gRPC method receives invalid request
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "INVALID_ARGUMENT"
    And the error should contain validation error details

  Scenario: Sync gRPC handles unexpected exceptions
    When a sync gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error code should be "INTERNAL_ERROR"

  @async
  Scenario: Async gRPC handles unexpected exceptions
    When an async gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error code should be "INTERNAL_ERROR"

  Scenario Outline: gRPC error trailing metadata
    When a gRPC method raises "<error_type>" error with additional data
    Then the gRPC call should fail
    And the trailing metadata should contain "additional_data" key
    And the trailing metadata "additional_data" should be valid JSON

    Examples:
      | error_type           |
      | NotFoundError        |
      | InvalidArgumentError |

  Scenario Outline: gRPC error message verification
    When a gRPC method raises "<error_type>" error
    Then the error message should match the error's get_message() result

    Examples:
      | error_type           |
      | NotFoundError        |
      | InvalidArgumentError |
      | UnauthenticatedError |

  Scenario Outline: Sync gRPC handles validation errors for phone number, email, and national code
    When a sync gRPC method raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "<error_code>"
    And the error message should contain "<expected_message_part>"

    Examples:
      | error_type              | invalid_value   | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | شماره تلفن همراه     | FA   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | فرمت ایمیل           | FA   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | کد ملی                | FA   |

  @async
  Scenario Outline: Async gRPC handles validation errors for phone number, email, and national code
    When an async gRPC method raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "<error_code>"
    And the error message should contain "<expected_message_part>"

    Examples:
      | error_type              | invalid_value   | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | شماره تلفن همراه     | FA   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | فرمت ایمیل           | FA   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | کد ملی                | FA   |
