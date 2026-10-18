Feature: Several SQLAlchemy databases of the same type

  Scenario: The same configuration shares one session manager
    Given two SQLite databases "first" and "second"
    Then the session manager of "first" is the session manager built again from its configuration
    And the session managers of "first" and "second" are different

  Scenario: Adapters with different configurations use their own database
    Given two SQLite databases "first" and "second"
    When an item "a" is added through the adapter of "first"
    Then the database "first" holds 1 items
    And the database "second" holds 0 items

  Scenario: A registry subclass keeps its own session manager
    Given two SQLite databases "first" and "second"
    Then the registry of "first" returns the session manager of "first"
    And the registry of "second" returns the session manager of "second"

  Scenario: The atomic decorator commits on the database of its registry
    Given two SQLite databases "first" and "second"
    When an item "b" is added in an atomic block on "second"
    Then the database "second" holds 1 items
    And the database "first" holds 0 items

  Scenario: The atomic decorator rolls back only the database of its registry
    Given two SQLite databases "first" and "second"
    When an item "c" is added in an atomic block on "first" that fails
    And an item "d" is added in an atomic block on "second"
    Then the database "first" holds 0 items
    And the database "second" holds 1 items

  Scenario: Nested atomic blocks on two databases stay independent
    Given two SQLite databases "first" and "second"
    When an item "e" is added on "first" and "f" on "second" in nested atomic blocks, then the outer block fails
    Then the database "first" holds 0 items
    And the database "second" holds 1 items
