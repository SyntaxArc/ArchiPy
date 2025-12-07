Feature: Custom Errors Handling

  Scenario Outline: Verify error message type details
    Given an error type "<error_enum>"
    Then the error code should be "<expected_code>"
    And the English message should be "<expected_message_en>"
    And the Persian message should be "<expected_message_fa>"

    Examples:
      | error_enum              | expected_code      | expected_message_en                     | expected_message_fa                          |
      | INVALID_PHONE           | INVALID_PHONE     | Invalid Iranian phone number: 09123456789 | شماره تلفن همراه ایران نامعتبر است: ۰۹۱۲۳۴۵۶۷۸۹ |
      | NOT_FOUND               | NOT_FOUND        | Requested resource not found: resource_type | منبع درخواستی یافت نشد: resource_type |
      | TOKEN_EXPIRED           | TOKEN_EXPIRED    | Authentication token has expired        | توکن احراز هویت منقضی شده است.              |

  Scenario Outline: Verify HTTP and gRPC status codes in error messages
    Given an error type "<error_enum>"
    Then the HTTP status should be <http_status>
    And the gRPC status should be <grpc_status>

    Examples:
      | error_enum              | http_status  | grpc_status  |
      | INVALID_PHONE           | 400         | 3            |
      | NOT_FOUND               | 404         | 5            |
      | TOKEN_EXPIRED           | 401         | 16           |
