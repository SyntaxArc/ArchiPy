@needs-postgres
Feature: SQLAlchemy Atomic Transactions

  Background:
    Given the application database is initialized
    And test entities are defined

  Scenario: Create and retrieve entity in atomic transaction
    When a new entity is created in an atomic transaction
    Then the entity should be retrievable

  Scenario: Handle transaction rollback on exception
    When a new entity creation fails within an atomic transaction
    Then no entity should exist in the database
    And the database session should remain usable

  Scenario: Support nested atomic transactions
    When nested atomic transactions are executed
    Then operations from successful nested transactions should not be committed
    And operations from failed nested transactions should be rolled back

  Scenario: Update entities in atomic transaction
    Given an entity exists in the database
    When the entity is updated within an atomic transaction
    Then the entity properties should reflect the updates

  Scenario: Create entities with relationships in atomic transaction
    When an entity with relationships is created in an atomic transaction
    Then the entity and its relationships should be retrievable

  Scenario: Support different entity types in atomic transactions
    When different types of entities are created in an atomic transaction
    Then all entity types should be retrievable

  Scenario: Test error handling in atomic transactions
    When an error is triggered within an atomic transaction
    Then the appropriate error should be raised
    And the transaction should be rolled back

  Scenario: Verify session consistency across multiple atomic blocks
    When operations are performed across multiple atomic blocks
    Then session should maintain consistency across atomic blocks

  @async
  Scenario: Create and retrieve entity in async atomic transaction
    When a new entity is created in an async atomic transaction
    Then the async entity should be retrievable

  @async
  Scenario: Handle transaction rollback in async atomic transaction
    When a new async entity creation fails within an atomic transaction
    Then no async entity should exist in the database
    And the async database session should remain usable

  @async
  Scenario: Create multiple entities in async atomic transaction
    When multiple entities are created in an async atomic transaction
    Then all async entities should be retrievable

  @async
  Scenario: Create and manage complex entity relationships asynchronously
    When complex async operations are performed in a transaction
    Then all related entities should be accessible
