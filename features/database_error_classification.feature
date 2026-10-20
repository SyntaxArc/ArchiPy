@unit
Feature: Database driver error classification
  Driver errors are mapped to domain errors by their error code (SQLSTATE, MySQL errno, SQLite name) instead of by
  message text, and the driver detail is logged once when the domain error is raised.

  Scenario Outline: Driver error codes map to domain errors
    Given a "<family>" driver error with code "<code>" and message "<message>"
    When the driver error is classified
    Then the domain error should be "<domain_error>"

    Examples:
      | family    | code        | message                                                                                                                                                 | domain_error                   |
      | postgres  | 40001       | could not serialize access                                                                                                                              | DatabaseSerializationError     |
      | postgres  | 40P01       | deadlock detected                                                                                                                                       | DatabaseDeadlockError          |
      | postgres  | 57014       | canceling statement due to statement timeout                                                                                                            | DatabaseTimeoutError           |
      | postgres  | 23505       | duplicate key value                                                                                                                                     | DatabaseConstraintError        |
      | postgres  | 23502       | null value in column                                                                                                                                    | DatabaseIntegrityError         |
      | postgres  | 08006       | connection failure                                                                                                                                      | DatabaseConnectionError        |
      | postgres  | 53200       | out of memory                                                                                                                                           | DatabaseResourceExhaustedError |
      | postgres  | 42703       | column does not exist                                                                                                                                   | none                           |
      | mysql     | 1213        | Deadlock found                                                                                                                                          | DatabaseDeadlockError          |
      | mysql     | 1205        | Lock wait timeout exceeded                                                                                                                              | DatabaseTimeoutError           |
      | mysql     | 1062        | Duplicate entry                                                                                                                                         | DatabaseConstraintError        |
      | mysql     | 2013        | Lost connection to server                                                                                                                               | DatabaseConnectionError        |
      | mysql     | 1041        | Out of memory                                                                                                                                           | DatabaseResourceExhaustedError |
      | starrocks | 1064        | Memory of process exceed limit. try consume:1342177280 Backend: 10.0.10.45, Used: 51805246184, Limit: 54611626843. Mem usage has exceed the limit of BE | DatabaseResourceExhaustedError |
      | starrocks | 1064        | Memory limit exceeded                                                                                                                                   | DatabaseResourceExhaustedError |
      | starrocks | 1064        | You have an error in your SQL syntax                                                                                                                    | none                           |
      | starrocks | 1064        | You have an error in your SQL syntax near 'out of memory'                                                                                               | none                           |
      | sqlite    | SQLITE_BUSY | database is locked                                                                                                                                      | DatabaseDeadlockError          |

  Scenario: The driver error code is read from the cause of an adapted driver error
    Given an adapted driver error whose cause has SQLSTATE "40001"
    When the driver error is classified
    Then the domain error should be "DatabaseSerializationError"

  Scenario Outline: The database adapter handler raises the classified domain error and logs the driver detail
    Given a "<family>" driver error with code "<code>" and message "<message>"
    When the adapter exception handler processes the driver error
    Then the raised error should be "<domain_error>"
    And the original driver error should be its cause
    And a "<level>" log record should mention code "<code>"

    Examples:
      | family    | code  | message                        | domain_error                   | level   |
      | postgres  | 40001 | could not serialize access     | DatabaseSerializationError     | WARNING |
      | postgres  | 23505 | duplicate key value            | DatabaseConstraintError        | ERROR   |
      | starrocks | 1064  | Memory of process exceed limit | DatabaseResourceExhaustedError | WARNING |
      | starrocks | 1064  | syntax error                   | DatabaseQueryError             | ERROR   |

  Scenario: Messages without a driver code still use the message fallback
    Given a plain exception with message "connection reset by peer"
    When the adapter exception handler processes the driver error
    Then the raised error should be "DatabaseConnectionError"

  Scenario: Resource exhaustion maps to HTTP 503 and gRPC RESOURCE_EXHAUSTED
    Given the DatabaseResourceExhaustedError type
    Then its HTTP status should be 503 and its gRPC status should be 8

  Scenario Outline: Classified errors can still be caught as DatabaseQueryError
    Given the <domain_error> type
    Then it should be a subclass of DatabaseQueryError

    Examples:
      | domain_error                   |
      | DatabaseConnectionError        |
      | DatabaseTimeoutError           |
      | DatabaseConstraintError        |
      | DatabaseIntegrityError         |
      | DatabaseDeadlockError          |
      | DatabaseSerializationError     |
      | DatabaseResourceExhaustedError |
