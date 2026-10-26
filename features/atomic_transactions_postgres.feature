@needs-postgres
Feature: SQLAlchemy Atomic Transactions on PostgreSQL

  Scenario Outline: Create and retrieve entity in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an atomic transaction
    Then the entity should be retrievable

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Handle transaction rollback on exception
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity creation fails within an atomic transaction
    Then no entity should exist in the database
    And the database session should remain usable

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Support nested atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When nested atomic transactions are executed
    Then operations from successful nested transactions should be visible within outer transaction
    And operations from failed nested transactions should be rolled back

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Update entities in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    And an entity exists in the database
    When the entity is updated within an atomic transaction
    Then the entity properties should reflect the updates

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Create entities with relationships in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an entity with relationships is created in an atomic transaction
    Then the entity and its relationships should be retrievable

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Support different entity types in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When different types of entities are created in an atomic transaction
    Then all entity types should be retrievable

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Test error handling in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an error is triggered within an atomic transaction
    Then the appropriate error should be raised
    And the transaction should be rolled back

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Verify session consistency across multiple atomic blocks
    Given the application database is initialized for <db_type>
    And test entities are defined
    When operations are performed across multiple atomic blocks
    Then session should maintain consistency across atomic blocks

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Create and retrieve entity in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an async atomic transaction
    Then the async entity should be retrievable

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Handle transaction rollback in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new async entity creation fails within an atomic transaction
    Then no async entity should exist in the database
    And the async database session should remain usable

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Update entities in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    And an async entity exists in the database
    When the entity is updated within an async atomic transaction
    Then the async entity properties should reflect the updates

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Support different entity types in async atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When different types of entities are created in an async atomic transaction
    Then all async entity types should be retrievable

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Test error handling in async atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an error is triggered within an async atomic transaction
    Then the appropriate error should be raised
    And the async transaction should be rolled back

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Create multiple entities in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When multiple entities are created in an async atomic transaction
    Then all async entities should be retrievable

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Create and manage complex entity relationships asynchronously
    Given the application database is initialized for <db_type>
    And test entities are defined
    When complex async operations are performed in a transaction
    Then all related entities should be accessible

    Examples:
      | db_type  |
      | postgres |

  @unit
  Scenario Outline: SQLAlchemy session manager callables stay inspectable at runtime
    When I inspect callables of the <db_type> SQLAlchemy session manager module
    Then all session manager callable signatures resolve without NameError

    Examples:
      | db_type  |
      | postgres |

  @unit
  Scenario Outline: Sync SQLAlchemy session manager modules do not load the asyncio extension
    When I import the <db_type> SQLAlchemy session manager module in a fresh interpreter
    Then sqlalchemy.ext.asyncio should not be loaded

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: The atomic marker is cleared once the outermost block exits
    Given the application database is initialized for <db_type>
    When a nested atomic block succeeds on <db_type>
    Then the atomic marker should be set in both blocks and cleared only after the outermost one

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: The atomic marker is cleared once the outermost async block exits
    Given the application database is initialized for <db_type>
    When a nested async atomic block succeeds on <db_type>
    Then the atomic marker should be set in both blocks and cleared only after the outermost one

    Examples:
      | db_type  |
      | postgres |

  @needs-otel-collector
  Scenario Outline: SQLAlchemy queries emit database spans
    Given adapter spans are exported to the collector
    When I run a query through the <db_type> SQLAlchemy adapter
    Then the collector should have a database span for "<system>" containing statement "span_probe"

    Examples:
      | db_type  | system     |
      | postgres | postgresql |

  @async @needs-otel-collector
  Scenario Outline: Async SQLAlchemy queries emit database spans
    Given adapter spans are exported to the collector
    When I run a query through the <db_type> SQLAlchemy adapter asynchronously
    Then the collector should have a database span for "<system>" containing statement "span_probe"

    Examples:
      | db_type  | system     |
      | postgres | postgresql |

  Scenario Outline: Search returns the total count across pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-total"
    When I search page <page> of size 10 for entities with description prefix "search-total"
    Then the search should return <rows> rows and a total of 25

    Examples:
      | db_type  | page | rows |
      | postgres | 1    | 10   |
      | postgres | 3    | 5    |
      | postgres | 4    | 0    |

  Scenario Outline: A first page that is not full skips the count query
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-short"
    When I search page 1 of size 50 for entities with description prefix "search-short"
    Then the search should return 25 rows and a total of 25
    And 0 COUNT queries should have run

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: A full page runs one count query
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-full"
    When I search page 1 of size 10 for entities with description prefix "search-full"
    Then the search should return 10 rows and a total of 25
    And 1 COUNT queries should have run

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: The total stays exact when it is below the count threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-below"
    When I search page 1 of size 10 for entities with description prefix "search-below" and count threshold 100
    Then the search should return 10 rows and a total of 25

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: The total is above the count threshold when there are more rows than the threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-above"
    When I search page 1 of size 10 for entities with description prefix "search-above" and count threshold 10
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: Every page counts when the count cache is disabled
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-nocache"
    When I search page 1 of size 10 for entities with description prefix "search-nocache"
    And I search page 2 of size 10 for entities with description prefix "search-nocache"
    Then the search should return 10 rows and a total of 25
    And 2 COUNT queries should have run

    Examples:
      | db_type  |
      | postgres |

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
      | db_type  |
      | postgres |

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
      | db_type  |
      | postgres |

  Scenario: The search output DTO reports whether the total is above the count threshold
    Given the application database is initialized for postgres
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-output"
    And the search count threshold config is 10
    And the global count threshold is 10
    When I search page 1 of size 10 for entities with description prefix "search-output"
    Then the search output DTO reports the total as estimated
    And the exact search output DTO reports the total as exact
    Given the global count threshold is 30
    When I search page 1 of size 10 for entities with description prefix "search-output"
    Then the search output DTO reports the total as exact
    Given the global count threshold is not set
    When I search page 1 of size 10 for entities with description prefix "search-output"
    Then the search output DTO reports the total as exact

  Scenario Outline: The configured count threshold applies when the search sets none
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-config"
    And the search count threshold config is 10
    When I search page 1 of size 10 for entities with description prefix "search-config"
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Async search returns the total count across pages
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-total"
    When I async search page 3 of size 10 for entities with description prefix "async-search-total"
    Then the search should return 5 rows and a total of 25

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Async search skips the count query on a short first page
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-short"
    When I async search page 1 of size 50 for entities with description prefix "async-search-short"
    Then the search should return 25 rows and a total of 25
    And 0 COUNT queries should have run

    Examples:
      | db_type  |
      | postgres |

  @async
  Scenario Outline: Async search is above the count threshold when there are more rows than the threshold
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 async searchable entities exist with description prefix "async-search-above"
    When I async search page 1 of size 10 for entities with description prefix "async-search-above" and count threshold 10
    Then the search should return 10 rows and a total of at least 11

    Examples:
      | db_type  |
      | postgres |

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
      | db_type  |
      | postgres |

  Scenario Outline: A search with its own limit totals only the limited rows
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-limit"
    When I search page 1 of size 3 for a query limited to 7 entities with description prefix "search-limit"
    Then the search should return 3 rows and a total of 7

    Examples:
      | db_type  |
      | postgres |

  Scenario Outline: A total equal to the count threshold is exact
    Given the application database is initialized for <db_type>
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-edge"
    When I search page 1 of size 10 for entities with description prefix "search-edge" and count threshold 25
    Then the search should return 10 rows and a total of 25
    And 0 EXPLAIN estimates should have run

    Examples:
      | db_type  |
      | postgres |

  Scenario: The estimate above the count threshold is close to the real total on PostgreSQL
    Given the application database is initialized for postgres
    And test entities are defined
    And 25 searchable entities exist with description prefix "search-estimate"
    And the table statistics are refreshed
    When I search page 1 of size 10 for entities with description prefix "search-estimate" and count threshold 10
    Then the search should return 10 rows and a total of 25
    And 1 EXPLAIN estimates should have run

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
      | db_type  |
      | postgres |

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
      | db_type  |
      | postgres |

  Scenario Outline: Search filters match the expected entities
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: apple,banana,cherry,NULL
    When I filter the descriptions with <operation> and value "<value>"
    Then the filter should match <count> entities

    Examples:
      | db_type  | operation             | value        | count |
      | postgres | EQUAL                 | apple        | 1     |
      | postgres | NOT_EQUAL             | apple        | 2     |
      | postgres | LESS_THAN             | banana       | 1     |
      | postgres | LESS_THAN_OR_EQUAL    | banana       | 2     |
      | postgres | GREATER_THAN          | banana       | 1     |
      | postgres | GREATER_THAN_OR_EQUAL | banana       | 2     |
      | postgres | LIKE                  | an           | 1     |
      | postgres | ILIKE                 | AN           | 1     |
      | postgres | STARTS_WITH           | ch           | 1     |
      | postgres | ENDS_WITH             | ana          | 1     |
      | postgres | CONTAINS              | rr           | 1     |
      | postgres | IS_NULL               | NULL         | 1     |
      | postgres | IS_NOT_NULL           | x            | 3     |
      | postgres | IN_LIST               | apple,cherry | 2     |
      | postgres | NOT_IN_LIST           | apple        | 2     |
      | postgres | EQUAL                 | NULL         | 4     |

  Scenario Outline: A <shape> search totals the distinct rows, not the entities
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: alpha,alpha,beta,beta,beta,gamma,delta
    When I search page 1 of size 2 for the <shape> descriptions
    Then the search should return 2 rows and a total of 4
    When I search page 2 of size 2 for the <shape> descriptions
    Then the search should return 2 rows and a total of 4

    Examples:
      | db_type  | shape    |
      | postgres | distinct |
      | postgres | grouped  |

  Scenario Outline: A <shape> search above the count threshold still totals the distinct rows
    Given the application database is initialized for <db_type>
    And test entities are defined
    And entities exist with these descriptions: alpha,alpha,beta,beta,beta,gamma,delta
    When I search page 1 of size 2 for the <shape> descriptions and count threshold 2
    Then the search should return 2 rows and a total of at least 3

    Examples:
      | db_type  | shape    |
      | postgres | distinct |
      | postgres | grouped  |

  Scenario Outline: Entities are fetched by UUID through the <mode> adapter
    Given the application database is initialized for <db_type>
    And test entities are defined
    When 2 entities are created through the <mode> adapter
    Then every created entity should be fetched by UUID through the <mode> adapter

    Examples: Sync adapter
      | db_type  | mode |
      | postgres | sync |

    @async
    Examples: Async adapter
      | db_type  | mode  |
      | postgres | async |

  Scenario Outline: An unknown UUID returns no entity through the <mode> adapter
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a random UUID is fetched through the <mode> adapter
    Then no entity should be returned

    Examples: Sync adapter
      | db_type  | mode |
      | postgres | sync |

    @async
    Examples: Async adapter
      | db_type  | mode  |
      | postgres | async |

  Scenario Outline: Entities deleted through the <mode> adapter by <method> are gone
    Given the application database is initialized for <db_type>
    And test entities are defined
    When 3 entities are created through the <mode> adapter
    And the created entities are deleted through the <mode> adapter by <method>
    Then no created entity should be fetched by UUID through the <mode> adapter

    Examples: Sync adapter
      | db_type  | mode | method |
      | postgres | sync | delete |
      | postgres | sync | bulk   |

    @async
    Examples: Async adapter
      | db_type  | mode  | method |
      | postgres | async | delete |
      | postgres | async | bulk   |

  Scenario Outline: A failing <statement_kind> through the <mode> adapter raises a database query error
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a statement on a missing table is run as <statement_kind> through the <mode> adapter
    Then a DatabaseQueryError should be raised
    And the <mode> adapter should remain usable

    Examples: Sync adapter
      | db_type  | mode | statement_kind |
      | postgres | sync | execute        |
      | postgres | sync | scalars        |

    @async
    Examples: Async adapter
      | db_type  | mode  | statement_kind |
      | postgres | async | execute        |
      | postgres | async | scalars        |
