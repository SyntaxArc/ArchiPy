Feature: FastAPI Error Handling

  Background:
    Given a FastAPI test application

  Scenario Outline: FastAPI handles custom BaseError exceptions
    When an endpoint raises "<error_type>" error
    Then the response should have HTTP status code <http_status>
    And the response should contain error code "<error_code>"
    And the response should contain message "<expected_message>"
    And the response JSON should have structure with "error" and "detail" keys

    Examples:
      | error_type           | http_status | error_code       | expected_message               |
      | NotFoundError        | 404         | NOT_FOUND        | Requested resource not found   |
      | InvalidArgumentError | 400         | INVALID_ARGUMENT | Invalid argument provided      |
      | UnauthenticatedError | 401         | UNAUTHENTICATED  | not authorized                 |
      | InternalError        | 500         | INTERNAL_ERROR   | Internal system error occurred |

  Scenario Outline: FastAPI handles validation errors from Pydantic
    When an endpoint receives invalid request data "<invalid_data_description>"
    Then the response should have HTTP status code 422
    And the response should contain error code "VALIDATION_ERROR"
    And the response detail should contain "field"

    Examples:
      | invalid_data_description |
      | missing required field   |
      | invalid field type       |
      | out of range value       |

  Scenario: FastAPI handles unexpected exceptions
    When an endpoint raises an unexpected exception
    Then the response should have HTTP status code 500
    And the response should contain error code "UNKNOWN_ERROR"

  Scenario Outline: FastAPI error response format verification
    When an endpoint raises "<error_type>" error
    Then the response JSON should have "error" key with value "<error_code>"
    And the response JSON "detail" should contain "code" with value "<error_code>"
    And the response JSON "detail" should contain "message" key
    And the response JSON "detail" should contain "http_status" with value <http_status>
    And the response JSON "detail" should contain "grpc_status" key

    Examples:
      | error_type           | error_code       | http_status |
      | NotFoundError        | NOT_FOUND        | 404         |
      | InvalidArgumentError | INVALID_ARGUMENT | 400         |

  Scenario Outline: FastAPI error message localization
    When an endpoint raises "<error_type>" error with language "<lang>"
    Then the response message should be in "<lang>" language
    And the message should match the expected "<lang>" message

    Examples:
      | error_type           | lang |
      | NotFoundError        | EN   |
      | NotFoundError        | FA   |
      | InvalidArgumentError | EN   |
      | InvalidArgumentError | FA   |

  Scenario: FastAPI error with additional data
    When an endpoint raises an error with additional data
    Then the response detail should contain the additional data fields

  Scenario Outline: FastAPI handles validation errors for phone number, email, and national code
    When an endpoint raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the response should have HTTP status code 400
    And the response should contain error code "<error_code>"
    And the response message should contain "<expected_message_part>"

    Examples:
      | error_type              | invalid_value   | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError | 08123456789     | INVALID_PHONE         | شماره تلفن همراه     | FA   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError       | invalid-email   | INVALID_EMAIL         | فرمت ایمیل           | FA   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError| 1234567890      | INVALID_NATIONAL_CODE | کد ملی                | FA   |
