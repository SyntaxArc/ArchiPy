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
      | postgres  | 40003       | statement completion unknown                                                                                                                            | DatabaseUnknownOutcomeError    |
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

  Scenario Outline: MySQL-family server errors are classified by errno even when the driver sets a SQLSTATE
    Given a <family> server error with errno "<errno>", SQLSTATE "<sqlstate>" and message "<message>"
    When the driver error is classified
    Then the domain error should be "<domain_error>"

    Examples:
      | family    | errno | sqlstate | message                        | domain_error                   |
      | mysql     | 1213  | 40001    | Deadlock found                 | DatabaseDeadlockError          |
      | mysql     | 1205  | HY000    | Lock wait timeout exceeded     | DatabaseTimeoutError           |
      | mysql     | 1062  | 23000    | Duplicate entry                | DatabaseConstraintError        |
      | mysql     | 1452  | 23000    | Cannot add or update a child   | DatabaseConstraintError        |
      | mysql     | 1040  | 08004    | Too many connections           | DatabaseResourceExhaustedError |
      | starrocks | 1064  | 42000    | Memory of process exceed limit | DatabaseResourceExhaustedError |
      | starrocks | 1064  | 42000    | You have an error in your SQL  | none                           |

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
      | DatabaseUnknownOutcomeError    |

  Scenario: A disconnect flagged by SQLAlchemy without a driver code is a connection error
    Given a driver error without a code that SQLAlchemy flagged as a disconnect
    When the driver error is classified
    Then the domain error should be "DatabaseConnectionError"

  Scenario Outline: Only transient database errors are marked retryable
    Given the <domain_error> type
    Then its retryable flag should be <retryable>

    Examples:
      | domain_error                   | retryable |
      | DatabaseSerializationError     | true      |
      | DatabaseDeadlockError          | true      |
      | DatabaseResourceExhaustedError | true      |
      | DatabaseUnknownOutcomeError    | false     |
      | DatabaseConstraintError        | false     |
      | DatabaseQueryError             | false     |

  Scenario: Logged statements carry no literal values
    Given a "postgres" driver error with code "23505" raised by statement "INSERT INTO users (name, age) VALUES ('bob''s', 42) WHERE id = 7"
    When the adapter exception handler processes the driver error at DEBUG level
    Then the logged statement should be "INSERT INTO users (name, age) VALUES (?, ?) WHERE id = ?"
