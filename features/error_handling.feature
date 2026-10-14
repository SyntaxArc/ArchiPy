@unit @grpc
Feature: Error Handling

  Background:
    Given a FastAPI test application
    And a gRPC test server

  @unit
  Scenario Outline: Verify error message type details
    Given an error type "<error_enum>"
    Then the error code should be "<expected_code>"
    And the English message should be "<expected_message_en>"
    And the Persian message should be "<expected_message_fa>"

    Examples:
      | error_enum    | expected_code | expected_message_en                         | expected_message_fa                             |
      | INVALID_PHONE | INVALID_PHONE | Invalid Iranian phone number: 09123456789   | شماره تلفن همراه ایران نامعتبر است: ۰۹۱۲۳۴۵۶۷۸۹ |
      | NOT_FOUND     | NOT_FOUND     | Requested resource not found: resource_type | منبع درخواستی یافت نشد: resource_type           |
      | TOKEN_EXPIRED | TOKEN_EXPIRED | Authentication token has expired            | توکن احراز هویت منقضی شده است.                  |

  @unit
  Scenario Outline: Verify HTTP and gRPC status codes in error messages
    Given an error type "<error_enum>"
    Then the HTTP status should be <http_status>
    And the gRPC status should be <grpc_status>

    Examples:
      | error_enum    | http_status | grpc_status |
      | INVALID_PHONE | 400         | 3           |
      | NOT_FOUND     | 404         | 5           |
      | TOKEN_EXPIRED | 401         | 16          |

  @unit
  Scenario: Create an error detail
    Given an error with code "ERR001", English message "Invalid data", and Persian message "داده نامعتبر"
    When an error detail is created
    Then the response should contain code "ERR001"

  @unit
  Scenario: Capture an error
    Given a raised error "ValueError" with message "Something went wrong"
    When the error is captured
    Then it should be logged

  @unit
  Scenario: Public error constructors stay inspectable at runtime
    When I inspect constructors of public BaseError subclasses
    Then all constructor signatures resolve without NameError

  # === FastAPI Error Handling ===
  @fastapi
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

  @fastapi
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

  @fastapi
  Scenario: FastAPI handles unexpected exceptions
    When an endpoint raises an unexpected exception
    Then the response should have HTTP status code 500
    And the response should contain error code "UNKNOWN_ERROR"

  @fastapi
  Scenario: FastAPI validation errors do not echo the rejected input
    When an endpoint receives invalid request data "invalid field type"
    Then the response should have HTTP status code 422
    And the response body should not contain "not_a_number"

  @fastapi
  Scenario: FastAPI unexpected exceptions are logged with the real cause and hidden from the client
    When an endpoint raises an unexpected exception while errors are captured
    Then the response should have HTTP status code 500
    And the response body should not contain "Unexpected error"
    And the captured error log should hold a "ValueError" with message "Unexpected error"

  @fastapi
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

  @fastapi
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

  @fastapi
  Scenario: FastAPI error with additional data
    When an endpoint raises an error with additional data
    Then the response detail should contain the additional data fields

  @fastapi @validation
  Scenario Outline: FastAPI handles validation errors for phone number, email, and national code
    When an endpoint raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the response should have HTTP status code 400
    And the response should contain error code "<error_code>"
    And the response message should contain "<expected_message_part>"

    Examples:
      | error_type               | invalid_value | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | شماره تلفن همراه      | FA   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | فرمت ایمیل            | FA   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | کد ملی                | FA   |

  # === gRPC Error Handling ===
  @grpc
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

  @grpc @async
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

  @grpc
  Scenario: Sync gRPC reports a ValidationError raised by the handler as INVALID_ARGUMENT
    When a sync gRPC method receives invalid request
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "INVALID_ARGUMENT"

  @grpc @async
  Scenario: Async gRPC reports a ValidationError raised by the handler as INVALID_ARGUMENT
    When an async gRPC method receives invalid request
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "INVALID_ARGUMENT"

  @grpc
  Scenario Outline: A ValidationError raised by the handler is INVALID_ARGUMENT and hides the input
    Given a <mode> gRPC server using the exception interceptor stack
    When a unary RPC whose handler raises a validation error is invoked
    Then the gRPC unary call should fail with status INVALID_ARGUMENT
    And the gRPC unary failure should not expose "secret-client-value"

    Examples: Sync interceptor
      | mode |
      | sync |

    @async
    Examples: Async interceptor
      | mode  |
      | async |

  @grpc
  Scenario Outline: A ValidationError inside request_validation is reported as INVALID_ARGUMENT
    Given a <mode> gRPC server using the exception interceptor stack
    When a unary RPC whose handler validates the request is invoked
    Then the gRPC unary call should fail with status INVALID_ARGUMENT
    And the gRPC unary failure should not expose "secret-client-value"

    Examples: Sync interceptor
      | mode |
      | sync |

    @async
    Examples: Async interceptor
      | mode  |
      | async |

  @grpc
  Scenario Outline: The internal flag reports every ValidationError as INTERNAL
    Given a <mode> gRPC server using the internal-validation interceptor stack
    When a unary RPC whose handler raises a validation error is invoked
    Then the gRPC unary call should fail with status INTERNAL
    And the gRPC unary failure should not expose "secret-client-value"

    Examples: Sync interceptor
      | mode |
      | sync |

    @async
    Examples: Async interceptor
      | mode  |
      | async |

  @grpc
  Scenario: Sync gRPC handles unexpected exceptions
    When a sync gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error code should be "INTERNAL_ERROR"

  @grpc @async
  Scenario: Async gRPC handles unexpected exceptions
    When an async gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error code should be "INTERNAL_ERROR"

  @grpc
  Scenario: Sync gRPC does not expose internal failure details to the client
    When a sync gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error should not expose the internal failure

  @grpc @async
  Scenario: Async gRPC does not expose internal failure details to the client
    When an async gRPC method raises an unexpected exception
    Then the gRPC call should fail with status code 13
    And the gRPC error should not expose the internal failure

  @unit
  Scenario Outline: gRPC abort serializes additional data that is not plain JSON
    When a <mode> gRPC context is aborted with an error holding a UUID, a datetime and a Decimal
    Then the context should be aborted with status code 13
    And the aborted context trailing metadata "additional_data" should be valid JSON

    Examples:
      | mode  |
      | sync  |
      | async |

  @unit
  Scenario Outline: gRPC abort replaces oversized additional data with a marker
    When a <mode> gRPC context is aborted with an error holding 100000 characters of additional data
    Then the context should be aborted with status code 13
    And the aborted context trailing metadata "additional_data" should be the truncation marker

    Examples:
      | mode  |
      | sync  |
      | async |

  @grpc
  Scenario Outline: gRPC error trailing metadata
    When a gRPC method raises "<error_type>" error with additional data
    Then the gRPC call should fail
    And the trailing metadata should contain "additional_data" key
    And the trailing metadata "additional_data" should be valid JSON

    Examples:
      | error_type           |
      | NotFoundError        |
      | InvalidArgumentError |

  @grpc
  Scenario Outline: gRPC error message verification
    When a gRPC method raises "<error_type>" error
    Then the error message should match the error's get_message() result

    Examples:
      | error_type           |
      | NotFoundError        |
      | InvalidArgumentError |
      | UnauthenticatedError |

  @grpc @validation
  Scenario Outline: Sync gRPC handles validation errors for phone number, email, and national code
    When a sync gRPC method raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "<error_code>"
    And the error message should contain "<expected_message_part>"

    Examples:
      | error_type               | invalid_value | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | شماره تلفن همراه      | FA   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | فرمت ایمیل            | FA   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | کد ملی                | FA   |

  @grpc @async @validation
  Scenario Outline: Async gRPC handles validation errors for phone number, email, and national code
    When an async gRPC method raises "<error_type>" validation error with value "<invalid_value>" in language "<lang>"
    Then the gRPC call should fail with status code 3
    And the gRPC error code should be "<error_code>"
    And the error message should contain "<expected_message_part>"

    Examples:
      | error_type               | invalid_value | error_code            | expected_message_part | lang |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | Invalid Iranian phone | EN   |
      | InvalidPhoneNumberError  | 08123456789   | INVALID_PHONE         | شماره تلفن همراه      | FA   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | Invalid email format  | EN   |
      | InvalidEmailError        | invalid-email | INVALID_EMAIL         | فرمت ایمیل            | FA   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | Invalid national code | EN   |
      | InvalidNationalCodeError | 1234567890    | INVALID_NATIONAL_CODE | کد ملی                | FA   |
