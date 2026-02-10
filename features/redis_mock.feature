@needs-redis
Feature: Redis Testing
  As a developer
  I want to test Redis operations with both mocks and real containers
  So that I can ensure compatibility and reliability across different environments

  Background:
    Given test entities are defined

  Scenario Outline: Store and retrieve a simple key-value pair
    Given a configured <adapter_type>
    When I store the key "user-id" with value "12345" in <adapter_type>
    Then the sync store operation should succeed
    When I retrieve the value for key "user-id" from <adapter_type>
    Then the sync retrieved value should be "12345"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  Scenario Outline: Remove a key
    Given a configured <adapter_type>
    When I store the key "session-token" with value "abcde" in <adapter_type>
    Then the sync store operation should succeed
    When I remove the key "session-token" from <adapter_type>
    Then the sync remove operation should delete one key
    When I check if "session-token" exists in <adapter_type>
    Then the sync key should not exist

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  Scenario Outline: Manage a list of items
    Given a configured <adapter_type>
    When I add "apple, banana, orange" to the list "fruits" in <adapter_type>
    Then the sync list "fruits" should have 3 items
    When I fetch all items from the list "fruits" in <adapter_type>
    Then the sync list "fruits" should contain "apple, banana, orange"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  Scenario Outline: Handle a hash structure
    Given a configured <adapter_type>
    When I assign "name" to "Alice" in the hash "profile" in <adapter_type>
    Then the sync hash assignment should succeed
    When I retrieve the "name" field from the hash "profile" in <adapter_type>
    Then the sync retrieved field value should be "Alice"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  Scenario Outline: Manage a set of colors
    Given a configured <adapter_type>
    When I add "red, blue, green" to the set "colors" in <adapter_type>
    Then the sync set "colors" should have 3 members
    When I fetch all members from the set "colors" in <adapter_type>
    Then the sync set "colors" should contain "red, blue, green"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  @async
  Scenario Outline: Store and retrieve a key-value pair asynchronously
    Given a configured async <adapter_type>
    When I store the key "order-id" with value "67890" in async <adapter_type>
    Then the async store operation should succeed
    When I retrieve the value for key "order-id" from async <adapter_type>
    Then the async retrieved value should be "67890"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  @async
  Scenario Outline: Remove a key asynchronously
    Given a configured async <adapter_type>
    When I store the key "cache-key" with value "xyz" in async <adapter_type>
    Then the async store operation should succeed
    When I remove the key "cache-key" from async <adapter_type>
    Then the async remove operation should delete one key
    When I check if "cache-key" exists in async <adapter_type>
    Then the async key should not exist

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  @async
  Scenario Outline: Manage a list of tasks asynchronously
    Given a configured async <adapter_type>
    When I add "task1, task2, task3" to the list "tasks" in async <adapter_type>
    Then the async list "tasks" should have 3 items
    When I fetch all items from the list "tasks" in async <adapter_type>
    Then the async list "tasks" should contain "task1, task2, task3"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  @async
  Scenario Outline: Handle a hash structure asynchronously
    Given a configured async <adapter_type>
    When I assign "email" to "bob@example.com" in the hash "contact" in async <adapter_type>
    Then the async hash assignment should succeed
    When I retrieve the "email" field from the hash "contact" in async <adapter_type>
    Then the async retrieved field value should be "bob@example.com"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |

  @async
  Scenario Outline: Manage a set of tags asynchronously
    Given a configured async <adapter_type>
    When I add "tag1, tag2, tag3" to the set "tags" in async <adapter_type>
    Then the async set "tags" should have 3 members
    When I fetch all members from the set "tags" in async <adapter_type>
    Then the async set "tags" should contain "tag1, tag2, tag3"

    Examples: Adapter Types
      | adapter_type    |
      | mock            |
      | container       |
