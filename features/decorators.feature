Feature: Helper decorators
  As a developer
  I want reusable decorators for retrying, timing out, timing and deprecating code
  So that cross-cutting concerns stay out of my business logic

  Rule: Retry decorator

    Scenario: Function succeeding on first call is not retried
      Given a retry config with max_retries 3 and delay 0.0
      And a retry-decorated function that raises ValueError on the first 0 calls
      When the retry-decorated function is called
      Then the retry-decorated function returns "ok"
      And the retry-decorated function was invoked 1 times

    Scenario: Function recovers after transient failures
      Given a retry config with max_retries 3 and delay 0.0
      And a retry-decorated function that raises ValueError on the first 2 calls
      When the retry-decorated function is called
      Then the retry-decorated function returns "ok"
      And the retry-decorated function was invoked 3 times

    Scenario: Retries are exhausted and ResourceExhaustedError is raised
      Given a retry config with max_retries 3 and delay 0.0
      And a retry resource type "external-api"
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises ResourceExhaustedError
      And the retry-decorated function was invoked 3 times
      And the retry error carries resource type "external-api"

    Scenario: Fewer than one attempt is rejected when the decorator is applied
      Given a retry config with max_retries 0 and delay 0.0
      When the retry decorator is applied
      Then the retry decorator is rejected with InvalidArgumentError

    Scenario: A backoff below one is rejected when the decorator is applied
      Given a retry config with max_retries 3 and delay 0.0
      And a retry backoff of 0.5
      When the retry decorator is applied
      Then the retry decorator is rejected with InvalidArgumentError

    Scenario: Backoff grows the delay between attempts
      Given a retry config with max_retries 3 and delay 0.05
      And a retry backoff of 2.0
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises ResourceExhaustedError
      And the retry elapsed time is at least 0.15 seconds

    Scenario: Async functions are retried without blocking the event loop
      Given a retry config with max_retries 3 and delay 0.0
      And an async retry-decorated function that raises ValueError on the first 2 calls
      When the retry-decorated function is called
      Then the retry-decorated function returns "ok"
      And the retry-decorated function was invoked 3 times

    Scenario: Async retries are exhausted and ResourceExhaustedError is raised
      Given a retry config with max_retries 2 and delay 0.0
      And an async retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises ResourceExhaustedError
      And the retry-decorated function was invoked 2 times
      And the retry error is chained from the last ValueError raised by the function

    Scenario: Delay is applied between attempts but not after the last one
      Given a retry config with max_retries 3 and delay 0.05
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises ResourceExhaustedError
      And the retry elapsed time is at least 0.1 seconds
      And the retry elapsed time is below 0.15 seconds

    Scenario: Only errors listed in retry_on are retried
      Given a retry config with max_retries 3 and delay 0.0
      And a retry config retrying only on ValueError
      And a retry-decorated function that raises ValueError on the first 2 calls
      When the retry-decorated function is called
      Then the retry-decorated function returns "ok"
      And the retry-decorated function was invoked 3 times

    Scenario: Errors not listed in retry_on propagate immediately
      Given a retry config with max_retries 3 and delay 0.0
      And a retry config retrying only on ValueError
      And a retry-decorated function that raises KeyError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises built-in error KeyError
      And the retry-decorated function was invoked 1 times

    Scenario: Ignored errors propagate immediately
      Given a retry config with max_retries 3 and delay 0.0
      And a retry config ignoring ValueError
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises built-in error ValueError
      And the retry-decorated function was invoked 1 times

    Scenario: Ignore takes precedence over retry_on
      Given a retry config with max_retries 3 and delay 0.0
      And a retry config retrying only on ValueError
      And a retry config ignoring ValueError
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises built-in error ValueError
      And the retry-decorated function was invoked 1 times

    Scenario: Arguments are passed through and function metadata is preserved
      Given a retry config with max_retries 2 and delay 0.0
      And a retry-decorated function that raises ValueError on the first 1 calls
      When the retry-decorated function is called with arguments 3 and 4
      Then the retry-decorated function returns "ok:7"
      And the retry-decorated function keeps its name "flaky_function"

    Scenario: Exhausted retries chain the last original exception as the cause
      Given a retry config with max_retries 3 and delay 0.0
      And a retry-decorated function that raises ValueError on the first 10 calls
      When the retry-decorated function is called
      Then the retry-decorated function raises ResourceExhaustedError
      And the retry error is chained from the last ValueError raised by the function

  Rule: Timeout decorator

    Scenario: Function finishing within the timeout returns its result
      Given a timeout-decorated function that sleeps 0.01 seconds with a 1.0 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function returns "done"
      And no timeout alarm remains pending

    Scenario: Function exceeding the timeout raises DeadlineExceededError
      Given a timeout-decorated function that sleeps 1.0 seconds with a 0.05 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function raises DeadlineExceededError
      And the timeout error names operation "slow_function"
      And the timeout error has code "DEADLINE_EXCEEDED"
      And the timeout error carries timeout 0.05
      And the timeout-decorated function was interrupted before 0.5 seconds
      And no timeout alarm remains pending

    Scenario: Errors raised by the function propagate and clear the alarm
      Given a timeout-decorated function that raises ValueError with a 1.0 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function raises ValueError
      And no timeout alarm remains pending

    Scenario: Arguments are passed through and function metadata is preserved
      Given a timeout-decorated function that sleeps 0.0 seconds with a 1.0 second limit
      When the timeout-decorated function is called with arguments 5 and 6
      Then the timeout-decorated function returns "done:11"
      And the timeout-decorated function keeps its name "slow_function"

    Scenario: Fractional timeouts are supported
      Given a timeout-decorated function that sleeps 0.01 seconds with a 0.5 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function returns "done"

    Scenario: Previous SIGALRM handler is restored after a successful call
      Given a custom SIGALRM handler is installed
      And a timeout-decorated function that sleeps 0.0 seconds with a 1.0 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function returns "done"
      And the previously installed SIGALRM handler is restored
      And no timeout alarm remains pending

    Scenario: Previous SIGALRM handler is restored after a timeout
      Given a custom SIGALRM handler is installed
      And a timeout-decorated function that sleeps 1.0 seconds with a 0.05 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function raises DeadlineExceededError
      And the previously installed SIGALRM handler is restored
      And no timeout alarm remains pending

    Scenario: Previous SIGALRM handler is restored after the function raises
      Given a custom SIGALRM handler is installed
      And a timeout-decorated function that raises ValueError with a 1.0 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function raises ValueError
      And the previously installed SIGALRM handler is restored

    Scenario: Async function finishing within the timeout returns its result
      Given an async timeout-decorated function that sleeps 0.0 seconds with a 1.0 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function returns "done"

    Scenario: Async function exceeding the timeout raises DeadlineExceededError
      Given an async timeout-decorated function that sleeps 2.0 seconds with a 0.1 second limit
      When the timeout-decorated function is called
      Then the timeout-decorated function raises DeadlineExceededError
      And the timeout error names operation "slow_function"
      And the timeout-decorated function was interrupted before 1.0 seconds

    Scenario: Sync function called outside the main thread is rejected instead of running unbounded
      Given a timeout-decorated function that sleeps 0.0 seconds with a 1.0 second limit
      When the timeout-decorated function is called from a worker thread
      Then the timeout-decorated function raises FailedPreconditionError

  Rule: Timing decorator

    Scenario: Execution time is logged when root logging level is DEBUG
      Given a timing-decorated function that sleeps 0.02 seconds
      And the root logging level is DEBUG
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And one timing log message is recorded for "slow_work"
      And the timing log message reports at least 0.02 seconds

    Scenario: Nothing is logged when root logging level is not DEBUG
      Given a timing-decorated function that sleeps 0.0 seconds
      And the root logging level is WARNING
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And no timing log message is recorded

    Scenario: Arguments are passed through and function metadata is preserved
      Given a timing-decorated function that sleeps 0.0 seconds
      And the root logging level is DEBUG
      When the timing-decorated function is called with arguments 2 and 3
      Then the timing-decorated function returns "result:5"
      And the timing-decorated function keeps its name "slow_work"

    Scenario: Execution time is logged when only the timing logger is at DEBUG
      Given a timing-decorated function that sleeps 0.0 seconds
      And the root logging level is WARNING
      And the timing logger level is DEBUG
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And one timing log message is recorded for "slow_work"

    Scenario: Execution time is logged when the root logger level is unset
      Given a timing-decorated function that sleeps 0.0 seconds
      And the root logging level is NOTSET
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And one timing log message is recorded for "slow_work"

    Scenario: Nothing is logged when the timing logger is above DEBUG
      Given a timing-decorated function that sleeps 0.0 seconds
      And the root logging level is DEBUG
      And the timing logger level is INFO
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And no timing log message is recorded

    Scenario: Errors from the function propagate and the execution time is still logged
      Given a timing-decorated function that raises ValueError
      And the root logging level is DEBUG
      When the timing-decorated function is called
      Then the timing-decorated function raises ValueError
      And one timing log message is recorded for "slow_work"

    Scenario: Async function execution time is logged
      Given an async timing-decorated function that sleeps 0.02 seconds
      And the root logging level is DEBUG
      When the timing-decorated function is called
      Then the timing-decorated function returns "result"
      And one timing log message is recorded for "slow_work"
      And the timing log message reports at least 0.02 seconds

  Rule: Deprecation decorators

    Scenario: Deprecated method warns with the default message and still runs
      Given a method decorated with method_deprecation_warning without a message
      When the deprecated-warning method is called
      Then the deprecation result is "old-result"
      And exactly one DeprecationWarning was emitted
      And the deprecation warning text is "This method is deprecated and will be removed in a future version."
      And the deprecation warning points at the calling code

    Scenario: Deprecated method warns with a custom message
      Given a method decorated with method_deprecation_warning with message "use new_method instead"
      When the deprecated-warning method is called
      Then the deprecation result is "old-result"
      And exactly one DeprecationWarning was emitted
      And the deprecation warning text is "use new_method instead"

    Scenario: Deprecated method warns on every call
      Given a method decorated with method_deprecation_warning without a message
      When the deprecated-warning method is called 3 times
      Then 3 DeprecationWarnings were emitted

    Scenario: Deprecated class warns with the default message on instantiation
      Given a class decorated with class_deprecation_warning without a message
      When the deprecated-warning class is instantiated with value 42
      Then the deprecated-warning instance holds value 42
      And exactly one DeprecationWarning was emitted
      And the deprecation warning text is "This class is deprecated and will be removed in a future version."
      And the deprecation warning points at the calling code

    Scenario: Deprecated class warns with a custom message
      Given a class decorated with class_deprecation_warning with message "use NewClass instead"
      When the deprecated-warning class is instantiated with value 1
      Then exactly one DeprecationWarning was emitted
      And the deprecation warning text is "use NewClass instead"

    Scenario: Deprecated classes keep their constructor metadata
      Given a class decorated with class_deprecation_warning without a message
      And a class decorated with class_deprecation_error with operation "OldThing" and language EN
      Then the warning class constructor keeps its docstring
      And the error class constructor keeps its docstring

    Scenario: Deprecated method raises DeprecationError in English by default
      Given a method decorated with method_deprecation_error without arguments
      When the deprecated-error method is called
      Then the deprecated-error method body did not run
      And a DeprecationError is raised
      And the deprecation error code is "DEPRECATED_FEATURE"
      And the deprecation error names feature "legacy_method"
      And the deprecation error message is "This feature is deprecated and should no longer be used"

    Scenario: Deprecated method raises DeprecationError with custom operation and language
      Given a method decorated with method_deprecation_error with operation "OldApi.call" and language FA
      When the deprecated-error method is called
      Then a DeprecationError is raised
      And the deprecation error names feature "OldApi.call"
      And the deprecation error message is "این ویژگی منسوخ شده و دیگر نباید استفاده شود"

    Scenario: Deprecated class raises DeprecationError in Persian by default
      Given a class decorated with class_deprecation_error without arguments
      When the deprecated-error class is instantiated
      Then a DeprecationError is raised
      And the deprecation error names feature "LegacyClass"
      And the deprecation error message is "این ویژگی منسوخ شده و دیگر نباید استفاده شود"

    Scenario: Deprecated class raises DeprecationError with custom operation and language
      Given a class decorated with class_deprecation_error with operation "OldThing" and language EN
      When the deprecated-error class is instantiated
      Then a DeprecationError is raised
      And the deprecation error names feature "OldThing"
      And the deprecation error message is "This feature is deprecated and should no longer be used"

  Rule: Renamed decorators keep their old names working

    Scenario Outline: Old name <old> still works and warns once pointing at <new>
      When the old decorator name "<old>" is applied
      Then exactly one DeprecationWarning should name "<new>"
      And the DeprecationWarning should point at the calling code

      Examples:
        | old                                         | new                         |
        | retry_decorator                             | retry                       |
        | timeout_decorator                           | timeout                     |
        | timing_decorator                            | timing                      |
        | singleton_decorator                         | singleton                   |
        | ttl_cache_decorator                         | ttl_cache                   |
        | grpc_rate_limit_decorator                   | grpc_rate_limit             |
        | sqlalchemy_atomic_decorator                 | sqlalchemy_atomic           |
        | postgres_sqlalchemy_atomic_decorator        | postgres_sqlalchemy_atomic  |
        | mysql_sqlalchemy_atomic_decorator           | mysql_sqlalchemy_atomic     |
        | sqlite_sqlalchemy_atomic_decorator          | sqlite_sqlalchemy_atomic    |
        | starrocks_sqlalchemy_atomic_decorator       | starrocks_sqlalchemy_atomic |
        | async_postgres_sqlalchemy_atomic_decorator  | postgres_sqlalchemy_atomic  |
        | async_mysql_sqlalchemy_atomic_decorator     | mysql_sqlalchemy_atomic     |
        | async_sqlite_sqlalchemy_atomic_decorator    | sqlite_sqlalchemy_atomic    |
        | async_starrocks_sqlalchemy_atomic_decorator | starrocks_sqlalchemy_atomic |

    Scenario Outline: New name <new> is exported without a warning
      When the new decorator name "<new>" is imported from the decorators package
      Then it should be a function and not a module
      And no DeprecationWarning should have been emitted

      Examples:
        | new             |
        | retry           |
        | timeout         |
        | timing          |
        | singleton       |
        | ttl_cache       |
        | grpc_rate_limit |

    Scenario Outline: Moved name <name> still resolves from the decorators package and warns
      When the new decorator name "<name>" is imported from the decorators package
      Then it should be a function and not a module
      And exactly one DeprecationWarning should name "archipy.adapters.base.sqlalchemy.atomic.<name>"
      And the DeprecationWarning should point at the calling code

      Examples:
        | name                        |
        | sqlalchemy_atomic           |
        | postgres_sqlalchemy_atomic  |
        | mysql_sqlalchemy_atomic     |
        | sqlite_sqlalchemy_atomic    |
        | starrocks_sqlalchemy_atomic |

    Scenario Outline: Name <name> is exported from the adapters module without a warning
      When the decorator name "<name>" is imported from the module "archipy.adapters.base.sqlalchemy.atomic"
      Then it should be a function and not a module
      And no DeprecationWarning should have been emitted

      Examples:
        | name                        |
        | sqlalchemy_atomic           |
        | postgres_sqlalchemy_atomic  |
        | mysql_sqlalchemy_atomic     |
        | sqlite_sqlalchemy_atomic    |
        | starrocks_sqlalchemy_atomic |

    Scenario Outline: Old module path <module> still exports <name>
      When "<name>" is imported from the old module path "<module>"
      Then the old module path should resolve to a callable

      Examples:
        | module            | name                                 |
        | retry             | retry_decorator                      |
        | timeout           | timeout_decorator                    |
        | timing            | timing_decorator                     |
        | singleton         | singleton_decorator                  |
        | cache             | ttl_cache_decorator                  |
        | grpc_rate_limit   | grpc_rate_limit_decorator            |
        | sqlalchemy_atomic | postgres_sqlalchemy_atomic_decorator |
        | sqlalchemy_atomic | _handle_db_exception                 |

    Scenario Outline: Deprecated KeycloakUtils method <name> warns and builds the same guard
      When the deprecated KeycloakUtils method "<name>" is called
      Then exactly one DeprecationWarning should name "<replacement>"
      And the Keycloak auth result is callable

      Examples:
        | name               | replacement  |
        | async_fastapi_auth | fastapi_auth |
        | async_grpc_auth    | grpc_auth    |

    Scenario Outline: Old path name <name> still resolves and warns
      When "<name>" is read from the old Keycloak utils module
      Then exactly one DeprecationWarning should name "<replacement>"
      And the Keycloak auth result is callable

      Examples:
        | name                        | replacement                                                |
        | AuthContextManager          | archipy.adapters.keycloak.auth.AuthContextManager          |
        | clear_keycloak_remote_cache | archipy.adapters.keycloak.auth.clear_keycloak_remote_cache |

    Scenario: The legacy KeycloakUtils namespace keeps its methods
      When "KeycloakUtils" is read from the old Keycloak utils module
      Then exactly one DeprecationWarning should name "the functions of archipy.adapters.keycloak.auth"
      And the legacy KeycloakUtils exposes fastapi_auth, async_fastapi_auth, grpc_auth and async_grpc_auth
