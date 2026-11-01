Feature: SQLAlchemy Atomic Transactions on SQLite

  Scenario Outline: Create and retrieve entity in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an atomic transaction
    Then the entity should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Handle transaction rollback on exception
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity creation fails within an atomic transaction
    Then no entity should exist in the database
    And the database session should remain usable

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Support nested atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When nested atomic transactions are executed
    Then operations from successful nested transactions should be visible within outer transaction
    And operations from failed nested transactions should be rolled back

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Update entities in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    And an entity exists in the database
    When the entity is updated within an atomic transaction
    Then the entity properties should reflect the updates

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Create entities with relationships in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an entity with relationships is created in an atomic transaction
    Then the entity and its relationships should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Support different entity types in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When different types of entities are created in an atomic transaction
    Then all entity types should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Test error handling in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an error is triggered within an atomic transaction
    Then the appropriate error should be raised
    And the transaction should be rolled back

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Verify session consistency across multiple atomic blocks
    Given the application database is initialized for <db_type>
    And test entities are defined
    When operations are performed across multiple atomic blocks
    Then session should maintain consistency across atomic blocks

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Create and retrieve entity in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an async atomic transaction
    Then the async entity should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Handle transaction rollback in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new async entity creation fails within an atomic transaction
    Then no async entity should exist in the database
    And the async database session should remain usable

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Update entities in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    And an async entity exists in the database
    When the entity is updated within an async atomic transaction
    Then the async entity properties should reflect the updates

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Support different entity types in async atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When different types of entities are created in an async atomic transaction
    Then all async entity types should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Test error handling in async atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an error is triggered within an async atomic transaction
    Then the appropriate error should be raised
    And the async transaction should be rolled back

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Create multiple entities in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When multiple entities are created in an async atomic transaction
    Then all async entities should be retrievable

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Create and manage complex entity relationships asynchronously
    Given the application database is initialized for <db_type>
    And test entities are defined
    When complex async operations are performed in a transaction
    Then all related entities should be accessible

    Examples:
      | db_type |
      | sqlite  |

  @unit
  Scenario Outline: SQLAlchemy session manager callables stay inspectable at runtime
    When I inspect callables of the <db_type> SQLAlchemy session manager module
    Then all session manager callable signatures resolve without NameError

    Examples:
      | db_type |
      | sqlite  |

  @unit
  Scenario Outline: Sync SQLAlchemy session manager modules do not load the asyncio extension
    When I import the <db_type> SQLAlchemy session manager module in a fresh interpreter
    Then sqlalchemy.ext.asyncio should not be loaded

    Examples:
      | db_type |
      | sqlite  |

  @unit
  Scenario Outline: SQLite adapters accept either driver and in-memory databases
    When a <mode> SQLite adapter runs a query with driver "<driver>" on database "<database>"
    Then the SQLite query should return 1

    Examples:
      | mode  | driver           | database |
      | sync  | sqlite           | :memory: |
      | sync  | sqlite+aiosqlite | :memory: |
      | sync  | sqlite+aiosqlite | file     |
      | async | sqlite           | :memory: |
      | async | sqlite           | file     |
      | async | sqlite+aiosqlite | :memory: |

  @unit
  Scenario Outline: Cancellation and interpreter exit pass through the atomic block unchanged
    Given a fake <mode> session behind the atomic decorator
    When the atomic function raises <exception>
    Then <exception> should propagate through the atomic block unchanged
    And the fake session should have been rolled back and closed

    Examples:
      | mode  | exception         |
      | sync  | KeyboardInterrupt |
      | sync  | SystemExit        |
      | async | CancelledError    |

  @unit
  Scenario Outline: A failing rollback does not hide the original error
    Given a fake <mode> session behind the atomic decorator
    And the fake session fails to roll back
    When the atomic function raises ValueError
    Then an InternalError chained from ValueError should be raised
    And the fake session should have been closed

    Examples:
      | mode  |
      | sync  |
      | async |

  @async
  Scenario Outline: Async atomic blocks leave no session behind in the registry
    Given the application database is initialized for <db_type>
    When 20 async atomic blocks run in separate tasks on <db_type>
    Then the async session registry should be empty

    Examples:
      | db_type |
      | sqlite  |

  @unit
  Scenario Outline: Driver error codes map to specific database errors
    When a <kind> error with driver code <code> is handled by the atomic decorator
    Then the atomic decorator should raise <expected>

    Examples:
      | kind        | code  | expected                   |
      | operational | 1213  | DatabaseDeadlockError      |
      | operational | 1205  | DatabaseTimeoutError       |
      | operational | 40001 | DatabaseSerializationError |
      | operational | 40P01 | DatabaseDeadlockError      |
      | operational | 2003  | DatabaseConnectionError    |
      | integrity   | 1062  | DatabaseConstraintError    |
      | integrity   | 1451  | DatabaseConstraintError    |
      | integrity   | 23505 | DatabaseConstraintError    |
      | integrity   | 1048  | DatabaseIntegrityError     |

  @needs-otel-collector
  Scenario Outline: SQLAlchemy queries emit database spans
    Given adapter spans are exported to the collector
    When I run a query through the <db_type> SQLAlchemy adapter
    Then the collector should have a database span for "<system>" containing statement "span_probe"

    Examples:
      | db_type | system |
      | sqlite  | sqlite |

  @async @needs-otel-collector
  Scenario Outline: Async SQLAlchemy queries emit database spans
    Given adapter spans are exported to the collector
    When I run a query through the <db_type> SQLAlchemy adapter asynchronously
    Then the collector should have a database span for "<system>" containing statement "span_probe"

    Examples:
      | db_type | system |
      | sqlite  | sqlite |

  Scenario Outline: Search returns the total count across pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-total"
    When I search page <page> of size 10 for entities with description prefix "search-total"
    Then the search should return <rows> rows and a total of 25

    Examples:
      | db_type | page | rows |
      | sqlite  | 1    | 10   |
      | sqlite  | 3    | 5    |

  Scenario Outline: A first page that is not full skips the count query
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-short"
    When I search page 1 of size 50 for entities with description prefix "search-short"
    Then the search should return 25 rows and a total of 25
    And 0 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: A full page runs one count query
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-full"
    When I search page 1 of size 10 for entities with description prefix "search-full"
    Then the search should return 10 rows and a total of 25
    And 1 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The total stays exact when it is below the count threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-below"
    When I search page 1 of size 10 for entities with description prefix "search-below" and count threshold 100
    Then the search should return 10 rows and a total of 25

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The total is above the count threshold when there are more rows than the threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-above"
    When I search page 1 of size 10 for entities with description prefix "search-above" and count threshold 10
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Every page counts when the count cache is disabled
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-nocache"
    When I search page 1 of size 10 for entities with description prefix "search-nocache"
    And I search page 2 of size 10 for entities with description prefix "search-nocache"
    Then the search should return 10 rows and a total of 25
    And 2 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The count cache reuses the total for later pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-cache"
    And the search count cache is enabled with a TTL of 60 seconds
    When I search page 1 of size 10 for entities with description prefix "search-cache"
    And I search page 2 of size 10 for entities with description prefix "search-cache"
    And I search page 3 of size 10 for entities with description prefix "search-cache"
    Then the search should return 5 rows and a total of 25
    And 1 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The count cache counts again after its TTL expires
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-expire"
    And the search count cache is enabled with a TTL of 1 seconds
    When I search page 1 of size 10 for entities with description prefix "search-expire"
    And the cached search total expires
    And I search page 2 of size 10 for entities with description prefix "search-expire"
    Then 2 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The configured count threshold applies when the search sets none
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-config"
    And the search count threshold config is 10
    When I search page 1 of size 10 for entities with description prefix "search-config"
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Async search returns the total count across pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-total"
    When I async search page 3 of size 10 for entities with description prefix "async-search-total"
    Then the search should return 5 rows and a total of 25

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Async search skips the count query on a short first page
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-short"
    When I async search page 1 of size 50 for entities with description prefix "async-search-short"
    Then the search should return 25 rows and a total of 25
    And 0 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: Async search is above the count threshold when there are more rows than the threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-above"
    When I async search page 1 of size 10 for entities with description prefix "async-search-above" and count threshold 10
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: The async count cache reuses the total for later pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-cache"
    And the search count cache is enabled with a TTL of 60 seconds
    When I async search page 1 of size 10 for entities with description prefix "async-search-cache"
    And I async search page 2 of size 10 for entities with description prefix "async-search-cache"
    Then the search should return 10 rows and a total of 25
    And 1 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: A search with its own limit totals only the limited rows
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-limit"
    When I search page 1 of size 3 for a query limited to 7 entities with description prefix "search-limit"
    Then the search should return 3 rows and a total of 7

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: A total equal to the count threshold is exact
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-edge"
    When I search page 1 of size 10 for entities with description prefix "search-edge" and count threshold 25
    Then the search should return 10 rows and a total of 25
    And 0 EXPLAIN estimates should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: The count cache keeps the totals of different searches apart
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 5 searchable entities exist with description prefix "cache-five"
    And 12 searchable entities exist with description prefix "cache-twelve"
    And the search count cache is enabled with a TTL of 60 seconds
    When I search page 1 of size 3 for entities with description prefix "cache-five"
    And I search page 1 of size 3 for entities with description prefix "cache-twelve"
    Then the search should return 3 rows and a total of 12
    And 2 COUNT queries should have run
    When I search page 2 of size 3 for entities with description prefix "cache-five"
    Then the search should return 2 rows and a total of 5
    And 2 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  @async
  Scenario Outline: The async count cache counts again after its TTL expires
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-expire"
    And the search count cache is enabled with a TTL of 1 seconds
    When I async search page 1 of size 10 for entities with description prefix "async-search-expire"
    And the cached search total expires
    And I async search page 2 of size 10 for entities with description prefix "async-search-expire"
    Then 2 COUNT queries should have run

    Examples:
      | db_type |
      | sqlite  |

  Scenario Outline: Search filters match the expected entities
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: apple,banana,cherry,NULL
    When I filter the descriptions with <operation> and value "<value>"
    Then the filter should match <count> entities

    Examples:
      | db_type | operation             | value        | count |
      | sqlite  | EQUAL                 | apple        | 1     |
      | sqlite  | NOT_EQUAL             | apple        | 2     |
      | sqlite  | LESS_THAN             | banana       | 1     |
      | sqlite  | GREATER_THAN_OR_EQUAL | banana       | 2     |
      | sqlite  | LIKE                  | an           | 1     |
      | sqlite  | ILIKE                 | AN           | 1     |
      | sqlite  | STARTS_WITH           | ch           | 1     |
      | sqlite  | ENDS_WITH             | ana          | 1     |
      | sqlite  | IS_NULL               | NULL         | 1     |
      | sqlite  | IS_NOT_NULL           | x            | 3     |
      | sqlite  | IN_LIST               | apple,cherry | 2     |
      | sqlite  | NOT_IN_LIST           | apple        | 2     |
      | sqlite  | EQUAL                 | NULL         | 4     |

  Scenario Outline: A list filter rejects a value that is not a list
    Given the application database is initialized for sqlite
    And test entities are defined
    When I filter the descriptions with <operation> and the non-list value "apple"
    Then the filter should be rejected with an InvalidArgumentError

    Examples:
      | operation   |
      | IN_LIST     |
      | NOT_IN_LIST |

  Scenario Outline: A <shape> search totals the distinct rows, not the entities
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: alpha,alpha,beta,beta,beta,gamma,delta
    When I search page 1 of size 2 for the <shape> descriptions
    Then the search should return 2 rows and a total of 4
    When I search page 2 of size 2 for the <shape> descriptions
    Then the search should return 2 rows and a total of 4

    Examples:
      | db_type | shape    |
      | sqlite  | distinct |
      | sqlite  | grouped  |

  Scenario Outline: A <shape> search above the count threshold still totals the distinct rows
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: alpha,alpha,beta,beta,beta,gamma,delta
    When I search page 1 of size 2 for the <shape> descriptions and count threshold 2
    Then the search should return 2 rows and a total of at least 3

    Examples:
      | db_type | shape    |
      | sqlite  | distinct |

  Scenario Outline: Entities are fetched by UUID through the <mode> adapter
    Given the application database is initialized for <db_type>
    And test entities are defined
    When 2 entities are created through the <mode> adapter
    Then every created entity should be fetched by UUID through the <mode> adapter

    Examples: Sync adapter
      | db_type | mode |
      | sqlite  | sync |

    @async
    Examples: Async adapter
      | db_type | mode  |
      | sqlite  | async |

  Scenario Outline: An unknown UUID returns no entity through the <mode> adapter
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a random UUID is fetched through the <mode> adapter
    Then no entity should be returned

    Examples: Sync adapter
      | db_type | mode |
      | sqlite  | sync |

    @async
    Examples: Async adapter
      | db_type | mode  |
      | sqlite  | async |

  Scenario Outline: Entities deleted through the <mode> adapter by <method> are gone
    Given the application database is initialized for <db_type>
    And test entities are defined
    When 3 entities are created through the <mode> adapter
    And the created entities are deleted through the <mode> adapter by <method>
    Then no created entity should be fetched by UUID through the <mode> adapter

    Examples: Sync adapter
      | db_type | mode | method |
      | sqlite  | sync | delete |
      | sqlite  | sync | bulk   |

    @async
    Examples: Async adapter
      | db_type | mode  | method |
      | sqlite  | async | delete |
      | sqlite  | async | bulk   |

  Scenario Outline: A failing <statement_kind> through the <mode> adapter raises a database query error
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a statement on a missing table is run as <statement_kind> through the <mode> adapter
    Then a DatabaseQueryError should be raised
    And the <mode> adapter should remain usable

    Examples: Sync adapter
      | db_type | mode | statement_kind |
      | sqlite  | sync | execute        |
      | sqlite  | sync | scalars        |

    @async
    Examples: Async adapter
      | db_type | mode  | statement_kind |
      | sqlite  | async | execute        |
      | sqlite  | async | scalars        |

  Scenario Outline: The <kind> driver applies the busy timeout from the configuration
    When I read busy_timeout from a <kind> sqlite connection configured with TIMEOUT <value>
    Then the session setting should be <expected>

    Examples: Busy timeout
      | kind  | value | expected |
      | sync  | 2.5   | 2500     |
      | async | 2.5   | 2500     |
