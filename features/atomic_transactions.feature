@needs-postgres
Feature: SQLAlchemy Atomic Transactions

  Scenario Outline: Create and retrieve entity in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an atomic transaction
    Then the entity should be retrievable

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Handle transaction rollback on exception
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity creation fails within an atomic transaction
    Then no entity should exist in the database
    And the database session should remain usable

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Support nested atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When nested atomic transactions are executed
    Then operations from successful nested transactions should be visible within outer transaction
    And operations from failed nested transactions should be rolled back

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Update entities in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    And an entity exists in the database
    When the entity is updated within an atomic transaction
    Then the entity properties should reflect the updates

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Create entities with relationships in atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an entity with relationships is created in an atomic transaction
    Then the entity and its relationships should be retrievable

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Support different entity types in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When different types of entities are created in an atomic transaction
    Then all entity types should be retrievable

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Test error handling in atomic transactions
    Given the application database is initialized for <db_type>
    And test entities are defined
    When an error is triggered within an atomic transaction
    Then the appropriate error should be raised
    And the transaction should be rolled back

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  Scenario Outline: Verify session consistency across multiple atomic blocks
    Given the application database is initialized for <db_type>
    And test entities are defined
    When operations are performed across multiple atomic blocks
    Then session should maintain consistency across atomic blocks

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  @async
  Scenario Outline: Create and retrieve entity in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When a new entity is created in an async atomic transaction
    Then the async entity should be retrievable

    Examples:
      | db_type |
      | postgres|
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
      | postgres|
      | sqlite  |

  @async
  Scenario Outline: Create multiple entities in async atomic transaction
    Given the application database is initialized for <db_type>
    And test entities are defined
    When multiple entities are created in an async atomic transaction
    Then all async entities should be retrievable

    Examples:
      | db_type |
      | postgres|
      | sqlite  |

  @async
  Scenario Outline: Create and manage complex entity relationships asynchronously
    Given the application database is initialized for <db_type>
    And test entities are defined
    When complex async operations are performed in a transaction
    Then all related entities should be accessible

    Examples:
      | db_type |
      | postgres|
      | sqlite  |
