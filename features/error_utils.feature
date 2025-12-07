Feature: Error Utilities

  Scenario: Capture an error
    Given a raised error "ValueError" with message "Something went wrong"
    When the error is captured
    Then it should be logged

  Scenario: Create an error detail
    Given an error with code "ERR001", English message "Invalid data", and Persian message "داده نامعتبر"
    When an error detail is created
    Then the response should contain code "ERR001"

  Scenario: Handle a FastAPI error
    Given a FastAPI error "BaseError"
    When an async FastAPI error is handled
    Then the response should have an HTTP status of 500

  Scenario: Handle a gRPC error
    Given a gRPC error "BaseError"
    When gRPC error is handled
    Then the response should have gRPC status "INTERNAL"

  Scenario: Generate FastAPI error responses
    Given a list of FastAPI errors ["InvalidPhoneNumberError", "NotFoundError"]
    When the FastAPI error responses are generated
    Then the responses should contain HTTP status codes
